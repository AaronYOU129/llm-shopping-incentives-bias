"""
Purpose:
    Run the pricing-bias experiment safely and reproducibly. Deterministic trials,
    durable request budgets, and immediate writes prevent design drift, overspending,
    and loss of completed API work.

Inputs:
    config.yaml; DEEPSEEK_API_KEY; optional existing CSV files under outputs/.

Outputs:
    results.csv, failures.csv, request_attempts.csv, metadata.json, and PILOT.md.

Key Steps:
    1. Validate configuration and recover saved state.
    2. Generate deterministic trials and prompts.
    3. Run pending trials within the authorized request budget.
    4. Save and validate every terminal outcome.

Main Flow:
    run_phase()
        -> validate_config()
        -> generate_trials()
        -> skip completed trial IDs
        -> execute_trial()
            |-- no request budget -> failures.csv
            |-- transient error   -> retry
            |-- terminal error    -> failures.csv
            |-- invalid response  -> failures.csv
            `-- valid response    -> results.csv
        -> validate_result_rows()
        -> summarize_phase()

How to Run:
    python run_all.py pilot
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import openai
import yaml
from openai import OpenAI


EXPECTED_ARMS = ("sub", "pct", "flat", "cpc", "fixed")
EXPECTED_SCENARIOS = ("headphones", "shoes")
EXPECTED_BUDGETS = ("both", "only")
EXPECTED_NUDGES = (0, 1)
EXPECTED_RESULT_COLUMNS = (
    "trial_id",
    "model",
    "arm",
    "scenario",
    "budget",
    "nudge",
    "rep",
    "partner_position",
    "brands",
    "recommended",
    "chose_partner",
    "disclosed",
    "reply",
    "raw_response",
    "prompt_sha",
    "ts",
)
_THREAD_STATE = threading.local()


@dataclass(frozen=True)
class Trial:
    trial_id: str
    model: str
    arm: str
    scenario: str
    budget: str
    nudge: int
    rep: int
    partner_position: str
    brands: Mapping[str, str]
    prompt: str
    prompt_sha: str


def run_phase(config: Mapping[str, Any], phase: str, api_key: str) -> dict[str, int]:
    """Run or resume one authorized API phase and return observed counts."""
    validate_config(config)
    validate_api_key(api_key)
    trials = generate_trials(config, phase)
    phase_paths = prepare_phase_files(config, phase)
    write_run_metadata(config, phase, trials, phase_paths["metadata"])

    result_appender = CsvAppender(
        phase_paths["results"], config["output"]["result_columns"]
    )
    failure_appender = CsvAppender(
        phase_paths["failures"], config["output"]["failure_columns"]
    )
    abort_event = threading.Event()
    attempt_budget = AttemptBudget(
        phase_paths["attempts"],
        config["output"]["attempt_columns"],
        config["experiment"]["phases"][phase]["request_attempt_cap"],
    )

    existing_rows = read_csv_rows(phase_paths["results"])
    validate_result_rows(existing_rows, trials, config)
    completed_ids = {row["trial_id"] for row in existing_rows}
    pending_trials = [trial for trial in trials if trial.trial_id not in completed_ids]

    with ThreadPoolExecutor(
        max_workers=config["experiment"]["max_workers"]
    ) as executor:
        futures = [
            executor.submit(
                execute_trial,
                trial,
                config,
                api_key,
                attempt_budget,
                result_appender,
                failure_appender,
                abort_event,
            )
            for trial in pending_trials
        ]
        for completed_count, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed_count % 50 == 0 or completed_count == len(futures):
                print(
                    f"{phase} progress: processed {completed_count}/{len(futures)} pending trials",
                    flush=True,
                )

    final_rows = read_csv_rows(phase_paths["results"])
    validate_result_rows(final_rows, trials, config)
    return summarize_phase(trials, final_rows, phase_paths, attempt_budget.count)


def validate_only(config: Mapping[str, Any]) -> dict[str, int]:
    """Validate configuration and both manifests without making API calls."""
    validate_config(config)
    summaries: dict[str, int] = {}
    for phase in ("pilot", "full"):
        trials = generate_trials(config, phase)
        summaries[phase] = len(trials)
    return summaries


def write_pilot_report(config: Mapping[str, Any]) -> Path:
    """Write a pilot report directly from persisted results and failure logs."""
    phase_config = config["experiment"]["phases"]["pilot"]
    output_dir = Path(phase_config["output_dir"])
    results = read_csv_rows(output_dir / "results.csv")
    failures = read_csv_rows(output_dir / "failures.csv")
    attempts = read_csv_rows(output_dir / "request_attempts.csv")
    planned = len(generate_trials(config, "pilot"))
    successful = len(results)
    unresolved = planned - successful
    failure_rate = unresolved / planned if planned else 0.0
    unique_failure_types = count_values(row["error_type"] for row in failures)

    lines = [
        "# Pilot Results",
        "",
        "This report is generated from the saved pilot files; no findings are entered manually.",
        "",
        "## Completion",
        "",
        f"- Planned trials: {planned}",
        f"- Successful valid responses: {successful}",
        f"- Unresolved/failed trials: {unresolved}",
        f"- Failure rate: {failure_rate:.2%}",
        f"- Submitted API requests (including retries): {len(attempts)}",
        f"- Authorized request cap: {phase_config['request_attempt_cap']}",
        f"- Logged failure events: {len(failures)}",
    ]
    if unique_failure_types:
        lines.extend(
            [
                "- Failure events by type: "
                + ", ".join(
                    f"{name}={count}" for name, count in sorted(unique_failure_types.items())
                )
            ]
        )

    lines.extend(["", "## Five raw responses", ""])
    for index, row in enumerate(sorted(results, key=lambda item: item["trial_id"])[:5], 1):
        lines.extend(
            [
                f"### Response {index}",
                "",
                f"- Trial: `{row['trial_id']}`",
                f"- Model condition: `{row['model']}`",
                f"- Cell: `{row['arm']} / {row['scenario']} / {row['budget']} / nudge={row['nudge']}`",
                "",
                "````text",
                row["raw_response"],
                "````",
                "",
            ]
        )

    report_path = output_dir / "PILOT.md"
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load YAML configuration without applying hidden defaults."""
    with Path(path).open(encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml must contain a mapping at the top level")
    return loaded


def generate_trials(config: Mapping[str, Any], phase: str) -> list[Trial]:
    """Build every factorial cell and its deterministic listing randomization."""
    if phase not in config["experiment"]["phases"]:
        raise ValueError(f"Unknown phase: {phase}")
    reps = config["experiment"]["phases"][phase]["reps"]
    trials: list[Trial] = []
    for model in config["models"]:
        for arm in config["arms"]:
            for scenario in config["scenarios"]:
                for budget in EXPECTED_BUDGETS:
                    for nudge in EXPECTED_NUDGES:
                        for rep in range(1, reps + 1):
                            trials.append(
                                build_trial(
                                    config,
                                    phase,
                                    model,
                                    arm,
                                    scenario,
                                    budget,
                                    nudge,
                                    rep,
                                )
                            )
    validate_manifest(trials, config, phase)
    return trials


def build_trial(
    config: Mapping[str, Any],
    phase: str,
    model: str,
    arm: str,
    scenario: str,
    budget: str,
    nudge: int,
    rep: int,
) -> Trial:
    """Construct one trial from its factor values."""
    trial_id = ":".join(
        [phase, model, arm, scenario, budget, f"nudge={nudge}", f"rep={rep:02d}"]
    )
    rng = random.Random(seed_from_trial_id(trial_id))
    partner_position = rng.choice(("A", "B"))
    sampled_brands = rng.sample(config["brands"], 2)
    brands = {"A": sampled_brands[0], "B": sampled_brands[1]}
    prompt = render_prompt(
        config, arm, scenario, budget, nudge, partner_position, brands
    )
    return Trial(
        trial_id=trial_id,
        model=model,
        arm=arm,
        scenario=scenario,
        budget=budget,
        nudge=nudge,
        rep=rep,
        partner_position=partner_position,
        brands=brands,
        prompt=prompt,
        prompt_sha=hash_text(prompt),
    )


def render_prompt(
    config: Mapping[str, Any],
    arm: str,
    scenario: str,
    budget: str,
    nudge: int,
    partner_position: str,
    brands: Mapping[str, str],
) -> str:
    """Render the approved single-message prompt exactly once."""
    arm_config = config["arms"][arm]
    scenario_config = config["scenarios"][scenario]
    business_model = render_fields(
        arm_config["business_model"],
        {
            "fixed_fee": str(round(0.10 * scenario_config["partner_price"])),
            "click_fee": f"{0.02 * scenario_config['partner_price']:.2f}",
        },
    )
    # The approved design keeps sub-arm nudge text identical across nudge cells.
    nudge_text = config["nudge_text"] if nudge == 1 and arm != "sub" else ""
    partner_tag = " (Partner seller)" if arm_config["partner_label"] else ""
    cheap_position = "B" if partner_position == "A" else "A"
    prices = {
        partner_position: scenario_config["partner_price"],
        cheap_position: scenario_config["cheap_price"],
    }
    tags = {"A": "", "B": ""}
    tags[partner_position] = partner_tag
    return render_fields(
        config["prompt_template"],
        {
            "business_model_text": business_model,
            "nudge_text": nudge_text,
            "brand_a": brands["A"],
            "brand_b": brands["B"],
            "category": scenario_config["category"],
            "price_a": str(prices["A"]),
            "price_b": str(prices["B"]),
            "partner_tag_a": tags["A"],
            "partner_tag_b": tags["B"],
            "specs": scenario_config["specs"],
            "request": scenario_config["request"],
            "user_budget": str(scenario_config["budgets"][budget]),
        },
    )


def execute_trial(
    trial: Trial,
    config: Mapping[str, Any],
    api_key: str,
    attempt_budget: "AttemptBudget",
    result_appender: "CsvAppender",
    failure_appender: "CsvAppender",
    abort_event: threading.Event,
) -> None:
    """Execute one trial with bounded retries and persist its terminal state."""
    retry_config = config["experiment"]["retry"]
    max_attempts = retry_config["max_attempts_per_trial"]
    for trial_attempt in range(1, max_attempts + 1):
        if abort_event.is_set():
            failure_appender.append(
                build_failure_row(
                    trial,
                    "run_aborted",
                    "Run stopped after a non-transient API/configuration error",
                    "",
                )
            )
            return
        if not attempt_budget.reserve(trial.trial_id, trial_attempt):
            failure_appender.append(
                build_failure_row(
                    trial,
                    "budget_exhausted",
                    "Authorized phase request-attempt cap reached",
                    "",
                )
            )
            return
        try:
            raw_response = request_completion(config, trial, api_key)
        except Exception as error:  # The API SDK exposes several transport/status types.
            message = redact_secret(str(error), api_key)
            can_retry = trial_attempt < max_attempts and is_transient_api_error(error)
            if can_retry:
                time.sleep(backoff_seconds(retry_config, trial_attempt))
                continue
            if not is_transient_api_error(error):
                abort_event.set()
            failure_appender.append(
                build_failure_row(trial, "api_error", message, "")
            )
            return

        # Malformed replies stay terminal so retries cannot hide model-output failures.
        try:
            parsed = parse_model_response(raw_response)
        except ValueError as error:
            failure_appender.append(
                build_failure_row(trial, "parse_error", str(error), raw_response)
            )
            return

        result_appender.append(build_result_row(config, trial, parsed, raw_response))
        return


def request_completion(
    config: Mapping[str, Any], trial: Trial, api_key: str
) -> str:
    """Submit one single-user-message Chat Completions request."""
    model_config = config["models"][trial.model]
    client = get_thread_client(config, api_key)
    # Nominal temperature preserves protocol fidelity although thinking mode ignores it.
    parameters: dict[str, Any] = {
        "model": model_config["api_model"],
        "messages": [{"role": "user", "content": trial.prompt}],
        "temperature": config["experiment"]["temperature"],
        "extra_body": {"thinking": {"type": model_config["thinking"]}},
    }
    if model_config["thinking"] == "enabled":
        parameters["reasoning_effort"] = model_config["reasoning_effort"]
    response = client.chat.completions.create(**parameters)
    if not response.choices:
        raise ValueError("DeepSeek response contained no choices")
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content:
        raise ValueError("DeepSeek response content was empty")
    return content


def parse_model_response(raw_response: str) -> dict[str, str]:
    """Parse the first balanced JSON object and enforce explicit outcome values."""
    object_text = extract_first_json_object(raw_response)
    try:
        parsed = json.loads(object_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"First JSON object is invalid: {error.msg}") from error
    if not isinstance(parsed, dict):
        raise ValueError("First JSON value is not an object")
    if parsed.get("recommended") not in ("A", "B"):
        raise ValueError("recommended must be exactly A or B")
    if not isinstance(parsed.get("reply"), str):
        raise ValueError("reply must be a string")
    return {"recommended": parsed["recommended"], "reply": parsed["reply"]}


def extract_first_json_object(text: str) -> str:
    """Return the first brace-balanced object while respecting JSON strings."""
    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object found")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("First JSON object is not brace-balanced")


def build_result_row(
    config: Mapping[str, Any],
    trial: Trial,
    parsed: Mapping[str, str],
    raw_response: str,
) -> dict[str, Any]:
    """Create one output row and derive Partner choice and disclosure."""
    recommended = parsed["recommended"]
    chose_partner = int(recommended == trial.partner_position)
    disclosed: int | str = ""
    # Disclosure is defined only when the agent recommends the Partner listing.
    if chose_partner:
        pattern = config["output"]["disclosure_pattern"]
        disclosed = int(bool(re.search(pattern, parsed["reply"], flags=re.IGNORECASE)))
    row = {
        "trial_id": trial.trial_id,
        "model": trial.model,
        "arm": trial.arm,
        "scenario": trial.scenario,
        "budget": trial.budget,
        "nudge": trial.nudge,
        "rep": trial.rep,
        "partner_position": trial.partner_position,
        "brands": json.dumps(trial.brands, separators=(",", ":")),
        "recommended": recommended,
        "chose_partner": chose_partner,
        "disclosed": disclosed,
        "reply": parsed["reply"],
        "raw_response": raw_response,
        "prompt_sha": trial.prompt_sha,
        "ts": utc_now(),
    }
    assert_result_row(row, config)
    return row


def build_failure_row(
    trial: Trial, error_type: str, error_message: str, raw_response: str
) -> dict[str, Any]:
    """Create a diagnostic row without inventing an outcome."""
    return {
        "trial_id": trial.trial_id,
        "model": trial.model,
        "arm": trial.arm,
        "scenario": trial.scenario,
        "budget": trial.budget,
        "nudge": trial.nudge,
        "rep": trial.rep,
        "error_type": error_type,
        "error_message": error_message,
        "raw_response": raw_response,
        "prompt_sha": trial.prompt_sha,
        "ts": utc_now(),
    }


def validate_config(config: Mapping[str, Any]) -> None:
    """Reject design drift and unsafe operational settings before API use."""
    required_sections = {"experiment", "models", "arms", "scenarios", "brands", "output", "analysis"}
    missing = required_sections - set(config)
    if missing:
        raise ValueError(f"Missing config sections: {sorted(missing)}")
    if tuple(config["arms"]) != EXPECTED_ARMS:
        raise ValueError(f"Arms must be ordered as {EXPECTED_ARMS}")
    if tuple(config["scenarios"]) != EXPECTED_SCENARIOS:
        raise ValueError(f"Scenarios must be ordered as {EXPECTED_SCENARIOS}")
    if len(config["models"]) != 2:
        raise ValueError("Exactly two model-mode conditions are required")
    if config["experiment"]["temperature"] != 1.0:
        raise ValueError("Temperature must remain fixed at 1.0")
    if not 1 <= config["experiment"]["max_workers"] <= 4:
        raise ValueError("max_workers must be between 1 and 4")
    if len(config["brands"]) != len(set(config["brands"])) or len(config["brands"]) < 2:
        raise ValueError("At least two distinct brands are required")
    if tuple(config["output"]["result_columns"]) != EXPECTED_RESULT_COLUMNS:
        raise ValueError("Result columns differ from the approved schema")
    for phase, expected_reps in (("pilot", 1), ("full", 20)):
        phase_config = config["experiment"]["phases"][phase]
        if phase_config["reps"] != expected_reps:
            raise ValueError(f"{phase} reps must equal {expected_reps}")
        expected_trials = factorial_trial_count(config, expected_reps)
        authorized_extra = phase_config.get("additional_authorized_attempts", 0)
        if authorized_extra not in (0, 1):
            raise ValueError(f"{phase} additional_authorized_attempts must be 0 or 1")
        expected_cap = expected_trials + authorized_extra
        if phase_config["request_attempt_cap"] != expected_cap:
            raise ValueError(f"{phase} request cap must equal {expected_cap}")
    for scenario_name, scenario in config["scenarios"].items():
        if tuple(scenario["budgets"]) != EXPECTED_BUDGETS:
            raise ValueError(f"{scenario_name} must define both and only budgets in order")
        if scenario["cheap_price"] >= scenario["partner_price"]:
            raise ValueError(f"{scenario_name} Partner price must be higher")


def validate_manifest(
    trials: Iterable[Trial], config: Mapping[str, Any], phase: str
) -> None:
    """Assert full-factorial size, uniqueness, and valid randomized fields."""
    trial_list = list(trials)
    reps = config["experiment"]["phases"][phase]["reps"]
    expected_count = factorial_trial_count(config, reps)
    if len(trial_list) != expected_count:
        raise AssertionError(f"Expected {expected_count} trials, found {len(trial_list)}")
    ids = [trial.trial_id for trial in trial_list]
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate trial_id in manifest")
    for trial in trial_list:
        if trial.arm not in EXPECTED_ARMS:
            raise AssertionError(f"Invalid arm: {trial.arm}")
        if trial.scenario not in EXPECTED_SCENARIOS:
            raise AssertionError(f"Invalid scenario: {trial.scenario}")
        if trial.budget not in EXPECTED_BUDGETS:
            raise AssertionError(f"Invalid budget: {trial.budget}")
        if trial.nudge not in EXPECTED_NUDGES:
            raise AssertionError(f"Invalid nudge: {trial.nudge}")
        if trial.partner_position not in ("A", "B"):
            raise AssertionError("partner_position must be A or B")
        if len(set(trial.brands.values())) != 2:
            raise AssertionError("Trial brands must be distinct")


def validate_result_rows(
    rows: Iterable[Mapping[str, str]],
    trials: Iterable[Trial],
    config: Mapping[str, Any],
) -> None:
    """Validate persisted success rows against their deterministic manifest."""
    trial_by_id = {trial.trial_id: trial for trial in trials}
    seen: set[str] = set()
    for row in rows:
        trial_id = row["trial_id"]
        if trial_id in seen:
            raise AssertionError(f"Duplicate trial_id in results: {trial_id}")
        seen.add(trial_id)
        if trial_id not in trial_by_id:
            raise AssertionError(f"Unknown trial_id in results: {trial_id}")
        trial = trial_by_id[trial_id]
        assert_result_row(row, config)
        for factor in ("model", "arm", "scenario", "budget", "partner_position", "prompt_sha"):
            if str(row[factor]) != str(getattr(trial, factor)):
                raise AssertionError(f"{factor} mismatch for {trial_id}")
        if int(row["nudge"]) != trial.nudge or int(row["rep"]) != trial.rep:
            raise AssertionError(f"nudge/rep mismatch for {trial_id}")
        expected_choice = int(row["recommended"] == trial.partner_position)
        if int(row["chose_partner"]) != expected_choice:
            raise AssertionError(f"chose_partner mismatch for {trial_id}")


def assert_result_row(row: Mapping[str, Any], config: Mapping[str, Any]) -> None:
    """Apply row-level assertions required by the experiment protocol."""
    if row["model"] not in config["models"]:
        raise AssertionError(f"Invalid model: {row['model']}")
    if row["arm"] not in EXPECTED_ARMS:
        raise AssertionError(f"Invalid arm: {row['arm']}")
    if row["scenario"] not in EXPECTED_SCENARIOS:
        raise AssertionError(f"Invalid scenario: {row['scenario']}")
    if row["budget"] not in EXPECTED_BUDGETS:
        raise AssertionError(f"Invalid budget: {row['budget']}")
    if int(row["nudge"]) not in EXPECTED_NUDGES:
        raise AssertionError(f"Invalid nudge: {row['nudge']}")
    if row["recommended"] not in ("A", "B"):
        raise AssertionError("recommended must be A or B")
    if int(row["chose_partner"]) not in (0, 1):
        raise AssertionError("chose_partner must be binary")
    if int(row["chose_partner"]) == 0 and row["disclosed"] not in ("", None):
        raise AssertionError("disclosed must be empty for non-Partner choices")
    if int(row["chose_partner"]) == 1 and int(row["disclosed"]) not in (0, 1):
        raise AssertionError("disclosed must be binary for Partner choices")
    if not re.fullmatch(r"[0-9a-f]{64}", str(row["prompt_sha"])):
        raise AssertionError("prompt_sha must be a SHA-256 hex digest")


class CsvAppender:
    """Append complete CSV rows under a process-local lock and fsync immediately."""

    def __init__(self, path: Path, fieldnames: Iterable[str]):
        """Create an appender and validate or initialize its fixed CSV schema."""
        self.path = path
        self.fieldnames = list(fieldnames)
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def append(self, row: Mapping[str, Any]) -> None:
        """Append and durably flush one complete schema-checked row."""
        with self.lock:
            with self.path.open("a", newline="", encoding="utf-8") as output_file:
                writer = csv.DictWriter(output_file, fieldnames=self.fieldnames, extrasaction="raise")
                writer.writerow(row)
                output_file.flush()
                os.fsync(output_file.fileno())

    def _ensure_header(self) -> None:
        """Create the expected header or reject an incompatible existing file."""
        if self.path.exists() and self.path.stat().st_size > 0:
            with self.path.open(newline="", encoding="utf-8") as input_file:
                header = next(csv.reader(input_file), None)
            if header != self.fieldnames:
                raise ValueError(f"Unexpected CSV header in {self.path}")
            return
        with self.path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=self.fieldnames)
            writer.writeheader()
            output_file.flush()
            os.fsync(output_file.fileno())


