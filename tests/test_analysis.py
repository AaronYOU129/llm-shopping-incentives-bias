"""
Purpose:    Verify statistical tables, contrast tests, disclosure denominators, and
            Markdown rendering on controlled synthetic data without external calls.
Inputs:     config.yaml and in-memory balanced synthetic trial outcomes.
Outputs:    Pytest pass/fail evidence only.
Key Steps:  Build known cells, calculate Wilson summaries and contrasts, and assert
            requested dimensions, flags, and disclosure conditioning.
How to Run: python -m pytest -q tests/test_analysis.py
"""

from __future__ import annotations

import csv
import copy
from pathlib import Path

import pandas as pd

import analysis
import experiment
import judge


def make_balanced_data(config: dict) -> pd.DataFrame:
    """Build controlled balanced cells for descriptive and inferential tests."""
    records = []
    for model in config["models"]:
        for nudge in (0, 1):
            for arm_index, arm in enumerate(config["analysis"]["arm_order"]):
                for budget in config["analysis"]["budget_order"]:
                    for index in range(20):
                        chose = int(index < arm_index + 2)
                        records.append(
                            {
                                "trial_id": f"{model}:{nudge}:{arm}:{budget}:{index}",
                                "model": model,
                                "nudge": nudge,
                                "arm": arm,
                                "budget": budget,
                                "scenario": "headphones" if index % 2 == 0 else "shoes",
                                "partner_position": "A" if index % 2 == 0 else "B",
                                "chose_partner": chose,
                                "disclosed": float(index % 2) if chose else float("nan"),
                            }
                        )
    return pd.DataFrame(records)


def test_requested_choice_table_has_40_cells() -> None:
    """Produce every requested model-by-nudge-by-arm-by-budget summary cell."""
    config = experiment.load_config("config.yaml")
    table = analysis.build_partner_choice_table(make_balanced_data(config), config)
    assert len(table) == 40
    assert set(table["n"]) == {20}
    assert not table["flag_n_lt_20"].any()
    assert table[["ci_lower", "share", "ci_upper"]].notna().all().all()


def test_contrasts_and_holm_values_are_present() -> None:
    """Return all prespecified contrasts with valid multiplicity-adjusted p-values."""
    config = experiment.load_config("config.yaml")
    contrasts = analysis.build_contrasts(make_balanced_data(config), config)
    assert list(contrasts["contrast"]) == [
        "pct_vs_flat_both",
        "cpc_vs_pct_only",
        "cpc_vs_flat_only",
        "fixed_vs_sub",
    ]
    assert contrasts["p_value"].between(0, 1).all()
    assert contrasts["p_value_holm"].between(0, 1).all()


def test_disclosure_uses_only_partner_recommendations() -> None:
    """Use Partner recommendations as the disclosure-rate denominator."""
    config = experiment.load_config("config.yaml")
    data = make_balanced_data(config)
    table = analysis.build_disclosure_table(data, config).set_index("arm")
    expected_sub_partner_rows = len(data[(data["arm"] == "sub") & (data["chose_partner"] == 1)])
    assert table.loc["sub", "n_partner_recommendations"] == expected_sub_partner_rows
    assert 0 <= table.loc["sub", "disclosure_rate"] <= 1


def test_degenerate_z_test_falls_back_to_fisher() -> None:
    """Use a finite exact test when the z-test variance degenerates."""
    statistic, p_value, test_name = analysis.compare_two_proportions(0, 20, 0, 20)
    assert "Fisher" in test_name
    assert p_value == 1.0
    assert statistic != float("inf")


def test_separation_diagnostic_names_constant_interaction_cells() -> None:
    """Identify constant arm-by-budget cells that make logits unavailable."""
    data = pd.DataFrame(
        {
            "arm": ["sub", "sub", "pct", "pct"],
            "budget": ["only", "only", "both", "both"],
            "chose_partner": [0, 0, 0, 1],
        }
    )
    diagnostic = analysis.describe_separation(data)
    assert "1 of 2 arm × budget cells" in diagnostic
    assert "sub/only=0" in diagnostic


