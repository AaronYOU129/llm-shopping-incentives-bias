"""
Purpose:
    Derive every reported result from saved artifacts. Keeping estimation and prose in
    one reproducible pipeline prevents the narrative from drifting from the evidence.

Inputs:
    config.yaml; outputs/full/results.csv; versioned judge CSVs; blinded hand-check
    workbooks and their private item keys.

Outputs:
    Statistical CSVs, validation summaries, logit status files, partner_choice.png,
    and RESULTS.md.

Key Steps:
    1. Load and validate completed experiment and judge data.
    2. Calculate prespecified rates, intervals, models, and contrasts.
    3. Evaluate human checks and compare judge versions.
    4. Render the figure, tables, diagnostics, and evidence-linked report.

Main Flow:
    analyze_full_results()
        -> load and validate full and judge data
        -> build descriptive tables and partner-choice figure
        -> fit_model_logits()
            |-- valid fit       -> logit table
            `-- separation      -> explicit status file
        -> evaluate human checks and judge-version changes
        -> write_results_report()
        `-- RESULTS.md and analysis artifacts

How to Run:
    python run_all.py analyze
"""

from __future__ import annotations

import itertools
import math
import os
import re
import warnings
from pathlib import Path
from typing import Any, Mapping

# A project-local cache keeps headless plotting writable in restricted environments.
os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact, hypergeom
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint, proportions_ztest
from statsmodels.tools.sm_exceptions import (
    ConvergenceWarning,
    PerfectSeparationError,
    PerfectSeparationWarning,
)

from experiment import generate_trials, read_csv_rows, validate_result_rows
from judge import (
    build_judge_items,
    resolve_judge_version_config,
    validate_judge_result_rows,
)