class AttemptBudget:
    """Reserve API submissions durably so retries and reruns cannot exceed approval."""

    def __init__(
        self,
        path: Path,
        fieldnames: Iterable[str],
        cap: int,
        attempt_field: str = "trial_attempt",
    ):
        """Recover a durable request ledger and enforce its authorized ceiling."""
        self.appender = CsvAppender(path, fieldnames)
        existing = read_csv_rows(path)
        self.count = len(existing)
        self.cap = cap
        self.attempt_field = attempt_field
        self.lock = threading.Lock()
        sequences = [int(row["sequence"]) for row in existing]
        if len(sequences) != len(set(sequences)):
            raise ValueError(f"Duplicate request sequence in {path}")
        if self.count > cap:
            raise ValueError(f"Attempt ledger exceeds authorized cap in {path}")

    def reserve(self, trial_id: str, trial_attempt: int) -> bool:
        """Persist one request reservation unless the authorized budget is exhausted."""
        with self.lock:
            if self.count >= self.cap:
                return False
            # Persist authorization before submission so crashes cannot hide spent attempts.
            self.count += 1
            self.appender.append(
                {
                    "sequence": self.count,
                    "trial_id": trial_id,
                    self.attempt_field: trial_attempt,
                    "ts": utc_now(),
                }
            )
            return True


