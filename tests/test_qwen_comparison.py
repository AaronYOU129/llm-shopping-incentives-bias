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
from experiment import CsvAppender, load_config, read_csv_rows


@pytest.fixture()
def qwen_config() -> dict:
    """Load the approved Qwen paired-replication configuration."""
    return load_config("config_qwen.yaml")


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

    qwen_comparison.request_qwen_completion(qwen_config, trial, "dummy-key")

    assert captured["model"] == "qwen3.7-plus-2026-05-26"
    assert captured["messages"] == [{"role": "user", "content": trial.prompt}]
    assert captured["temperature"] == 1.0
    assert captured["extra_body"] == {"enable_thinking": False}


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
        return json.dumps({
            "recommended": cheap_position,
            "reply": "Choose the cheaper equivalent listing.",
        })

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


@pytest.mark.parametrize("value", ["", "REPLACE_WITH_QWEN_API_KEY"])
def test_qwen_key_validation_rejects_absent_or_placeholder(value: str) -> None:
    """Fail before paid work when the Qwen credential is not configured."""
    with pytest.raises(ValueError, match="QWEN_API_KEY"):
        qwen_comparison.validate_qwen_api_key(value)
