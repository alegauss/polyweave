"""A recorded track split into stems, each saying where it plays (§PW558).

The separator is Demucs, which is heavy and optional; these stand a fake in its place
that knows the mix's parts, so what is held is everything around the model: the split,
the files, their records and the spans. The real model runs only when it is installed.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import wave

import numpy as np
import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sound_stems

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None,
                                  reason="ffmpeg absent: it decodes and encodes")
needs_demucs = pytest.mark.skipif(importlib.util.find_spec("demucs") is None,
                                  reason="demucs absent: the stems extra")

RATE = sound_stems.RATE
SECONDS = 6.0


def stereo(signal: np.ndarray) -> np.ndarray:
    return np.stack([signal, signal], axis=1) * 32767.0


def parts(voice_level: float = 0.3) -> dict[str, np.ndarray]:
    """A tone throughout, and a 'voice' from 2 s to 4 s, int16-scaled stereo.

    The voice's residue, a hundredth of its level, runs the whole track, as
    separation's leakage does.
    """
    t = np.arange(int(SECONDS * RATE)) / RATE
    music = 0.2 * np.sin(2 * np.pi * 220.0 * t)
    sung = (t >= 2.0) & (t < 4.0)
    voice = voice_level * np.sin(2 * np.pi * 700.0 * t) * np.where(sung, 1.0, 0.01)
    silent = np.zeros_like(t)
    return {"drums": stereo(silent), "bass": stereo(silent),
            "other": stereo(music), "vocals": stereo(voice)}


def project(tmp_path) -> str:
    mix = sum(parts().values()).mean(axis=1)
    with wave.open(str(tmp_path / "track.wav"), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes(np.clip(mix, -32768, 32767).astype("<i2").tobytes())
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    return "track.wav"


ENGINE = {"name": "demucs", "version": "test", "model": sound_stems.MODEL}


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(sound_stems, "_separate", lambda frames: (parts(), ENGINE))


def near(seconds: float):
    return pytest.approx(seconds, abs=0.1)


@needs_ffmpeg
def test_the_voice_comes_out_and_says_where_it_was(tmp_path, fake):
    # The residue runs the whole track and is not read as the voice.
    found = sound_stems.stems(project(tmp_path), root=str(tmp_path))
    assert list(found["stems"]) == ["vocals", "no_vocals"]
    assert found["stems"]["vocals"]["plays"] == [[near(2.0), near(4.0)]]
    assert found["stems"]["no_vocals"]["plays"] == [[0.0, near(SECONDS)]]
    assert found["gain_db"] == 0.0
    written = tmp_path / "track.stems" / "no_vocals.wav"
    assert written.is_file()
    record = json.loads((tmp_path / "track.stems" / "no_vocals.wav.prov.json")
                        .read_text(encoding="utf-8"))
    assert record["engine"]["name"] == "sound.stems"
    assert record["engine"]["model"] == sound_stems.MODEL


@needs_ffmpeg
def test_four_stems_name_the_silent_ones(tmp_path, fake):
    found = sound_stems.stems(project(tmp_path), out="split", split="four",
                              format="ogg", root=str(tmp_path))
    assert list(found["stems"]) == ["drums", "bass", "other", "vocals"]
    assert (tmp_path / "split" / "other.ogg").is_file()
    assert found["stems"]["drums"]["plays"] == []
    assert "drums, bass silent" in found["says"]


@needs_ffmpeg
def test_a_stem_over_full_scale_lowers_every_stem_alike(tmp_path, monkeypatch):
    monkeypatch.setattr(sound_stems, "_separate",
                        lambda frames: (parts(voice_level=2.0), ENGINE))
    found = sound_stems.stems(project(tmp_path), split="four", root=str(tmp_path))
    assert found["gain_db"] == pytest.approx(-6.02, abs=0.05)
    assert found["stems"]["vocals"]["peak"] <= 0.0
    # other is lowered by the same gain, so the stems still add up to the mix
    assert found["stems"]["other"]["peak"] == pytest.approx(-14 - 6.02, abs=0.2)


def test_a_track_that_is_not_there_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_stems.stems("gone.wav", root=str(tmp_path))
    assert refused.value.code == "spec.unreadable-sound"


@pytest.mark.skipif(importlib.util.find_spec("demucs") is not None,
                    reason="demucs is installed, so nothing is missing to refuse")
def test_without_demucs_the_split_is_refused_with_its_extra():
    with pytest.raises(PolyweaveError) as refused:
        sound_stems._separate(np.zeros((RATE, 2)))
    assert refused.value.code == "sound.no-separator"
    assert "polyweave[stems]" in refused.value.remedy


@needs_ffmpeg
@needs_demucs
def test_the_real_model_hears_a_tone_as_no_voice(tmp_path):
    t = np.arange(int(4 * RATE)) / RATE
    pulse = 1 + np.sign(np.sin(2 * np.pi * 2 * t))
    tone = 0.3 * np.sin(2 * np.pi * 110.0 * t) * pulse
    with wave.open(str(tmp_path / "bass.wav"), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes((tone * 16000).astype("<i2").tobytes())
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    found = sound_stems.stems("bass.wav", root=str(tmp_path))
    assert found["separator"]["name"] == "demucs"
    assert (found["stems"]["no_vocals"]["loudness"]
            > found["stems"]["vocals"]["loudness"] + 10)
