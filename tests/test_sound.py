"""A sound held to a spec, as a picture is (§PW113).

The owner decided sound belongs in the acceptance spec. The measure is Cottony's own,
from `tools/audio/loop_music.py`: a loop fails when its seam stands out from the rest of
the track, as a step between samples or as a spectral change. The sounds here are made
in the test, so the verdicts are known before anything is measured.
"""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from polyweave import accept, sound
from polyweave.errors import PolyweaveError

RATE = 44100


def written(where: Path, samples: np.ndarray, *, width: int = 2) -> Path:
    """A mono PCM WAV of `samples` in [-1, 1], at 16 or 24 bits."""
    whole = np.round(samples * (2 ** (8 * width - 1) - 1)).astype(np.int64)
    if width == 2:
        raw = whole.astype("<i2").tobytes()
    else:
        raw = b"".join(int(v).to_bytes(3, "little", signed=True) for v in whole)
    with wave.open(str(where), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(width)
        held.setframerate(RATE)
        held.writeframes(raw)
    return where


def tone(seconds: float, hz: float = 441.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(int(round(seconds * RATE))) / RATE
    return amplitude * np.sin(2 * np.pi * hz * t)


def texture(samples: int = 2 * RATE) -> np.ndarray:
    """A loop by construction: band-limited noise from an inverse FFT, which is periodic
    over its own length, swelling eight times so it has moments that differ. A pure
    tone will not do here: every moment of it is the same, so its spectral change is
    noise over noise."""
    rng = np.random.default_rng(3)
    at = np.fft.rfftfreq(samples, 1 / RATE)
    band = (at > 80) & (at < 6000)
    spectrum = np.zeros(len(at), complex)
    spectrum[band] = np.exp(2j * np.pi * rng.random(band.sum())) / np.sqrt(at[band])
    body = np.fft.irfft(spectrum, samples)
    swell = 0.6 + 0.4 * np.cos(2 * np.pi * np.arange(samples) / (samples / 8))
    return body / np.abs(body).max() * 0.5 * swell


def seamless(tmp_path) -> Path:
    return written(tmp_path / "seamless.wav", texture())


def cut_short(tmp_path) -> Path:
    """The same loop stopped 68 ms early, mid-swell, so the wrap is a cut."""
    return written(tmp_path / "cut.wav", texture()[:-3001])


def fades_out(tmp_path) -> Path:
    """The loop faded into silence before it starts again at full level."""
    body = texture()
    body[-RATE // 2 :] *= np.linspace(1.0, 0.0, RATE // 2) ** 3
    body[-RATE // 10 :] = 0.0
    return written(tmp_path / "fade.wav", body)


def spec(tmp_path, body: str) -> accept.Spec:
    where = tmp_path / "loop.accept.toml"
    where.write_text('asset = "loop"\n' + body, encoding="utf-8")
    return accept.read(where)


SEAM = (
    '[[predicate]]\nid = "step"\nmeasure = "seam_step"\nmax = 1.0\n'
    '[[predicate]]\nid = "flux"\nmeasure = "seam_flux"\nmax = 1.0\n'
)


def test_a_seamless_loop_wraps_like_any_other_moment(tmp_path):
    found = sound.measure(seamless(tmp_path))
    assert found["seam_step"] <= 1.0
    assert found["seam_flux"] <= 1.0
    assert found["duration"] == pytest.approx(2.0)


def test_a_loop_cut_short_changes_across_the_wrap(tmp_path):
    assert sound.measure(cut_short(tmp_path))["seam_flux"] > 1.0


def crashes(samples: int = 2 * RATE) -> np.ndarray:
    """The seamless texture played like music: a kick on every beat and a crash on
    each section's downbeat, the first included, so the loop restarts on one as the
    synthwave loop in the PW184 spike did."""
    body = texture(samples)
    rng = np.random.default_rng(5)
    decay = np.exp(-np.arange(RATE // 5) / 1500.0)
    crash = rng.standard_normal(RATE // 5) * decay
    kick = np.sin(2 * np.pi * 60 * np.arange(RATE // 5) / RATE) * decay
    for start in range(0, samples, RATE // 8):  # a beat every eighth of a second
        body[start : start + len(kick)] += 0.6 * kick[: samples - start]
    for start in range(0, samples, RATE // 2):  # a section every half second
        body[start : start + len(crash)] += 0.6 * crash[: samples - start]
    return body / np.abs(body).max() * 0.8


def test_a_loop_that_restarts_on_a_crash_reads_close_to_its_other_downbeats(tmp_path):
    # §PW222: against the 90th percentile of every frame this seam read 13.8, though it
    # is the same downbeat the loop plays three more times. Against the track's own
    # strong onsets it reads 1.10: the seam falls on a frame boundary and the crashes
    # inside fall between two, which is as close as a synthetic loop with nothing else
    # strong in it gets. A rendered drum loop reads below one (test_music_render).
    found = sound.measure(written(tmp_path / "crash.wav", crashes()))
    assert found["seam_flux"] < 1.25
    assert found["seam_step"] <= 1.0


def test_a_tone_cut_mid_period_clicks(tmp_path):
    whole = written(tmp_path / "whole.wav", tone(2.0))
    cut = written(tmp_path / "cut.wav", tone(2.0)[:-25])
    assert sound.measure(whole)["seam_step"] <= 1.0 < sound.measure(cut)["seam_step"]


def test_a_loop_that_fades_to_silence_is_a_cut_rather_than_a_note(tmp_path):
    found = sound.measure(fades_out(tmp_path))
    assert found["seam_step"] > 1.0 and found["seam_flux"] > 1.0


def test_level_and_peak_are_in_decibels_of_full_scale(tmp_path):
    found = sound.measure(written(tmp_path / "tone.wav", tone(2.0)))
    # A sine at half scale: its peak is -6 dB and its RMS 3 dB below that.
    assert found["peak"] == pytest.approx(-6.02, abs=0.05)
    assert found["loudness"] == pytest.approx(-9.03, abs=0.05)


def test_a_24_bit_wav_reads_as_the_same_sound(tmp_path):
    sixteen = sound.measure(written(tmp_path / "16.wav", tone(2.0)))
    twenty_four = sound.measure(written(tmp_path / "24.wav", tone(2.0), width=3))
    assert twenty_four["peak"] == pytest.approx(sixteen["peak"], abs=0.01)


def test_a_spec_passes_a_clean_loop_and_fails_a_clicking_one(tmp_path):
    bar = spec(tmp_path, SEAM)
    assert accept.check(bar, seamless(tmp_path), root=tmp_path)["passed"] is True
    failed = accept.check(bar, cut_short(tmp_path), root=tmp_path)
    assert failed["passed"] is False
    assert "flux" in failed["failed"]
    assert failed["predicates"][0]["rung"] is None
    assert bar.needs_rung() == "sphere"  # a sound asks nothing of the ladder


def test_a_sound_bound_on_a_picture_is_refused(tmp_path):
    picture = tmp_path / "p.png"
    Image.new("RGBA", (8, 8), (200, 80, 60, 255)).save(picture)
    with pytest.raises(PolyweaveError) as refused:
        accept.check(spec(tmp_path, SEAM), picture, root=tmp_path)
    assert refused.value.code == "spec.not-sound"


def test_a_committed_loop_is_held_to_its_spec_by_verify(tmp_path):
    seamless(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "loop.accept.toml").write_text(
        'asset = "loop"\nartefact = "seamless.wav"\n' + SEAM, encoding="utf-8"
    )
    found = accept.verify(str(tmp_path), under="specs")
    assert found["passed"] is True
    assert found["counts"]["passed"] == 1


def test_a_one_shot_is_measured_without_a_seam(tmp_path):
    found = sound.measure(written(tmp_path / "short.wav", tone(0.1)))
    assert set(found) == {"loudness", "peak", "duration"}
    assert found["duration"] == pytest.approx(0.1, abs=0.001)
    assert found["peak"] == pytest.approx(-6.02, abs=0.05)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg to decode with")
def test_a_file_ffmpeg_cannot_decode_is_refused_with_a_code(tmp_path):
    # §PW224: this used to leave sound.read as subprocess.CalledProcessError.
    bogus = tmp_path / "theme.ogg"
    bogus.write_text("<html>502 Bad Gateway</html>", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound.measure(bogus)
    assert refused.value.code == "spec.unreadable-sound"
    assert "theme.ogg" in refused.value.message
    assert refused.value.detail


def test_a_file_with_no_samples_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        sound.measure(written(tmp_path / "empty.wav", np.zeros(0)))
    assert refused.value.code == "spec.unreadable-sound"


def test_a_seam_bound_on_a_one_shot_is_refused_with_the_length_it_needs(tmp_path):
    written(tmp_path / "pop.wav", tone(0.1))
    bar = spec(
        tmp_path, '[[predicate]]\nid = "flux"\nmeasure = "seam_flux"\nmax = 1.0\n'
    )
    with pytest.raises(PolyweaveError) as refused:
        accept.check(bar, tmp_path / "pop.wav", root=tmp_path)
    assert refused.value.code == "spec.no-seam"
    assert f"{sound.shortest_seam():.2f} s" in refused.value.remedy


def test_a_one_shot_is_held_to_its_level_and_length(tmp_path):
    written(tmp_path / "pop.wav", tone(0.1))
    bar = spec(
        tmp_path,
        '[[predicate]]\nid = "short"\nmeasure = "duration"\nmax = 0.3\n'
        '[[predicate]]\nid = "loud"\nmeasure = "peak"\nmax = -3.0\n',
    )
    assert accept.check(bar, tmp_path / "pop.wav", root=tmp_path)["passed"] is True


def test_the_operation_measures_a_sound_by_path(tmp_path):
    seamless(tmp_path)
    assert sound.measured("seamless.wav", root=str(tmp_path))["seam_step"] <= 1.0
