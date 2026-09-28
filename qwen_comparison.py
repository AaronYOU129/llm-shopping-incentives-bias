"""
Purpose:
    Replay the exact DeepSeek non-thinking mechanism prompts on a pinned Qwen model.
    Prompt-hash pairing isolates model family while durable caps bound paid requests.

Inputs:
    config_qwen.yaml; config_mechanism.yaml; outputs/mechanism/full/results.csv;
    QWEN_API_KEY; optional saved files under outputs/qwen_comparison/.

Outputs:
    Qwen results, failures, request-attempt ledger, and protocol metadata.

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


EXPECTED_TRIALS = 760
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
    pending_trials = [trial for trial in trials if trial.trial_id not in completed_ids]
    abort_event = threading.Event()
    rate_limiter = RequestRateLimiter(
        config["experiment"]["minimum_request_interval_seconds"]
    )

    with ThreadPoolExecutor(max_workers=config["experiment"]["max_workers"]) as executor:
        futures = [
            executor.submit(
                execute_qwen_trial,
                trial,
                config,
                api_key,
                attempt_budget,
                result_appender,
                failure_appender,
                abort_event,
                rate_limiter,
            )
            for trial in pending_trials
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


def generate_qwen_trials(config: Mapping[str, Any]) -> list[QwenTrial]:
    """Reconstruct source prompts and require hashes to match saved DeepSeek rows."""
    mechanism_config = load_config(config["source"]["mechanism_config"])
    all_source_trials = generate_mechanism_trials(mechanism_config, "full")
    source_rows = read_csv_rows(Path(config["source"]["mechanism_results"]))
    validate_mechanism_results(source_rows, all_source_trials, mechanism_config)
    source_row_by_id = {row["trial_id"]: row for row in source_rows}
    selected = [
        trial for trial in all_source_trials
        if trial.model == config["source"]["model"]
    ]
    trials = [build_qwen_trial(config, trial, source_row_by_id) for trial in selected]
    validate_qwen_manifest(trials, config)
    return trials


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
    return QwenTrial(
        trial_id=f"qwen:{source_trial.trial_id}",
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
    if not attempt_budget.reserve(trial.trial_id, 1):
        failure_appender.append(
            build_qwen_failure_row(
                trial, "budget_exhausted", "Authorized Qwen request cap reached", ""
            )
        )
        return
    rate_limiter.wait()
    try:
        raw_response = request_qwen_completion(config, trial, api_key)
    except Exception as error:  # SDK errors share one redacted persistence boundary.
        abort_event.set()
        failure_appender.append(
            build_qwen_failure_row(
                trial, "api_error", redact_secret(str(error), api_key), ""
            )
        )
        return
    try:
        parsed = parse_model_response(raw_response)
    except ValueError as error:
        failure_appender.append(
            build_qwen_failure_row(trial, "parse_error", str(error), raw_response)
        )
        return
    result_appender.append(build_qwen_result_row(config, trial, parsed, raw_response))


def request_qwen_completion(
    config: Mapping[str, Any], trial: QwenTrial, api_key: str
) -> str:
    """Submit the source user message with Qwen thinking explicitly disabled."""
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
    return content


def build_qwen_result_row(
    config: Mapping[str, Any],
    trial: QwenTrial,
    parsed: Mapping[str, str],
    raw_response: str,
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
    if experiment["request_attempt_cap"] != EXPECTED_TRIALS:
        raise ValueError(f"Qwen request cap must equal {EXPECTED_TRIALS}")
    if experiment["temperature"] != 1.0:
        raise ValueError("Qwen temperature must remain 1.0")
    if not 1 <= experiment["max_workers"] <= 4:
        raise ValueError("Qwen max_workers must be between one and four")
    if experiment["minimum_request_interval_seconds"] < 1.0:
        raise ValueError("Qwen request interval must respect the 60 RPM limit")
    if config["model"] != {
        "label": "qwen3.7-plus/non-thinking",
        "api_model": "qwen3.7-plus-2026-05-26",
        "enable_thinking": False,
    }:
        raise ValueError("Qwen model snapshot or thinking mode has changed")
    if config["source"]["model"] != "deepseek-flash/non-thinking":
        raise ValueError("Qwen source model must remain DeepSeek non-thinking")


def validate_qwen_manifest(
    trials: Iterable[QwenTrial], config: Mapping[str, Any]
) -> None:
    """Require 760 unique paired IDs and valid prompt hashes."""
    trial_list = list(trials)
    if len(trial_list) != EXPECTED_TRIALS:
        raise AssertionError(f"Expected {EXPECTED_TRIALS} Qwen trials, found {len(trial_list)}")
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