def test_joint_outcome_table_places_three_rates_side_by_side() -> None:
    """Report choice, disclosure, and fabrication rates in aligned cells."""
    config = experiment.load_config("config.yaml")
    data = make_balanced_data(config)
    judge_data = data[["trial_id"]].copy()
    judge_data["fabricated_claim"] = data["chose_partner"].astype(int)
    table = analysis.build_joint_outcome_table(data, judge_data, config)
    assert len(table) == 20
    assert set(table["n"]) == {40}
    assert {
        "chose_partner_rate",
        "disclosed_rate",
        "fabricated_claim_rate",
    }.issubset(table.columns)


def test_judge_version_comparison_counts_both_change_directions() -> None:
    """Count both label-change directions and preserve paired comparisons."""
    v1 = pd.DataFrame(
        {
            "trial_id": ["a", "b", "c", "d"],
            "fabricated_claim": [0, 0, 1, 1],
            "quote": ["", "", "old c", "old d"],
        }
    )
    v2 = pd.DataFrame(
        {
            "trial_id": ["a", "b", "c", "d"],
            "fabricated_claim": [0, 1, 0, 1],
            "quote": ["", "new b", "", "new d"],
        }
    )

    rows, summary = analysis.compare_judge_versions(v1, v2)

    assert len(rows) == 4
    assert summary["changed_0_to_1"] == 1
    assert summary["changed_1_to_0"] == 1
    assert summary["total_changed"] == 2
    assert summary["change_rate"] == 0.5


def test_binary_agreement_reports_false_positives_when_humans_are_all_zero() -> None:
    """Compute agreement and false positives under a degenerate human margin."""
    judged = pd.Series([1] * 4 + [0] * 16)
    human = pd.Series([0] * 20)

    result = analysis.calculate_binary_agreement(judged, human)

    assert result["agreement_count"] == 16
    assert result["agreement_rate"] == 0.8
    assert result["cohen_kappa"] == 0
    assert result["judge_1_human_0"] == 4


def test_corrected_partner_rate_uses_strata_and_finite_population_interval() -> None:
    """Apply design weights and exact finite-population bounds by validation stratum."""
    config = experiment.load_config("config.yaml")
    trial_ids = [f"partner-{index:03d}" for index in range(127)]
    results = pd.DataFrame({"trial_id": trial_ids, "chose_partner": [1] * 127})
    judge_data = pd.DataFrame(
        {
            "trial_id": trial_ids,
            "fabricated_claim": [1] * 22 + [0] * 105,
        }
    )
    agreement = {
        "status": "complete",
        "judge_0_human_0": 24,
        "judge_0_human_1": 4,
        "judge_1_human_0": 1,
        "judge_1_human_1": 21,
    }
    result = analysis.estimate_corrected_partner_fabrication(
        results, judge_data, agreement, config
    )
    assert result["estimated_fabricated_claim_count"] == 36
    assert result["corrected_fabricated_claim_rate"] == 36 / 127
    assert result["ci_lower"] == 27 / 127
    assert result["ci_upper"] == 52 / 127
    assert analysis.exact_hypergeometric_success_bounds(105, 28, 4, 0.95) == (
        6,
        31,
    )


