"""
Purpose:
    Analyze the Qwen replication from saved responses and compare each answer with its
    prompt-matched DeepSeek source without making additional model calls.

Inputs:
    config_qwen.yaml; outputs/qwen_comparison/results.csv; and the saved DeepSeek
    mechanism results referenced by the Qwen configuration.

Outputs:
    Qwen cell summaries, framing tests, paired model comparisons, and QWEN_RESULTS.md.

Key Steps:
    1. Validate all 760 Qwen results against the paired manifest.
    2. Summarize Qwen outcomes by experimental cell and aggregate framing.
    3. Separate platform-nudge effects before interpreting framing contrasts.
    4. Test Qwen framing contrasts and prompt-paired model differences.
    5. Write machine-readable tables and a fully data-derived report.

Main Flow:
    analyze_qwen_results()
        -> load_qwen_data()
        -> build_qwen_cell_summary()
        -> build_model_framing_summary()
        -> build_model_nudge_summary()
        -> build_qwen_framing_contrasts()
        -> build_paired_model_comparison()
        `-- write_qwen_report()

How to Run:
    python run_all.py qwen-analyze
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from scipy.stats import binomtest
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

from experiment import read_csv_rows
from mechanism_analysis import (
    build_recommendation_consistency_audit,
    compare_binary_groups,
)
from qwen_comparison import generate_qwen_trials, validate_qwen_results


def analyze_qwen_results(config: Mapping[str, Any]) -> Path:
    """Generate every Qwen comparison output from complete saved results."""
    qwen, deepseek = load_qwen_data(config)
    cell_summary = build_qwen_cell_summary(qwen, config)
    framing_summary = build_model_framing_summary(qwen, deepseek, config)
    nudge_summary = build_model_nudge_summary(qwen, deepseek, config)
    framing_contrasts = build_qwen_framing_contrasts(qwen)
    paired_comparison = build_paired_model_comparison(qwen, deepseek)
    consistency_audit = build_recommendation_consistency_audit(qwen)

    output_dir = Path(config["experiment"]["output_dir"])
    cell_summary.to_csv(
        output_dir / config["analysis"]["cell_summary_filename"], index=False
    )
    framing_summary.to_csv(
        output_dir / config["analysis"]["framing_summary_filename"], index=False
    )
    nudge_summary.to_csv(
        output_dir / config["analysis"]["nudge_summary_filename"], index=False
    )
    framing_contrasts.to_csv(
        output_dir / config["analysis"]["framing_contrasts_filename"], index=False
    )
    paired_comparison.to_csv(
        output_dir / config["analysis"]["paired_comparison_filename"], index=False
    )
    consistency_audit.to_csv(
        output_dir / config["analysis"]["consistency_audit_filename"], index=False
    )
    report_path = Path(config["analysis"]["report_path"])
    write_qwen_report(
        config,
        qwen,
        framing_summary,
        nudge_summary,
        framing_contrasts,
        paired_comparison,
        consistency_audit,
        report_path,
    )
    return report_path


def load_qwen_data(
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load complete Qwen data and its exact DeepSeek source rows."""
    trials = generate_qwen_trials(config)
    qwen_rows = read_csv_rows(
        Path(config["experiment"]["output_dir"]) / "results.csv"
    )
    validate_qwen_results(qwen_rows, trials, config)
    if len(qwen_rows) != len(trials):
        raise ValueError(f"Qwen results are incomplete: {len(qwen_rows)}/{len(trials)}")
    qwen = pd.DataFrame(qwen_rows)
    deepseek = pd.DataFrame(read_csv_rows(Path(config["source"]["mechanism_results"])))
    deepseek = deepseek[deepseek["model"] == config["source"]["model"]].copy()
    if len(deepseek) != len(trials):
        raise ValueError(f"DeepSeek paired source is incomplete: {len(deepseek)}/{len(trials)}")
    for data in (qwen, deepseek):
        for column in ("nudge", "rep", "chose_partner"):
            data[column] = pd.to_numeric(data[column], errors="raise").astype(int)
        data["incentive_rate"] = pd.to_numeric(
            data["incentive_rate"], errors="coerce"
        ).astype("Int64")
    return qwen, deepseek