def analyze_full_results(config: Mapping[str, Any]) -> Path:
    """Generate every requested output from a complete, validated full result set."""
    output_dir = Path(config["experiment"]["phases"]["full"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    results = load_full_dataframe(config, output_dir)
    judge_results = load_judge_dataframe(config)

    choice_table = build_partner_choice_table(results, config)
    choice_table.to_csv(output_dir / "partner_choice_table.csv", index=False)
    create_partner_choice_figure(choice_table, config, output_dir)

    logit_outputs = fit_model_logits(results, config, output_dir)
    contrasts = build_contrasts(results, config)
    contrasts.to_csv(output_dir / "contrasts.csv", index=False)
    disclosure = build_disclosure_table(results, config)
    disclosure.to_csv(output_dir / "disclosure_by_arm.csv", index=False)
    outcomes = build_joint_outcome_table(results, judge_results, config)
    outcomes.to_csv(output_dir / "outcomes_by_arm_budget_nudge.csv", index=False)
    agreement = evaluate_handcheck(config, judge_results)
    agreement_path = Path(config["judge"]["output_dir"]) / "handcheck_agreement.csv"
    pd.DataFrame([agreement]).to_csv(agreement_path, index=False)
    corrected_partner_rate = estimate_corrected_partner_fabrication(
        results, judge_results, agreement, config
    )
    corrected_path = (
        Path(config["judge"]["output_dir"])
        / "corrected_partner_fabricated_claim.csv"
    )
    pd.DataFrame([corrected_partner_rate]).to_csv(corrected_path, index=False)
    nonpartner_validation = evaluate_nonpartner_negative_handcheck(
        config, results, judge_results
    )
    nonpartner_validation_path = (
        Path(config["judge"]["output_dir"])
        / "nonpartner_negative_validation_v1.csv"
    )
    pd.DataFrame([nonpartner_validation]).to_csv(
        nonpartner_validation_path, index=False
    )
    v2_results = load_optional_judge_v2_dataframe(config)
    v2_outcomes = None
    v2_comparison = {"status": "pending rubric-v2 results"}
    v2_agreement = {"status": "pending rubric-v2 results"}
    v2_nonpartner_agreement = {"status": "pending rubric-v2 results"}
    v2_recommendation_summary = None
    if v2_results is not None:
        v2_outcomes = build_joint_outcome_table(results, v2_results, config)
        v2_outcomes.to_csv(
            output_dir / "outcomes_by_arm_budget_nudge_v2.csv", index=False
        )
        comparison_rows, v2_comparison = compare_judge_versions(
            judge_results, v2_results
        )
        v2_dir = Path(config["judge_v2"]["output_dir"])
        comparison_rows.to_csv(v2_dir / "label_comparison_vs_v1.csv", index=False)
        pd.DataFrame([v2_comparison]).to_csv(
            v2_dir / "label_change_summary.csv", index=False
        )
        v2_agreement = evaluate_handcheck(config, v2_results)
        pd.DataFrame([v2_agreement]).to_csv(
            v2_dir / "agreement_on_v1_handcheck.csv", index=False
        )
        v2_nonpartner_agreement = evaluate_nonpartner_handcheck_agreement(
            config, v2_results
        )
        pd.DataFrame([v2_nonpartner_agreement]).to_csv(
            v2_dir / "agreement_on_nonpartner_handcheck.csv", index=False
        )
        v2_recommendation_summary = build_fabricated_rate_by_recommendation(
            results, v2_results
        )
        v2_recommendation_summary.to_csv(
            v2_dir / "fabricated_claim_by_recommendation.csv", index=False
        )

    report_path = Path("RESULTS.md")
    write_results_report(
        config,
        output_dir,
        choice_table,
        contrasts,
        disclosure,
        outcomes,
        agreement,
        corrected_partner_rate,
        nonpartner_validation,
        v2_outcomes,
        v2_comparison,
        v2_agreement,
        v2_nonpartner_agreement,
        v2_recommendation_summary,
        logit_outputs,
        report_path,
    )
    return report_path


def load_full_dataframe(config: Mapping[str, Any], output_dir: Path) -> pd.DataFrame:
    """Validate full results against the deterministic 1,600-trial manifest."""
    rows = read_csv_rows(output_dir / "results.csv")
    trials = generate_trials(config, "full")
    validate_result_rows(rows, trials, config)
    if len(rows) != len(trials):
        raise ValueError(f"Full results are incomplete: {len(rows)}/{len(trials)} valid rows")

    data = pd.DataFrame(rows)
    for column in ("nudge", "rep", "chose_partner"):
        data[column] = pd.to_numeric(data[column], errors="raise").astype(int)
    data["disclosed"] = pd.to_numeric(data["disclosed"], errors="coerce")
    data["arm"] = pd.Categorical(
        data["arm"], categories=config["analysis"]["arm_order"], ordered=True
    )
    data["budget"] = pd.Categorical(
        data["budget"], categories=config["analysis"]["budget_order"], ordered=True
    )
    return data


def load_judge_dataframe(
    config: Mapping[str, Any], judge_key: str = "judge"
) -> pd.DataFrame:
    """Load and validate one post-hoc judgment for every full-run reply."""
    scoped_config = resolve_judge_version_config(config, judge_key)
    full_dir = Path(scoped_config["experiment"]["phases"]["full"]["output_dir"])
    full_rows = read_csv_rows(full_dir / "results.csv")
    items = build_judge_items(scoped_config, full_rows)
    judge_dir = Path(scoped_config["judge"]["output_dir"])
    rows = read_csv_rows(judge_dir / "judge_results.csv")
    validate_judge_result_rows(rows, items, scoped_config)
    if len(rows) != len(items):
        raise ValueError(f"Judge results are incomplete: {len(rows)}/{len(items)} valid rows")
    data = pd.DataFrame(rows)
    data["fabricated_claim"] = pd.to_numeric(
        data["fabricated_claim"], errors="raise"
    ).astype(int)
    return data


def load_optional_judge_v2_dataframe(
    config: Mapping[str, Any],
) -> pd.DataFrame | None:
    """Load v2 only after its independently capped run is complete."""
    result_path = Path(config["judge_v2"]["output_dir"]) / "judge_results.csv"
    if not result_path.exists():
        return None
    try:
        return load_judge_dataframe(config, "judge_v2")
    except ValueError as error:
        if "incomplete" in str(error):
            return None
        raise


def build_partner_choice_table(
    data: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Calculate requested model × nudge × arm × budget shares and Wilson CIs."""
    records: list[dict[str, Any]] = []
    alpha = 1 - config["analysis"]["confidence_level"]
    factor_cells = itertools.product(
        config["models"],
        (0, 1),
        config["analysis"]["arm_order"],
        config["analysis"]["budget_order"],
    )
    for model, nudge, arm, budget in factor_cells:
        cell = data[
            (data["model"] == model)
            & (data["nudge"] == nudge)
            & (data["arm"] == arm)
            & (data["budget"] == budget)
        ]
        n = len(cell)
        choices = int(cell["chose_partner"].sum())
        lower, upper = wilson_interval(choices, n, alpha)
        records.append(
            {
                "model": model,
                "nudge": nudge,
                "arm": arm,
                "budget": budget,
                "n": n,
                "partner_choices": choices,
                "share": choices / n if n else np.nan,
                "ci_lower": lower,
                "ci_upper": upper,
                "flag_n_lt_20": n < 20,
            }
        )
    return pd.DataFrame(records)


def create_partner_choice_figure(
    table: pd.DataFrame, config: Mapping[str, Any], output_dir: Path
) -> None:
    """Draw grouped budget bars in one panel for every model × nudge condition."""
    figure_config = config["analysis"]["figure"]
    models = list(config["models"])
    arms = config["analysis"]["arm_order"]
    budgets = config["analysis"]["budget_order"]
    figure, axes = plt.subplots(
        len(models),
        2,
        figsize=(figure_config["width_inches"], figure_config["height_inches"]),
        sharey=True,
        constrained_layout=True,
    )
    axes_array = np.atleast_2d(axes)
    x_positions = np.arange(len(arms))
    bar_width = 0.36
    colors = {"both": "#2563EB", "only": "#F97316"}

    for model_index, model in enumerate(models):
        for nudge in (0, 1):
            axis = axes_array[model_index, nudge]
            panel = table[(table["model"] == model) & (table["nudge"] == nudge)]
            for budget_index, budget in enumerate(budgets):
                budget_rows = (
                    panel[panel["budget"] == budget]
                    .set_index("arm")
                    .reindex(arms)
                )
                shares = budget_rows["share"].to_numpy(dtype=float)
                lower_errors = shares - budget_rows["ci_lower"].to_numpy(dtype=float)
                upper_errors = budget_rows["ci_upper"].to_numpy(dtype=float) - shares
                offsets = x_positions + (budget_index - 0.5) * bar_width
                axis.bar(
                    offsets,
                    shares,
                    bar_width,
                    label=budget,
                    color=colors[budget],
                    yerr=np.vstack([lower_errors, upper_errors]),
                    capsize=3,
                    error_kw={"elinewidth": 1, "capthick": 1},
                )
            axis.set_title(f"{model} | nudge={nudge}")
            axis.set_xticks(x_positions, arms)
            axis.set_ylim(0, 1)
            axis.grid(axis="y", alpha=0.25)
            axis.set_xlabel("Platform payment arm")
            if nudge == 0:
                axis.set_ylabel("Share choosing Partner product")
            if model_index == 0 and nudge == 1:
                axis.legend(title="Budget", loc="upper right")

    figure.suptitle("Partner-product recommendations by model mode, nudge, arm, and budget")
    figure.savefig(
        output_dir / figure_config["filename"],
        dpi=figure_config["dpi"],
        bbox_inches="tight",
    )
    plt.close(figure)


def fit_model_logits(
    data: pd.DataFrame, config: Mapping[str, Any], output_dir: Path
) -> dict[str, dict[str, Any]]:
    """Fit the prespecified robust logit separately for each model condition."""
    outputs: dict[str, dict[str, Any]] = {}
    formula = config["analysis"]["logit_formula"]
    covariance = config["analysis"]["robust_covariance"]
    for model in config["models"]:
        model_data = data[data["model"] == model].copy()
        slug = slugify(model)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                fitted = smf.logit(formula, data=model_data).fit(
                    disp=False, cov_type=covariance
                )
            problematic = [
                warning
                for warning in caught
                if issubclass(
                    warning.category, (PerfectSeparationWarning, ConvergenceWarning)
                )
            ]
            converged = bool(fitted.mle_retvals.get("converged", False))
            finite = bool(
                np.isfinite(fitted.params.to_numpy()).all()
                and np.isfinite(fitted.bse.to_numpy()).all()
            )
            if problematic or not converged or not finite:
                warning_text = "; ".join(str(item.message) for item in problematic)
                raise RuntimeError(
                    warning_text or "Logit did not converge to finite coefficients"
                )
            coefficient_table = format_logit_table(fitted, len(model_data))
            path = output_dir / f"logit_{slug}.csv"
            coefficient_table.to_csv(path, index=False)
            outputs[model] = {
                "status": "converged",
                "path": path,
                "table": coefficient_table,
            }
        except (PerfectSeparationError, np.linalg.LinAlgError, RuntimeError, ValueError) as error:
            separation = describe_separation(model_data)
            if separation:
                status = (
                    f"Logit unavailable because complete/quasi-complete separation is present: "
                    f"{separation} Fit error: {type(error).__name__}: {error}"
                )
            else:
                status = f"Logit unavailable: {type(error).__name__}: {error}"
            path = output_dir / f"logit_{slug}_status.txt"
            path.write_text(status + "\n", encoding="utf-8")
            outputs[model] = {"status": status, "path": path, "table": None}
    return outputs


def describe_separation(model_data: pd.DataFrame) -> str:
    """Describe constant arm × budget cells represented by the interaction terms."""
    grouped = model_data.groupby(["arm", "budget"], observed=True)["chose_partner"]
    constant_cells = [
        f"{arm}/{budget}={int(values.iloc[0])}"
        for (arm, budget), values in grouped
        if values.nunique() == 1
    ]
    if not constant_cells:
        return ""
    return (
        f"chose_partner is constant in {len(constant_cells)} of "
        f"{grouped.ngroups} arm × budget cells ({', '.join(constant_cells)})."
    )


def build_contrasts(data: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    """Run the four prespecified arm comparisons on their requested budget subsets."""
    alpha = 1 - config["analysis"]["confidence_level"]
    records: list[dict[str, Any]] = []
    for contrast in config["analysis"]["contrasts"]:
        subset = data
        if contrast["budget"] != "all":
            subset = subset[subset["budget"] == contrast["budget"]]
        first = subset[subset["arm"] == contrast["arm_1"]]["chose_partner"]
        second = subset[subset["arm"] == contrast["arm_2"]]["chose_partner"]
        count_1, count_2 = int(first.sum()), int(second.sum())
        n_1, n_2 = len(first), len(second)
        share_1 = count_1 / n_1
        share_2 = count_2 / n_2
        ci_1 = wilson_interval(count_1, n_1, alpha)
        ci_2 = wilson_interval(count_2, n_2, alpha)
        statistic, p_value, test_used = compare_two_proportions(
            count_1, n_1, count_2, n_2
        )
        records.append(
            {
                "contrast": contrast["name"],
                "budget": contrast["budget"],
                "arm_1": contrast["arm_1"],
                "arm_2": contrast["arm_2"],
                "n_1": n_1,
                "partner_choices_1": count_1,
                "share_1": share_1,
                "ci_lower_1": ci_1[0],
                "ci_upper_1": ci_1[1],
                "n_2": n_2,
                "partner_choices_2": count_2,
                "share_2": share_2,
                "ci_lower_2": ci_2[0],
                "ci_upper_2": ci_2[1],
                "difference_arm1_minus_arm2": share_1 - share_2,
                "test": test_used,
                "statistic": statistic,
                "p_value": p_value,
                "ci_overlap": intervals_overlap(ci_1, ci_2),
                "flag_n_lt_20": n_1 < 20 or n_2 < 20,
            }
        )
    table = pd.DataFrame(records)
    table["p_value_holm"] = multipletests(
        table["p_value"].to_numpy(), method=config["analysis"]["p_adjustment"]
    )[1]
    return table


def build_disclosure_table(
    data: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Estimate disclosure only among rows that recommend the Partner product."""
    alpha = 1 - config["analysis"]["confidence_level"]
    partner_rows = data[data["chose_partner"] == 1]
    records: list[dict[str, Any]] = []
    for arm in config["analysis"]["arm_order"]:
        cell = partner_rows[partner_rows["arm"] == arm]
        n = len(cell)
        disclosed = int(cell["disclosed"].sum()) if n else 0
        lower, upper = wilson_interval(disclosed, n, alpha)
        records.append(
            {
                "arm": arm,
                "n_partner_recommendations": n,
                "disclosed_count": disclosed,
                "disclosure_rate": disclosed / n if n else np.nan,
                "ci_lower": lower,
                "ci_upper": upper,
                "flag_n_lt_20": n < 20,
            }
        )
    return pd.DataFrame(records)


def build_joint_outcome_table(
    data: pd.DataFrame,
    judge_data: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Report primary and post-hoc rates together by arm × budget × nudge."""
    merged = data.merge(
        judge_data[["trial_id", "fabricated_claim"]],
        on="trial_id",
        how="left",
        validate="one_to_one",
    )
    if merged["fabricated_claim"].isna().any():
        raise ValueError("At least one full result lacks a fabricated_claim judgment")
    alpha = 1 - config["analysis"]["confidence_level"]
    records: list[dict[str, Any]] = []
    cells = itertools.product(
        config["analysis"]["arm_order"],
        config["analysis"]["budget_order"],
        (0, 1),
    )
    for arm, budget, nudge in cells:
        cell = merged[
            (merged["arm"] == arm)
            & (merged["budget"] == budget)
            & (merged["nudge"] == nudge)
        ]
        n = len(cell)
        partner_choices = int(cell["chose_partner"].sum())
        partner_ci = wilson_interval(partner_choices, n, alpha)
        partner_rows = cell[cell["chose_partner"] == 1]
        disclosure_n = len(partner_rows)
        disclosed = int(partner_rows["disclosed"].sum()) if disclosure_n else 0
        disclosure_ci = wilson_interval(disclosed, disclosure_n, alpha)
        fabricated = int(cell["fabricated_claim"].sum())
        fabricated_ci = wilson_interval(fabricated, n, alpha)
        records.append(
            {
                "arm": arm,
                "budget": budget,
                "nudge": nudge,
                "n": n,
                "chose_partner_count": partner_choices,
                "chose_partner_rate": partner_choices / n,
                "chose_partner_ci_lower": partner_ci[0],
                "chose_partner_ci_upper": partner_ci[1],
                "disclosure_denominator_partner_recommendations": disclosure_n,
                "disclosed_count": disclosed,
                "disclosed_rate": disclosed / disclosure_n if disclosure_n else np.nan,
                "disclosed_ci_lower": disclosure_ci[0],
                "disclosed_ci_upper": disclosure_ci[1],
                "fabricated_claim_count": fabricated,
                "fabricated_claim_rate": fabricated / n,
                "fabricated_claim_ci_lower": fabricated_ci[0],
                "fabricated_claim_ci_upper": fabricated_ci[1],
                "flag_n_lt_20": n < 20,
            }
        )
    return pd.DataFrame(records)


def compare_judge_versions(
    v1_data: pd.DataFrame, v2_data: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create a complete item-level audit and an aggregate label-change summary."""
    comparison = v1_data[["trial_id", "fabricated_claim", "quote"]].merge(
        v2_data[["trial_id", "fabricated_claim", "quote"]],
        on="trial_id",
        suffixes=("_v1", "_v2"),
        validate="one_to_one",
    )
    if len(comparison) != len(v1_data) or len(comparison) != len(v2_data):
        raise ValueError("Judge versions do not cover the same trial IDs")
    comparison["label_changed"] = (
        comparison["fabricated_claim_v1"] != comparison["fabricated_claim_v2"]
    ).astype(int)
    comparison["change_direction"] = (
        comparison["fabricated_claim_v1"].astype(str)
        + "->"
        + comparison["fabricated_claim_v2"].astype(str)
    )
    comparison = comparison.rename(
        columns={
            "fabricated_claim_v1": "v1_fabricated_claim",
            "fabricated_claim_v2": "v2_fabricated_claim",
            "quote_v1": "v1_quote",
            "quote_v2": "v2_quote",
        }
    )
    directions = comparison["change_direction"].value_counts()
    changed = int(comparison["label_changed"].sum())
    summary = {
        "status": "complete",
        "total_replies": len(comparison),
        "v1_positive": int(comparison["v1_fabricated_claim"].sum()),
        "v2_positive": int(comparison["v2_fabricated_claim"].sum()),
        "unchanged_0_to_0": int(directions.get("0->0", 0)),
        "changed_0_to_1": int(directions.get("0->1", 0)),
        "changed_1_to_0": int(directions.get("1->0", 0)),
        "unchanged_1_to_1": int(directions.get("1->1", 0)),
        "total_changed": changed,
        "change_rate": changed / len(comparison),
    }
    columns = [
        "trial_id",
        "v1_fabricated_claim",
        "v2_fabricated_claim",
        "label_changed",
        "change_direction",
        "v1_quote",
        "v2_quote",
    ]
    return comparison[columns], summary


def build_fabricated_rate_by_recommendation(
    results: pd.DataFrame, judge_data: pd.DataFrame
) -> pd.DataFrame:
    """Summarize revised labels separately for Partner and non-Partner choices."""
    merged = results[["trial_id", "chose_partner"]].merge(
        judge_data[["trial_id", "fabricated_claim"]],
        on="trial_id",
        validate="one_to_one",
    )
    records = []
    for chose_partner, label in ((0, "non-Partner"), (1, "Partner")):
        cell = merged[merged["chose_partner"] == chose_partner]
        positives = int(cell["fabricated_claim"].sum())
        records.append(
            {
                "recommendation": label,
                "n": len(cell),
                "fabricated_claim_count": positives,
                "fabricated_claim_rate": positives / len(cell),
            }
        )
    return pd.DataFrame(records)


def evaluate_handcheck(
    config: Mapping[str, Any], judge_data: pd.DataFrame
) -> dict[str, Any]:
    """Calculate agreement after all 50 labels in the blinded workbook are valid."""
    judge_dir = Path(config["judge"]["output_dir"])
    workbook_path = judge_dir / "handcheck_sample.xlsx"
    csv_path = judge_dir / "handcheck_sample.csv"
    key_path = judge_dir / "handcheck_key.csv"
    required = config["judge"]["handcheck"]["sample_size"]
    if not workbook_path.exists() and not csv_path.exists():
        return pending_agreement(required, 0)
    if not key_path.exists():
        raise ValueError("Hand-check item key is missing")

    sample = (
        pd.read_excel(workbook_path, dtype=str, keep_default_na=False)
        if workbook_path.exists()
        else pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    )
    required_columns = set(config["output"]["handcheck_columns"])
    if not required_columns.issubset(sample.columns):
        raise ValueError("Hand-check workbook columns do not match the approved template")
    if len(sample) != required or sample["item_id"].duplicated().any():
        raise ValueError(f"Hand-check sample must contain {required} unique item IDs")

    labels = sample["my_label"].str.strip()
    invalid = labels[~labels.isin(("", "0", "1"))]
    if not invalid.empty:
        raise ValueError("my_label cells must be blank, 0, or 1")
    completed = int(labels.isin(("0", "1")).sum())
    if completed < required:
        return pending_agreement(required, completed)

    key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    if (
        len(key) != required
        or key["item_id"].duplicated().any()
        or key["trial_id"].duplicated().any()
    ):
        raise ValueError(f"Hand-check key must contain {required} unique mappings")
    if set(sample["item_id"]) != set(key["item_id"]):
        raise ValueError("Hand-check workbook item IDs do not match the private key")
    trial_ids = sample["item_id"].map(key.set_index("item_id")["trial_id"])
    human = labels.astype(int)
    judge_by_id = judge_data.set_index("trial_id")["fabricated_claim"]
    if not set(trial_ids).issubset(set(judge_by_id.index)):
        raise ValueError("Hand-check key contains an unknown trial_id")
    judged = trial_ids.map(judge_by_id).astype(int)
    return calculate_binary_agreement(judged, human)


def evaluate_nonpartner_handcheck_agreement(
    config: Mapping[str, Any], judge_data: pd.DataFrame
) -> dict[str, Any]:
    """Compare any judge version with the completed 20-case non-Partner review."""
    judge_dir = Path(config["judge"]["output_dir"])
    workbook_path = judge_dir / "handcheck_nonpartner_negatives_v1.xlsx"
    csv_path = judge_dir / "handcheck_nonpartner_negatives_v1.csv"
    key_path = judge_dir / "handcheck_nonpartner_negatives_v1_key.csv"
    required = config["judge"]["nonpartner_handcheck"]["sample_size"]
    if not workbook_path.exists() and not csv_path.exists():
        return pending_agreement(required, 0)
    sample = (
        pd.read_excel(workbook_path, dtype=str, keep_default_na=False)
        if workbook_path.exists()
        else pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    )
    if len(sample) != required or sample["item_id"].duplicated().any():
        raise ValueError(
            f"Non-Partner hand-check must contain {required} unique item IDs"
        )
    labels = sample["my_label"].str.strip()
    invalid = labels[~labels.isin(("", "0", "1"))]
    if not invalid.empty:
        raise ValueError("Non-Partner my_label cells must be blank, 0, or 1")
    completed = int(labels.isin(("0", "1")).sum())
    if completed < required:
        return pending_agreement(required, completed)
    if not key_path.exists():
        raise ValueError("Non-Partner hand-check item key is missing")
    key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    if len(key) != required or key["item_id"].duplicated().any():
        raise ValueError(
            f"Non-Partner hand-check key must contain {required} unique mappings"
        )
    if set(sample["item_id"]) != set(key["item_id"]):
        raise ValueError("Non-Partner hand-check item IDs do not match the private key")
    trial_ids = sample["item_id"].map(key.set_index("item_id")["trial_id"])
    judge_by_id = judge_data.set_index("trial_id")["fabricated_claim"]
    if not set(trial_ids).issubset(set(judge_by_id.index)):
        raise ValueError("Non-Partner hand-check key contains an unknown trial_id")
    judged = trial_ids.map(judge_by_id).astype(int)
    return calculate_binary_agreement(judged, labels.astype(int))


def calculate_binary_agreement(
    judged: pd.Series, human: pd.Series
) -> dict[str, Any]:
    """Calculate agreement, kappa, and the judge-by-human confusion counts."""
    required = len(human)
    agreement_count = int((judged.to_numpy() == human.to_numpy()).sum())
    observed = agreement_count / required
    judge_positive = float(judged.mean())
    human_positive = float(human.mean())
    expected = judge_positive * human_positive + (1 - judge_positive) * (1 - human_positive)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else np.nan
    return {
        "status": "complete",
        "required_n": required,
        "completed_n": required,
        "agreement_count": agreement_count,
        "agreement_rate": observed,
        "cohen_kappa": kappa,
        "judge_0_human_0": int(((judged == 0) & (human == 0)).sum()),
        "judge_0_human_1": int(((judged == 0) & (human == 1)).sum()),
        "judge_1_human_0": int(((judged == 1) & (human == 0)).sum()),
        "judge_1_human_1": int(((judged == 1) & (human == 1)).sum()),
    }


def pending_agreement(required: int, completed: int) -> dict[str, Any]:
    """Return an explicit non-result while blinded coding remains incomplete."""
    return {
        "status": "pending human hand-check",
        "required_n": required,
        "completed_n": completed,
        "agreement_count": "",
        "agreement_rate": "",
        "cohen_kappa": "",
        "judge_0_human_0": "",
        "judge_0_human_1": "",
        "judge_1_human_0": "",
        "judge_1_human_1": "",
    }


def estimate_corrected_partner_fabrication(
    results: pd.DataFrame,
    judge_data: pd.DataFrame,
    agreement: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Estimate the Partner rate using the validation design and exact finite CI."""
    if agreement["status"] != "complete":
        return {"status": "pending completed human hand-check"}

    merged = results[["trial_id", "chose_partner"]].merge(
        judge_data[["trial_id", "fabricated_claim"]],
        on="trial_id",
        validate="one_to_one",
    )
    partner = merged[merged["chose_partner"] == 1]
    judge_positive_population = int(partner["fabricated_claim"].sum())
    judge_negative_population = len(partner) - judge_positive_population
    judge_positive_sample = (
        agreement["judge_1_human_0"] + agreement["judge_1_human_1"]
    )
    judge_negative_sample = (
        agreement["judge_0_human_0"] + agreement["judge_0_human_1"]
    )
    if judge_positive_sample != judge_positive_population:
        raise ValueError("Corrected Partner rate requires a census of judge positives")
    if judge_negative_sample != config["judge"]["handcheck"]["partner_negative_count"]:
        raise ValueError("Corrected Partner rate has the wrong negative-stratum sample size")

    human_positive_in_positive_stratum = agreement["judge_1_human_1"]
    human_positive_in_negative_stratum = agreement["judge_0_human_1"]
    # Only sampled judge negatives need weighting; judge positives form a census.
    estimated_negative_stratum_claims = (
        judge_negative_population
        * human_positive_in_negative_stratum
        / judge_negative_sample
    )
    estimated_total_claims = (
        human_positive_in_positive_stratum + estimated_negative_stratum_claims
    )
    total_partner = len(partner)
    confidence_level = config["analysis"]["confidence_level"]
    negative_lower, negative_upper = exact_hypergeometric_success_bounds(
        population_size=judge_negative_population,
        sample_size=judge_negative_sample,
        observed_successes=human_positive_in_negative_stratum,
        confidence_level=confidence_level,
    )
    return {
        "status": "complete",
        "partner_recommendations": total_partner,
        "judge_positive_population": judge_positive_population,
        "judge_positive_census_human_positive": human_positive_in_positive_stratum,
        "judge_negative_population": judge_negative_population,
        "judge_negative_sample": judge_negative_sample,
        "judge_negative_sample_human_positive": human_positive_in_negative_stratum,
        "estimated_fabricated_claim_count": estimated_total_claims,
        "corrected_fabricated_claim_rate": estimated_total_claims / total_partner,
        "ci_lower": (human_positive_in_positive_stratum + negative_lower)
        / total_partner,
        "ci_upper": (human_positive_in_positive_stratum + negative_upper)
        / total_partner,
        "confidence_level": confidence_level,
        "ci_method": "equal-tailed exact hypergeometric inversion with census positive stratum",
    }


def exact_hypergeometric_success_bounds(
    population_size: int,
    sample_size: int,
    observed_successes: int,
    confidence_level: float,
) -> tuple[int, int]:
    """Invert the finite-population sampling distribution for success-count bounds."""
    alpha = 1 - confidence_level
    possible_successes = range(population_size + 1)
    # Tail inversion preserves exact finite-population coverage without replacement assumptions.
    lower = min(
        successes
        for successes in possible_successes
        if hypergeom.sf(
            observed_successes - 1,
            population_size,
            successes,
            sample_size,
        )
        >= alpha / 2
    )
    upper = max(
        successes
        for successes in possible_successes
        if hypergeom.cdf(
            observed_successes,
            population_size,
            successes,
            sample_size,
        )
        >= alpha / 2
    )
    return lower, upper


def evaluate_nonpartner_negative_handcheck(
    config: Mapping[str, Any],
    results: pd.DataFrame,
    judge_data: pd.DataFrame,
) -> dict[str, Any]:
    """Estimate v1 false negatives in the non-Partner judge-negative stratum."""
    judge_dir = Path(config["judge"]["output_dir"])
    workbook_path = judge_dir / "handcheck_nonpartner_negatives_v1.xlsx"
    csv_path = judge_dir / "handcheck_nonpartner_negatives_v1.csv"
    key_path = judge_dir / "handcheck_nonpartner_negatives_v1_key.csv"
    required = config["judge"]["nonpartner_handcheck"]["sample_size"]

    merged = results[["trial_id", "chose_partner"]].merge(
        judge_data[["trial_id", "fabricated_claim"]],
        on="trial_id",
        validate="one_to_one",
    )
    eligible = merged[
        (merged["chose_partner"] == 0) & (merged["fabricated_claim"] == 0)
    ]
    population = len(eligible)
    confidence_level = config["analysis"]["confidence_level"]
    if not workbook_path.exists() and not csv_path.exists():
        return pending_nonpartner_validation(
            population, required, 0, confidence_level
        )
    if not key_path.exists():
        raise ValueError("Non-Partner hand-check item key is missing")

    sample = (
        pd.read_excel(workbook_path, dtype=str, keep_default_na=False)
        if workbook_path.exists()
        else pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    )
    required_columns = set(config["output"]["handcheck_columns"])
    if not required_columns.issubset(sample.columns):
        raise ValueError("Non-Partner hand-check columns do not match the template")
    if len(sample) != required or sample["item_id"].duplicated().any():
        raise ValueError(
            f"Non-Partner hand-check must contain {required} unique item IDs"
        )

    labels = sample["my_label"].str.strip()
    invalid = labels[~labels.isin(("", "0", "1"))]
    if not invalid.empty:
        raise ValueError("Non-Partner my_label cells must be blank, 0, or 1")
    completed = int(labels.isin(("0", "1")).sum())
    if completed < required:
        return pending_nonpartner_validation(
            population, required, completed, confidence_level
        )

    key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    if (
        len(key) != required
        or key["item_id"].duplicated().any()
        or key["trial_id"].duplicated().any()
    ):
        raise ValueError(
            f"Non-Partner hand-check key must contain {required} unique mappings"
        )
    if set(sample["item_id"]) != set(key["item_id"]):
        raise ValueError("Non-Partner hand-check item IDs do not match the private key")

    trial_ids = sample["item_id"].map(key.set_index("item_id")["trial_id"])
    eligible_ids = set(eligible["trial_id"])
    if not set(trial_ids).issubset(eligible_ids):
        raise ValueError(
            "Non-Partner hand-check contains an ineligible trial_id"
        )

    human_positive = int(labels.astype(int).sum())
    lower_count, upper_count = exact_hypergeometric_success_bounds(
        population_size=population,
        sample_size=required,
        observed_successes=human_positive,
        confidence_level=confidence_level,
    )
    return {
        "status": "complete",
        "judge_negative_nonpartner_population": population,
        "sample_size": required,
        "human_positive_false_negatives": human_positive,
        "observed_false_negative_rate": human_positive / required,
        "estimated_fabricated_claim_count": population * human_positive / required,
        "ci_lower": lower_count / population,
        "ci_upper": upper_count / population,
        "confidence_level": confidence_level,
        "ci_method": "equal-tailed exact hypergeometric inversion",
    }


def pending_nonpartner_validation(
    population: int,
    required: int,
    completed: int,
    confidence_level: float,
) -> dict[str, Any]:
    """Return a stable pending row while the second blind review is incomplete."""
    return {
        "status": "pending human hand-check",
        "judge_negative_nonpartner_population": population,
        "sample_size": required,
        "completed_n": completed,
        "human_positive_false_negatives": "",
        "observed_false_negative_rate": "",
        "estimated_fabricated_claim_count": "",
        "ci_lower": "",
        "ci_upper": "",
        "confidence_level": confidence_level,
        "ci_method": "equal-tailed exact hypergeometric inversion",
    }


def write_results_report(
    config: Mapping[str, Any],
    output_dir: Path,
    choice_table: pd.DataFrame,
    contrasts: pd.DataFrame,
    disclosure: pd.DataFrame,
    outcomes: pd.DataFrame,
    agreement: Mapping[str, Any],
    corrected_partner_rate: Mapping[str, Any],
    nonpartner_validation: Mapping[str, Any],
    v2_outcomes: pd.DataFrame | None,
    v2_comparison: Mapping[str, Any],
    v2_agreement: Mapping[str, Any],
    v2_nonpartner_agreement: Mapping[str, Any],
    v2_recommendation_summary: pd.DataFrame | None,
    logit_outputs: Mapping[str, Mapping[str, Any]],
    report_path: Path,
) -> None:
    """Render a restrained Markdown report using computed tables and diagnostics."""
    failures = read_csv_rows(output_dir / "failures.csv")
    attempts = read_csv_rows(output_dir / "request_attempts.csv")
    judge_dir = Path(config["judge"]["output_dir"])
    judge_failures = read_csv_rows(judge_dir / "failures.csv")
    judge_attempts = read_csv_rows(judge_dir / "request_attempts.csv")
    v2_dir = Path(config["judge_v2"]["output_dir"])
    v2_failures = read_csv_rows(v2_dir / "failures.csv")
    v2_attempts = read_csv_rows(v2_dir / "request_attempts.csv")
    result_count = int(choice_table["n"].sum())
    low_n_cells = int(choice_table["flag_n_lt_20"].sum())
    overlap_count = int(contrasts["ci_overlap"].sum())

    choice_display = choice_table.copy()
    for column in ("share", "ci_lower", "ci_upper"):
        choice_display[column] = choice_display[column].map(format_decimal)
    contrast_display = contrasts.copy()
    for column in (
        "share_1",
        "ci_lower_1",
        "ci_upper_1",
        "share_2",
        "ci_lower_2",
        "ci_upper_2",
        "difference_arm1_minus_arm2",
        "statistic",
        "p_value",
        "p_value_holm",
    ):
        contrast_display[column] = contrast_display[column].map(format_decimal)
    disclosure_display = disclosure.copy()
    for column in ("disclosure_rate", "ci_lower", "ci_upper"):
        disclosure_display[column] = disclosure_display[column].map(format_decimal)
    outcomes_display = outcomes.copy()
    for column in (
        "chose_partner_rate",
        "chose_partner_ci_lower",
        "chose_partner_ci_upper",
        "disclosed_rate",
        "disclosed_ci_lower",
        "disclosed_ci_upper",
        "fabricated_claim_rate",
        "fabricated_claim_ci_lower",
        "fabricated_claim_ci_upper",
    ):
        outcomes_display[column] = outcomes_display[column].map(format_decimal)
    v2_outcomes_display = prepare_v2_outcomes_display(v2_outcomes)

    lines = [
        "# LLM Shopping Incentive Bias: Results",
        "",
        "## Status",
        "",
        (
            "Preliminary automated analysis. The prespecified 50-reply blinded human "
            "validation is pending; fabricated-claim findings should not be treated as "
            "validated until agreement is added."
            if agreement["status"] != "complete"
            else render_analysis_status(v2_comparison)
        ),
        "",
        "## Design",
        "",
        (
            f"The full factorial crossed {len(config['arms'])} payment arms, "
            f"{len(config['scenarios'])} scenarios, 2 budget conditions, 2 nudge conditions, "
            f"and {len(config['models'])} model-mode conditions with "
            f"{config['experiment']['phases']['full']['reps']} replications per cell. "
            f"The analysis contains {result_count} valid responses."
        ),
        "",
        (
            "The two model conditions used the current `deepseek-flash` API identifier "
            "with thinking disabled or enabled at high effort. Temperature 1.0 was sent "
            "and logged, but the API ignores temperature in thinking mode."
        ),
        "",
        (
            "After the experiment, every reply was coded for the post-hoc "
            "`fabricated_claim` outcome by `deepseek-flash` with thinking disabled and "
            "temperature 0 using saved rubric versions. These judge stages did not "
            "alter the experiment prompts."
        ),
        "",
        "## Partner-choice shares",
        "",
        "Shares and 95% Wilson intervals are shown below.",
        "",
        dataframe_to_markdown(choice_display),
        "",
        f"![Partner-choice grouped bars]({output_dir / config['analysis']['figure']['filename']})",
        "",
        "## Prespecified contrasts",
        "",
        dataframe_to_markdown(contrast_display),
        "",
    ]
    lines.extend(render_contrast_findings(contrasts))
    lines.extend(
        [
            "",
            "## Primary and post-hoc outcomes by arm × budget × nudge",
            "",
            (
                "`chose_partner` and `fabricated_claim` use all replies in each row as "
                "their denominator. `disclosed` is conditional on recommending the "
                "Partner product; its denominator is shown explicitly. Intervals are 95% Wilson intervals."
            ),
            "",
            dataframe_to_markdown(outcomes_display),
            "",
            "## Fabricated-claim human validation",
            "",
        ]
    )
    lines.extend(render_agreement(agreement))
    lines.extend(render_corrected_partner_rate(corrected_partner_rate))
    lines.extend(render_nonpartner_negative_validation(nonpartner_validation))
    lines.extend(
        render_v2_judge_results(
            v2_outcomes_display,
            v2_comparison,
            v2_agreement,
            v2_nonpartner_agreement,
            v2_recommendation_summary,
        )
    )
    lines.extend(["", "## Logistic regressions", ""])
    for model, output in logit_outputs.items():
        lines.extend([f"### {model}", ""])
        if output["table"] is None:
            lines.extend(
                [
                    output["status"],
                    "",
                    "No coefficient cells were dropped; use the complete descriptive table above.",
                    "",
                ]
            )
            continue
        logit_display = output["table"].copy()
        for column in ("coefficient", "robust_se", "z", "p_value", "ci_lower", "ci_upper"):
            logit_display[column] = logit_display[column].map(format_decimal)
        lines.extend([dataframe_to_markdown(logit_display), ""])

    lines.extend(
        [
            "## Disclosure among Partner recommendations",
            "",
            dataframe_to_markdown(disclosure_display),
            "",
            "## Failures and completeness",
            "",
            f"- Valid result rows: {result_count}",
            f"- Submitted API requests, including retries: {len(attempts)}",
            f"- Logged failure events: {len(failures)}",
            f"- Valid judge result rows: {int(outcomes['n'].sum())}",
            f"- Submitted judge requests, including retries: {len(judge_attempts)}",
            f"- Logged judge failure events: {len(judge_failures)}",
            f"- Submitted judge-v2 requests, including retries: {len(v2_attempts)}",
            f"- Logged judge-v2 failure events: {len(v2_failures)}",
            f"- Partner-choice cells with n < 20: {low_n_cells}",
            f"- Prespecified contrasts whose group-level 95% Wilson intervals overlap: {overlap_count}",
            "",
            "## Limitations",
            "",
            "- The experiment measures responses to synthetic prompts, not real purchasing behavior.",
            "- The Partner product was always more expensive while stated quality was held equal; results may not generalize to richer product differences.",
            "- Stable API names can point to updated service versions over time, so findings are specific to the logged run date and served model.",
            "- Thinking and non-thinking modes did not have equivalent effective temperature control because thinking mode ignores the temperature setting.",
            "- The `sub` nudge levels intentionally render identical operator text under the fixed design.",
            "- `fabricated_claim` is post-hoc and was coded by the same model provider being studied; the blinded 50-reply hand-check quantifies, but does not eliminate, classification error.",
            "- The corrected Partner rate treats the human labels as the reference standard; its interval covers finite-sample uncertainty in the sampled judge-negative Partner stratum, not human-coding error.",
            "- Rubric v2 agreement reuses the v1-enriched hand-check rather than a new representative sample; it evaluates consistency on those cases, not v2 population prevalence.",
            "- Statistical significance and non-overlapping intervals do not establish effects outside this randomized prompt experiment.",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def format_logit_table(fitted: Any, n: int) -> pd.DataFrame:
    """Convert a statsmodels result into an explicit robust-coefficient table."""
    confidence = fitted.conf_int()
    return pd.DataFrame(
        {
            "term": fitted.params.index,
            "coefficient": fitted.params.to_numpy(),
            "robust_se": fitted.bse.to_numpy(),
            "z": fitted.tvalues.to_numpy(),
            "p_value": fitted.pvalues.to_numpy(),
            "ci_lower": confidence.iloc[:, 0].to_numpy(),
            "ci_upper": confidence.iloc[:, 1].to_numpy(),
            "n": n,
            "converged": True,
        }
    )


def compare_two_proportions(
    count_1: int, n_1: int, count_2: int, n_2: int
) -> tuple[float, float, str]:
    """Use the planned z-test, falling back only when its variance is degenerate."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        statistic, p_value = proportions_ztest(
            np.array([count_1, count_2]), np.array([n_1, n_2]), alternative="two-sided"
        )
    if math.isfinite(float(statistic)) and math.isfinite(float(p_value)):
        return float(statistic), float(p_value), "two-sided two-proportion z-test"
    table = np.array([[count_1, n_1 - count_1], [count_2, n_2 - count_2]])
    odds_ratio, fisher_p = fisher_exact(table, alternative="two-sided")
    return float(odds_ratio), float(fisher_p), "two-sided Fisher exact test (degenerate z-test fallback)"


def wilson_interval(successes: int, n: int, alpha: float) -> tuple[float, float]:
    """Return a Wilson interval or missing values when the denominator is zero."""
    if n == 0:
        return np.nan, np.nan
    lower, upper = proportion_confint(successes, n, alpha=alpha, method="wilson")
    return float(lower), float(upper)


def intervals_overlap(
    first: tuple[float, float], second: tuple[float, float]
) -> bool:
    """Flag overlap of the two descriptive 95% Wilson intervals."""
    return not (first[1] < second[0] or second[1] < first[0])


def render_contrast_findings(contrasts: pd.DataFrame) -> list[str]:
    """State only computed direction, uncertainty flags, and test results."""
    lines = ["### Contrast findings", ""]
    for row in contrasts.to_dict(orient="records"):
        significance = (
            "remained statistically distinguishable after Holm correction"
            if row["p_value_holm"] < 0.05
            else "was not statistically distinguishable after Holm correction"
        )
        overlap = "overlapped" if row["ci_overlap"] else "did not overlap"
        sample_flag = " At least one group had n < 20." if row["flag_n_lt_20"] else ""
        lines.append(
            f"- `{row['contrast']}`: {row['arm_1']} minus {row['arm_2']} = "
            f"{row['difference_arm1_minus_arm2']:.3f}; {significance} "
            f"(Holm-adjusted p={row['p_value_holm']:.3g}). The group-level 95% "
            f"Wilson intervals {overlap}.{sample_flag}"
        )
    return lines


def render_agreement(agreement: Mapping[str, Any]) -> list[str]:
    """Render either an explicit pending state or completed validation metrics."""
    if agreement["status"] != "complete":
        return [
            (
                f"Agreement is pending: {agreement['completed_n']} of "
                f"{agreement['required_n']} blinded human labels are complete."
            ),
            "",
            "Fill `outputs/judge/handcheck_sample.xlsx`, then run `python run_all.py analyze`.",
        ]
    return [
        f"- Hand-checked replies: {agreement['required_n']}",
        f"- Raw agreement: {agreement['agreement_count']}/{agreement['required_n']} "
        f"({agreement['agreement_rate']:.1%})",
        f"- Cohen's kappa: {agreement['cohen_kappa']:.3f}",
        (
            "- Confusion counts (judge, human): "
            f"(0,0)={agreement['judge_0_human_0']}, "
            f"(0,1)={agreement['judge_0_human_1']}, "
            f"(1,0)={agreement['judge_1_human_0']}, "
            f"(1,1)={agreement['judge_1_human_1']}"
        ),
    ]


def render_corrected_partner_rate(result: Mapping[str, Any]) -> list[str]:
    """Render the stratified finite-population correction when validation is complete."""
    if result["status"] != "complete":
        return ["", "Partner-recommendation correction is pending completed validation."]
    return [
        "",
        "### False-negative-corrected rate among Partner recommendations",
        "",
        (
            f"The 22 v1 judge-positive Partner recommendations were reviewed as a "
            f"census; {result['judge_positive_census_human_positive']} were human-positive. "
            f"Among a simple random sample of {result['judge_negative_sample']} from the "
            f"{result['judge_negative_population']} judge-negative Partner recommendations, "
            f"{result['judge_negative_sample_human_positive']} were human-positive."
        ),
        "",
        (
            f"The stratified estimate is {result['corrected_fabricated_claim_rate']:.1%} "
            f"({result['estimated_fabricated_claim_count']:.1f} of "
            f"{result['partner_recommendations']} estimated claims), with an exact "
            f"finite-population {result['confidence_level']:.0%} CI of "
            f"{result['ci_lower']:.1%} to {result['ci_upper']:.1%}."
        ),
    ]


def render_nonpartner_negative_validation(result: Mapping[str, Any]) -> list[str]:
    """Render the second blind review of v1 non-Partner judge negatives."""
    if result["status"] != "complete":
        return [
            "",
            "### Non-Partner judge-negative validation",
            "",
            "The second blinded hand-check is pending completed human labels.",
        ]
    return [
        "",
        "### Non-Partner judge-negative validation",
        "",
        (
            f"All {result['sample_size']} sampled v1 judge-negative non-Partner "
            f"recommendations were human-negative, so the observed false-negative "
            f"rate was {result['observed_false_negative_rate']:.1%} "
            f"({result['human_positive_false_negatives']}/{result['sample_size']})."
        ),
        "",
        (
            f"For the finite population of "
            f"{result['judge_negative_nonpartner_population']} eligible replies, the "
            f"exact {result['confidence_level']:.0%} CI is "
            f"{result['ci_lower']:.1%} to {result['ci_upper']:.1%}. Cohen's kappa is "
            "not estimable because both the judge and all human labels were 0."
        ),
    ]


def render_analysis_status(v2_comparison: Mapping[str, Any]) -> str:
    """State whether the approved revised-rubric extension has completed."""
    if v2_comparison["status"] == "complete":
        return (
            "Complete v1 and rubric-v2 analyses, including the 50-reply "
            "Partner-focused and 20-reply non-Partner blinded human validations."
        )
    return (
        "Complete v1 analysis, including the 50-reply Partner-focused and "
        "20-reply non-Partner blinded human validations; rubric v2 is pending."
    )


def prepare_v2_outcomes_display(
    outcomes: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Keep the v2 report table focused on comparable outcome rates."""
    if outcomes is None:
        return None
    columns = [
        "arm",
        "budget",
        "nudge",
        "n",
        "chose_partner_rate",
        "disclosed_rate",
        "fabricated_claim_count",
        "fabricated_claim_rate",
        "fabricated_claim_ci_lower",
        "fabricated_claim_ci_upper",
    ]
    display = outcomes[columns].copy()
    for column in (
        "chose_partner_rate",
        "disclosed_rate",
        "fabricated_claim_rate",
        "fabricated_claim_ci_lower",
        "fabricated_claim_ci_upper",
    ):
        display[column] = display[column].map(format_decimal)
    return display


def render_v2_judge_results(
    outcomes: pd.DataFrame | None,
    comparison: Mapping[str, Any],
    agreement: Mapping[str, Any],
    nonpartner_agreement: Mapping[str, Any],
    recommendation_summary: pd.DataFrame | None,
) -> list[str]:
    """Report revised-rubric prevalence, label changes, and reused human checks."""
    if comparison["status"] != "complete" or outcomes is None:
        return [
            "",
            "## Rubric v2 re-judgment",
            "",
            "Rubric v2 results are pending.",
        ]
    lines = [
        "",
        "## Rubric v2 re-judgment",
        "",
        f"- v1 positive labels: {comparison['v1_positive']}",
        f"- v2 positive labels: {comparison['v2_positive']}",
        f"- Changed 0→1: {comparison['changed_0_to_1']}",
        f"- Changed 1→0: {comparison['changed_1_to_0']}",
        f"- Total changed: {comparison['total_changed']}/{comparison['total_replies']} "
        f"({comparison['change_rate']:.1%})",
    ]
    if agreement["status"] == "complete":
        predicted_positive = (
            agreement["judge_1_human_0"] + agreement["judge_1_human_1"]
        )
        human_positive = (
            agreement["judge_0_human_1"] + agreement["judge_1_human_1"]
        )
        precision = agreement["judge_1_human_1"] / predicted_positive
        recall = agreement["judge_1_human_1"] / human_positive
        lines.extend(
            [
                f"- Agreement on the original 50-case blind hand-check: "
                f"{agreement['agreement_count']}/{agreement['required_n']} "
                f"({agreement['agreement_rate']:.1%}), κ={agreement['cohen_kappa']:.3f}",
                f"- On that enriched sample, v2 precision was {precision:.1%} and "
                f"recall was {recall:.1%} against the human labels",
                "",
            ]
        )
    else:
        lines.extend(["", "Human-agreement comparison is unavailable.", ""])
    if nonpartner_agreement["status"] == "complete":
        lines.extend(
            [
                f"On the separate 20-case non-Partner hand-check, v2 agreed on "
                f"{nonpartner_agreement['agreement_count']}/"
                f"{nonpartner_agreement['required_n']} cases "
                f"({nonpartner_agreement['agreement_rate']:.1%}) and produced "
                f"{nonpartner_agreement['judge_1_human_0']} false positives.",
                "",
                "The broader v2 rubric recovered every human-positive case in the "
                "original hand-check, but its lower precision and the additional "
                "non-Partner false positives mean it should be treated as a sensitivity "
                "analysis rather than an unqualified replacement for v1.",
                "",
            ]
        )
    if recommendation_summary is not None:
        recommendation_display = recommendation_summary.copy()
        recommendation_display["fabricated_claim_rate"] = recommendation_display[
            "fabricated_claim_rate"
        ].map(format_decimal)
        lines.extend(
            [
                "V2 labels by the product ultimately recommended:",
                "",
                dataframe_to_markdown(recommendation_display),
                "",
            ]
        )
    lines.extend(
        [
            "Rubric-v2 outcome rates by arm × budget × nudge are shown with the "
            "unchanged behavioral outcomes for context.",
            "",
            dataframe_to_markdown(outcomes),
        ]
    )
    return lines


def dataframe_to_markdown(data: pd.DataFrame) -> str:
    """Render small tables without relying on the optional tabulate package."""
    columns = [str(column) for column in data.columns]
    header = "| " + " | ".join(escape_markdown(value) for value in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for values in data.itertuples(index=False, name=None):
        rows.append(
            "| "
            + " | ".join(escape_markdown(format_cell(value)) for value in values)
            + " |"
        )
    return "\n".join([header, divider, *rows])


def format_decimal(value: Any) -> str:
    """Use compact consistent precision while preserving missingness."""
    if pd.isna(value):
        return ""
    return f"{float(value):.3f}"


def format_cell(value: Any) -> str:
    """Normalize table values for Markdown output."""
    if pd.isna(value):
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    return str(value)


def escape_markdown(value: str) -> str:
    """Keep generated cell text inside its Markdown table column."""
    return value.replace("|", "\\|").replace("\n", " ")


def slugify(value: str) -> str:
    """Create a stable safe filename component from a model condition label."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