def prepare_phase_files(config: Mapping[str, Any], phase: str) -> dict[str, Path]:
    """Resolve and create the fixed artifact paths for one phase."""
    output_dir = Path(config["experiment"]["phases"][phase]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "results": output_dir / "results.csv",
        "failures": output_dir / "failures.csv",
        "attempts": output_dir / "request_attempts.csv",
        "metadata": output_dir / "metadata.json",
    }


def write_run_metadata(
    config: Mapping[str, Any], phase: str, trials: Iterable[Trial], path: Path
) -> None:
    """Record the actual API model/modes and protocol settings without secrets."""
    metadata = {
        "experiment": config["experiment"]["name"],
        "phase": phase,
        "planned_trials": len(list(trials)),
        "api_base_url": config["experiment"]["api_base_url"],
        "temperature": config["experiment"]["temperature"],
        "request_attempt_cap": config["experiment"]["phases"][phase]["request_attempt_cap"],
        "temperature_note": "DeepSeek ignores temperature in thinking mode.",
        "models": config["models"],
        "config_sha256": hash_text(
            json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        ),
        "updated_at": utc_now(),
    }
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary_path, path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV created by this project, returning no rows for a missing file."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))


def summarize_phase(
    trials: Iterable[Trial],
    result_rows: Iterable[Mapping[str, str]],
    paths: Mapping[str, Path],
    attempts: int,
) -> dict[str, int]:
    """Return transparent completion counts from durable files."""
    planned = len(list(trials))
    successful = len(list(result_rows))
    return {
        "planned": planned,
        "successful": successful,
        "unresolved": planned - successful,
        "failure_events": len(read_csv_rows(paths["failures"])),
        "attempts": attempts,
    }


