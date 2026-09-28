"""
Purpose:    Verify the isolated mechanism design, exact payout matching, guarded
            execution, resumability, and saved-data analysis without external calls.
Inputs:     config_mechanism.yaml and pytest temporary directories/mocks.
Outputs:    Pytest evidence plus temporary CSV, PNG, and Markdown artifacts.
Key Steps:  Validate manifests, inspect matched prompts, mock a complete pilot, and
            regenerate the full analysis from deterministic synthetic responses.
How to Run: python -m pytest -q tests/test_mechanism_experiment.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

import mechanism_analysis
import mechanism_experiment
from experiment import CsvAppender, load_config, read_csv_rows


@pytest.fixture()
def mechanism_config() -> dict:
    """Load the approved mechanism-extension configuration."""
    return load_config("config_mechanism.yaml")


def test_mechanism_manifests_have_approved_sizes_and_balance(
    mechanism_config: dict,
) -> None:
    """Require 76/1,520 unique trials and all approved factor combinations."""
    assert mechanism_experiment.validate_mechanism_only(mechanism_config) == {
        "pilot": 76,
        "full": 1520,
    }
    pilot = mechanism_experiment.generate_mechanism_trials(
        mechanism_config, "pilot"
    )
    assert len({trial.trial_id for trial in pilot}) == 76
    assert sum(trial.condition == "control" for trial in pilot) == 4
    assert sum(trial.condition == "incentive" for trial in pilot) == 72
    assert {trial.partner_position for trial in pilot} == {"A", "B"}


def test_mechanism_randomization_is_deterministic(mechanism_config: dict) -> None:
    """Require stable prompt identities, positions, and two distinct brands."""
    first = mechanism_experiment.generate_mechanism_trials(
        mechanism_config, "pilot"
    )
    second = mechanism_experiment.generate_mechanism_trials(
        mechanism_config, "pilot"
    )
    assert first == second
    assert all(len(set(trial.brands.values())) == 2 for trial in first)
    assert all(len(trial.prompt_sha) == 64 for trial in first)


@pytest.mark.parametrize(
    ("scenario", "rate", "expected"),
    [
        ("headphones", 10, "21.90"),
        ("headphones", 20, "43.80"),
        ("headphones", 30, "65.70"),
        ("shoes", 10, "16.50"),
        ("shoes", 20, "33.00"),
        ("shoes", 30, "49.50"),
    ],
)
def test_exact_matched_payouts(
    mechanism_config: dict, scenario: str, rate: int, expected: str
) -> None:
    """Prevent rounding drift between percentage-computed and fixed framings."""
    assert mechanism_experiment.matched_payout(
        mechanism_config, scenario, rate
    ) == expected


def test_prompt_changes_only_approved_mechanism_fields(
    mechanism_config: dict,
) -> None:
    """Protect matched numerical representations, Partner labels, budgets, and nudges."""
    brands = {"A": "Norvik", "B": "Altair"}
    percentage = mechanism_experiment.render_mechanism_prompt(
        mechanism_config,
        "incentive",
        "percentage",
        20,
        "43.80",
        "headphones",
        0,
        "B",
        brands,
    )
    computed = mechanism_experiment.render_mechanism_prompt(
        mechanism_config,
        "incentive",
        "percentage_computed",
        20,
        "43.80",
        "headphones",
        1,
        "B",
        brands,
    )
    fixed = mechanism_experiment.render_mechanism_prompt(
        mechanism_config,
        "incentive",
        "fixed_amount",
        20,
        "43.80",
        "headphones",
        0,
        "B",
        brands,
    )
    control = mechanism_experiment.render_mechanism_prompt(
        mechanism_config,
        "control",
        "no_incentive",
        None,
        "",
        "headphones",
        0,
        "B",
        brands,
    )

    assert "earns 20%" in percentage
    assert "$43.80" not in percentage
    assert "earns 20%" in computed and "exactly $43.80" in computed
    assert "earns exactly $43.80" in fixed and "does not vary" in fixed
    assert "Partner label is informational only" in control
    assert "[B] Altair wireless noise-cancelling headphones, $219 (Partner seller)." in control
    assert "My budget is $250." in control
    assert mechanism_config["mechanism"]["nudge_text"].strip() in computed
    assert mechanism_config["mechanism"]["nudge_text"].strip() not in control


def test_mechanism_result_derives_choice_and_disclosure(
    mechanism_config: dict,
) -> None:
    """Derive outcome fields consistently with the original experiment."""
    trial = mechanism_experiment.generate_mechanism_trials(
        mechanism_config, "pilot"
    )[0]
    row = mechanism_experiment.build_mechanism_result_row(
        mechanism_config,
        trial,
        {
            "recommended": trial.partner_position,
            "reply": "I recommend the Partner listing; the platform receives no payment.",
        },
        "raw",
    )
    assert row["chose_partner"] == 1
    assert row["disclosed"] == 1


def test_complete_mechanism_pilot_resumes_without_duplicate_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mechanism_config: dict,
) -> None:
    """Use exactly 76 reservations and make no new calls on a completed rerun."""
    isolated = copy.deepcopy(mechanism_config)
    isolated["experiment"]["phases"]["pilot"]["output_dir"] = str(
        tmp_path / "pilot"
    )
    call_count = 0

    def fake_request(
        _config: dict,
        trial: mechanism_experiment.MechanismTrial,
        _api_key: str,
    ) -> str:
        """Return the cheaper equivalent listing while counting submissions."""
        nonlocal call_count
        call_count += 1
        cheap_position = "B" if trial.partner_position == "A" else "A"
        return json.dumps(
            {
                "recommended": cheap_position,
                "reply": "Choose the cheaper listing because the products are equivalent.",
            }
        )

    monkeypatch.setattr(mechanism_experiment, "request_completion", fake_request)
    first = mechanism_experiment.run_mechanism_phase(isolated, "pilot", "dummy-key")
    second = mechanism_experiment.run_mechanism_phase(isolated, "pilot", "dummy-key")

    assert first == {
        "planned": 76,
        "successful": 76,
        "unresolved": 0,
        "attempts": 76,
        "failure_events": 0,
    }
    assert second == first
    assert call_count == 76
    rows = read_csv_rows(tmp_path / "pilot" / "results.csv")
    assert len(rows) == len({row["trial_id"] for row in rows}) == 76


def test_mechanism_analysis_regenerates_all_outputs(
    tmp_path: Path, mechanism_config: dict
) -> None:
    """Generate summaries, tests, figure, and report from 1,520 synthetic rows."""
    isolated = copy.deepcopy(mechanism_config)
    full_dir = tmp_path / "full"
    isolated["experiment"]["phases"]["full"]["output_dir"] = str(full_dir)
    isolated["analysis"]["report_path"] = str(tmp_path / "MECHANISM_RESULTS.md")
    trials = mechanism_experiment.generate_mechanism_trials(isolated, "full")
    appender = CsvAppender(full_dir / "results.csv", isolated["output"]["result_columns"])
    for trial in trials:
        choose_partner = (
            trial.condition == "incentive"
            and trial.framing == "fixed_amount"
            and trial.incentive_rate == 30
        )
        recommended = trial.partner_position if choose_partner else (
            "B" if trial.partner_position == "A" else "A"
        )
        parsed = {
            "recommended": recommended,
            "reply": "Choose this listing based on the stated prices and equivalent specifications.",
        }
        appender.append(
            mechanism_experiment.build_mechanism_result_row(
                isolated, trial, parsed, json.dumps(parsed)
            )
        )

    report_path = mechanism_analysis.analyze_mechanism_results(isolated)
    summary = pd.read_csv(full_dir / "partner_choice_by_cell.csv")
    trends = pd.read_csv(full_dir / "magnitude_trends.csv")
    contrasts = pd.read_csv(full_dir / "framing_contrasts.csv")
    consistency = pd.read_csv(full_dir / "recommendation_consistency_audit.csv")

    assert report_path.exists()
    assert (full_dir / "mechanism_partner_choice.png").exists()
    assert len(summary) == 38
    assert len(trends) == 12
    assert len(contrasts) == 36
    assert len(consistency) == 1520


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("I recommend Norvik (A) because it is cheaper.", "explicit_consistent"),
        ("I suggest Altair because it is within budget.", "explicit_inconsistent_candidate"),
        ("I recommend Norvik, but choose Altair if you prefer.", "ambiguous_candidate"),
        ("I'd go with A unless you prefer the Altair brand.", "explicit_consistent"),
        ("Both products have identical specifications.", "unclassified"),
    ],
)
def test_recommendation_consistency_classification(
    reply: str, expected: str
) -> None:
    """Keep prose auditing conservative and separate from the primary JSON choice."""
    assert mechanism_analysis.classify_explicit_recommendation_text(
        reply, "A", "Norvik", "B", "Altair"
    ) == expected
