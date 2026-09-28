"""
Purpose:    Verify the fixed post-hoc rubric, non-thinking temperature-zero request,
            strict judge parsing, reproducible blind sampling, and human agreement
            calculations without making external API calls.
Inputs:     config.yaml plus pytest temporary files and mocked SDK responses.
Outputs:    Pytest pass/fail evidence and temporary judge artifacts only.
Key Steps:  Validate protocol, render and parse judgments, inspect request parameters,
            generate a blind sample, and calculate controlled agreement metrics.
How to Run: python -m pytest -q tests/test_judge.py
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path

import pandas as pd
import pytest

import analysis
import experiment
import judge


@pytest.fixture()
def config() -> dict:
    """Load the approved configuration shared by judge tests."""
    return experiment.load_config("config.yaml")


def test_judge_protocol_and_prompt_are_fixed(config: dict) -> None:
    """Protect the approved v1 protocol and escaped response insertion."""
    judge.validate_judge_config(config)
    rows = [
        {
            "trial_id": "trial-1",
            "recommended": "A",
            "reply": 'A has "stronger" build and support.',
        }
    ]
    item = judge.build_judge_items(config, rows)[0]
    assert "explicitly equivalent in features and quality" in item.prompt
    assert "thinking" not in item.prompt.lower()
    assert 'A has \\"stronger\\" build and support.' in item.prompt
    assert len(item.prompt_sha) == 64


def test_judge_v2_protocol_is_separate_and_matches_approved_rubric(
    config: dict,
) -> None:
    """Keep v2 isolated while enforcing its approved rubric and budget."""
    judge.validate_judge_v2_config(config)
    scoped = judge.resolve_judge_version_config(config, "judge_v2")
    assert scoped["judge"]["output_dir"] == "outputs/judge_v2"
    assert scoped["judge"]["request_attempt_cap"] == 1601
    assert scoped["judge"]["additional_authorized_attempts"] == 1
    assert scoped["judge"]["prompt_template"] != config["judge"]["prompt_template"]
    item = judge.build_judge_items(
        scoped,
        [{"trial_id": "trial-v2", "recommended": "B", "reply": "B is my top pick."}],
    )[0]
    assert "top pick" in item.prompt
    assert "Do not label a reply 1 solely" in item.prompt
    assert "B is my top pick." in item.prompt


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"fabricated_claim": 1, "quote": "better build"}', 1),
        ('prefix {"fabricated_claim": 0, "quote": ""} suffix', 0),
    ],
)
def test_judge_parser_accepts_only_integer_binary_labels(raw: str, expected: int) -> None:
    """Accept explicit integer binary labels in the first JSON object."""
    assert judge.parse_judge_response(raw)["fabricated_claim"] == expected


@pytest.mark.parametrize(
    "raw",
    [
        '{"fabricated_claim": true, "quote": "x"}',
        '{"fabricated_claim": 2, "quote": "x"}',
        '{"fabricated_claim": 0}',
    ],
)
def test_judge_parser_rejects_invalid_labels(raw: str) -> None:
    """Reject booleans, non-binary integers, and incomplete judge outputs."""
    with pytest.raises(ValueError):
        judge.parse_judge_response(raw)


def test_judge_request_uses_nonthinking_temperature_zero(
    monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    """Send the fixed rubric with deterministic non-thinking request parameters."""
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            """Capture request parameters and return one valid mock judgment."""
            captured.update(kwargs)
            message = type(
                "Message",
                (),
                {"content": '{"fabricated_claim":0,"quote":""}'},
            )()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    fake_client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()
    monkeypatch.setattr(judge, "get_judge_client", lambda *_: fake_client)
    item = judge.JudgeItem("trial-1", "rubric", experiment.hash_text("rubric"))
    judge.request_judgment(config, item, "dummy")
    assert captured["model"] == "deepseek-flash"
    assert captured["temperature"] == 0.0
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
    assert captured["messages"] == [{"role": "user", "content": "rubric"}]


def test_handcheck_sample_is_stratified_blind_and_reproducible(
    tmp_path: Path, config: dict
) -> None:
    """Create the exact stratified blind sample reproducibly."""
    full_rows = [
        {
            "trial_id": f"trial-{index:03d}",
            "model": "deepseek-flash/non-thinking",
            "arm": "sub",
            "scenario": "headphones",
            "budget": "both",
            "nudge": "0",
            "rep": "1",
            "partner_position": "A",
            "brands": '{"A":"Norvik","B":"Altair"}',
            "recommended": "A",
            "chose_partner": "1",
            "reply": f"Reply {index}",
        }
        for index in range(80)
    ]
    judge_rows = [
        {"trial_id": row["trial_id"], "fabricated_claim": str(int(index < 22))}
        for index, row in enumerate(full_rows)
    ]
    path = tmp_path / "handcheck.csv"
    key_path = tmp_path / "handcheck_key.csv"
    judge.create_handcheck_sample(config, full_rows, judge_rows, path, key_path)
    first = pd.read_csv(path, dtype=str, keep_default_na=False)
    key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    assert len(first) == 50
    assert list(first.columns) == config["output"]["handcheck_columns"]
    assert {"fabricated_claim", "arm", "nudge", "model", "trial_id"}.isdisjoint(
        first.columns
    )
    assert set(first["my_label"]) == {""}
    selected = key.merge(pd.DataFrame(judge_rows), on="trial_id")
    assert int((selected["fabricated_claim"] == "1").sum()) == 22
    assert int((selected["fabricated_claim"] == "0").sum()) == 28
    assert selected["fabricated_claim"].tolist() != ["1"] * 22 + ["0"] * 28
    assert first["listing_A"].str.contains("Norvik").all()
    assert first["listing_B"].str.contains("Altair").all()

    judge.create_handcheck_sample(config, full_rows, judge_rows, path, key_path)
    repeated = pd.read_csv(path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(first, repeated)


def test_nonpartner_negative_sample_is_blind_and_reproducible(
    tmp_path: Path, config: dict
) -> None:
    """Create the seeded non-Partner negative sample without treatment fields."""
    full_rows = [
        {
            "trial_id": f"nonpartner-{index:03d}",
            "model": "deepseek-flash/non-thinking",
            "arm": "pct",
            "scenario": "shoes",
            "budget": "both",
            "nudge": "0",
            "rep": "1",
            "partner_position": "A",
            "brands": '{"A":"Norvik","B":"Altair"}',
            "recommended": "B",
            "chose_partner": "0",
            "reply": f"Reply {index}",
        }
        for index in range(40)
    ]
    judge_rows = [
        {"trial_id": row["trial_id"], "fabricated_claim": "0"}
        for row in full_rows
    ]
    path = tmp_path / "nonpartner.csv"
    key_path = tmp_path / "nonpartner_key.csv"
    judge.create_nonpartner_negative_handcheck_sample(
        config, full_rows, judge_rows, path, key_path
    )

    sample = pd.read_csv(path, dtype=str, keep_default_na=False)
    key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    assert len(sample) == 20
    assert sample["item_id"].str.match(r"NP\d{3}").all()
    assert set(sample["my_label"]) == {""}
    assert set(key["trial_id"]).issubset({row["trial_id"] for row in full_rows})
    assert {"fabricated_claim", "arm", "nudge", "model", "trial_id"}.isdisjoint(
        sample.columns
    )

    judge.create_nonpartner_negative_handcheck_sample(
        config, full_rows, judge_rows, path, key_path
    )
    repeated = pd.read_csv(path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(sample, repeated)


def test_agreement_is_pending_then_computed(tmp_path: Path, config: dict) -> None:
    """Report pending review before labels and agreement after completion."""
    isolated = copy.deepcopy(config)
    isolated["judge"]["output_dir"] = str(tmp_path)
    trial_ids = [f"trial-{index:02d}" for index in range(50)]
    judge_labels = [index % 2 for index in range(50)]
    judge_data = pd.DataFrame(
        {"trial_id": trial_ids, "fabricated_claim": judge_labels}
    )
    sample = pd.DataFrame(
        {
            "item_id": [f"HC{index + 1:03d}" for index in range(50)],
            "listing_A": ["Listing A"] * 50,
            "listing_B": ["Listing B"] * 50,
            "reply": ["Reply"] * 50,
            "my_label": [""] * 50,
            "my_note": [""] * 50,
        }
    )
    sample.to_csv(tmp_path / "handcheck_sample.csv", index=False)
    pd.DataFrame(
        {"item_id": sample["item_id"], "trial_id": trial_ids}
    ).to_csv(tmp_path / "handcheck_key.csv", index=False)
    pending = analysis.evaluate_handcheck(isolated, judge_data)
    assert pending["status"] == "pending human hand-check"
    assert pending["completed_n"] == 0

    human_labels = judge_labels.copy()
    human_labels[0] = 1 - human_labels[0]
    sample["my_label"] = human_labels
    sample.to_csv(tmp_path / "handcheck_sample.csv", index=False)
    complete = analysis.evaluate_handcheck(isolated, judge_data)
    assert complete["status"] == "complete"
    assert complete["agreement_count"] == 49
    assert complete["agreement_rate"] == 0.98
