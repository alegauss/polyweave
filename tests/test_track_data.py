"""A track's waveform peaks and beat grid, for a game's own tools (§PW611)."""

from __future__ import annotations

import json
import shutil
import wave

import numpy as np
import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import music, track_data
from test_music_render import GM, Reported, fluid_paths, needs_fluid, project

RATE = 44100


def test_peaks_hold_each_channel_s_extremes_and_loudness_per_bucket():
    left = np.concatenate([np.full(RATE // 10, 0.5), np.zeros(RATE // 10)])
    right = -left
    found = track_data.peaks(np.stack([left, right], axis=1), RATE)
    coarse = found[0]
    assert [one["per_second"] for one in found] == list(track_data.RESOLUTIONS)
    assert coarse["max"] == [[0.5, 0.0], [-0.5, 0.0]]
    assert coarse["min"] == [[0.5, 0.0], [-0.5, 0.0]]
    assert coarse["loudness"] == [pytest.approx(-6.0, abs=0.1), track_data.FLOOR]
    assert len(found[-1]["loudness"]) == 40


def test_a_score_s_grid_is_its_beats_bars_sections_and_loop_in_seconds():
    model, problems = music.compile_source(GM.replace("bars = 2", "bars = 3"), "cue")
    assert problems == []
    grid = track_data.declared_grid(model)
    assert grid["estimated"] is False
    assert grid["tempo"] == [{"at": 0.0, "bpm": 120.0}]
    assert grid["meter"] == [4, 4]
    assert grid["beats"] == [i * 0.5 for i in range(12)]
    assert grid["bars"] == [0.0, 2.0, 4.0]
    assert grid["sections"] == [{"id": "A-1", "name": "A", "start": 0.0, "end": 6.0}]


def test_a_tempo_change_moves_every_beat_after_it():
    model, _ = music.compile_source(GM, "cue")
    model["timing"]["tempo"].append({"tick": 4 * model["timing"]["ticksPerQuarter"],
                                     "microsecondsPerQuarter": 250_000})
    grid = track_data.declared_grid(model)
    assert grid["tempo"] == [{"at": 0.0, "bpm": 120.0}, {"at": 2.0, "bpm": 240.0}]
    assert grid["beats"][3:6] == [1.5, 2.0, 2.25]


def clicks(bpm: float, first: float, seconds: float) -> np.ndarray:
    """A click on every beat, as a drum loop's kick would be."""
    out = np.zeros(int(seconds * RATE))
    for at in np.arange(first, seconds, 60.0 / bpm):
        start = int(at * RATE)
        burst = np.random.default_rng(int(at * 1000)).normal(0, 0.6, 400)
        out[start: start + 400] += burst[: len(out) - start]
    return np.stack([out, out], axis=1).clip(-1, 1)


def test_a_track_polyweave_did_not_render_has_its_beats_heard_and_marked_estimated():
    grid = track_data.estimated_grid(clicks(128.0, 0.25, 8.0))
    assert grid["estimated"] is True
    assert grid["tempo"][0]["bpm"] == pytest.approx(128.0, abs=0.5)
    assert grid["beats"][0] == pytest.approx(0.25, abs=0.02)
    assert grid["bars"] == grid["beats"][::4]
    assert grid["sections"] == [] and grid["loop"] is None


def write_wav(path, frames: np.ndarray) -> None:
    pcm = np.round(frames * 32767).astype("<i2")
    with wave.open(str(path), "wb") as held:
        held.setnchannels(2)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes(pcm.tobytes())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg absent")
def test_music_track_writes_the_file_beside_the_track_and_it_goes_stale_with_it(
        tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "music").mkdir()
    write_wav(tmp_path / "music" / "boss.wav", clicks(120.0, 0.0, 6.0))
    said = track_data.track("music/boss.wav", root=str(tmp_path))
    assert said["track"] == "music/boss.track.json"
    assert said["estimated"] is True
    body = json.loads((tmp_path / "music" / "boss.track.json").read_text("utf-8"))
    assert body["audio"] == "music/boss.wav"
    assert body["seconds"] == pytest.approx(6.0, abs=0.01)
    assert body["channels"] == 2 and len(body["peaks"]) == 3
    record = provenance.read("music/boss.track.json", root=tmp_path)
    assert record["inputs"][0] == {**record["inputs"][0], "role": "audio",
                                   "path": "music/boss.wav"}
    assert provenance.outdated(root=str(tmp_path))["sound"] is True
    write_wav(tmp_path / "music" / "boss.wav", clicks(100.0, 0.0, 6.0))
    stale = provenance.outdated(root=str(tmp_path))["outdated"]
    assert [one["artefact"] for one in stale] == ["music/boss.track.json"]


def test_a_track_that_is_not_there_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        track_data.track("music/none.ogg", root=str(tmp_path))
    assert refused.value.code == "spec.unreadable-sound"


@needs_fluid
def test_a_rendered_track_leaves_its_peaks_and_declared_grid_beside_it(tmp_path):
    from polyweave.layers.sound import music_render

    found = music_render.render(Reported(), project(tmp_path, GM, fluid_paths()),
                                root=str(tmp_path), formats=["wav"])
    assert found["track"] == "music/cue.track.json"
    body = json.loads((tmp_path / found["track"]).read_text("utf-8"))
    assert body["audio"] == "music/cue.wav"
    assert body["grid"]["estimated"] is False
    assert body["grid"]["bars"] == [0.0, 2.0]
    assert body["grid"]["loop"] == {"start": 0.0, "end": 4.0}
    assert len(body["peaks"][0]["loudness"]) == 40
    roles = [one["role"] for one in provenance.read(found["track"], tmp_path)["inputs"]]
    assert roles == ["audio", "score"]
