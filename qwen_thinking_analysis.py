"""
Purpose:
    Compare Qwen thinking with its prompt-matched non-thinking responses so inference
    mode, rather than prompt composition or model snapshot, is the varying factor.

Inputs:
    config_qwen_thinking_full.yaml; outputs/qwen_thinking/results.csv; and the completed
    Qwen non-thinking results referenced by the configuration.

Outputs:
    Three paired summary CSV files and QWEN_THINKING_RESULTS.md.

Key Steps:
    1. Validate all 760 thinking results and their non-thinking prompt matches.
    2. Join outcomes one-to-one by immutable source trial identifier.
    3. Estimate paired changes overall, by framing, and by platform nudge.
    4. Translate Partner choices into mechanical user extra spending.
    5. Write machine-readable tables and a data-derived report.

Main Flow:
    analyze_qwen_thinking_results()
        -> load_paired_mode_results()
        -> summarize_paired_groups()
        -> write_qwen_thinking_report()

How to Run:
    python run_all.py qwen-thinking-analyze
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from scipy.stats import binomtest

from experiment import read_csv_rows
from qwen_comparison import generate_qwen_trials, validate_qwen_results


def analyze_qwen_thinking_results(config: Mapping[str, Any]) -> Path:
    """Generate paired mode-effect outputs from complete saved responses."""
    paired = load_paired_mode_results(config)
    framing = summarize_paired_groups(paired, ["condition", "framing"])
    incentive = paired[paired["condition"] == "incentive"]
    nudge = summarize_paired_groups(incentive, ["nudge"])
    framing_nudge = summarize_paired_groups(incentive, ["framing", "nudge"])

    output_dir = Path(config["experiment"]["output_dir"])
    framing.to_csv(output_dir / config["analysis"]["framing_summary_filename"], index=False)
    nudge.to_csv(output_dir / config["analysis"]["nudge_summary_filename"], index=False)
    framing_nudge.to_csv(
        output_dir / config["analysis"]["framing_nudge_filename"], index=False
    )
    report_path = Path(config["analysis"]["report_path"])
    write_qwen_thinking_report(config, paired, framing, nudge, framing_nudge, report_path)
    return report_path


def load_paired_mode_results(config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate and join thinking and non-thinking results one-to-one."""
    trials = generate_qwen_trials(config)
    result_path = Path(config["experiment"]["output_dir"]) / "results.csv"
    thinking_rows = read_csv_rows(result_path)
    validate_qwen_results(thinking_rows, trials, config)
    if len(thinking_rows) != len(trials):
        raise ValueError(
            f"Qwen thinking results are incomplete: {len(thinking_rows)}/{len(trials)}"
        )

    thinking = pd.DataFrame(thinking_rows)
    nonthinking = pd.DataFrame(
        read_csv_rows(Path(config["source"]["qwen_nonthinking_results"]))
    )
    if len(nonthinking) != len(trials):
        raise ValueError(
            f"Qwen non-thinking results are incomplete: {len(nonthinking)}/{len(trials)}"
        )
    if nonthinking["source_trial_id"].duplicated().any():
        raise ValueError("Qwen non-thinking source_trial_id values must be unique")

    source = nonthinking[["source_trial_id", "prompt_sha", "chose_partner"]].rename(
        columns={
            "prompt_sha": "source_prompt_sha",
            "chose_partner": "nonthinking_choice",
        }
    )
    paired = thinking.merge(source, on="source_trial_id", validate="one_to_one")
    if not (paired["prompt_sha"] == paired["source_prompt_sha"]).all():
        raise ValueError("Thinking and non-thinking prompt hashes differ")
    for column in ("nudge", "rep", "chose_partner", "nonthinking_choice"):
        paired[column] = pd.to_numeric(paired[column], errors="raise").astype(int)
    paired["user_extra_spend"] = paired["scenario"].map(
        {"headphones": 90, "shoes": 70}
    )
    if paired["user_extra_spend"].isna().any():
        raise ValueError("Unknown scenario prevents extra-spend calculation")
    return paired


