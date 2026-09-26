"""What a game needs to hear, declared by the game (§PW185).

Cottony keeps its audio list in its own scripts, so nothing could say which file was
missing. A `[sound.<family>]` table names the cues, and `sound.declared` answers where
each lands, whether it is there, and what it measures. The layout here is Cottony's:
music and effects side by side in one folder.
"""

from __future__ import annotations

import pytest

from polyweave import config, sound
from polyweave.errors import PolyweaveError
from test_sound import RATE, texture, tone, written

COTTONY = """
[paths]
audio = "docs/design/audio"

[sound.music]
kind = "loop"
format = "ogg"
duration = 90.0
loudness = -18.0
cues = ["music_calm"]

[sound.effects]
cues = ["pop_candy", "swap", "reject"]
"""


def project(tmp_path, text: str):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


def audio(tmp_path):
    folder = tmp_path / "docs" / "design" / "audio"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def test_a_project_that_declares_no_audio_needs_none(tmp_path):
    assert sound.declared(root=str(project(tmp_path, ""))) == {
        "families": {},
        "missing": [],
    }


def test_every_cue_is_placed_and_the_absent_ones_are_named(tmp_path):
    root = project(tmp_path, COTTONY)
    folder = audio(tmp_path)
    written(folder / "music_calm.wav", texture())
    written(folder / "swap.wav", tone(1.0))
    found = sound.declared(root=str(root))
    assert set(found["families"]) == {"music", "effects"}
    assert found["missing"] == [
        "docs/design/audio/music_calm.ogg",  # declared ogg, and a wav is not it
        "docs/design/audio/pop_candy.wav",
        "docs/design/audio/reject.wav",
    ]
    effects = found["families"]["effects"]
    assert effects["kind"] == "effect" and effects["folder"] == "docs/design/audio"
    swap = effects["cues"][1]
    assert swap["exists"] is True
    assert swap["measured"]["duration"] == pytest.approx(1.0)


def test_a_loop_carries_its_seam_and_an_effect_does_not(tmp_path):
    root = project(
        tmp_path,
        COTTONY.replace('format = "ogg"', 'format = "wav"'),
    )
    folder = audio(tmp_path)
    written(folder / "music_calm.wav", texture())
    written(folder / "swap.wav", tone(1.0))
    families = sound.declared(root=str(root))["families"]
    assert "seam_flux" in families["music"]["cues"][0]["measured"]
    assert families["music"]["loudness"] == -18.0
    assert "seam_flux" not in families["effects"]["cues"][1]["measured"]


def test_a_file_that_cannot_be_measured_says_why_rather_than_failing_the_read(tmp_path):
    root = project(tmp_path, COTTONY)
    written(audio(tmp_path) / "pop_candy.wav", tone(0.1))
    found = sound.declared(family="effects", root=str(root))
    cue = found["families"]["effects"]["cues"][0]
    assert cue["exists"] is True
    assert cue["unmeasured"]["code"] == "spec.unreadable-sound"


def test_a_bare_table_is_one_family_under_the_default_folder(tmp_path):
    root = project(tmp_path, '[sound]\ncues = ["click"]\n')
    found = sound.declared(root=str(root))
    assert found["missing"] == ["assets/audio/click.wav"]
    assert list(found["families"]) == [config.DEFAULT_FAMILY]


def test_a_family_may_keep_its_own_folder(tmp_path):
    root = project(tmp_path, '[sound.ui]\nfolder = "ui"\ncues = ["click"]\n')
    assert sound.declared(root=str(root))["missing"] == ["assets/audio/ui/click.wav"]


def test_a_family_is_named_among_several_and_a_misspelling_is_answered(tmp_path):
    settings = config.load(project(tmp_path, COTTONY))
    with pytest.raises(PolyweaveError) as unnamed:
        settings.sound()
    assert unnamed.value.code == "sound.family-unnamed"
    with pytest.raises(PolyweaveError) as unknown:
        sound.declared(family="efects", root=str(tmp_path))
    assert unknown.value.code == "sound.unknown-family"
    assert "effects" in unknown.value.remedy


def test_two_cues_landing_on_one_file_are_refused(tmp_path):
    root = project(tmp_path, '[sound.a]\ncues = ["pop"]\n[sound.b]\ncues = ["pop"]\n')
    with pytest.raises(PolyweaveError) as refused:
        sound.declared(root=str(root))
    assert refused.value.code == "sound.cue-twice"


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ('[sound]\ncues = ["sfx/pop"]\n', "config.bad-type"),
        ('[sound]\nkind = "music"\n', "config.bad-type"),
        ('[sound]\nformat = "aiff"\n', "config.bad-type"),
        ('[sound]\nvolume = 1\n', "config.unknown-key"),
        ('[sound.ui]\nfolder = "../../../out"\ncues = ["a"]\n', "config.path-outside"),
    ],
)
def test_a_declaration_that_is_not_one_file_per_cue_is_refused(tmp_path, text, code):
    with pytest.raises(PolyweaveError) as refused:
        sound.declared(root=str(project(tmp_path, text)))
    assert refused.value.code == code


def test_rate_is_the_one_the_measures_read(tmp_path):
    # The helpers are shared with test_sound; a drift in either would show here first.
    assert RATE == sound.RATE
