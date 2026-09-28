"""Sounds heard beside the ones they replace, the verdict kept in a record (§PW256).

Starship remade twelve effects and three phase tracks, kept the old ones aside, and had
nothing but a chat message to ask a person about them in.
"""

from __future__ import annotations

import json
import wave

import numpy as np
import pytest

from polyweave import provenance, review, sfx, sound, verdict
from polyweave.errors import PolyweaveError


def _tone(path, seconds=0.2, level=0.5):
    """A plain sine as mono 16-bit WAV, standing in for a sound made by hand."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(seconds * 44100)) / 44100
    samples = (np.sin(2 * np.pi * 440 * t) * level * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(44100)
        out.writeframes(samples.tobytes())


def _project(tmp_path, config=""):
    (tmp_path / "polyweave.toml").write_text(config, encoding="utf-8")
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "board.sfx.toml").write_text(
        '[effect.bomb]\ngenerator = "explosion"\n', encoding="utf-8"
    )
    sfx.synth("audio/board.sfx.toml", root=str(tmp_path))
    _tone(tmp_path / "before" / "bomb.wav")


def test_each_sound_is_laid_out_beside_the_one_it_replaces(tmp_path):
    _project(tmp_path)
    laid = sound.sitting(
        [{"name": "bomb", "new": "audio/bomb.wav", "old": "before/bomb.wav"}],
        out="review/sounds", root=str(tmp_path),
    )
    assert laid["sounds"] == ["bomb"]
    assert set(laid["measured"]["bomb"]) == {"old", "new"}
    assert "seam_step" not in laid["measured"]["bomb"]["new"]
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert set(manifest["choices"]) == set(sound.SOUND_CHOICES)
    # Each choice says what it is and what it leads to (§PW287).
    assert all({"label", "means", "then"} <= set(one)
               for one in manifest["choices"].values())
    member = manifest["families"]["bomb"]["members"][0]
    assert member["sound"] is True and member["loop"] is False
    assert member["old"] == "before/bomb.wav"
    assert (tmp_path / "review" / "sounds" / "bomb.png").is_file()


def test_a_verdict_given_on_the_page_lands_in_the_sounds_record(tmp_path):
    _project(tmp_path)
    sitting = sound.sitting(
        [{"name": "bomb", "new": "audio/bomb.wav", "old": "before/bomb.wav"}],
        out="review/sounds", root=str(tmp_path),
    )["sitting"]
    said = review.answer(tmp_path, {"sitting": sitting, "family": "bomb",
                                    "choice": "accept", "why": "punchier, same weight"})
    heard = said["members"][0]["heard"]
    assert heard["record"] == "audio/bomb.wav.prov.json"
    record = provenance.read("audio/bomb.wav", root=str(tmp_path))
    kept = record["verdicts"][-1]
    assert (kept["choice"], kept["why"]) == ("accept", "punchier, same weight")
    assert kept["sha256"] == record["artefact"]["sha256"]
    assert kept["against"] == "before/bomb.wav"
    assert verdict.answers(root=str(tmp_path))["answers"][-1]["family"] == "bomb"
    assert provenance.verify(str(tmp_path))["changed"] == []


def test_a_declared_loop_is_played_looped_and_measured_at_its_seam(tmp_path):
    _project(tmp_path, '[sound.music]\nkind = "loop"\ncues = ["theme"]\n')
    _tone(tmp_path / "assets" / "audio" / "theme.wav", seconds=1.0)
    laid = sound.sitting([{"name": "theme", "new": "assets/audio/theme.wav"}],
                         out="review/music", root=str(tmp_path))
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert manifest["families"]["theme"]["members"][0]["loop"] is True
    assert "seam_step" in laid["measured"]["theme"]["new"]


def test_a_sound_with_no_record_keeps_the_verdict_in_the_ledger_and_says_so(tmp_path):
    _project(tmp_path)
    sitting = sound.sitting([{"name": "old", "new": "before/bomb.wav"}],
                            out="review/sounds", root=str(tmp_path))["sitting"]
    said = review.answer(tmp_path, {"sitting": sitting, "family": "old",
                                    "choice": "look", "why": "too thin"})
    assert said["members"][0]["heard"]["record"] is None
    assert "no record" in said["members"][0]["heard"]["why_unrecorded"]


def test_a_member_with_no_file_to_hear_is_refused(tmp_path):
    _project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        sound.sitting([{"name": "gone", "new": "audio/gone.wav"}],
                      out="review/sounds", root=str(tmp_path))
    assert refused.value.code == "sound.no-source"


def test_the_page_may_be_sent_the_sounds_it_plays(tmp_path):
    _project(tmp_path)
    assert review._served(tmp_path.resolve(), "audio/bomb.wav")
    assert not review._served(tmp_path.resolve(), "audio/board.sfx.toml")
