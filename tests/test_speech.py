"""A spoken take held to its line before a person hears it (§PW323).

A tone between two silences stands in for a voice: what is measured is where the sound
starts and stops and how loud it is, which a tone has exactly. The transcription is
replaced, since faster-whisper is optional and a test downloads no model.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave import sound
from test_sound import RATE, tone, written


def take(where, lead=0.5, spoken=1.0, tail=0.8, amplitude=0.5):
    quiet = np.zeros
    samples = np.concatenate([
        quiet(int(lead * RATE)), tone(spoken, amplitude=amplitude),
        quiet(int(tail * RATE)),
    ])
    return written(where, samples)


def test_a_take_says_its_silences_and_its_rate(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", lambda path, vocabulary=(): None)
    found = sound.speech(take(tmp_path / "t.wav"), "Hold fast")
    assert found["lead_silence"] == pytest.approx(0.5, abs=0.03)
    assert found["tail_silence"] == pytest.approx(0.8, abs=0.03)
    # Eight letters over a second spoken.
    assert found["rate"] == pytest.approx(8.0, rel=0.06)
    assert found["said"] is None and "faster-whisper" in found["unheard"]


def test_the_projects_bounds_name_what_a_take_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", lambda path, vocabulary=(): None)
    (tmp_path / "polyweave.toml").write_text(
        "[voice]\nlead_silence = 0.25\ntail_silence = 1.0\nrate = [10.0, 20.0]\n",
        encoding="utf-8",
    )
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert [one["measure"] for one in said["failed"]] == ["lead_silence", "rate"]


def test_no_bound_is_no_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", lambda path, vocabulary=(): None)
    take(tmp_path / "t.wav", lead=2.0)
    assert sound.spoken("t.wav", text="Go", root=str(tmp_path))["failed"] == []


def test_a_misread_name_is_named_and_the_worlds_names_are_expected(
    tmp_path, monkeypatch
):
    asked = {}

    def heard(path, vocabulary=()):
        asked["vocabulary"] = list(vocabulary)
        return "Hold fast, Captain Aida."

    monkeypatch.setattr(sound, "_transcribed", heard)
    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Captain Ada"\nkind = "character"\n', encoding="utf-8")
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="Hold fast, Captain Ada.", root=str(tmp_path))
    assert said["said"]["missing"] == ["ada"] and said["said"]["extra"] == ["aida"]
    assert said["failed"][-1]["measure"] == "said"
    assert asked["vocabulary"] == ["Captain Ada"]


def test_a_sitting_shows_a_takes_speech_and_marks_one_that_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", lambda path, vocabulary=(): None)
    (tmp_path / "polyweave.toml").write_text(
        "[voice]\nlead_silence = 0.25\n", encoding="utf-8")
    take(tmp_path / "late.wav")
    take(tmp_path / "prompt.wav", lead=0.1)
    laid = sound.sitting(
        [{"name": "late", "new": "late.wav", "line": "Hold fast"},
         {"name": "prompt", "new": "prompt.wav", "line": "Hold fast"}],
        out="sitting", root=str(tmp_path),
    )
    failed = {name: [f["measure"] for f in said["failed"]]
              for name, said in laid["speech"].items()}
    assert failed == {"late": ["lead_silence"], "prompt": []}
    assert (tmp_path / "sitting" / "late.png").is_file()
