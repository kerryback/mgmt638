"""Tests for the Jev playground.

The Jev tests are live and not mocked. A mocked test of a demo whose entire
claim is "the model returns typed answers" would assert only that the mock was
written correctly. They need OPENROUTER_API_KEY; without one they skip rather
than fail.

Run:  .venv/bin/python -m pytest test_jevdemo.py -v
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient

import config
import jev
from app import app

needs_key = pytest.mark.skipif(not config.API_KEY, reason="no OPENROUTER_API_KEY")
client = TestClient(app)


# --- the page (no network) ---------------------------------------------------


def test_page_renders_with_presets_substituted():
    body = client.get("/").text
    assert not re.search(r"__[A-Z]+__", body), "a placeholder was left unsubstituted"
    assert "Jev playground" in body
    for name in config.PRESETS:
        assert name in body


def test_every_preset_is_a_well_formed_request():
    """A preset that errors on Run would waste class time."""
    for name, preset in config.PRESETS.items():
        assert "state" in preset and "questions" in preset, name
        for qname, q in preset["questions"].items():
            assert q["type"] in {"noul", "choice", "score"}, (name, qname)
            if q["type"] in {"choice", "score"}:
                assert q.get("criteria"), f"{name}/{qname} needs criteria"
        json.dumps(preset)      # must survive the trip to the browser


def test_templates_match_the_three_question_types():
    assert set(config.TEMPLATES) == {"noul", "choice", "score"}
    for kind, tpl in config.TEMPLATES.items():
        assert tpl["type"] == kind


def test_empty_questions_is_rejected_before_calling_jev():
    r = client.post("/api/run", json={"state": {"x": "y"}, "questions": {}})
    assert r.status_code == 400
    assert "at least one question" in r.json()["detail"]


# --- Jev (live) --------------------------------------------------------------


@needs_key
def test_run_returns_all_three_answer_types_typed():
    result = asyncio.run(
        jev.run(
            {"ticket": "I was charged twice. Please fix this ASAP."},
            config.PRESETS["Support ticket"]["questions"],
        )
    )
    answers = result["answers"]
    assert set(answers) == {"billing", "tone", "urgency"}

    assert isinstance(answers["billing"]["noul"], float)
    assert 0.0 <= answers["billing"]["noul"] <= 1.0
    assert answers["billing"]["noul"] > 0.5, "a double charge is a billing ticket"

    assert answers["tone"]["choice"] in {"calm", "frustrated", "angry"}
    assert set(answers["tone"]["probabilities"]) == {"calm", "frustrated", "angry"}

    assert 0.0 <= answers["urgency"]["score"] <= 2.0
    # int keys here; they become strings once serialized to the browser, which is
    # why the page indexes the legend with a string.
    assert answers["urgency"]["legend"] == {0: "low", 1: "medium", 2: "high"}

    assert result["model"].startswith("typesafe/jev")
    assert result["usage"]["input_tokens"] > 0


@needs_key
@pytest.mark.parametrize("preset", list(config.PRESETS))
def test_each_preset_actually_runs(preset):
    p = config.PRESETS[preset]
    result = asyncio.run(jev.run(p["state"], p["questions"]))
    assert set(result["answers"]) == set(p["questions"])


@needs_key
def test_endpoint_surfaces_sdk_validation_errors():
    r = client.post(
        "/api/run",
        json={"state": {"x": "y"}, "questions": {"tone": {"type": "choice", "instructions": "Tone?"}}},
    )
    assert r.status_code == 400
    assert "criteria" in r.json()["detail"]


@needs_key
def test_endpoint_round_trip():
    p = config.PRESETS["Earnings call"]
    r = client.post("/api/run", json={"state": p["state"], "questions": p["questions"]})
    assert r.status_code == 200
    body = r.json()
    # steering margin to "the low end of our prior range" is a guidance cut, and
    # the criteria on that Noul say so explicitly
    assert body["answers"]["cuts_guidance"]["noul"] > 0.5
    assert body["answers"]["confidence_tone"]["score"] <= 1.5, "this is not a confident quote"
    assert body["elapsed_ms"] > 0


@needs_key
def test_legend_and_probability_keys_are_strings_over_json():
    """The browser indexes legend/probabilities by string key; lock that in."""
    p = config.PRESETS["Support ticket"]
    body = client.post("/api/run", json={"state": p["state"], "questions": p["questions"]}).json()
    score = body["answers"]["urgency"]
    assert set(score["legend"]) == {"0", "1", "2"}
    assert set(score["probabilities"]) == {"0", "1", "2"}


def test_new_preset_is_minimal_and_separated():
    """The blank slate is one field and one question -- the smallest thing that runs."""
    new = config.PRESETS[config.NEW_PRESET]
    assert len(new["state"]) == 1
    assert len(new["questions"]) == 1
    assert config.NEW_PRESET != config.DEFAULT_PRESET


def test_dropdown_groups_demos_apart_from_the_blank_slate():
    body = client.get("/").text
    assert 'label = "Demos"' in body and 'label = "Start from scratch"' in body


def test_there_are_three_demos_plus_the_blank_slate():
    demos = [k for k in config.PRESETS if k != config.NEW_PRESET]
    assert len(demos) == 3, demos
    assert demos[0] == config.DEFAULT_PRESET, "the default should load first"


def test_company_screen_asks_many_questions_in_one_call():
    """The fan-out is the demo; if it shrinks, the point is lost."""
    assert len(config.PRESETS["Company screen"]["questions"]) >= 8


def test_blank_slate_is_marked_blank_and_demos_are_not():
    """`blank` drives placeholder-vs-content in the page; demos must load as content."""
    assert config.PRESETS[config.NEW_PRESET].get("blank") is True
    for name, p in config.PRESETS.items():
        if name != config.NEW_PRESET:
            assert not p.get("blank"), f"{name} would load as empty boxes"


def test_selecting_a_demo_clears_the_previous_answers():
    """Leaving stale answers up reads as though selecting a demo ran it."""
    body = client.get("/").text
    loader = body[body.index("function loadPreset"):body.index("$(\"preset\").addEventListener")]
    assert "out.innerHTML = EMPTY_MSG" in loader


def test_run_is_never_wired_to_preset_selection():
    """Nothing should fire a request except the Run button and the keyboard shortcut."""
    body = client.get("/").text
    loader = body[body.index("function loadPreset"):body.index("$(\"preset\").addEventListener")]
    assert "run()" not in loader


def test_answer_type_badges_carry_an_explanation():
    """The badge tooltip is where a student finds out what a noul is."""
    body = client.get("/").text
    assert "Short for Bernoulli" in body
    for kind in ("noul:", "choice:", "score:"):
        assert kind in body
