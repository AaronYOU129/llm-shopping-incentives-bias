"""
Purpose:
    Replay the exact DeepSeek non-thinking mechanism prompts on a pinned Qwen model.
    Prompt-hash pairing isolates model family while durable caps bound paid requests.

Inputs:
    config_qwen.yaml or config_qwen_thinking.yaml; config_mechanism.yaml;
    saved DeepSeek/Qwen source results; QWEN_API_KEY; optional resumable artifacts.

Outputs:
    Mode-isolated Qwen results, failures, request ledger, metadata, and pilot report.

Key Steps:
    1. Reconstruct and verify every saved DeepSeek source prompt.
    2. Build 760 prompt-matched Qwen trials without changing prompt text.
    3. Submit pending trials once within the durable request cap and rate limit.
    4. Persist and validate every terminal outcome before analysis.

Main Flow:
    run_qwen_comparison()
        -> generate_qwen_trials()
        -> validate_qwen_results()
        -> execute_qwen_trial()
            |-- no request budget -> failure artifact
            |-- API/parse failure  -> failure artifact
            `-- valid response     -> results artifact
        `-- summarize_qwen_run()

How to Run:
    QWEN_API_KEY="$(<.secrets/qwen_api_key)" \
      python run_all.py qwen-run --approve-qwen-run
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from openai import OpenAI

from experiment import (
    AttemptBudget,
    CsvAppender,
    hash_text,
    load_config,
    parse_model_response,
    read_csv_rows,
    redact_secret,
    utc_now,
)
from mechanism_experiment import (
    MechanismTrial,
    generate_mechanism_trials,
    validate_mechanism_results,
)


EXPECTED_SOURCE_TRIALS = 760
CELLS_PER_REPLICATION = 38
_QWEN_THREAD_STATE = threading.local()


@dataclass(frozen=True)
class QwenTrial:
    """Represent one Qwen request paired to an immutable DeepSeek source prompt."""

    trial_id: str
    source_trial_id: str
    model: str
    condition: str
    framing: str
    incentive_rate: int | None
    platform_payout: str
    scenario: str
    nudge: int
    rep: int
    partner_position: str
    brands: Mapping[str, str]
    prompt: str
    prompt_sha: str


@dataclass(frozen=True)
class QwenCompletion:
    """Keep the final answer separate from optional model reasoning content."""

    content: str
    reasoning_content: str


class RequestRateLimiter:
    """Serialize request starts so the run stays below the documented RPM limit."""

    def __init__(self, minimum_interval_seconds: float) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self._lock = threading.Lock()
        self._last_started = 0.0

    def wait(self) -> None:
        """Wait until the next request-start slot is available."""
        with self._lock:
            remaining = self.minimum_interval_seconds - (
                time.monotonic() - self._last_started
            )
            if remaining > 0:
                time.sleep(remaining)
            self._last_started = time.monotonic()


def run_qwen_comparison(
    config: Mapping[str, Any], api_key: str
) -> dict[str, int]:
    """Run or resume the approved Qwen replication and return durable counts."""
    validate_qwen_config(config)
    validate_qwen_api_key(api_key)
    trials = generate_qwen_trials(config)
    paths = prepare_qwen_files(config)
    write_qwen_metadata(config, trials, paths["metadata"])

    result_appender = CsvAppender(paths["results"], config["output"]["result_columns"])
    failure_appender = CsvAppender(paths["failures"], config["output"]["failure_columns"])
    attempt_budget = AttemptBudget(
        paths["attempts"],
        config["output"]["attempt_columns"],
        config["experiment"]["request_attempt_cap"],
    )
    existing_rows = read_csv_rows(paths["results"])
    validate_qwen_results(existing_rows, trials, config)
    completed_ids = {row["trial_id"] for row in existing_rows}
    attempt_counts = Counter(
        row["trial_id"] for row in read_csv_rows(paths["attempts"])
    )
    replacement_ids = set(
        config["experiment"].get("authorized_replacement_trial_ids", [])
    )
    pending_requests: list[tuple[QwenTrial, int]] = []
    for trial in trials:
        if trial.trial_id in completed_ids:
            continue
        prior_attempts = attempt_counts[trial.trial_id]
        if prior_attempts == 0:
            pending_requests.append((trial, 1))
        elif trial.trial_id in replacement_ids and prior_attempts == 1:
            pending_requests.append((trial, 2))
    abort_event = threading.Event()
    rate_limiter = RequestRateLimiter(
        config["experiment"]["minimum_request_interval_seconds"]
    )

    with ThreadPoolExecutor(max_workers=config["experiment"]["max_workers"]) as executor:
        futures = [
            executor.submit(
                execute_qwen_trial,
                trial,
                trial_attempt,
                config,
                api_key,
                attempt_budget,
                result_appender,
                failure_appender,
                abort_event,
                rate_limiter,
            )
            for trial, trial_attempt in pending_requests
        ]
        for completed_count, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed_count % 25 == 0 or completed_count == len(futures):
                print(
                    f"qwen: processed {completed_count}/{len(futures)} pending trials",
                    flush=True,
                )

    final_rows = read_csv_rows(paths["results"])
    validate_qwen_results(final_rows, trials, config)
    return summarize_qwen_run(trials, final_rows, paths, attempt_budget.count)


def validate_qwen_only(config: Mapping[str, Any]) -> dict[str, int]:
    """Validate configuration and exact source pairing without external calls."""
    validate_qwen_config(config)
    trials = generate_qwen_trials(config)
    return {
        "paired_trials": len(trials),
        "unique_prompt_hashes": len({trial.prompt_sha for trial in trials}),
    }


def write_qwen_thinking_pilot_report(config: Mapping[str, Any]) -> Path:
    """Write a compact review artifact from a complete thinking-mode pilot."""
    trials = generate_qwen_trials(config)
    paths = prepare_qwen_files(config)
    rows = read_csv_rows(paths["results"])
    validate_qwen_results(rows, trials, config)
    if len(rows) != len(trials):
        raise ValueError(f"Qwen thinking pilot is incomplete: {len(rows)}/{len(trials)}")

    source_rows = read_csv_rows(Path(config["source"]["qwen_nonthinking_results"]))
    source_by_id = {row["source_trial_id"]: row for row in source_rows}
    framing_counts: dict[str, list[int]] = {}
    transitions = {"0->0": 0, "0->1": 0, "1->0": 0, "1->1": 0}
    for row in rows:
        framing_counts.setdefault(row["framing"], [0, 0])
        framing_counts[row["framing"]][0] += int(row["chose_partner"])
        framing_counts[row["framing"]][1] += 1
        before = int(source_by_id[row["source_trial_id"]]["chose_partner"])
        after = int(row["chose_partner"])
        transitions[f"{before}->{after}"] += 1

    lines = [
        "# Qwen Thinking Pilot",
        "",
        f"- Model snapshot: `{config['model']['api_model']}`",
        "- Thinking enabled: `true`",
        f"- Valid results: {len(rows)}/{len(trials)}",
        f"- Submitted requests: {len(read_csv_rows(paths['attempts']))}",
        f"- Failure events: {len(read_csv_rows(paths['failures']))}",
        "- Remaining full-run prompts submitted: 0",
        "",
        "## Partner choices by framing",
        "",
        "| Framing | Partner choices | n | Share |",
        "| --- | ---: | ---: | ---: |",
    ]
    for framing in ("no_incentive", "percentage", "percentage_computed", "fixed_amount"):
        choices, count = framing_counts.get(framing, [0, 0])
        share = choices / count if count else 0
        lines.append(f"| {framing} | {choices} | {count} | {share:.1%} |")
    lines.extend([
        "",
        "## Paired changes versus Qwen non-thinking",
        "",
        "| Non-thinking → thinking | Count |",
        "| --- | ---: |",
    ])
    for direction in ("0->0", "0->1", "1->0", "1->1"):
        lines.append(f"| {direction} | {transitions[direction]} |")
    reasoning_count = sum(bool(row.get("reasoning_content", "")) for row in rows)
    lines.extend([
        "",
        f"Reasoning content was returned for {reasoning_count}/{len(rows)} responses.",
        "",
        "## Five unedited final responses",
        "",
    ])
    for row in sorted(rows, key=lambda item: item["trial_id"])[:5]:
        lines.extend([
            f"### `{row['trial_id']}`",
            "",
            "````json",
            row["raw_response"],
            "````",
            "",
        ])

    report_path = Path(config["analysis"]["pilot_report_path"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def generate_qwen_trials(config: Mapping[str, Any]) -> list[QwenTrial]:
    """Reconstruct source prompts and require hashes to match saved DeepSeek rows."""
    mechanism_config = load_config(config["source"]["mechanism_config"])
    all_source_trials = generate_mechanism_trials(mechanism_config, "full")
    source_rows = read_csv_rows(Path(config["source"]["mechanism_results"]))
    validate_mechanism_results(source_rows, all_source_trials, mechanism_config)
    source_row_by_id = {row["trial_id"]: row for row in source_rows}
    selected_reps = config.get("selection", {}).get("selected_reps")
    selected = [
        trial for trial in all_source_trials
        if trial.model == config["source"]["model"]
        and (selected_reps is None or trial.rep in selected_reps)
    ]
    trials = [build_qwen_trial(config, trial, source_row_by_id) for trial in selected]
    validate_qwen_manifest(trials, config)
    validate_qwen_nonthinking_pairing(trials, config)
    return trials


def validate_qwen_nonthinking_pairing(
    trials: Iterable[QwenTrial], config: Mapping[str, Any]
) -> None:
    """Require thinking prompts to match completed Qwen non-thinking observations."""
    source_path = config["source"].get("qwen_nonthinking_results")
    if not source_path:
        return
    rows = read_csv_rows(Path(source_path))
    if len(rows) != EXPECTED_SOURCE_TRIALS:
        raise AssertionError(
            f"Expected {EXPECTED_SOURCE_TRIALS} saved Qwen source rows, found {len(rows)}"
        )
    row_by_source_id = {row["source_trial_id"]: row for row in rows}
    if len(row_by_source_id) != len(rows):
        raise AssertionError("Saved Qwen source_trial_id values must be unique")
    for trial in trials:
        row = row_by_source_id.get(trial.source_trial_id)
        if row is None:
            raise AssertionError(
                f"Missing saved Qwen source result: {trial.source_trial_id}"
            )
        if row["prompt_sha"] != trial.prompt_sha:
            raise AssertionError(
                f"Saved Qwen prompt hash mismatch: {trial.source_trial_id}"
            )


def build_qwen_trial(
    config: Mapping[str, Any],
    source_trial: MechanismTrial,
    source_row_by_id: Mapping[str, Mapping[str, str]],
) -> QwenTrial:
    """Clone source factors and exact prompt after verifying the persisted hash."""
    if source_trial.trial_id not in source_row_by_id:
        raise AssertionError(f"Missing DeepSeek source result: {source_trial.trial_id}")
    source_row = source_row_by_id[source_trial.trial_id]
    if source_row["prompt_sha"] != source_trial.prompt_sha:
        raise AssertionError(f"Source prompt hash mismatch: {source_trial.trial_id}")
    trial_prefix = config["experiment"].get("trial_id_prefix", "qwen")
    return QwenTrial(
        trial_id=f"{trial_prefix}:{source_trial.trial_id}",
        source_trial_id=source_trial.trial_id,
        model=config["model"]["label"],
        condition=source_trial.condition,
        framing=source_trial.framing,
        incentive_rate=source_trial.incentive_rate,
        platform_payout=source_trial.platform_payout,
        scenario=source_trial.scenario,
        nudge=source_trial.nudge,
        rep=source_trial.rep,
        partner_position=source_trial.partner_position,
        brands=source_trial.brands,
        prompt=source_trial.prompt,
        prompt_sha=source_trial.prompt_sha,
    )


def execute_qwen_trial(
    trial: QwenTrial,
    trial_attempt: int,
    config: Mapping[str, Any],
    api_key: str,
    attempt_budget: AttemptBudget,
    result_appender: CsvAppender,
    failure_appender: CsvAppender,
    abort_event: threading.Event,
    rate_limiter: RequestRateLimiter,
) -> None:
    """Submit one request exactly once and persist its terminal outcome."""
    if abort_event.is_set():
        failure_appender.append(
            build_qwen_failure_row(
                trial, "run_aborted",
                "Run stopped after a non-transient API/configuration error", ""
            )
        )
        return
    if not attempt_budget.reserve(trial.trial_id, trial_attempt):
        failure_appender.append(
            build_qwen_failure_row(
                trial, "budget_exhausted", "Authorized Qwen request cap reached", ""
            )
        )
        return
    rate_limiter.wait()
    try:
        completion = request_qwen_completion(config, trial, api_key)
    except Exception as error:  # SDK errors share one redacted persistence boundary.
        abort_event.set()
        failure_appender.append(
            build_qwen_failure_row(
                trial, "api_error", redact_secret(str(error), api_key), ""
            )
        )
        return
    try:
        parsed = parse_model_response(completion.content)
    except ValueError as error:
        failure_appender.append(
            build_qwen_failure_row(trial, "parse_error", str(error), completion.content)
        )
        return
    result_appender.append(build_qwen_result_row(
        config,
        trial,
        parsed,
        completion.content,
        completion.reasoning_content,
    ))


def request_qwen_completion(
    config: Mapping[str, Any], trial: QwenTrial, api_key: str
) -> QwenCompletion:
    """Submit one immutable user message with the configured Qwen thinking mode."""
    client = get_qwen_thread_client(config, api_key)
    response = client.chat.completions.create(
        model=config["model"]["api_model"],
        messages=[{"role": "user", "content": trial.prompt}],
        temperature=config["experiment"]["temperature"],
        extra_body={"enable_thinking": config["model"]["enable_thinking"]},
    )
    if not response.choices:
        raise ValueError("Qwen response contained no choices")
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content:
        raise ValueError("Qwen response content was empty")
    reasoning_content = getattr(response.choices[0].message, "reasoning_content", "")
    if not isinstance(reasoning_content, str):
        reasoning_content = ""
    return QwenCompletion(content=content, reasoning_content=reasoning_content)


def build_qwen_result_row(
    config: Mapping[str, Any],
    trial: QwenTrial,
    parsed: Mapping[str, str],
    raw_response: str,
    reasoning_content: str = "",
) -> dict[str, Any]:
    """Derive outcomes using the same rules as the source mechanism experiment."""
    chose_partner = int(parsed["recommended"] == trial.partner_position)
    disclosed: int | str = ""
    if chose_partner:
        disclosed = int(bool(re.search(
            config["output"]["disclosure_pattern"], parsed["reply"], re.IGNORECASE
        )))
    row = {
        "trial_id": trial.trial_id,
        "source_trial_id": trial.source_trial_id,
        "model": trial.model,
        "api_model": config["model"]["api_model"],
        "condition": trial.condition,
        "framing": trial.framing,
        "incentive_rate": "" if trial.incentive_rate is None else trial.incentive_rate,
        "platform_payout": trial.platform_payout,
        "scenario": trial.scenario,
        "nudge": trial.nudge,
        "rep": trial.rep,
        "partner_position": trial.partner_position,
        "brands": json.dumps(trial.brands, separators=(",", ":")),
        "recommended": parsed["recommended"],
        "chose_partner": chose_partner,
        "disclosed": disclosed,
        "reply": parsed["reply"],
        "raw_response": raw_response,
        "prompt_sha": trial.prompt_sha,
        "ts": utc_now(),
    }
    if "reasoning_content" in config["output"]["result_columns"]:
        row["reasoning_content"] = reasoning_content
    assert_qwen_result_row(row, config)
    return row


def build_qwen_failure_row(
    trial: QwenTrial, error_type: str, error_message: str, raw_response: str
) -> dict[str, Any]:
    """Create one auditable failure row without inferring an outcome."""
    return {
        "trial_id": trial.trial_id,
        "source_trial_id": trial.source_trial_id,
        "model": trial.model,
        "condition": trial.condition,
        "framing": trial.framing,
        "incentive_rate": "" if trial.incentive_rate is None else trial.incentive_rate,
        "scenario": trial.scenario,
        "nudge": trial.nudge,
        "rep": trial.rep,
        "error_type": error_type,
        "error_message": error_message,
        "raw_response": raw_response,
        "prompt_sha": trial.prompt_sha,
        "ts": utc_now(),
    }


def validate_qwen_config(config: Mapping[str, Any]) -> None:
    """Reject model, endpoint, source, or spending drift before API use."""
    required = {"experiment", "model", "source", "output", "analysis"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"Missing Qwen config sections: {sorted(missing)}")
    experiment = config["experiment"]
    selected_reps = config.get("selection", {}).get("selected_reps")
    expected_trials = EXPECTED_SOURCE_TRIALS
    if selected_reps is not None:
        if not selected_reps or len(selected_reps) != len(set(selected_reps)):
            raise ValueError("Qwen selected_reps must be unique and non-empty")
        if any(not isinstance(rep, int) or not 1 <= rep <= 20 for rep in selected_reps):
            raise ValueError("Qwen selected_reps must be integers from 1 through 20")
        expected_trials = CELLS_PER_REPLICATION * len(selected_reps)
    replacement_ids = experiment.get("authorized_replacement_trial_ids", [])
    if len(replacement_ids) != len(set(replacement_ids)):
        raise ValueError("Authorized Qwen replacement trial IDs must be unique")
    authorized_cap = expected_trials + len(replacement_ids)
    if experiment["request_attempt_cap"] != authorized_cap:
        raise ValueError(f"Qwen request cap must equal {authorized_cap}")
    if experiment["temperature"] != 1.0:
        raise ValueError("Qwen temperature must remain 1.0")
    if not 1 <= experiment["max_workers"] <= 4:
        raise ValueError("Qwen max_workers must be between one and four")
    if experiment["minimum_request_interval_seconds"] < 1.0:
        raise ValueError("Qwen request interval must respect the 60 RPM limit")
    approved_modes = {
        ("qwen3.7-plus/non-thinking", False),
        ("qwen3.7-plus/thinking", True),
    }
    model = config["model"]
    if model.get("api_model") != "qwen3.7-plus-2026-05-26" or (
        model.get("label"), model.get("enable_thinking")
    ) not in approved_modes:
        raise ValueError("Qwen model snapshot or thinking mode has changed")
    if model["enable_thinking"] and not config["source"].get(
        "qwen_nonthinking_results"
    ):
        raise ValueError("Qwen thinking runs require saved non-thinking source results")
    if config["source"]["model"] != "deepseek-flash/non-thinking":
        raise ValueError("Qwen source model must remain DeepSeek non-thinking")


def validate_qwen_manifest(
    trials: Iterable[QwenTrial], config: Mapping[str, Any]
) -> None:
    """Require the capped number of unique paired IDs and valid prompt hashes."""
    trial_list = list(trials)
    selected_reps = config.get("selection", {}).get("selected_reps")
    expected_trials = (
        EXPECTED_SOURCE_TRIALS
        if selected_reps is None
        else CELLS_PER_REPLICATION * len(selected_reps)
    )
    if len(trial_list) != expected_trials:
        raise AssertionError(
            f"Expected {expected_trials} Qwen trials, found {len(trial_list)}"
        )
    for attribute in ("trial_id", "source_trial_id"):
        values = [getattr(trial, attribute) for trial in trial_list]
        if len(values) != len(set(values)):
            raise AssertionError(f"Duplicate Qwen {attribute}")
    for trial in trial_list:
        if trial.model != config["model"]["label"]:
            raise AssertionError("Qwen model label mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", trial.prompt_sha):
            raise AssertionError("Qwen prompt_sha must be SHA-256")
        if hash_text(trial.prompt) != trial.prompt_sha:
            raise AssertionError(f"Qwen prompt text/hash mismatch: {trial.trial_id}")
    replacement_ids = set(
        config["experiment"].get("authorized_replacement_trial_ids", [])
    )
    unknown_replacements = replacement_ids - {trial.trial_id for trial in trial_list}
    if unknown_replacements:
        raise AssertionError(
            f"Unknown authorized Qwen replacements: {sorted(unknown_replacements)}"
        )


def validate_qwen_results(
    rows: Iterable[Mapping[str, str]],
    trials: Iterable[QwenTrial],
    config: Mapping[str, Any],
) -> None:
    """Validate saved outcomes against every immutable paired trial field."""
    trial_by_id = {trial.trial_id: trial for trial in trials}
    seen: set[str] = set()
    for row in rows:
        trial_id = row["trial_id"]
        if trial_id in seen:
            raise AssertionError(f"Duplicate Qwen result: {trial_id}")
        seen.add(trial_id)
        if trial_id not in trial_by_id:
            raise AssertionError(f"Unknown Qwen trial: {trial_id}")
        trial = trial_by_id[trial_id]
        assert_qwen_result_row(row, config)
        for field in (
            "source_trial_id", "model", "condition", "framing", "scenario",
            "partner_position", "prompt_sha",
        ):
            if str(row[field]) != str(getattr(trial, field)):
                raise AssertionError(f"Qwen {field} mismatch for {trial_id}")
        expected_rate = "" if trial.incentive_rate is None else str(trial.incentive_rate)
        if str(row["incentive_rate"]) != expected_rate:
            raise AssertionError(f"Qwen rate mismatch for {trial_id}")
        if int(row["nudge"]) != trial.nudge or int(row["rep"]) != trial.rep:
            raise AssertionError(f"Qwen nudge/rep mismatch for {trial_id}")
        expected_choice = int(row["recommended"] == trial.partner_position)
        if int(row["chose_partner"]) != expected_choice:
            raise AssertionError(f"Qwen choice mismatch for {trial_id}")


def assert_qwen_result_row(
    row: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    """Apply schema-level constraints to one Qwen result row."""
    if row["model"] != config["model"]["label"]:
        raise AssertionError(f"Invalid Qwen model: {row['model']}")
    if row["api_model"] != config["model"]["api_model"]:
        raise AssertionError(f"Invalid Qwen API model: {row['api_model']}")
    if row["recommended"] not in ("A", "B"):
        raise AssertionError("Qwen recommended must be A or B")
    if int(row["chose_partner"]) not in (0, 1):
        raise AssertionError("Qwen chose_partner must be binary")
    if int(row["chose_partner"]) == 0 and row["disclosed"] not in ("", None):
        raise AssertionError("Qwen disclosure is undefined for non-Partner choices")
    if int(row["chose_partner"]) == 1 and int(row["disclosed"]) not in (0, 1):
        raise AssertionError("Qwen disclosed must be binary")
    if not re.fullmatch(r"[0-9a-f]{64}", str(row["prompt_sha"])):
        raise AssertionError("Qwen prompt_sha must be SHA-256")


def prepare_qwen_files(config: Mapping[str, Any]) -> dict[str, Path]:
    """Create and return isolated Qwen artifact paths."""
    output_dir = Path(config["experiment"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "results": output_dir / "results.csv",
        "failures": output_dir / "failures.csv",
        "attempts": output_dir / "request_attempts.csv",
        "metadata": output_dir / "metadata.json",
    }


def write_qwen_metadata(
    config: Mapping[str, Any], trials: Iterable[QwenTrial], path: Path
) -> None:
    """Persist the pinned Qwen protocol without credential material."""
    metadata = {
        "experiment": config["experiment"]["name"],
        "planned_trials": len(list(trials)),
        "api_base_url": config["experiment"]["api_base_url"],
        "temperature": config["experiment"]["temperature"],
        "request_attempt_cap": config["experiment"]["request_attempt_cap"],
        "minimum_request_interval_seconds": config["experiment"]["minimum_request_interval_seconds"],
        "model": config["model"],
        "source": config["source"],
        "config_sha256": hash_text(json.dumps(
            config, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )),
        "updated_at": utc_now(),
    }
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary_path.replace(path)


def get_qwen_thread_client(config: Mapping[str, Any], api_key: str) -> OpenAI:
    """Reuse one Alibaba-compatible SDK client per worker thread."""
    client = getattr(_QWEN_THREAD_STATE, "client", None)
    if client is None:
        client = OpenAI(
            api_key=api_key,
            base_url=config["experiment"]["api_base_url"],
            timeout=config["experiment"]["timeout_seconds"],
            max_retries=0,
        )
        _QWEN_THREAD_STATE.client = client
    return client


def validate_qwen_api_key(api_key: str) -> None:
    """Reject missing or known-placeholder credentials without displaying them."""
    placeholders = {"", "REPLACE_WITH_QWEN_API_KEY", "REPLACE_WITH_NEW_KEY"}
    if not api_key or api_key.strip() in placeholders:
        raise ValueError("QWEN_API_KEY is missing or still contains the placeholder")


def summarize_qwen_run(
    trials: Iterable[QwenTrial],
    result_rows: Iterable[Mapping[str, str]],
    paths: Mapping[str, Path],
    attempts: int,
) -> dict[str, int]:
    """Return transparent Qwen completion counts from durable artifacts."""
    planned = len(list(trials))
    successful = len(list(result_rows))
    return {
        "planned": planned,
        "successful": successful,
        "unresolved": planned - successful,
        "attempts": attempts,
        "failure_events": len(read_csv_rows(paths["failures"])),
    }
