"""Sounds heard beside the ones they replace, the verdict kept in a record (§PW256).

Starship remade twelve effects and three phase tracks, kept the old ones aside, and had
nothing but a chat message to ask a person about them in.
"""

from __future__ import annotations

import json
import wave

import numpy as np
import pytest

from polyweave.kernel import git, provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sfx, sound
from polyweave.loop import review, verdict


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


def test_a_sound_sitting_says_what_changed_under_its_summary(tmp_path):
    """§PW464: Cottony's effects moved to a SoundFont and the page could not say so."""
    _project(tmp_path)
    said = "O timbre agora vem do SoundFont; os pops soam 6 dB mais cheios."
    laid = sound.sitting(
        [{"name": "bomb", "new": "audio/bomb.wav", "old": "before/bomb.wav"}],
        out="review/sounds", root=str(tmp_path), about=said,
    )
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert said in manifest["about"]
    plain = sound.sitting([{"name": "bomb", "new": "audio/bomb.wav"}],
                          out="review/plain", root=str(tmp_path))
    assert said not in json.loads((tmp_path / plain["sitting"]).read_text("utf-8"))[
        "about"]


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


def _git(tmp_path, *args):
    import subprocess

    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=tmp_path, check=True, capture_output=True)


def test_the_sound_a_render_overwrote_is_heard_from_git(tmp_path):
    """§PW425: the old take lived only in git, three commands a track to hear it."""
    _project(tmp_path)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "audio/bomb.wav")
    _git(tmp_path, "commit", "-q", "-m", "the bomb as it shipped")
    committed = (tmp_path / "audio" / "bomb.wav").read_bytes()
    _tone(tmp_path / "audio" / "bomb.wav", seconds=0.4)  # the render, in place
    laid = sound.sitting(
        [{"name": "bomb", "new": "audio/bomb.wav", "old": "HEAD:audio/bomb.wav"}],
        out="review/sounds", root=str(tmp_path),
    )
    member = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))[
        "families"]["bomb"]["members"][0]
    assert (tmp_path / member["old"]).read_bytes() == committed
    assert member["old"].startswith(".polyweave/sound/old/")
    assert member["old_from"]["rev"] == "HEAD"
    assert member["old_from"]["path"] == "audio/bomb.wav"
    assert len(member["old_from"]["commit"]) == 40


def test_a_committed_old_git_does_not_hold_is_refused(tmp_path):
    _project(tmp_path)
    _git(tmp_path, "init", "-q")
    with pytest.raises(PolyweaveError) as refused:
        sound.sitting(
            [{"name": "bomb", "new": "audio/bomb.wav", "old": "HEAD:audio/bomb.wav"}],
            out="review/sounds", root=str(tmp_path),
        )
    assert refused.value.code == "sound.no-source"
    assert "HEAD" in refused.value.message


def test_a_windows_path_is_never_read_as_a_revision():
    assert git.committed("C:/game/audio/bomb.wav") is None
    assert git.committed("before/bomb.wav") is None
    assert git.committed("HEAD~2:audio/bomb.wav") == ("HEAD~2", "audio/bomb.wav")


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