def test_nonpartner_negative_validation_uses_completed_blind_sample(
    tmp_path: Path,
) -> None:
    """Estimate false negatives from a completed blind non-Partner sample."""
    config = copy.deepcopy(experiment.load_config("config.yaml"))
    judge_dir = tmp_path / "judge"
    judge_dir.mkdir()
    config["judge"]["output_dir"] = str(judge_dir)
    trial_ids = [f"nonpartner-{index:03d}" for index in range(30)]
    results = pd.DataFrame(
        {"trial_id": trial_ids, "chose_partner": [0] * len(trial_ids)}
    )
    judge_data = pd.DataFrame(
        {"trial_id": trial_ids, "fabricated_claim": [0] * len(trial_ids)}
    )
    sample_rows = [
        {
            "item_id": f"NP{index + 1:03d}",
            "listing_A": "A",
            "listing_B": "B",
            "reply": "Equivalent products.",
            "my_label": "0",
            "my_note": "",
        }
        for index in range(20)
    ]
    key_rows = [
        {"item_id": f"NP{index + 1:03d}", "trial_id": trial_ids[index]}
        for index in range(20)
    ]
    write_csv(
        judge_dir / "handcheck_nonpartner_negatives_v1.csv",
        config["output"]["handcheck_columns"],
        sample_rows,
    )
    write_csv(
        judge_dir / "handcheck_nonpartner_negatives_v1_key.csv",
        config["output"]["handcheck_key_columns"],
        key_rows,
    )

    result = analysis.evaluate_nonpartner_negative_handcheck(
        config, results, judge_data
    )

    assert result["status"] == "complete"
    assert result["judge_negative_nonpartner_population"] == 30
    assert result["human_positive_false_negatives"] == 0
    assert result["observed_false_negative_rate"] == 0
    assert result["ci_lower"] == 0
    assert 0 < result["ci_upper"] < 1


def test_complete_synthetic_pipeline_generates_all_analysis_outputs(
    monkeypatch, tmp_path: Path
) -> None:
    """Generate the complete analysis artifact set from synthetic saved inputs."""
    config = copy.deepcopy(experiment.load_config("config.yaml"))
    full_dir = tmp_path / "full"
    judge_dir = tmp_path / "judge"
    config["experiment"]["phases"]["full"]["output_dir"] = str(full_dir)
    config["judge"]["output_dir"] = str(judge_dir)
    full_dir.mkdir()
    judge_dir.mkdir()

    trials = experiment.generate_trials(config, "full")
    result_rows = []
    for trial in trials:
        chose_partner = int(trial.prompt_sha[-2:], 16) % 4 == 0
        recommended = (
            trial.partner_position
            if chose_partner
            else ("B" if trial.partner_position == "A" else "A")
        )
        reply = (
            "The Partner option has better build quality."
            if chose_partner
            else "Choose the lower-priced equivalent."
        )
        result_rows.append(
            experiment.build_result_row(
                config,
                trial,
                {"recommended": recommended, "reply": reply},
                f'{{"recommended":"{recommended}","reply":"{reply}"}}',
            )
        )
    write_csv(full_dir / "results.csv", config["output"]["result_columns"], result_rows)
    write_csv(full_dir / "failures.csv", config["output"]["failure_columns"], [])
    write_csv(full_dir / "request_attempts.csv", config["output"]["attempt_columns"], [])

    items = judge.build_judge_items(config, result_rows)
    judge_rows = [
        judge.build_judge_result(
            config,
            item,
            {
                "fabricated_claim": int(index < 22),
                "quote": "better build quality" if index < 22 else "",
            },
            "raw",
        )
        for index, item in enumerate(items)
    ]
    write_csv(
        judge_dir / "judge_results.csv",
        config["output"]["judge_result_columns"],
        judge_rows,
    )
    write_csv(
        judge_dir / "failures.csv",
        config["output"]["judge_failure_columns"],
        [],
    )
    write_csv(
        judge_dir / "request_attempts.csv",
        config["output"]["judge_attempt_columns"],
        [],
    )
    judge.create_handcheck_sample(
        config,
        result_rows,
        judge_rows,
        judge_dir / "handcheck_sample.csv",
        judge_dir / "handcheck_key.csv",
    )

    monkeypatch.chdir(tmp_path)
    report = analysis.analyze_full_results(config)
    assert report.exists()
    assert (full_dir / "partner_choice_table.csv").exists()
    assert (full_dir / "outcomes_by_arm_budget_nudge.csv").exists()
    assert (full_dir / "partner_choice.png").exists()
    assert (judge_dir / "handcheck_agreement.csv").exists()
    assert (judge_dir / "nonpartner_negative_validation_v1.csv").exists()
    assert "Agreement is pending" in report.read_text(encoding="utf-8")


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Write a test fixture using an explicit schema."""
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
