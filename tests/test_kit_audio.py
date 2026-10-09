"""The audio kit the plugin carries, proved in its own fixture (§PW351).

Its proof is a script, since what a bus mixes is only heard while the game runs; each
bus it hears is written beside the game and held to its loudness by sound.measure, the
measure a track is held to. It runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil
import wave

import numpy as np
import pytest

from polyweave import kits


def test_the_audio_kit_declares_its_layout_and_contributes_the_audio_tab():
    found = kits.every()["audio"]
    assert found["requires"] == ["menus"]
    assert found["tab"] == "audio"
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}
    assert found["declares"]["buses"] == ["Master", "Music", "SFX", "UI", "Voice"]


def test_the_audio_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("audio")["kits"]
    assert said["status"] == "skipped"


def _tone(path, db, seconds=0.5, rate=44100):
    t = np.arange(int(seconds * rate)) / rate
    samples = np.sin(2 * np.pi * 441 * t) * 10 ** (db / 20) * np.sqrt(2)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((samples * 32767).astype("<i2").tobytes())


def test_a_sound_a_proof_heard_is_held_to_its_bounds_by_sound_measure(tmp_path):
    _tone(tmp_path / "heard" / "Music.wav", -18.0)
    _tone(tmp_path / "heard" / "SFX.wav", -24.0)
    printed = (
        "KIT SOUND heard/Music.wav loudness -19.00 -17.00\n"
        "KIT SOUND heard/SFX.wav loudness -17.00 -15.00\n"
        "KIT SOUND heard/Voice.wav loudness -17.00 -15.00\n"
        "KIT PROVED\n"
    )
    music, sfx, voice = kits._sounds(printed, tmp_path)
    assert music["held"]
    assert music["value"] == pytest.approx(-18.0, abs=0.05)
    assert not sfx["held"]
    assert sfx["said"].startswith("heard/SFX.wav loudness -2")
    assert "outside [-17.0, -15.0]" in sfx["said"]
    assert not voice["held"]
    assert voice["value"] is None
    assert "no sound" in voice["said"]


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "audio" / "fixture", game)
    said = kits.install("audio", root=str(game))
    return game, said


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_audio_kit_lands_after_menus_and_holds_every_bus_to_its_loudness(tmp_path):
    game, said = _installed(tmp_path)
    assert said["order"] == ["prompts", "menus", "audio"]
    assert said["proved"]["passed"] is True, said["proved"]
    [audio] = [s for s in said["proved"]["scripts"] if s["kit"] == "audio"]
    heard = {s["path"].rsplit("/", 1)[-1]: s for s in audio["sounds"]}
    assert sorted(heard) == ["Ambience.wav", "Music.wav", "SFX.wav", "UI.wav",
                             "Voice.wav"]
    assert all(s["held"] for s in heard.values())
    assert heard["SFX.wav"]["value"] == pytest.approx(-16.0, abs=0.5)


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("addons/polyweave/audio/audio.gd",
     "_db(sin(share * PI / 2.0)) + _duck\n"
     "\toutgoing.volume_db = _db(cos(share * PI / 2.0))",
     "_db(share) + _duck\n\toutgoing.volume_db = _db(1.0 - share)",
     "the crossfade fell"),
    ("addons/polyweave/audio/audio.gd",
     "_duck = move_toward(_duck, target, rate * delta)", "_duck = 0.0",
     "the music under voice moved"),
    ("addons/polyweave/audio/audio.gd", "1.0 + randf_range(-vary, vary)", "1.0",
     "all played at one pitch"),
    ("addons/polyweave/audio/audio.gd", "AudioServer.set_bus_send(at, send)",
     'AudioServer.set_bus_send(at, "Master")', "Ambience sends to Master, not to SFX"),
    ("addons/polyweave/audio/audio.gd", 'play(ui_sounds["focus"], "UI", 0.0)', "pass",
     "played no focus sound"),
    ("polyweave_audio.gd", '{"name": "SFX", "send": "Master", "loudness": -16.0}',
     '{"name": "SFX", "send": "Master", "loudness": -16.0, "volume_db": -6.0}',
     ".polyweave/kits/audio/SFX.wav loudness -2"),
])
def test_a_broken_audio_runtime_fails_the_proof_by_name(tmp_path, where, before, after,
                                                      said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["audio"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
