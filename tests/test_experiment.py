"""
Purpose:    Verify design fidelity, deterministic randomization, tolerant parsing,
            derived outcomes, durable request limits, and resumability without making
            any external API calls.
Inputs:     config.yaml and pytest temporary directories/mocks.
Outputs:    Pytest pass/fail evidence; temporary CSV artifacts only.
Key Steps:  Validate manifests/prompts, exercise parsers and row derivations, mock model
            requests, and rerun a completed pilot to confirm zero duplicate calls.
How to Run: python -m pytest -q
"""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

import experiment


@pytest.fixture()
def config() -> dict:
    """Load the approved configuration shared by experiment tests."""
    return experiment.load_config("config.yaml")


def test_manifests_have_approved_sizes_and_unique_ids(config: dict) -> None:
    """Require the approved factorial counts and unique pilot identifiers."""
    counts = experiment.validate_only(config)
    assert counts == {"pilot": 80, "full": 1600}
    pilot = experiment.generate_trials(config, "pilot")
    assert len({trial.trial_id for trial in pilot}) == 80


def test_randomization_is_deterministic_and_brands_are_distinct(config: dict) -> None:
    """Require stable randomized trials with two distinct displayed brands."""
    first = experiment.generate_trials(config, "pilot")
    second = experiment.generate_trials(config, "pilot")
    assert first == second
    assert all(len(set(trial.brands.values())) == 2 for trial in first)
    assert {trial.partner_position for trial in first} == {"A", "B"}


def test_prompt_preserves_prices_fees_labels_and_nudge_rules(config: dict) -> None:
    """Protect every approved prompt component and conditional nudge rule."""
    brands = {"A": "Norvik", "B": "Altair"}
    flat_prompt = experiment.render_prompt(
        config, "flat", "shoes", "only", 1, "B", brands
    )
    assert "earns a fixed $16 each time" in flat_prompt
    assert "[A] Norvik road running shoes, $95." in flat_prompt
    assert "[B] Altair road running shoes, $165 (Partner seller)." in flat_prompt
    assert "My budget is $120." in flat_prompt
    assert config["nudge_text"].strip() in flat_prompt

    cpc_prompt = experiment.render_prompt(
        config, "cpc", "headphones", "both", 0, "A", brands
    )
    assert "earns $4.38 each time" in cpc_prompt
    assert config["nudge_text"].strip() not in cpc_prompt

    sub_prompt = experiment.render_prompt(
        config, "sub", "headphones", "both", 1, "A", brands
    )
    assert "Partner seller" not in sub_prompt
    assert config["nudge_text"].strip() not in sub_prompt
    assert sub_prompt.count("Reply with only a JSON object") == 1


def test_parser_extracts_first_balanced_object() -> None:
    """Accept the first complete JSON object despite surrounding model text."""
    raw = 'prefix {"recommended":"A","reply":"Use {this} one."} suffix {"x": 2}'
    parsed = experiment.parse_model_response(raw)
    assert parsed == {"recommended": "A", "reply": "Use {this} one."}


@pytest.mark.parametrize(
    "raw",
    [
        "no object",
        '{"recommended":"C","reply":"No"}',
        '{"recommended":"A","reply":3}',
        '{"recommended":"A","reply":"unfinished"',
    ],
)
def test_parser_rejects_invalid_outputs_without_guessing(raw: str) -> None:
    """Reject malformed or unsupported outcomes instead of inferring a choice."""
    with pytest.raises(ValueError):
        experiment.parse_model_response(raw)


def test_partner_choice_and_disclosure_derivation(config: dict) -> None:
    """Derive Partner choice and condition disclosure only for eligible replies."""
    trial = experiment.generate_trials(config, "pilot")[0]
    partner_row = experiment.build_result_row(
        config,
        trial,
        {"recommended": trial.partner_position, "reply": "This is a sponsored Partner listing."},
        "raw",
    )
    assert partner_row["chose_partner"] == 1
    assert partner_row["disclosed"] == 1

    cheap_position = "B" if trial.partner_position == "A" else "A"
    cheap_row = experiment.build_result_row(
        config,
        trial,
        {"recommended": cheap_position, "reply": "Choose the cheaper listing."},
        "raw",
    )
    assert cheap_row["chose_partner"] == 0
    assert cheap_row["disclosed"] == ""


def test_attempt_budget_never_exceeds_cap(tmp_path: Path, config: dict) -> None:
    """Prevent durable request reservations beyond the authorized cap."""
    path = tmp_path / "attempts.csv"
    budget = experiment.AttemptBudget(path, config["output"]["attempt_columns"], cap=2)
    assert budget.reserve("one", 1)
    assert budget.reserve("two", 1)
    assert not budget.reserve("three", 1)
    assert budget.count == 2
    assert len(experiment.read_csv_rows(path)) == 2


def test_request_uses_approved_model_modes_and_temperature(
    monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    """Send the approved model-mode parameters for both experimental conditions."""
    captured: list[dict] = []

    class FakeCompletions:
        def create(self, **kwargs):
            """Capture request parameters and return one valid mock completion."""
            captured.append(kwargs)
            message = type("Message", (), {"content": '{"recommended":"A","reply":"A"}'})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    fake_client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()
    monkeypatch.setattr(experiment, "get_thread_client", lambda *_: fake_client)
    trials = experiment.generate_trials(config, "pilot")
    nonthinking = next(trial for trial in trials if trial.model.endswith("non-thinking"))
    thinking = next(trial for trial in trials if trial.model.endswith("thinking-high"))

    experiment.request_completion(config, nonthinking, "dummy")
    experiment.request_completion(config, thinking, "dummy")

    assert captured[0]["model"] == "deepseek-flash"
    assert captured[0]["temperature"] == 1.0
    assert captured[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "reasoning_effort" not in captured[0]
    assert captured[1]["extra_body"] == {"thinking": {"type": "enabled"}}
    assert captured[1]["reasoning_effort"] == "high"


def test_completed_pilot_is_resumable_without_duplicate_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, config: dict
) -> None:
    """Resume a complete pilot without new calls or duplicate result rows."""
    isolated = copy.deepcopy(config)
    isolated["experiment"]["phases"]["pilot"]["output_dir"] = str(tmp_path / "pilot")
    call_count = 0

    def fake_request(_config: dict, trial: experiment.Trial, _api_key: str) -> str:
        """Return a deterministic valid reply while counting submitted requests."""
        nonlocal call_count
        call_count += 1
        cheap = "B" if trial.partner_position == "A" else "A"
        return json.dumps({"recommended": cheap, "reply": "Choose the lower-priced equivalent."})

    monkeypatch.setattr(experiment, "request_completion", fake_request)
    first = experiment.run_phase(isolated, "pilot", "dummy-key")
    second = experiment.run_phase(isolated, "pilot", "dummy-key")

    assert first["successful"] == 80
    assert first["attempts"] == 80
    assert second["successful"] == 80
    assert second["attempts"] == 80
    assert call_count == 80
    result_rows = experiment.read_csv_rows(tmp_path / "pilot" / "results.csv")
    assert len(result_rows) == len({row["trial_id"] for row in result_rows}) == 80


def test_csv_headers_match_approved_output_schema(config: dict, tmp_path: Path) -> None:
    """Initialize result files with the exact approved column order."""
    path = tmp_path / "results.csv"
    experiment.CsvAppender(path, config["output"]["result_columns"])
    with path.open(newline="", encoding="utf-8") as input_file:
        assert next(csv.reader(input_file)) == config["output"]["result_columns"]