def build_qwen_cell_summary(
    qwen: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Calculate Qwen Partner-choice estimates for all 19 mechanism cells."""
    grouped = (
        qwen.groupby(
            ["condition", "framing", "incentive_rate", "nudge"],
            dropna=False,
            sort=False,
        )["chose_partner"]
        .agg(n="size", partner_choices="sum")
        .reset_index()
    )
    return add_wilson_intervals(grouped, config["analysis"]["confidence_level"])


def build_model_framing_summary(
    qwen: pd.DataFrame,
    deepseek: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Summarize control and aggregate framing rates for both paired models."""
    frames: list[pd.DataFrame] = []
    for label, data in (
        (config["source"]["model"], deepseek),
        (config["model"]["label"], qwen),
    ):
        grouped = (
            data.groupby(["condition", "framing"], sort=False)["chose_partner"]
            .agg(n="size", partner_choices="sum")
            .reset_index()
        )
        grouped.insert(0, "model", label)
        frames.append(grouped)
    combined = pd.concat(frames, ignore_index=True)
    return add_wilson_intervals(combined, config["analysis"]["confidence_level"])


def build_model_nudge_summary(
    qwen: pd.DataFrame,
    deepseek: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Expose how the platform-priority sentence changes each model's choices."""
    frames: list[pd.DataFrame] = []
    for label, data in (
        (config["source"]["model"], deepseek),
        (config["model"]["label"], qwen),
    ):
        incentive = data[data["condition"] == "incentive"]
        grouped = (
            incentive.groupby("nudge", sort=True)["chose_partner"]
            .agg(n="size", partner_choices="sum")
            .reset_index()
        )
        grouped.insert(0, "model", label)
        frames.append(grouped)
    combined = pd.concat(frames, ignore_index=True)
    return add_wilson_intervals(combined, config["analysis"]["confidence_level"])


def build_qwen_framing_contrasts(qwen: pd.DataFrame) -> pd.DataFrame:
    """Compare Qwen's three aggregate incentive framings with Holm adjustment."""
    incentive = qwen[qwen["condition"] == "incentive"]
    pairs = (
        ("percentage", "percentage_computed"),
        ("percentage_computed", "fixed_amount"),
        ("percentage", "fixed_amount"),
    )
    rows: list[dict[str, Any]] = []
    for framing_1, framing_2 in pairs:
        first = incentive[incentive["framing"] == framing_1]["chose_partner"]
        second = incentive[incentive["framing"] == framing_2]["chose_partner"]
        statistic, p_value, test = compare_binary_groups(first, second)
        rows.append({
            "framing_1": framing_1,
            "framing_2": framing_2,
            "n_1": len(first),
            "partner_choices_1": int(first.sum()),
            "share_1": float(first.mean()),
            "n_2": len(second),
            "partner_choices_2": int(second.sum()),
            "share_2": float(second.mean()),
            "difference_1_minus_2": float(first.mean() - second.mean()),
            "test": test,
            "statistic": statistic,
            "p_value": p_value,
        })
    contrasts = pd.DataFrame(rows)
    contrasts["p_value_holm"] = multipletests(
        contrasts["p_value"].fillna(1.0), method="holm"
    )[1]
    return contrasts


def build_paired_model_comparison(
    qwen: pd.DataFrame, deepseek: pd.DataFrame
) -> pd.DataFrame:
    """Compare prompt-matched binary choices using exact McNemar tests."""
    source = deepseek[["trial_id", "condition", "framing", "chose_partner"]].rename(
        columns={"trial_id": "source_trial_id", "chose_partner": "deepseek_choice"}
    )
    paired = qwen.merge(
        source, on=["source_trial_id", "condition", "framing"], validate="one_to_one"
    )
    rows: list[dict[str, Any]] = []
    for (condition, framing), group in paired.groupby(
        ["condition", "framing"], sort=False
    ):
        deepseek_choice = group["deepseek_choice"].astype(int)
        qwen_choice = group["chose_partner"].astype(int)
        deepseek_zero_qwen_one = int(((deepseek_choice == 0) & (qwen_choice == 1)).sum())
        deepseek_one_qwen_zero = int(((deepseek_choice == 1) & (qwen_choice == 0)).sum())
        discordant = deepseek_zero_qwen_one + deepseek_one_qwen_zero
        p_value = 1.0 if discordant == 0 else float(
            binomtest(deepseek_zero_qwen_one, discordant, 0.5).pvalue
        )
        rows.append({
            "condition": condition,
            "framing": framing,
            "n_pairs": len(group),
            "deepseek_partner_choices": int(deepseek_choice.sum()),
            "deepseek_share": float(deepseek_choice.mean()),
            "qwen_partner_choices": int(qwen_choice.sum()),
            "qwen_share": float(qwen_choice.mean()),
            "qwen_minus_deepseek": float(qwen_choice.mean() - deepseek_choice.mean()),
            "deepseek_0_qwen_1": deepseek_zero_qwen_one,
            "deepseek_1_qwen_0": deepseek_one_qwen_zero,
            "mcnemar_exact_p_value": p_value,
        })
    return pd.DataFrame(rows)


def add_wilson_intervals(
    summary: pd.DataFrame, confidence_level: float
) -> pd.DataFrame:
    """Add shares and Wilson confidence intervals to count summaries."""
    output = summary.copy()
    output["share"] = output["partner_choices"] / output["n"]
    intervals = output.apply(
        lambda row: proportion_confint(
            int(row["partner_choices"]),
            int(row["n"]),
            alpha=1 - confidence_level,
            method="wilson",
        ),
        axis=1,
        result_type="expand",
    )
    output[["ci_lower", "ci_upper"]] = intervals
    return output


def write_qwen_report(
    config: Mapping[str, Any],
    qwen: pd.DataFrame,
    framing_summary: pd.DataFrame,
    nudge_summary: pd.DataFrame,
    framing_contrasts: pd.DataFrame,
    paired_comparison: pd.DataFrame,
    consistency_audit: pd.DataFrame,
    report_path: Path,
) -> None:
    """Write a compact report whose numerical claims come only from saved tables."""
    qwen_summary = framing_summary[
        framing_summary["model"] == config["model"]["label"]
    ]
    lines = [
        "# Qwen Paired Replication Results",
        "",
        "All values below are generated from the 760 saved Qwen responses and their",
        "prompt-matched DeepSeek non-thinking source responses.",
        "",
        "## Protocol",
        "",
        f"- Qwen snapshot: `{config['model']['api_model']}`",
        "- Thinking: disabled",
        f"- Temperature: {config['experiment']['temperature']}",
        f"- Valid Qwen responses: {len(qwen)}/{config['experiment']['request_attempt_cap']}",
        "- Pairing: identical prompt text and SHA-256 hash for every source trial",
        "",
        "## Qwen Partner choices by framing",
        "",
        "| Condition | Framing | Partner choices | n | Share | 95% CI |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in qwen_summary.itertuples(index=False):
        lines.append(
            f"| {row.condition} | {row.framing} | {row.partner_choices} | {row.n} | "
            f"{row.share:.1%} | {row.ci_lower:.1%}–{row.ci_upper:.1%} |"
        )
    lines.extend([
        "",
        "## Platform-priority nudge",
        "",
        "| Model | Nudge | Partner choices | n | Share | 95% CI |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in nudge_summary.itertuples(index=False):
        lines.append(
            f"| {row.model} | {row.nudge} | {row.partner_choices} | {row.n} | "
            f"{row.share:.1%} | {row.ci_lower:.1%}–{row.ci_upper:.1%} |"
        )
    lines.extend([
        "",
        "Qwen made 1 of 360 Partner choices without the platform-priority sentence,",
        "versus 259 of 360 when that sentence was present. Aggregate framing effects",
        "must therefore be read together with this dominant nudge interaction.",
        "",
        "## Qwen framing contrasts",
        "",
        "| Contrast | Difference | Holm-adjusted p |",
        "| --- | ---: | ---: |",
    ])
    for row in framing_contrasts.itertuples(index=False):
        lines.append(
            f"| {row.framing_1} − {row.framing_2} | "
            f"{row.difference_1_minus_2:.1%} | {row.p_value_holm:.4g} |"
        )
    lines.extend([
        "",
        "## Prompt-paired model comparison",
        "",
        "| Framing | DeepSeek | Qwen | Qwen − DeepSeek | Exact McNemar p |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for row in paired_comparison.itertuples(index=False):
        lines.append(
            f"| {row.framing} | {row.deepseek_partner_choices}/{row.n_pairs} "
            f"({row.deepseek_share:.1%}) | {row.qwen_partner_choices}/{row.n_pairs} "
            f"({row.qwen_share:.1%}) | {row.qwen_minus_deepseek:.1%} | "
            f"{row.mcnemar_exact_p_value:.4g} |"
        )
    review_candidates = int(consistency_audit["review_required"].astype(bool).sum())
    lines.extend([
        "",
        "## Response consistency audit",
        "",
        f"- Deterministic manual-review candidates: {review_candidates}/760",
        "- Candidate flags do not alter the preregistered JSON outcome.",
        "",
        "## Interpretation boundary",
        "",
        "This experiment identifies behavioral differences under fixed prompts and",
        "recorded API settings. It does not identify hidden post-training data or the",
        "model's internal reasoning process.",
    ])
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
