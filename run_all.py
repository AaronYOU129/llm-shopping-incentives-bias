"""
Purpose:
    Provide one guarded command-line entry point. Explicit approval gates preserve the
    authorized pilot-to-full order and prevent accidental API spending.

Inputs:
    Original, mechanism, Qwen, or Qwen-thinking YAML configuration; the provider-specific
    API key for paid phases; persisted artifacts for resumed or analysis-only commands.

Outputs:
    Phase CSV artifacts, versioned judge artifacts, analysis tables and figures,
    RESULTS.md, MECHANISM_RESULTS.md, QWEN_RESULTS.md, and isolated pilot reports.

Key Steps:
    1. Parse the requested command and validate centralized configuration.
    2. Enforce approval and completion gates before paid phases.
    3. Run or resume the selected experiment or judge phase.
    4. Stop after the pilot or incomplete work.
    5. Keep the completed original study isolated from the mechanism extension.
    6. Run Qwen replications and thinking phases under separate approval gates.
    7. Generate analysis only from complete saved artifacts.

Main Flow:
    main()
        -> parse_arguments()
        |-- validate -> validate manifests and protocols
        |-- analyze  -> analyze_full_results()
        |-- pilot    -> run_phase() -> PILOT.md -> stop
        |-- full     -> pilot gate -> run_phase() -> run_judge() -> analysis
        |-- judge-v2 -> rubric gate -> run_judge_v2() -> analysis
        |-- mechanism-* -> isolated validation/pilot/full/analysis workflow
        `-- qwen-* -> paired validation/run/analysis workflow

How to Run:
    python run_all.py pilot
    python run_all.py full --approve-full
    python run_all.py judge-v2 --approve-rubric-v2
    python run_all.py analyze
    python run_all.py mechanism-pilot
    python run_all.py qwen-validate
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from experiment import (
    generate_trials,
    load_config,
    read_csv_rows,
    run_phase,
    validate_only,
    validate_result_rows,
    write_pilot_report,
)


def main(arguments: Sequence[str] | None = None) -> int:
    """Dispatch the single public workflow entry point."""
    parsed = parse_arguments(arguments)
    if parsed.command.startswith("qwen-"):
        qwen_config = load_config(parsed.qwen_config)
        return run_qwen_command(parsed, qwen_config)
    if parsed.command.startswith("mechanism-"):
        mechanism_config = load_config(parsed.mechanism_config)
        return run_mechanism_command(parsed, mechanism_config)
    config = load_config(parsed.config)

    if parsed.command == "validate":
        counts = validate_only(config)
        from judge import validate_judge_config, validate_judge_v2_config

        validate_judge_config(config)
        validate_judge_v2_config(config)
        print(
            f"Validated manifests: pilot={counts['pilot']}, full={counts['full']}, "
            f"judge_cap={config['judge']['request_attempt_cap']}, "
            f"judge_v2_cap={config['judge_v2']['request_attempt_cap']}"
        )
        return 0
    if parsed.command == "analyze":
        run_analysis(config)
        return 0
    if parsed.command == "judge-v2":
        if not parsed.approve_rubric_v2:
            raise SystemExit(
                "Judge v2 requires --approve-rubric-v2 after explicit rubric approval."
            )
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        from judge import run_judge_v2

        summary = run_judge_v2(config, api_key)
        print_phase_summary("judge-v2", summary)
        if summary["unresolved"]:
            print("Analysis not run because valid judge-v2 results are incomplete.")
            return 2
        run_analysis(config)
        return 0

    if parsed.command == "full":
        if not parsed.approve_full:
            raise SystemExit("Full run requires --approve-full after explicit pilot approval.")
        assert_pilot_complete(config)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    summary = run_phase(config, parsed.command, api_key)
    print_phase_summary(parsed.command, summary)

    if parsed.command == "pilot":
        report_path = write_pilot_report(config)
        print("\n" + report_path.read_text(encoding="utf-8"))
        print("STOP: the full run has not started. Explicit user approval is required.")
        return 0 if summary["unresolved"] == 0 else 2

    if summary["unresolved"]:
        print("Judge and analysis not run because valid full results are incomplete.")
        return 2
    from judge import run_judge

    judge_summary = run_judge(config, api_key)
    print_phase_summary("judge", judge_summary)
    if judge_summary["unresolved"]:
        print("Analysis not run because valid judge results are incomplete.")
        return 2
    run_analysis(config)
    return 0


def parse_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    """Define a small CLI whose full phase requires an unmistakable approval flag."""
    parser = argparse.ArgumentParser(description="Run the platform-pricing bias experiment")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML configuration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate config and manifests without API calls")
    subparsers.add_parser("pilot", help="Run/resume the 80-trial pilot and stop")
    full_parser = subparsers.add_parser("full", help="Run/resume the approved full phase")
    full_parser.add_argument(
        "--approve-full",
        action="store_true",
        help="Confirm that the user reviewed and approved the pilot",
    )
    subparsers.add_parser("analyze", help="Regenerate analysis without API calls")
    v2_parser = subparsers.add_parser(
        "judge-v2", help="Run/resume the approved rubric-v2 judge only"
    )
    v2_parser.add_argument(
        "--approve-rubric-v2",
        action="store_true",
        help="Confirm that the user approved the exact rubric-v2 text",
    )
    for command, help_text in (
        ("mechanism-validate", "Validate mechanism manifests without API calls"),
        ("mechanism-pilot", "Run/resume the 76-trial mechanism pilot and stop"),
        ("mechanism-analyze", "Regenerate mechanism analysis without API calls"),
    ):
        mechanism_parser = subparsers.add_parser(command, help=help_text)
        mechanism_parser.add_argument(
            "--mechanism-config",
            default="config_mechanism.yaml",
            help="Path to the isolated mechanism configuration",
        )
    mechanism_full = subparsers.add_parser(
        "mechanism-full", help="Run/resume the approved 1,520-trial mechanism phase"
    )
    mechanism_full.add_argument(
        "--mechanism-config",
        default="config_mechanism.yaml",
        help="Path to the isolated mechanism configuration",
    )
    mechanism_full.add_argument(
        "--approve-mechanism-full",
        action="store_true",
        help="Confirm that the user reviewed and approved the mechanism pilot",
    )
    for command, help_text in (
        ("qwen-validate", "Validate all 760 prompt pairs without API calls"),
        ("qwen-analyze", "Regenerate Qwen comparison analysis without API calls"),
    ):
        qwen_parser = subparsers.add_parser(command, help=help_text)
        qwen_parser.add_argument(
            "--qwen-config",
            default="config_qwen.yaml",
            help="Path to the isolated Qwen configuration",
        )
    qwen_run = subparsers.add_parser(
        "qwen-run", help="Run/resume the approved 760-request Qwen comparison"
    )
    qwen_run.add_argument(
        "--qwen-config",
        default="config_qwen.yaml",
        help="Path to the isolated Qwen configuration",
    )
    qwen_run.add_argument(
        "--approve-qwen-run",
        action="store_true",
        help="Confirm the user approved the capped Qwen comparison",
    )
    qwen_thinking_validate = subparsers.add_parser(
        "qwen-thinking-validate", help="Validate the 38-prompt Qwen thinking pilot"
    )
    qwen_thinking_validate.add_argument(
        "--qwen-config",
        default="config_qwen_thinking.yaml",
        help="Path to the isolated Qwen thinking configuration",
    )
    qwen_thinking_pilot = subparsers.add_parser(
        "qwen-thinking-pilot", help="Run/resume the approved 38-request thinking pilot"
    )
    qwen_thinking_pilot.add_argument(
        "--qwen-config",
        default="config_qwen_thinking.yaml",
        help="Path to the isolated Qwen thinking configuration",
    )
    qwen_thinking_pilot.add_argument(
        "--approve-qwen-thinking-pilot",
        action="store_true",
        help="Confirm the user approved the capped Qwen thinking pilot",
    )
    qwen_thinking_full_validate = subparsers.add_parser(
        "qwen-thinking-full-validate", help="Validate all 760 Qwen thinking pairs"
    )
    qwen_thinking_full_validate.add_argument(
        "--qwen-config",
        default="config_qwen_thinking_full.yaml",
        help="Path to the full Qwen thinking configuration",
    )
    qwen_thinking_analyze = subparsers.add_parser(
        "qwen-thinking-analyze", help="Analyze saved Qwen thinking results"
    )
    qwen_thinking_analyze.add_argument(
        "--qwen-config",
        default="config_qwen_thinking_full.yaml",
        help="Path to the full Qwen thinking configuration",
    )
    qwen_thinking_full = subparsers.add_parser(
        "qwen-thinking-full", help="Run/resume the approved 760-request thinking phase"
    )
    qwen_thinking_full.add_argument(
        "--qwen-config",
        default="config_qwen_thinking_full.yaml",
        help="Path to the full Qwen thinking configuration",
    )
    qwen_thinking_full.add_argument(
        "--approve-qwen-thinking-full",
        action="store_true",
        help="Confirm the user approved the full Qwen thinking extension",
    )
    qwen_thinking_full.add_argument(
        "--approve-qwen-thinking-replacement",
        action="store_true",
        help="Confirm approval for the exact configured replacement request",
    )
    return parser.parse_args(arguments)


def run_qwen_command(parsed: argparse.Namespace, config: dict) -> int:
    """Dispatch the isolated Qwen workflow and enforce its spending gate."""
    from qwen_comparison import (
        run_qwen_comparison,
        validate_qwen_only,
        write_qwen_thinking_pilot_report,
    )

    if parsed.command in (
        "qwen-validate", "qwen-thinking-validate", "qwen-thinking-full-validate"
    ):
        counts = validate_qwen_only(config)
        print(
            f"Validated Qwen pairs: trials={counts['paired_trials']}, "
            f"unique_prompt_hashes={counts['unique_prompt_hashes']}"
        )
        return 0
    if parsed.command == "qwen-analyze":
        run_qwen_analysis(config)
        return 0
    if parsed.command == "qwen-thinking-analyze":
        run_qwen_thinking_analysis(config)
        return 0
    if parsed.command == "qwen-thinking-pilot":
        if not parsed.approve_qwen_thinking_pilot:
            raise SystemExit(
                "Qwen thinking pilot requires --approve-qwen-thinking-pilot."
            )
        api_key = os.environ.get("QWEN_API_KEY", "")
        summary = run_qwen_comparison(config, api_key)
        print_phase_summary("qwen-thinking-pilot", summary)
        if summary["unresolved"]:
            print("Pilot report not written because valid results are incomplete.")
            return 2
        report_path = write_qwen_thinking_pilot_report(config)
        print("\n" + report_path.read_text(encoding="utf-8"))
        print("STOP: the remaining 722 thinking prompts have not been submitted.")
        return 0
    if parsed.command == "qwen-thinking-full":
        if not parsed.approve_qwen_thinking_full:
            raise SystemExit(
                "Qwen thinking full requires --approve-qwen-thinking-full."
            )
        replacement_ids = config["experiment"].get(
            "authorized_replacement_trial_ids", []
        )
        if replacement_ids and not parsed.approve_qwen_thinking_replacement:
            raise SystemExit(
                "Configured Qwen replacement requires "
                "--approve-qwen-thinking-replacement."
            )
        api_key = os.environ.get("QWEN_API_KEY", "")
        summary = run_qwen_comparison(config, api_key)
        print_phase_summary("qwen-thinking-full", summary)
        if summary["unresolved"]:
            print("Thinking analysis not run because paired results are incomplete.")
            return 2
        run_qwen_thinking_analysis(config)
        return 0
    if not parsed.approve_qwen_run:
        raise SystemExit(
            "Qwen run requires --approve-qwen-run after explicit spending approval."
        )
    api_key = os.environ.get("QWEN_API_KEY", "")
    summary = run_qwen_comparison(config, api_key)
    print_phase_summary("qwen", summary)
    if summary["unresolved"]:
        print("Qwen analysis not run because valid paired results are incomplete.")
        return 2
    run_qwen_analysis(config)
    return 0


def run_mechanism_command(parsed: argparse.Namespace, config: dict) -> int:
    """Dispatch the isolated mechanism workflow and enforce its approval gate."""
    from mechanism_experiment import (
        generate_mechanism_trials,
        run_mechanism_phase,
        validate_mechanism_only,
        validate_mechanism_results,
        write_mechanism_pilot_report,
    )

    if parsed.command == "mechanism-validate":
        counts = validate_mechanism_only(config)
        print(
            f"Validated mechanism manifests: pilot={counts['pilot']}, "
            f"full={counts['full']}"
        )
        return 0
    if parsed.command == "mechanism-analyze":
        run_mechanism_analysis(config)
        return 0
    if parsed.command == "mechanism-full":
        if not parsed.approve_mechanism_full:
            raise SystemExit(
                "Mechanism full run requires --approve-mechanism-full after pilot review."
            )
        pilot_dir = Path(config["experiment"]["phases"]["pilot"]["output_dir"])
        pilot_trials = generate_mechanism_trials(config, "pilot")
        pilot_rows = read_csv_rows(pilot_dir / "results.csv")
        validate_mechanism_results(pilot_rows, pilot_trials, config)
        if len(pilot_rows) != len(pilot_trials):
            raise SystemExit(
                f"Mechanism pilot is incomplete ({len(pilot_rows)}/{len(pilot_trials)}); "
                "full run is blocked."
            )

    phase = "pilot" if parsed.command == "mechanism-pilot" else "full"
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    summary = run_mechanism_phase(config, phase, api_key)
    print_phase_summary(f"mechanism-{phase}", summary)
    if phase == "pilot":
        report_path = write_mechanism_pilot_report(config)
        print("\n" + report_path.read_text(encoding="utf-8"))
        print("STOP: mechanism full has not started. Explicit approval is required.")
        return 0 if summary["unresolved"] == 0 else 2
    if summary["unresolved"]:
        print("Mechanism analysis not run because valid full results are incomplete.")
        return 2
    run_mechanism_analysis(config)
    return 0


def assert_pilot_complete(config: dict) -> None:
    """Prevent a full run before all pilot cells have valid saved responses."""
    pilot_dir = Path(config["experiment"]["phases"]["pilot"]["output_dir"])
    rows = read_csv_rows(pilot_dir / "results.csv")
    trials = generate_trials(config, "pilot")
    validate_result_rows(rows, trials, config)
    if len(rows) != len(trials):
        raise SystemExit(
            f"Pilot is incomplete ({len(rows)}/{len(trials)} valid results); full run is blocked."
        )


def run_analysis(config: dict) -> None:
    """Import plotting dependencies only for the analysis phase."""
    from analysis import analyze_full_results

    report_path = analyze_full_results(config)
    print(f"Analysis complete: {report_path}")


def run_mechanism_analysis(config: dict) -> None:
    """Import mechanism plotting dependencies only for its analysis phase."""
    from mechanism_analysis import analyze_mechanism_results

    report_path = analyze_mechanism_results(config)
    print(f"Mechanism analysis complete: {report_path}")


def run_qwen_analysis(config: dict) -> None:
    """Import Qwen analysis dependencies only for its saved-data phase."""
    from qwen_analysis import analyze_qwen_results

    report_path = analyze_qwen_results(config)
    print(f"Qwen analysis complete: {report_path}")


def run_qwen_thinking_analysis(config: dict) -> None:
    """Generate the prompt-paired Qwen inference-mode comparison."""
    from qwen_thinking_analysis import analyze_qwen_thinking_results

    report_path = analyze_qwen_thinking_results(config)
    print(f"Qwen thinking analysis complete: {report_path}")


def print_phase_summary(phase: str, summary: dict[str, int]) -> None:
    """Print counts only; never print credentials or prompts."""
    print(
        f"{phase}: planned={summary['planned']}, successful={summary['successful']}, "
        f"unresolved={summary['unresolved']}, attempts={summary['attempts']}, "
        f"failure_events={summary['failure_events']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
