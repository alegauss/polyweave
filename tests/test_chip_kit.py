"""Chip percussion from an effects kit (§PW223).

The chiptune loop a person passed in the PW184 spike played its drums on four sfxr hits
set by hand. A score names such a kit as `chip:<kit>`, and a pattern written for a
General MIDI kit plays on it unchanged. The kit here is the spike's own four hits.
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from polyweave import music, music_render, sfx
from polyweave.errors import PolyweaveError

PEDALBOARD = importlib.util.find_spec("pedalboard") is not None

#: The spike's hand-set kit: a kick from a sine sliding down, a snare and two hats from
#: noise with a short decay and a high-pass.
KIT = """\
[effect.bd]
wave = "sine"
base_freq = 0.32
freq_ramp = -0.55
env_sustain = 0.06
env_decay = 0.22
env_punch = 0.5

[effect.sd]
wave = "noise"
base_freq = 0.55
freq_ramp = -0.1
env_sustain = 0.03
env_decay = 0.24
env_punch = 0.3
hpf_freq = 0.12

[effect.hh]
wave = "noise"
base_freq = 0.95
env_sustain = 0.0
env_decay = 0.09
hpf_freq = 0.55

[effect.oh]
wave = "noise"
base_freq = 0.95
env_sustain = 0.05
env_decay = 0.28
hpf_freq = 0.5
"""

SCORE = """\
[music]
title = "Sugar Rush"
bpm = 132
form = ["A"]

[section.A]
bars = 2

[kit.chip]
effects = "audio/chip.sfx.toml"

[pattern]
beat = "[bd ~ ~ ~ sd ~ ~ ~ bd ~ bd ~ sd ~ ~ ~, hh hh hh hh hh hh hh oh]"

[[track]]
name = "drums"
instrument = "chip:chip"
drums = true
groove = 1.0
play = { A = "beat" }
"""


def project(tmp_path, score: str = SCORE, kit: str = KIT) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "chip.sfx.toml").write_text(kit, encoding="utf-8")
    (tmp_path / "music").mkdir(exist_ok=True)
    (tmp_path / "music" / "cue.music.toml").write_text(score, encoding="utf-8")
    return "music/cue.music.toml"


def test_a_chip_kit_scores_like_a_drum_kit(tmp_path):
    found = music.validate(project(tmp_path), root=str(tmp_path))
    assert found["valid"] is True
    assert found["notes"]["drums"] == 2 * (5 + 8)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (('"chip:chip"', '"chip:nes"'), "music.unknown-instrument"),
        (("drums = true\n", ""), "music.unknown-instrument"),
        (('"audio/chip.sfx.toml"', '"chip.wav"'), "music.bad-value"),
    ],
)
def test_a_kit_the_score_cannot_use_is_named_when_it_compiles(change, code):
    _, problems = music.compile_source(SCORE.replace(*change))
    assert code in [p["code"] for p in problems]


def test_a_kit_that_lacks_a_hit_the_track_plays_is_named(tmp_path):
    thin = KIT.split("[effect.oh]")[0]
    found = music.validate(project(tmp_path, kit=thin), root=str(tmp_path))
    assert found["valid"] is False
    assert found["problems"][0]["code"] == "music.bad-kit"
    assert "[effect.oh]" in found["problems"][0]["remedy"]


def test_a_kit_file_that_is_not_there_is_named(tmp_path):
    source = project(tmp_path, SCORE.replace("audio/chip", "audio/none"))
    found = music.validate(source, root=str(tmp_path))
    assert found["problems"][0]["code"] == "music.bad-kit"


def test_every_hit_lands_on_its_tick_and_velocity_scales_it(tmp_path):
    project(tmp_path)
    hits = sfx.kit(tmp_path / "audio" / "chip.sfx.toml")
    per_tick = 0.5 / music.TICKS  # 120 BPM
    notes = [
        {"pitch": 36, "start": 0, "duration": 100, "velocity": 127, "part": "d"},
        {"pitch": 36, "start": 480, "duration": 100, "velocity": 64, "part": "d"},
    ]
    stem = music_render.chip_stem(notes, hits, per_tick, 1.2)[:, 0]
    kick = hits["bd"]
    assert np.allclose(stem[: len(kick)], kick, atol=1e-9)
    second = int(round(0.5 * music_render.RATE))
    assert np.allclose(stem[second : second + 100], kick[:100] * 64 / 127, atol=1e-9)


@pytest.mark.skipif(not PEDALBOARD, reason="audio engine absent: Pedalboard")
def test_a_chip_score_renders_with_no_soundfont_and_records_sfxr(tmp_path):
    from polyweave import provenance

    class Reported:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    found = music_render.render(Reported(), project(tmp_path), root=str(tmp_path))
    assert found["parts"] == {"drums": "chip"}
    assert found["measured"]["loudness"] == pytest.approx(music_render.LOUDNESS, abs=2)
    named = [i["name"] for i in found["instruments"]]
    assert "sfxr (DrPetter), ported" in named
    assert provenance.read(str(tmp_path / "music" / "cue.wav.prov.json"), tmp_path)


def test_a_render_is_refused_before_anything_plays_when_the_kit_lacks_a_hit(tmp_path):
    thin = KIT.split("[effect.oh]")[0]
    with pytest.raises(PolyweaveError) as refused:
        music_render.render(None, project(tmp_path, kit=thin), root=str(tmp_path))
    assert refused.value.code == "music.invalid"