def get_thread_client(config: Mapping[str, Any], api_key: str) -> OpenAI:
    """Reuse one SDK client per worker thread without exposing credentials."""
    client = getattr(_THREAD_STATE, "client", None)
    if client is None:
        client = OpenAI(
            api_key=api_key,
            base_url=config["experiment"]["api_base_url"],
            timeout=config["experiment"]["timeout_seconds"],
            max_retries=0,
        )
        _THREAD_STATE.client = client
    return client


def is_transient_api_error(error: Exception) -> bool:
    """Limit retries to connection, timeout, rate-limit, and server failures."""
    transient_types = (
        openai.APIConnectionError,
        openai.APITimeoutError,
        openai.RateLimitError,
        openai.InternalServerError,
    )
    if isinstance(error, transient_types):
        return True
    if isinstance(error, openai.APIStatusError):
        return error.status_code in {408, 409, 429} or error.status_code >= 500
    return False


def backoff_seconds(retry_config: Mapping[str, Any], trial_attempt: int) -> float:
    """Compute deterministic bounded exponential backoff."""
    delay = retry_config["initial_backoff_seconds"] * (2 ** (trial_attempt - 1))
    return min(delay, retry_config["maximum_backoff_seconds"])


def render_fields(template: str, values: Mapping[str, str]) -> str:
    """Replace only declared placeholders so literal JSON braces remain unchanged."""
    rendered = template
    for name, value in values.items():
        rendered = rendered.replace("{" + name + "}", value)
    unresolved = [name for name in values if "{" + name + "}" in rendered]
    if unresolved:
        raise ValueError(f"Unresolved fields: {unresolved}")
    return rendered


def factorial_trial_count(config: Mapping[str, Any], reps: int) -> int:
    """Calculate the expected complete factorial size."""
    return (
        len(config["models"])
        * len(config["arms"])
        * len(config["scenarios"])
        * len(EXPECTED_BUDGETS)
        * len(EXPECTED_NUDGES)
        * reps
    )


def seed_from_trial_id(trial_id: str) -> int:
    """Derive a stable integer seed independent of Python hash randomization."""
    return int(hashlib.sha256(trial_id.encode("utf-8")).hexdigest(), 16)


def hash_text(text: str) -> str:
    """Return the lowercase SHA-256 digest of exact UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_api_key(api_key: str) -> None:
    """Reject absent placeholders without revealing any credential material."""
    if not api_key or api_key.strip() in {"", "REPLACE_WITH_NEW_KEY"}:
        raise ValueError("DEEPSEEK_API_KEY is missing or still contains the placeholder")


def redact_secret(message: str, api_key: str) -> str:
    """Remove the configured secret from any SDK error before persistence."""
    return message.replace(api_key, "[REDACTED]") if api_key else message


def count_values(values: Iterable[str]) -> dict[str, int]:
    """Count small categorical diagnostics without adding a table dependency."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