def summarize_paired_groups(
    paired: pd.DataFrame, group_columns: Sequence[str]
) -> pd.DataFrame:
    """Calculate paired rates, transitions, exact tests, and spending by group."""
    rows: list[dict[str, Any]] = []
    grouped = paired.groupby(list(group_columns), dropna=False, sort=False)
    for keys, group in grouped:
        key_values = keys if isinstance(keys, tuple) else (keys,)
        nonthinking = group["nonthinking_choice"]
        thinking = group["chose_partner"]
        zero_to_one = int(((nonthinking == 0) & (thinking == 1)).sum())
        one_to_zero = int(((nonthinking == 1) & (thinking == 0)).sum())
        discordant = zero_to_one + one_to_zero
        p_value = 1.0 if discordant == 0 else float(
            binomtest(zero_to_one, discordant, 0.5).pvalue
        )
        row = dict(zip(group_columns, key_values, strict=True))
        row.update({
            "n_pairs": len(group),
            "nonthinking_partner_choices": int(nonthinking.sum()),
            "nonthinking_share": float(nonthinking.mean()),
            "thinking_partner_choices": int(thinking.sum()),
            "thinking_share": float(thinking.mean()),
            "thinking_minus_nonthinking": float(thinking.mean() - nonthinking.mean()),
            "nonthinking_0_thinking_1": zero_to_one,
            "nonthinking_1_thinking_0": one_to_zero,
            "mcnemar_exact_p_value": p_value,
            "nonthinking_mean_extra_spend": float(
                (nonthinking * group["user_extra_spend"]).mean()
            ),
            "thinking_mean_extra_spend": float(
                (thinking * group["user_extra_spend"]).mean()
            ),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def write_qwen_thinking_report(
    config: Mapping[str, Any],
    paired: pd.DataFrame,
    framing: pd.DataFrame,
    nudge: pd.DataFrame,
    framing_nudge: pd.DataFrame,
    report_path: Path,
) -> None:
    """Write the full mode comparison using only persisted result tables."""
    replacement_count = len(
        config["experiment"].get("authorized_replacement_trial_ids", [])
    )
    planned_pairs = config["experiment"]["request_attempt_cap"] - replacement_count
    attempt_count = len(read_csv_rows(
        Path(config["experiment"]["output_dir"]) / "request_attempts.csv"
    ))
    incentive = paired[paired["condition"] == "incentive"].assign(scope="all incentive")
    overall = summarize_paired_groups(incentive, ["scope"]).iloc[0]
    lines = [
        "# Qwen Thinking-Mode Results",
        "",
        "All comparisons use the same pinned Qwen snapshot and byte-identical prompts.",
        "",
        "## Protocol",
        "",
        f"- Model snapshot: `{config['model']['api_model']}`",
        "- Thinking comparison: enabled versus disabled",
        f"- Temperature: {config['experiment']['temperature']}",
        f"- Valid paired responses: {len(paired)}/{planned_pairs}",
        f"- Submitted requests: {attempt_count}/{config['experiment']['request_attempt_cap']}",
        "",
        "## Overall incentive result",
        "",
        f"- Non-thinking: {overall.nonthinking_partner_choices}/{overall.n_pairs} "
        f"({overall.nonthinking_share:.1%})",
        f"- Thinking: {overall.thinking_partner_choices}/{overall.n_pairs} "
        f"({overall.thinking_share:.1%})",
        f"- Difference: {overall.thinking_minus_nonthinking:.1%}",
        f"- Exact paired p-value: {overall.mcnemar_exact_p_value:.4g}",
        f"- Mean extra user spending if recommendations are followed: "
        f"${overall.nonthinking_mean_extra_spend:.2f} versus "
        f"${overall.thinking_mean_extra_spend:.2f} per incentive prompt",
        "",
        "## By framing",
        "",
        "| Condition | Framing | Non-thinking | Thinking | Difference | Exact p (raw) |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in framing.itertuples(index=False):
        lines.append(
            f"| {row.condition} | {row.framing} | {row.nonthinking_partner_choices}/{row.n_pairs} "
            f"({row.nonthinking_share:.1%}) | {row.thinking_partner_choices}/{row.n_pairs} "
            f"({row.thinking_share:.1%}) | {row.thinking_minus_nonthinking:.1%} | "
            f"{row.mcnemar_exact_p_value:.4g} |"
        )
    lines.extend([
        "",
        "## By platform-priority nudge",
        "",
        "| Nudge | Non-thinking | Thinking | Difference | Exact p (raw) |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in nudge.itertuples(index=False):
        lines.append(
            f"| {row.nudge} | {row.nonthinking_partner_choices}/{row.n_pairs} "
            f"({row.nonthinking_share:.1%}) | {row.thinking_partner_choices}/{row.n_pairs} "
            f"({row.thinking_share:.1%}) | {row.thinking_minus_nonthinking:.1%} | "
            f"{row.mcnemar_exact_p_value:.4g} |"
        )
    lines.extend([
        "",
        "## Framing × nudge",
        "",
        "| Framing | Nudge | Non-thinking | Thinking | Difference | Exact p (raw) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in framing_nudge.itertuples(index=False):
        lines.append(
            f"| {row.framing} | {row.nudge} | {row.nonthinking_partner_choices}/{row.n_pairs} "
            f"({row.nonthinking_share:.1%}) | {row.thinking_partner_choices}/{row.n_pairs} "
            f"({row.thinking_share:.1%}) | {row.thinking_minus_nonthinking:.1%} | "
            f"{row.mcnemar_exact_p_value:.4g} |"
        )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
