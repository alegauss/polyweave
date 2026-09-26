"""A score rendered without a DAW open (§PW187).

The engines are the PW184 spike's: Surge XT through Pedalboard, and FluidSynth with a
General MIDI SoundFont. A test that needs one finds it through the environment
(`FLUIDSYNTH`, `SOUNDFONT`, and Surge where it installs itself) and skips by name, as
the Blender and Godot tests do, so the gate reports what went unrendered.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

import pytest

from polyweave import music_render, sound
from polyweave.errors import PolyweaveError

PEDALBOARD = importlib.util.find_spec("pedalboard") is not None
FLUIDSYNTH = os.environ.get("FLUIDSYNTH") or shutil.which("fluidsynth")
SOUNDFONT = os.environ.get("SOUNDFONT", "")
SURGE = music_render.surge_binary()

needs_fluid = pytest.mark.skipif(
    not (PEDALBOARD and FLUIDSYNTH and Path(SOUNDFONT).is_file()),
    reason="audio engine absent: Pedalboard, FluidSynth (FLUIDSYNTH) or a SoundFont "
    "(SOUNDFONT)",
)
needs_surge = pytest.mark.skipif(
    not (PEDALBOARD and SURGE),
    reason="audio engine absent: Pedalboard or Surge XT",
)

GM = """\
[music]
title = "Garden"
bpm = 120
form = ["A"]

[section.A]
bars = 2

[pattern]
tune = "<[d5 f#5 a5 f#5] [e5 g5 b5 g5]>"
beat = "[bd ~ sd ~, hh*8]"

[[track]]
name = "flute"
instrument = "gm:73"
reverb = -10.0
play = { A = "tune" }

[[track]]
name = "drums"
instrument = "drums:0"
drums = true
groove = 1.0
gain = -3.0
play = { A = "beat" }
"""

SURGE_SCORE = """\
[music]
title = "Pulse"
bpm = 132
form = ["A"]

[section.A]
bars = 1

[pattern]
riff = "c4 e4 g4 c5"

[patch.pulse]
a_osc_1_shape = -100.0
a_osc_1_width_1 = 25.0
a_amp_eg_attack = 2.0
a_amp_eg_release = 40.0

[[track]]
name = "lead"
instrument = "surge:pulse"
play = { A = "riff" }
"""


class Reported:
    """A job's report, kept rather than written, so a test can read the stages."""

    def __init__(self):
        self.stages: list[str] = []

    def stage(self, stage, *, progress=None, note=None):
        self.stages.append(stage)

    def progress(self, value, *, note=None):
        pass

    def note(self, text):
        pass


def project(tmp_path, score: str, paths: str = "") -> str:
    (tmp_path / "polyweave.toml").write_text(f"[paths]\n{paths}", encoding="utf-8")
    (tmp_path / "music").mkdir()
    (tmp_path / "music" / "cue.music.toml").write_text(score, encoding="utf-8")
    return "music/cue.music.toml"


def fluid_paths(credit: str = "") -> str:
    paths = (f"fluidsynth = {str(FLUIDSYNTH)!r}\nsoundfont = {SOUNDFONT!r}\n"
             .replace("'", '"').replace("\\", "/"))
    return paths + (
        f'\n[licence."{Path(SOUNDFONT).name}"]\n'
        'terms = "GeneralUser GS License v2.0: any music use, commercial included"\n'
        f'credit = "{credit}"\n'
        'note = "the author cannot vouch for the origin of every sample"\n'
    )


def test_a_label_is_matched_to_the_nearest_number_in_its_own_unit():
    labels = ["0.0 ms", "3.9 ms", "250.0 ms", "1.00 s", "2.00 s"]
    assert music_render.nearest_label(labels, 5.0) == "3.9 ms"
    assert music_render.nearest_label(labels, 900.0) == "1.00 s"
    assert music_render.nearest_label(["Off", "LP 12 dB"], "LP 12 dB") == "LP 12 dB"
    assert music_render.nearest_label([0.0, 1.0], 0.5) == 0.5


def test_on_windows_the_binary_inside_the_bundle_is_the_one_loaded(tmp_path):
    bundle = tmp_path / "Surge XT.vst3"
    inner = bundle / "Contents" / "x86_64-win" / "Surge XT.vst3"
    inner.parent.mkdir(parents=True)
    inner.write_bytes(b"")
    assert music_render.surge_binary(str(bundle), platform="win32") == inner
    assert music_render.surge_binary(str(bundle), platform="darwin") == bundle
    assert music_render.surge_binary(str(tmp_path / "none"), platform="linux") is None


def test_a_score_with_problems_is_refused_before_any_engine_is_looked_for(tmp_path):
    source = project(tmp_path, GM.replace("bpm = 120", ""))
    with pytest.raises(PolyweaveError) as refused:
        music_render.render(Reported(), source, root=str(tmp_path))
    assert refused.value.code == "music.invalid"


@pytest.mark.skipif(not PEDALBOARD, reason="audio engine absent: Pedalboard")
def test_general_midi_without_a_soundfont_is_refused_by_name(tmp_path):
    source = project(tmp_path, GM, 'fluidsynth = "fluidsynth"\n')
    with pytest.raises(PolyweaveError) as refused:
        music_render.render(Reported(), source, root=str(tmp_path))
    assert refused.value.code == "music.no-engine"


