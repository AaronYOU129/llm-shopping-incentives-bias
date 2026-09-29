"""
Purpose:    Verify exact DeepSeek-to-Qwen prompt pairing, guarded API parameters,
            resumability, request caps, and saved-data comparison analysis.
Inputs:     config_qwen.yaml, saved mechanism artifacts, and pytest mocks/temp paths.
Outputs:    Pytest evidence plus temporary Qwen CSV and Markdown artifacts.
Key Steps:  Validate the 760-prompt manifest, mock API execution, verify resumption,
            and regenerate comparison tables from deterministic synthetic responses.
How to Run: python -m pytest -q tests/test_qwen_comparison.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import qwen_analysis
import qwen_comparison
import qwen_thinking_analysis
from experiment import CsvAppender, load_config, read_csv_rows


@pytest.fixture()
def qwen_config() -> dict:
    """Load the approved Qwen paired-replication configuration."""
    return load_config("config_qwen.yaml")


@pytest.fixture()
def qwen_thinking_config() -> dict:
    """Load the approved prompt-matched Qwen thinking pilot configuration."""
    return load_config("config_qwen_thinking.yaml")


@pytest.fixture()
def qwen_thinking_full_config() -> dict:
    """Load the approved full Qwen thinking configuration."""
    return load_config("config_qwen_thinking_full.yaml")


def test_qwen_manifest_matches_all_saved_source_prompts(qwen_config: dict) -> None:
    """Require exactly 760 unique source IDs and byte-identical prompt hashes."""
    counts = qwen_comparison.validate_qwen_only(qwen_config)
    trials = qwen_comparison.generate_qwen_trials(qwen_config)

    assert counts == {"paired_trials": 760, "unique_prompt_hashes": 696}
    assert len({trial.trial_id for trial in trials}) == 760
    assert len({trial.source_trial_id for trial in trials}) == 760
    assert all(trial.model == "qwen3.7-plus/non-thinking" for trial in trials)


def test_qwen_request_uses_pinned_nonthinking_parameters(
    monkeypatch: pytest.MonkeyPatch, qwen_config: dict
) -> None:
    """Send one user message with the fixed snapshot and thinking disabled."""
    captured: dict = {}

    class FakeCompletions:
        """Capture the SDK arguments and return a valid JSON response."""

        def create(self, **parameters: object) -> SimpleNamespace:
            """Return an OpenAI-shaped response after recording parameters."""
            captured.update(parameters)
            message = SimpleNamespace(content='{"recommended":"A","reply":"Choose A."}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(
        qwen_comparison, "get_qwen_thread_client", lambda _config, _key: fake_client
    )
    trial = qwen_comparison.generate_qwen_trials(qwen_config)[0]

    completion = qwen_comparison.request_qwen_completion(
        qwen_config, trial, "dummy-key"
    )

    assert captured["model"] == "qwen3.7-plus-2026-05-26"
    assert captured["messages"] == [{"role": "user", "content": trial.prompt}]
    assert captured["temperature"] == 1.0
    assert captured["extra_body"] == {"enable_thinking": False}
    assert completion.content == '{"recommended":"A","reply":"Choose A."}'
    assert completion.reasoning_content == ""


def test_complete_qwen_run_resumes_without_extra_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qwen_config: dict,
) -> None:
    """Use exactly 760 reservations and make no call on a completed rerun."""
    isolated = copy.deepcopy(qwen_config)
    isolated["experiment"]["output_dir"] = str(tmp_path / "qwen")
    call_count = 0

    def fake_request(
        _config: dict,
        trial: qwen_comparison.QwenTrial,
        _api_key: str,
    ) -> str:
        """Return the cheaper listing while counting submitted requests."""
        nonlocal call_count
        call_count += 1
        cheap_position = "B" if trial.partner_position == "A" else "A"
        return qwen_comparison.QwenCompletion(
            content=json.dumps({
                "recommended": cheap_position,
                "reply": "Choose the cheaper equivalent listing.",
            }),
            reasoning_content="",
        )

    monkeypatch.setattr(qwen_comparison, "request_qwen_completion", fake_request)
    monkeypatch.setattr(qwen_comparison.RequestRateLimiter, "wait", lambda _self: None)

    first = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")
    second = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")

    expected = {
        "planned": 760,
        "successful": 760,
        "unresolved": 0,
        "attempts": 760,
        "failure_events": 0,
    }
    assert first == second == expected
    assert call_count == 760
    assert len(read_csv_rows(tmp_path / "qwen" / "results.csv")) == 760


def test_qwen_analysis_regenerates_all_outputs(
    tmp_path: Path, qwen_config: dict
) -> None:
    """Generate comparison tables and report from 760 synthetic Qwen responses."""
    isolated = copy.deepcopy(qwen_config)
    output_dir = tmp_path / "qwen"
    isolated["experiment"]["output_dir"] = str(output_dir)
    isolated["analysis"]["report_path"] = str(tmp_path / "QWEN_RESULTS.md")
    trials = qwen_comparison.generate_qwen_trials(isolated)
    appender = CsvAppender(
        output_dir / "results.csv", isolated["output"]["result_columns"]
    )
    for trial in trials:
        choose_partner = trial.condition == "incentive" and trial.framing == "fixed_amount"
        recommended = trial.partner_position if choose_partner else (
            "B" if trial.partner_position == "A" else "A"
        )
        parsed = {
            "recommended": recommended,
            "reply": "Choose this listing based on the stated prices.",
        }
        appender.append(qwen_comparison.build_qwen_result_row(
            isolated, trial, parsed, json.dumps(parsed)
        ))

    report_path = qwen_analysis.analyze_qwen_results(isolated)
    cells = pd.read_csv(output_dir / "qwen_partner_choice_by_cell.csv")
    framing = pd.read_csv(output_dir / "model_framing_summary.csv")
    nudge = pd.read_csv(output_dir / "model_nudge_summary.csv")
    contrasts = pd.read_csv(output_dir / "qwen_framing_contrasts.csv")
    paired = pd.read_csv(output_dir / "deepseek_qwen_paired_comparison.csv")
    consistency = pd.read_csv(output_dir / "recommendation_consistency_audit.csv")

    assert report_path.exists()
    assert len(cells) == 19
    assert len(framing) == 8
    assert len(nudge) == 4
    assert len(contrasts) == 3
    assert len(paired) == 4
    assert len(consistency) == 760
    assert set(paired["framing"]) == {
        "no_incentive", "percentage", "percentage_computed", "fixed_amount"
    }


def test_qwen_thinking_pilot_is_balanced_and_prompt_paired(
    qwen_thinking_config: dict,
) -> None:
    """Select one saved prompt per cell while preserving exact non-thinking pairing."""
    counts = qwen_comparison.validate_qwen_only(qwen_thinking_config)
    trials = qwen_comparison.generate_qwen_trials(qwen_thinking_config)

    assert counts["paired_trials"] == 38
    assert len(trials) == 38
    assert all(trial.rep == 1 for trial in trials)
    assert all(trial.model == "qwen3.7-plus/thinking" for trial in trials)
    assert sum(trial.condition == "control" for trial in trials) == 2
    assert sum(trial.condition == "incentive" for trial in trials) == 36
    incentive_cells = {
        (trial.framing, trial.incentive_rate, trial.scenario, trial.nudge)
        for trial in trials if trial.condition == "incentive"
    }
    assert len(incentive_cells) == 36


def test_qwen_thinking_full_reuses_pilot_ids_and_covers_all_prompts(
    qwen_thinking_config: dict,
    qwen_thinking_full_config: dict,
) -> None:
    """Expand to 760 pairs while retaining every completed pilot identifier."""
    pilot = qwen_comparison.generate_qwen_trials(qwen_thinking_config)
    full = qwen_comparison.generate_qwen_trials(qwen_thinking_full_config)

    assert len(full) == 760
    assert {trial.trial_id for trial in pilot} <= {trial.trial_id for trial in full}
    assert len({trial.source_trial_id for trial in full}) == 760


def test_qwen_thinking_summary_uses_paired_transitions() -> None:
    """Base the mode test and spending estimates on prompt-paired outcomes."""
    paired = pd.DataFrame({
        "scope": ["all"] * 4,
        "nonthinking_choice": [0, 0, 1, 1],
        "chose_partner": [0, 1, 0, 1],
        "user_extra_spend": [90, 90, 70, 70],
    })

    row = qwen_thinking_analysis.summarize_paired_groups(paired, ["scope"]).iloc[0]

    assert row.n_pairs == 4
    assert row.nonthinking_partner_choices == 2
    assert row.thinking_partner_choices == 2
    assert row.nonthinking_0_thinking_1 == 1
    assert row.nonthinking_1_thinking_0 == 1
    assert row.mcnemar_exact_p_value == 1.0
    assert row.nonthinking_mean_extra_spend == 35.0
    assert row.thinking_mean_extra_spend == 40.0


def test_qwen_thinking_request_uses_same_snapshot_and_returns_reasoning(
    monkeypatch: pytest.MonkeyPatch,
    qwen_thinking_config: dict,
) -> None:
    """Enable thinking on the pinned snapshot and retain its separate reasoning field."""
    captured: dict = {}

    class FakeCompletions:
        """Capture thinking parameters and return both reasoning and final JSON."""

        def create(self, **parameters: object) -> SimpleNamespace:
            """Return an OpenAI-shaped hybrid-thinking response."""
            captured.update(parameters)
            message = SimpleNamespace(
                content='{"recommended":"A","reply":"Choose A."}',
                reasoning_content="The listings are equivalent, so compare prices.",
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(
        qwen_comparison, "get_qwen_thread_client", lambda _config, _key: fake_client
    )
    trial = qwen_comparison.generate_qwen_trials(qwen_thinking_config)[0]

    completion = qwen_comparison.request_qwen_completion(
        qwen_thinking_config, trial, "dummy-key"
    )

    assert captured["model"] == "qwen3.7-plus-2026-05-26"
    assert captured["messages"] == [{"role": "user", "content": trial.prompt}]
    assert captured["temperature"] == 1.0
    assert captured["extra_body"] == {"enable_thinking": True}
    assert completion.reasoning_content.startswith("The listings are equivalent")


def test_complete_qwen_thinking_pilot_stops_at_38_requests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qwen_thinking_config: dict,
) -> None:
    """Complete and resume the pilot without submitting beyond its 38-call cap."""
    isolated = copy.deepcopy(qwen_thinking_config)
    isolated["experiment"]["output_dir"] = str(tmp_path / "qwen-thinking")
    isolated["analysis"]["pilot_report_path"] = str(tmp_path / "PILOT.md")
    call_count = 0

    def fake_request(
        _config: dict,
        trial: qwen_comparison.QwenTrial,
        _api_key: str,
    ) -> qwen_comparison.QwenCompletion:
        """Return a valid cheaper choice and count each reserved request."""
        nonlocal call_count
        call_count += 1
        cheap_position = "B" if trial.partner_position == "A" else "A"
        return qwen_comparison.QwenCompletion(
            content=json.dumps({
                "recommended": cheap_position,
                "reply": "Choose the cheaper equivalent listing.",
            }),
            reasoning_content="Both listings are equivalent, so minimize user cost.",
        )

    monkeypatch.setattr(qwen_comparison, "request_qwen_completion", fake_request)
    monkeypatch.setattr(qwen_comparison.RequestRateLimiter, "wait", lambda _self: None)

    first = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")
    second = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")
    report = qwen_comparison.write_qwen_thinking_pilot_report(isolated)

    expected = {
        "planned": 38,
        "successful": 38,
        "unresolved": 0,
        "attempts": 38,
        "failure_events": 0,
    }
    assert first == second == expected
    assert call_count == 38
    assert report.exists()
    assert "Remaining full-run prompts submitted: 0" in report.read_text()


def test_qwen_resume_does_not_retry_a_previously_attempted_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qwen_thinking_config: dict,
) -> None:
    """Resume only never-submitted trials when automatic retries are prohibited."""
    isolated = copy.deepcopy(qwen_thinking_config)
    output_dir = tmp_path / "qwen-thinking"
    isolated["experiment"]["output_dir"] = str(output_dir)
    first_trial = qwen_comparison.generate_qwen_trials(isolated)[0]
    attempt_appender = CsvAppender(
        output_dir / "request_attempts.csv", isolated["output"]["attempt_columns"]
    )
    attempt_appender.append({
        "sequence": 1,
        "trial_id": first_trial.trial_id,
        "trial_attempt": 1,
        "ts": "2026-09-29T00:00:00+00:00",
    })
    requested_ids: list[str] = []

    def fake_request(
        _config: dict,
        trial: qwen_comparison.QwenTrial,
        _api_key: str,
    ) -> qwen_comparison.QwenCompletion:
        """Record requested IDs and return a valid non-Partner choice."""
        requested_ids.append(trial.trial_id)
        cheap_position = "B" if trial.partner_position == "A" else "A"
        return qwen_comparison.QwenCompletion(
            content=json.dumps({
                "recommended": cheap_position,
                "reply": "Choose the cheaper equivalent listing.",
            }),
            reasoning_content="Reasoning retained.",
        )

    monkeypatch.setattr(qwen_comparison, "request_qwen_completion", fake_request)
    monkeypatch.setattr(qwen_comparison.RequestRateLimiter, "wait", lambda _self: None)

    summary = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")

    assert first_trial.trial_id not in requested_ids
    assert len(requested_ids) == 37
    assert summary["successful"] == 37
    assert summary["unresolved"] == 1
    assert summary["attempts"] == 38


def test_qwen_runs_only_the_exact_authorized_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qwen_thinking_config: dict,
) -> None:
    """Permit one configured second attempt without reopening other failures."""
    isolated = copy.deepcopy(qwen_thinking_config)
    output_dir = tmp_path / "qwen-thinking"
    isolated["experiment"]["output_dir"] = str(output_dir)
    trials = qwen_comparison.generate_qwen_trials(isolated)
    replacement_trial = trials[0]
    skipped_failed_trial = trials[1]
    isolated["experiment"]["authorized_replacement_trial_ids"] = [
        replacement_trial.trial_id
    ]
    isolated["experiment"]["request_attempt_cap"] = 39
    attempt_appender = CsvAppender(
        output_dir / "request_attempts.csv", isolated["output"]["attempt_columns"]
    )
    for sequence, trial in enumerate((replacement_trial, skipped_failed_trial), 1):
        attempt_appender.append({
            "sequence": sequence,
            "trial_id": trial.trial_id,
            "trial_attempt": 1,
            "ts": "2026-09-29T00:00:00+00:00",
        })
    requested_ids: list[str] = []

    def fake_request(
        _config: dict,
        trial: qwen_comparison.QwenTrial,
        _api_key: str,
    ) -> qwen_comparison.QwenCompletion:
        """Return a valid response while retaining submitted identifiers."""
        requested_ids.append(trial.trial_id)
        cheap_position = "B" if trial.partner_position == "A" else "A"
        return qwen_comparison.QwenCompletion(
            content=json.dumps({
                "recommended": cheap_position,
                "reply": "Choose the cheaper equivalent listing.",
            }),
            reasoning_content="Reasoning retained.",
        )

    monkeypatch.setattr(qwen_comparison, "request_qwen_completion", fake_request)
    monkeypatch.setattr(qwen_comparison.RequestRateLimiter, "wait", lambda _self: None)

    summary = qwen_comparison.run_qwen_comparison(isolated, "dummy-key")

    assert replacement_trial.trial_id in requested_ids
    assert skipped_failed_trial.trial_id not in requested_ids
    assert len(requested_ids) == 37
    assert summary["successful"] == 37
    assert summary["unresolved"] == 1
    assert summary["attempts"] == 39


@pytest.mark.parametrize("value", ["", "REPLACE_WITH_QWEN_API_KEY"])
def test_qwen_key_validation_rejects_absent_or_placeholder(value: str) -> None:
    """Fail before paid work when the Qwen credential is not configured."""
    with pytest.raises(ValueError, match="QWEN_API_KEY"):
        qwen_comparison.validate_qwen_api_key(value)
