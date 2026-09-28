"""
Purpose:
    Run the incentive-magnitude mechanism extension without changing the completed
    original experiment. Matched payouts separate numerical framing from incentive size.

Inputs:
    config_mechanism.yaml; DEEPSEEK_API_KEY; optional saved mechanism CSV artifacts.

Outputs:
    outputs/mechanism/{pilot,full}/ results, failures, attempt ledgers, metadata, and
    a pilot report.

Key Steps:
    1. Validate the isolated mechanism protocol and recover saved state.
    2. Build deterministic matched-framing trials plus a Partner-label control.
    3. Submit pending trials within an exact durable request budget.
    4. Persist and validate each terminal outcome before reporting completion.

Main Flow:
    run_mechanism_phase()
        -> validate_mechanism_config()
        -> generate_mechanism_trials()
        -> execute_mechanism_trial()
            |-- retryable failure -> bounded retry
            |-- terminal failure  -> failures.csv
            `-- valid response    -> results.csv
        -> validate_mechanism_results()
        `-- phase summary

How to Run:
    python run_all.py mechanism-pilot
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

from experiment import (
    AttemptBudget,
    CsvAppender,
    backoff_seconds,
    hash_text,
    is_transient_api_error,
    parse_model_response,
    read_csv_rows,
    redact_secret,
    render_fields,
    request_completion,
    seed_from_trial_id,
    utc_now,
    validate_api_key,
)


EXPECTED_LEVELS = (10, 20, 30)
EXPECTED_FRAMINGS = ("percentage", "percentage_computed", "fixed_amount")
EXPECTED_SCENARIOS = ("headphones", "shoes")
EXPECTED_NUDGES = (0, 1)


@dataclass(frozen=True)
class MechanismTrial:
    """Represent one immutable mechanism-extension prompt and its factor values."""

    trial_id: str
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


def run_mechanism_phase(
    config: Mapping[str, Any], phase: str, api_key: str
) -> dict[str, int]:
    """Run or resume one mechanism phase and return durable completion counts."""
    validate_mechanism_config(config)
    validate_api_key(api_key)
    trials = generate_mechanism_trials(config, phase)
    paths = prepare_mechanism_files(config, phase)
    write_mechanism_metadata(config, phase, trials, paths["metadata"])

    result_appender = CsvAppender(paths["results"], config["output"]["result_columns"])
    failure_appender = CsvAppender(paths["failures"], config["output"]["failure_columns"])
    attempt_budget = AttemptBudget(
        paths["attempts"],
        config["output"]["attempt_columns"],
        config["experiment"]["phases"][phase]["request_attempt_cap"],
    )
    existing_rows = read_csv_rows(paths["results"])
    validate_mechanism_results(existing_rows, trials, config)
    completed_ids = {row["trial_id"] for row in existing_rows}
    pending_trials = [trial for trial in trials if trial.trial_id not in completed_ids]
    abort_event = threading.Event()

    with ThreadPoolExecutor(max_workers=config["experiment"]["max_workers"]) as executor:
        futures = [
            executor.submit(
                execute_mechanism_trial,
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
            if completed_count % 25 == 0 or completed_count == len(futures):
                print(
                    f"mechanism {phase}: processed {completed_count}/{len(futures)} pending trials",
                    flush=True,
                )

    final_rows = read_csv_rows(paths["results"])
    validate_mechanism_results(final_rows, trials, config)
    return summarize_mechanism_phase(trials, final_rows, paths, attempt_budget.count)


def validate_mechanism_only(config: Mapping[str, Any]) -> dict[str, int]:
    """Validate both deterministic manifests without making external calls."""
    validate_mechanism_config(config)
    return {
        phase: len(generate_mechanism_trials(config, phase))
        for phase in ("pilot", "full")
    }


def generate_mechanism_trials(
    config: Mapping[str, Any], phase: str
) -> list[MechanismTrial]:
    """Build treatment cells and non-duplicated contemporaneous control cells."""
    if phase not in config["experiment"]["phases"]:
        raise ValueError(f"Unknown mechanism phase: {phase}")
    reps = config["experiment"]["phases"][phase]["reps"]
    trials: list[MechanismTrial] = []
    for model in config["models"]:
        for scenario in config["scenarios"]:
            for rep in range(1, reps + 1):
                trials.append(
                    build_mechanism_trial(
                        config, phase, model, "control", "no_incentive", None,
                        scenario, 0, rep
                    )
                )
            for framing in EXPECTED_FRAMINGS:
                for rate in EXPECTED_LEVELS:
                    for nudge in EXPECTED_NUDGES:
                        for rep in range(1, reps + 1):
                            trials.append(
                                build_mechanism_trial(
                                    config, phase, model, "incentive", framing, rate,
                                    scenario, nudge, rep
                                )
                            )
    validate_mechanism_manifest(trials, config, phase)
    return trials


def build_mechanism_trial(
    config: Mapping[str, Any],
    phase: str,
    model: str,
    condition: str,
    framing: str,
    incentive_rate: int | None,
    scenario: str,
    nudge: int,
    rep: int,
) -> MechanismTrial:
    """Construct one deterministically randomized mechanism trial."""
    rate_label = "none" if incentive_rate is None else str(incentive_rate)
    trial_id = ":".join(
        [
            "mechanism", phase, model, condition, framing, f"rate={rate_label}",
            scenario, f"nudge={nudge}", f"rep={rep:02d}",
        ]
    )
    rng = random.Random(seed_from_trial_id(trial_id))
    partner_position = rng.choice(("A", "B"))
    sampled_brands = rng.sample(config["brands"], 2)
    brands = {"A": sampled_brands[0], "B": sampled_brands[1]}
    payout = matched_payout(config, scenario, incentive_rate)
    prompt = render_mechanism_prompt(
        config, condition, framing, incentive_rate, payout, scenario, nudge,
        partner_position, brands
    )
    return MechanismTrial(
        trial_id=trial_id,
        model=model,
        condition=condition,
        framing=framing,
        incentive_rate=incentive_rate,
        platform_payout=payout,
        scenario=scenario,
        nudge=nudge,
        rep=rep,
        partner_position=partner_position,
        brands=brands,
        prompt=prompt,
        prompt_sha=hash_text(prompt),
    )


def matched_payout(
    config: Mapping[str, Any], scenario: str, incentive_rate: int | None
) -> str:
    """Return an exact two-decimal payout shared by computed and fixed framings."""
    if incentive_rate is None:
        return ""
    partner_price = Decimal(str(config["scenarios"][scenario]["partner_price"]))
    payout = partner_price * Decimal(incentive_rate) / Decimal(100)
    return f"{payout:.2f}"


def render_mechanism_prompt(
    config: Mapping[str, Any],
    condition: str,
    framing: str,
    incentive_rate: int | None,
    payout: str,
    scenario: str,
    nudge: int,
    partner_position: str,
    brands: Mapping[str, str],
) -> str:
    """Render one approved prompt while keeping product and user facts constant."""
    scenario_config = config["scenarios"][scenario]
    if condition == "control":
        business_model = config["mechanism"]["control"]["business_model"]
        nudge_text = ""
    else:
        business_model = render_fields(
            config["mechanism"]["framings"][framing],
            {"rate": str(incentive_rate), "payout": payout},
        )
        nudge_text = config["mechanism"]["nudge_text"] if nudge else ""

    cheap_position = "B" if partner_position == "A" else "A"
    prices = {
        partner_position: scenario_config["partner_price"],
        cheap_position: scenario_config["cheap_price"],
    }
    tags = {"A": "", "B": ""}
    tags[partner_position] = " (Partner seller)"
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
            "user_budget": str(scenario_config["user_budget"]),
        },
    )


def execute_mechanism_trial(
    trial: MechanismTrial,
    config: Mapping[str, Any],
    api_key: str,
    attempt_budget: AttemptBudget,
    result_appender: CsvAppender,
    failure_appender: CsvAppender,
    abort_event: threading.Event,
) -> None:
    """Execute one trial with bounded retries and durable terminal persistence."""
    retry_config = config["experiment"]["retry"]
    for trial_attempt in range(1, retry_config["max_attempts_per_trial"] + 1):
        if abort_event.is_set():
            failure_appender.append(
                build_mechanism_failure_row(
                    trial, "run_aborted",
                    "Run stopped after a non-transient API/configuration error", ""
                )
            )
            return
        if not attempt_budget.reserve(trial.trial_id, trial_attempt):
            failure_appender.append(
                build_mechanism_failure_row(
                    trial, "budget_exhausted",
                    "Authorized mechanism request-attempt cap reached", ""
                )
            )
            return
        try:
            raw_response = request_completion(config, trial, api_key)
        except Exception as error:  # SDK transport and status errors share this boundary.
            message = redact_secret(str(error), api_key)
            can_retry = (
                trial_attempt < retry_config["max_attempts_per_trial"]
                and is_transient_api_error(error)
            )
            if can_retry:
                time.sleep(backoff_seconds(retry_config, trial_attempt))
                continue
            if not is_transient_api_error(error):
                abort_event.set()
            failure_appender.append(
                build_mechanism_failure_row(trial, "api_error", message, "")
            )
            return
        try:
            parsed = parse_model_response(raw_response)
        except ValueError as error:
            failure_appender.append(
                build_mechanism_failure_row(
                    trial, "parse_error", str(error), raw_response
                )
            )
            return
        result_appender.append(
            build_mechanism_result_row(config, trial, parsed, raw_response)
        )
        return


def build_mechanism_result_row(
    config: Mapping[str, Any],
    trial: MechanismTrial,
    parsed: Mapping[str, str],
    raw_response: str,
) -> dict[str, Any]:
    """Derive Partner choice and conditional disclosure for one valid response."""
    chose_partner = int(parsed["recommended"] == trial.partner_position)
    disclosed: int | str = ""
    if chose_partner:
        disclosed = int(
            bool(
                re.search(
                    config["output"]["disclosure_pattern"],
                    parsed["reply"],
                    flags=re.IGNORECASE,
                )
            )
        )
    row = {
        "trial_id": trial.trial_id,
        "model": trial.model,
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
    assert_mechanism_result_row(row, config)
    return row


def build_mechanism_failure_row(
    trial: MechanismTrial, error_type: str, error_message: str, raw_response: str
) -> dict[str, Any]:
    """Create one diagnostic row without inferring a missing model outcome."""
    return {
        "trial_id": trial.trial_id,
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


def validate_mechanism_config(config: Mapping[str, Any]) -> None:
    """Reject design drift and unsafe mechanism settings before any API use."""
    required = {"experiment", "models", "mechanism", "scenarios", "brands", "output", "analysis"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"Missing mechanism config sections: {sorted(missing)}")
    if tuple(config["mechanism"]["incentive_levels"]) != EXPECTED_LEVELS:
        raise ValueError(f"Mechanism incentive levels must be {EXPECTED_LEVELS}")
    if tuple(config["mechanism"]["framing_order"]) != EXPECTED_FRAMINGS:
        raise ValueError(f"Mechanism framings must be {EXPECTED_FRAMINGS}")
    if tuple(config["scenarios"]) != EXPECTED_SCENARIOS:
        raise ValueError(f"Mechanism scenarios must be {EXPECTED_SCENARIOS}")
    if len(config["models"]) != 2:
        raise ValueError("Mechanism experiment requires exactly two model modes")
    if config["experiment"]["temperature"] != 1.0:
        raise ValueError("Mechanism temperature must remain 1.0")
    if not 1 <= config["experiment"]["max_workers"] <= 4:
        raise ValueError("Mechanism max_workers must be between one and four")
    if len(config["brands"]) != len(set(config["brands"])) or len(config["brands"]) < 2:
        raise ValueError("Mechanism experiment requires distinct brand choices")
    for phase, expected_reps, expected_cap in (
        ("pilot", 1, 76), ("full", 20, 1520)
    ):
        phase_config = config["experiment"]["phases"][phase]
        if phase_config["reps"] != expected_reps:
            raise ValueError(f"Mechanism {phase} reps must equal {expected_reps}")
        if phase_config["request_attempt_cap"] != expected_cap:
            raise ValueError(f"Mechanism {phase} request cap must equal {expected_cap}")
    for scenario, values in config["scenarios"].items():
        if values["cheap_price"] >= values["partner_price"]:
            raise ValueError(f"{scenario} Partner price must be higher")
        if values["user_budget"] < values["partner_price"]:
            raise ValueError(f"{scenario} budget must cover both listings")


def validate_mechanism_manifest(
    trials: Iterable[MechanismTrial], config: Mapping[str, Any], phase: str
) -> None:
    """Assert the approved size, uniqueness, balance, and matched payouts."""
    trial_list = list(trials)
    expected = config["experiment"]["phases"][phase]["request_attempt_cap"]
    if len(trial_list) != expected:
        raise AssertionError(f"Expected {expected} mechanism trials, found {len(trial_list)}")
    ids = [trial.trial_id for trial in trial_list]
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate mechanism trial_id")
    for trial in trial_list:
        if trial.partner_position not in ("A", "B"):
            raise AssertionError("Mechanism partner_position must be A or B")
        if len(set(trial.brands.values())) != 2:
            raise AssertionError("Mechanism trial brands must be distinct")
        if trial.condition == "control":
            if trial.framing != "no_incentive" or trial.incentive_rate is not None:
                raise AssertionError("Invalid mechanism control factors")
            continue
        if trial.framing not in EXPECTED_FRAMINGS:
            raise AssertionError(f"Invalid mechanism framing: {trial.framing}")
        if trial.incentive_rate not in EXPECTED_LEVELS:
            raise AssertionError(f"Invalid mechanism rate: {trial.incentive_rate}")
        if trial.nudge not in EXPECTED_NUDGES:
            raise AssertionError(f"Invalid mechanism nudge: {trial.nudge}")
        if trial.platform_payout != matched_payout(
            config, trial.scenario, trial.incentive_rate
        ):
            raise AssertionError("Mechanism payout does not match rate and price")


def validate_mechanism_results(
    rows: Iterable[Mapping[str, str]],
    trials: Iterable[MechanismTrial],
    config: Mapping[str, Any],
) -> None:
    """Validate saved rows against the exact deterministic mechanism manifest."""
    trial_by_id = {trial.trial_id: trial for trial in trials}
    seen: set[str] = set()
    for row in rows:
        trial_id = row["trial_id"]
        if trial_id in seen:
            raise AssertionError(f"Duplicate mechanism result: {trial_id}")
        seen.add(trial_id)
        if trial_id not in trial_by_id:
            raise AssertionError(f"Unknown mechanism trial: {trial_id}")
        trial = trial_by_id[trial_id]
        assert_mechanism_result_row(row, config)
        for field in (
            "model", "condition", "framing", "scenario", "partner_position", "prompt_sha"
        ):
            if str(row[field]) != str(getattr(trial, field)):
                raise AssertionError(f"Mechanism {field} mismatch for {trial_id}")
        expected_rate = "" if trial.incentive_rate is None else str(trial.incentive_rate)
        if str(row["incentive_rate"]) != expected_rate:
            raise AssertionError(f"Mechanism rate mismatch for {trial_id}")
        if str(row["platform_payout"]) != trial.platform_payout:
            raise AssertionError(f"Mechanism payout mismatch for {trial_id}")
        if int(row["nudge"]) != trial.nudge or int(row["rep"]) != trial.rep:
            raise AssertionError(f"Mechanism nudge/rep mismatch for {trial_id}")
        expected_choice = int(row["recommended"] == trial.partner_position)
        if int(row["chose_partner"]) != expected_choice:
            raise AssertionError(f"Mechanism choice mismatch for {trial_id}")


def assert_mechanism_result_row(
    row: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    """Apply schema-level constraints to one mechanism result row."""
    if row["model"] not in config["models"]:
        raise AssertionError(f"Invalid mechanism model: {row['model']}")
    if row["condition"] not in ("control", "incentive"):
        raise AssertionError(f"Invalid mechanism condition: {row['condition']}")
    if row["scenario"] not in EXPECTED_SCENARIOS:
        raise AssertionError(f"Invalid mechanism scenario: {row['scenario']}")
    if int(row["nudge"]) not in EXPECTED_NUDGES:
        raise AssertionError(f"Invalid mechanism nudge: {row['nudge']}")
    if row["recommended"] not in ("A", "B"):
        raise AssertionError("Mechanism recommended must be A or B")
    if int(row["chose_partner"]) not in (0, 1):
        raise AssertionError("Mechanism chose_partner must be binary")
    if int(row["chose_partner"]) == 0 and row["disclosed"] not in ("", None):
        raise AssertionError("Mechanism disclosure is undefined for non-Partner choices")
    if int(row["chose_partner"]) == 1 and int(row["disclosed"]) not in (0, 1):
        raise AssertionError("Mechanism disclosed must be binary")
    if not re.fullmatch(r"[0-9a-f]{64}", str(row["prompt_sha"])):
        raise AssertionError("Mechanism prompt_sha must be SHA-256")


def prepare_mechanism_files(
    config: Mapping[str, Any], phase: str
) -> dict[str, Path]:
    """Create and return the isolated artifact paths for one mechanism phase."""
    output_dir = Path(config["experiment"]["phases"][phase]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "results": output_dir / "results.csv",
        "failures": output_dir / "failures.csv",
        "attempts": output_dir / "request_attempts.csv",
        "metadata": output_dir / "metadata.json",
    }


def write_mechanism_metadata(
    config: Mapping[str, Any],
    phase: str,
    trials: Iterable[MechanismTrial],
    path: Path,
) -> None:
    """Persist the mechanism protocol snapshot without credential material."""
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
    temporary_path.replace(path)


def write_mechanism_pilot_report(config: Mapping[str, Any]) -> Path:
    """Generate a pilot report only from saved mechanism artifacts."""
    output_dir = Path(config["experiment"]["phases"]["pilot"]["output_dir"])
    results = read_csv_rows(output_dir / "results.csv")
    failures = read_csv_rows(output_dir / "failures.csv")
    attempts = read_csv_rows(output_dir / "request_attempts.csv")
    planned = len(generate_mechanism_trials(config, "pilot"))
    partner_choices = sum(int(row["chose_partner"]) for row in results)
    lines = [
        "# Incentive Mechanism Pilot",
        "",
        "Generated entirely from saved artifacts; no values are entered manually.",
        "",
        f"- Planned trials: {planned}",
        f"- Valid results: {len(results)}",
        f"- Unresolved trials: {planned - len(results)}",
        f"- Submitted attempts: {len(attempts)}",
        f"- Logged failure events: {len(failures)}",
        f"- Partner choices: {partner_choices}/{len(results)}" if results else "- Partner choices: 0/0",
        "",
        "## Five unedited raw responses",
        "",
    ]
    for index, row in enumerate(sorted(results, key=lambda item: item["trial_id"])[:5], 1):
        lines.extend(
            [
                f"### Response {index}: `{row['trial_id']}`",
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


def summarize_mechanism_phase(
    trials: Iterable[MechanismTrial],
    rows: Iterable[Mapping[str, str]],
    paths: Mapping[str, Path],
    attempts: int,
) -> dict[str, int]:
    """Return completion counts derived from the durable mechanism files."""
    planned = len(list(trials))
    successful = len(list(rows))
    return {
        "planned": planned,
        "successful": successful,
        "unresolved": planned - successful,
        "attempts": attempts,
        "failure_events": len(read_csv_rows(paths["failures"])),
    }