@needs_fluid
def test_a_general_midi_score_renders_to_a_mastered_seamless_loop(tmp_path):
    source = project(tmp_path, GM, fluid_paths())
    report = Reported()
    found = music_render.render(report, source, root=str(tmp_path))
    assert report.stages == ["building", "rendering"]
    assert found["wav"] == "music/cue.wav"
    assert found["parts"] == {"flute": "gm", "drums": "drums"}
    measured = found["measured"]
    assert measured["duration"] == pytest.approx(4.0, abs=0.01)
    assert measured["peak"] <= -0.9
    assert measured["loudness"] == pytest.approx(music_render.LOUDNESS, abs=2.0)
    assert measured["seam_step"] <= 1.0
    if shutil.which("ffmpeg"):
        assert (tmp_path / "music" / "cue.ogg").is_file()
    assert sound.measure(tmp_path / found["wav"])["duration"] == measured["duration"]


@needs_fluid
def test_layers_are_files_of_one_length_that_add_up_to_the_whole(tmp_path):
    import numpy as np

    score = GM.replace('instrument = "gm:73"', 'instrument = "gm:73"\nlayer = "tense"')
    found = music_render.render(Reported(), project(tmp_path, score, fluid_paths()),
                                root=str(tmp_path))
    assert list(found["layers"]) == ["base", "tense"]
    assert found["layers"]["tense"]["wav"] == "music/cue.tense.wav"
    whole, _ = sound.read(tmp_path / found["wav"])
    parts = [sound.read(tmp_path / one["wav"])[0] for one in found["layers"].values()]
    assert {len(p) for p in parts} == {len(whole)}
    summed = sum(parts)
    likeness = np.corrcoef(summed.mean(axis=1), whole.mean(axis=1))[0, 1]
    # Each layer rides the master's gain: 0.997 measured, against 0.906 for one static
    # gain, whose layers drifted from the mix wherever the compressor moved.
    assert likeness > 0.99
    for layer in found["layers"].values():
        assert layer["measured"]["seam_step"] <= 1.0


@pytest.mark.skipif(not PEDALBOARD, reason="audio engine absent: Pedalboard")
def test_a_library_with_no_declared_licence_is_refused_before_anything_plays(tmp_path):
    import sys

    font = tmp_path / "Mystery.sf2"
    font.write_bytes(b"sfbk")
    engine = str(Path(sys.executable)).replace("\\", "/")
    paths = f'fluidsynth = "{engine}"\nsoundfont = "{font.as_posix()}"\n'
    with pytest.raises(PolyweaveError) as refused:
        music_render.render(Reported(), project(tmp_path, GM, paths),
                            root=str(tmp_path))
    assert refused.value.code == "music.licence-undeclared"
    assert 'licence."Mystery.sf2"' in refused.value.remedy
    assert not (tmp_path / "music" / "cue.wav").exists()


@needs_fluid
def test_every_file_made_carries_its_instruments_and_what_they_owe(tmp_path):
    from polyweave import provenance

    score = GM.replace('instrument = "gm:73"', 'instrument = "gm:73"\nlayer = "tense"')
    found = music_render.render(
        Reported(), project(tmp_path, score, fluid_paths("Sounds: GeneralUser GS")),
        root=str(tmp_path))
    record = provenance.read(str(tmp_path / "music" / "cue.wav.prov.json"), tmp_path)
    assert record["kind"] == "sound"
    assert [i["path"] for i in record["inputs"]][0] == "music/cue.music.toml"
    named = {i["name"]: i for i in record["instruments"]}
    assert named["FluidSynth"]["licence"] == "LGPL-2.1"
    assert named[Path(SOUNDFONT).name]["used_by"] == ["drums", "flute"]
    tense = provenance.read(
        str(tmp_path / found["layers"]["tense"]["wav"]) + ".prov.json", tmp_path)
    assert {i["name"]: i for i in tense["instruments"]}[Path(SOUNDFONT).name][
        "used_by"] == ["drums", "flute"]
    owed = provenance.credits(str(tmp_path))["owed"]
    assert owed[0]["credit"] == "Sounds: GeneralUser GS"
    assert "music/cue.wav" in owed[0]["files"]


@needs_fluid
def test_one_layer_writes_no_layer_files(tmp_path):
    found = music_render.render(Reported(), project(tmp_path, GM, fluid_paths()),
                                root=str(tmp_path))
    assert "layers" not in found


@needs_fluid
def test_a_stinger_keeps_its_tail_and_has_no_seam(tmp_path):
    score = GM.replace('form = ["A"]', 'form = ["A"]\nloop = false')
    found = music_render.render(Reported(), project(tmp_path, score, fluid_paths()),
                                root=str(tmp_path))
    assert found["loop"] is None
    assert found["measured"]["duration"] > 4.0
    assert "seam_flux" not in found["measured"]


@needs_surge
def test_a_surge_patch_renders_through_the_plugin(tmp_path):
    found = music_render.render(Reported(), project(tmp_path, SURGE_SCORE),
                                root=str(tmp_path))
    assert found["parts"] == {"lead": "surge"}
    assert found["measured"]["loudness"] == pytest.approx(music_render.LOUDNESS,
                                                          abs=2.0)


@needs_surge
def test_a_parameter_surge_does_not_have_is_refused_with_its_nearest(tmp_path):
    score = SURGE_SCORE.replace("a_amp_eg_release", "a_amp_eg_releese")
    with pytest.raises(PolyweaveError) as refused:
        music_render.render(Reported(), project(tmp_path, score), root=str(tmp_path))
    assert refused.value.code == "music.unknown-parameter"
    assert "a_amp_eg_release" in refused.value.remedy
