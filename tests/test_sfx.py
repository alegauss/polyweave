"""Retro effects from a seed (§PW189).

The ten effects here are the PW184 spike's, which a person listened to and passed: the
same generators and the same seeds (each name's CRC32) must give the same lengths the
spike measured, which is what says the port is sfxr and not a lookalike.
"""

from __future__ import annotations

import shutil
import wave

import pytest

from polyweave import sfx, sfxr
from polyweave.errors import PolyweaveError

#: The spike's ten effects, each generator's first draw and the length it came out at.
SPIKE = {
    "tile_select": ("blip", 0.10),
    "tile_swap": ("jump", 0.18),
    "match": ("pickup", 0.29),
    "combo": ("powerup", 0.51),
    "invalid_move": ("hit", 0.16),
    "booster_fire": ("laser", 0.21),
    "bomb": ("explosion", 0.20),
    "star_earned": ("pickup", 0.17),
    "level_won": ("powerup", 0.11),
    "button_click": ("blip", 0.10),
}


def effects(tmp_path, body: str, config: str = "") -> str:
    (tmp_path / "polyweave.toml").write_text(config, encoding="utf-8")
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "board.sfx.toml").write_text(body, encoding="utf-8")
    return "audio/board.sfx.toml"


def spike_body() -> str:
    return "".join(
        f'[effect.{name}]\ngenerator = "{kind}"\n\n'
        for name, (kind, _) in SPIKE.items()
    )


def test_the_spikes_ten_effects_come_out_at_the_lengths_a_person_heard(tmp_path):
    found = sfx.synth(effects(tmp_path, spike_body()), root=str(tmp_path))["effects"]
    for name, (kind, seconds) in SPIKE.items():
        assert found[name]["generator"] == kind
        assert found[name]["duration"] == pytest.approx(seconds, abs=0.005), name
        assert found[name]["tries"] == 1
        assert found[name]["peak"] == pytest.approx(sfx.PEAK, abs=0.01)
    assert found["match"]["file"] == "audio/match.wav"


def test_each_effect_carries_a_record_of_what_made_it(tmp_path):
    from polyweave import provenance

    sfx.synth(effects(tmp_path, spike_body()), effect="bomb", root=str(tmp_path))
    record = provenance.read(str(tmp_path / "audio" / "bomb.wav.prov.json"), tmp_path)
    assert record["kind"] == "sound"
    assert record["params"]["generator"] == "explosion"
    assert record["instruments"][0]["licence"] == "MIT"
    # An engine's licence is on its code, so a game owes nothing for sfxr's sounds.
    assert provenance.credits(str(tmp_path)) == {"owed": [], "notes": [], "people": []}


def test_the_same_seed_gives_the_same_bytes(tmp_path):
    source = effects(tmp_path, '[effect.pop]\ngenerator = "pickup"\nseed = 7\n')
    sfx.synth(source, root=str(tmp_path))
    first = (tmp_path / "audio" / "pop.wav").read_bytes()
    sfx.synth(source, root=str(tmp_path))
    assert (tmp_path / "audio" / "pop.wav").read_bytes() == first


def test_a_duration_bound_moves_to_the_next_seed_and_says_which_was_kept(tmp_path):
    body = '[effect.level_won]\ngenerator = "powerup"\nmin_duration = 0.4\n'
    made = sfx.synth(effects(tmp_path, body), root=str(tmp_path))
    found = made["effects"]["level_won"]
    assert found["duration"] >= 0.4
    assert found["tries"] > 1
    import zlib

    assert found["seed"] == zlib.crc32(b"level_won") + found["tries"] - 1


def test_a_pinned_parameter_wins_over_the_draw(tmp_path):
    body = ('[effect.a]\ngenerator = "pickup"\nseed = 3\n'
            '[effect.b]\ngenerator = "pickup"\nseed = 3\nenv_decay = 0.8\n')
    found = sfx.synth(effects(tmp_path, body), root=str(tmp_path))["effects"]
    assert found["b"]["duration"] > found["a"]["duration"]
    assert sfxr.drawn("pickup", 3).env_decay != 0.8


def test_an_effect_set_wholly_by_hand_needs_no_generator(tmp_path):
    body = '[effect.kick]\nwave = "sine"\nbase_freq = 0.32\nfreq_ramp = -0.55\n'
    found = sfx.synth(effects(tmp_path, body), root=str(tmp_path))["effects"]["kick"]
    assert found["generator"] is None and found["duration"] > 0


def test_an_effect_named_as_a_declared_cue_lands_at_that_cue(tmp_path):
    config = '[paths]\naudio = "game/audio"\n[sound.effects]\ncues = ["match"]\n'
    found = sfx.synth(effects(tmp_path, spike_body(), config), effect="match",
                      root=str(tmp_path))["effects"]
    assert list(found) == ["match"]
    assert found["match"]["file"] == "game/audio/match.wav"
    assert found["match"]["declared"] is True
    with wave.open(str(tmp_path / "game" / "audio" / "match.wav"), "rb") as held:
        assert (held.getnchannels(), held.getsampwidth(), held.getframerate()) == (
            1, 2, sfxr.RATE)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg to encode with")
def test_a_cue_declared_as_ogg_is_encoded(tmp_path):
    config = '[sound.effects]\nformat = "ogg"\ncues = ["bomb"]\n'
    found = sfx.synth(effects(tmp_path, spike_body(), config), effect="bomb",
                      root=str(tmp_path))["effects"]["bomb"]
    assert found["file"] == "assets/audio/bomb.ogg"
    assert (tmp_path / "assets" / "audio" / "bomb.ogg").is_file()
    assert not (tmp_path / "assets" / "audio" / "bomb.synth.wav").exists()


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ('[effect.a]\ngenerator = "coin"\n', "sound.bad-effect"),
        ('[effect.a]\ngenerator = "pickup"\nbase_frq = 0.3\n', "sound.bad-effect"),
        ('[effect.a]\ngenerator = "pickup"\nbase_freq = 2.0\n', "sound.bad-effect"),
        ('[effect.a]\ngenerator = "pickup"\nenv_decay = -0.1\n', "sound.bad-effect"),
        ('[effect.a]\nwave = "triangle"\n', "sound.bad-effect"),
        ('[effect.a]\nseed = 3\n', "sound.bad-effect"),
        ('[effect.a]\ngenerator = "hit"\nmin_duration = 3.0\n', "sound.no-draw"),
        ('[effects.a]\ngenerator = "hit"\n', "sound.no-source"),
        ('[effect.a\n', "sound.no-source"),
    ],
)
def test_an_effect_that_cannot_be_made_is_refused_with_a_code(tmp_path, body, code):
    with pytest.raises(PolyweaveError) as refused:
        sfx.synth(effects(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == code


def test_an_effect_lands_at_the_loudness_it_declares(tmp_path):
    """§PW254: at a peak alone, Starship's kill came out 13 dB louder than the old."""
    source = effects(
        tmp_path, '[effect.kill]\ngenerator = "explosion"\nloudness = -18.6\n'
    )
    made = sfx.synth(source, root=str(tmp_path))["effects"]["kill"]
    assert made["aimed"] == -18.6
    assert abs(made["loudness"] - -18.6) <= 0.5
    assert made["ceiling_bound"] is False


def test_an_effect_matches_the_sound_it_replaces(tmp_path):
    source = effects(
        tmp_path,
        '[effect.old]\ngenerator = "explosion"\nloudness = -20.0\n\n'
        '[effect.new]\ngenerator = "explosion"\nseed = 99\nmatch = "audio/old.wav"\n',
    )
    sfx.synth(source, effect="old", root=str(tmp_path))
    made = sfx.synth(source, effect="new", root=str(tmp_path))["effects"]["new"]
    assert abs(made["aimed"] - -20.0) <= 0.1
    assert abs(made["loudness"] - made["aimed"]) <= 0.5


def test_the_peak_is_a_ceiling_said_when_it_binds(tmp_path):
    source = effects(
        tmp_path, '[effect.loud]\ngenerator = "blip"\nloudness = -1.0\npeak = -6.0\n'
    )
    made = sfx.synth(source, root=str(tmp_path))["effects"]["loud"]
    assert made["ceiling_bound"] is True
    assert made["peak"] <= -6.0 + 0.01
    assert made["loudness"] < -1.0


def test_loudness_and_match_together_are_refused(tmp_path):
    source = effects(
        tmp_path,
        '[effect.both]\ngenerator = "blip"\nloudness = -10.0\nmatch = "x.wav"\n',
    )
    with pytest.raises(PolyweaveError) as refused:
        sfx.synth(source, root=str(tmp_path))
    assert refused.value.code == "sound.bad-effect"


def test_a_misspelled_key_is_answered_with_its_nearest(tmp_path):
    body = '[effect.a]\ngenerator = "pickup"\nbase_frq = 0.3\n'
    with pytest.raises(PolyweaveError) as refused:
        sfx.synth(effects(tmp_path, body), root=str(tmp_path))
    assert "base_freq" in refused.value.remedy


def test_a_missing_file_and_an_unknown_effect_are_refused(tmp_path):
    with pytest.raises(PolyweaveError) as missing:
        sfx.synth("audio/none.sfx.toml", root=str(tmp_path))
    assert missing.value.code == "sound.no-source"
    source = effects(tmp_path, spike_body())
    with pytest.raises(PolyweaveError) as unknown:
        sfx.synth(source, effect="bom", root=str(tmp_path))
    assert "'bomb'" in unknown.value.remedy


JINGLE = """\
[effect.whistle]
generator = "powerup"
seed = 3

[effect.pop]
generator = "pickup"
seed = 7

[arrangement.splash]
cues = [
  { effect = "whistle", at = 0.0 },
  { effect = "pop", at = 0.25, pitch = 2 },
  { effect = "pop", at = 0.5, pitch = 4, gain = -6 },
]
"""


def test_an_arrangement_is_mixed_as_the_game_plays_it(tmp_path):
    # §PW313: a jingle heard whole, at the times its cues are played.
    import json

    from polyweave import provenance

    made = sfx.synth(effects(tmp_path, JINGLE), root=str(tmp_path))
    splash = made["arrangements"]["splash"]
    assert splash["file"] == "audio/splash.wav"
    pop = made["effects"]["pop"]["duration"]
    # The last pop starts at 0.5 s and, a major third up, plays shorter than its own.
    assert 0.5 < splash["duration"] < 0.5 + pop + 0.01
    assert splash["peak"] <= sfx.MIX_PEAK + 0.001
    plan = json.loads((tmp_path / splash["plan"]).read_text("utf-8"))
    assert [c["at"] for c in plan["cues"]] == [0.0, 0.25, 0.5]
    assert plan["cues"][1] == {
        "effect": "pop", "file": "audio/pop.wav", "at": 0.25, "pitch": 2.0, "gain": 0.0
    }
    record = provenance.read(str(tmp_path / "audio" / "splash.wav"), root=tmp_path)
    assert record["params"]["arrangement"] == "splash"


def test_a_higher_pitch_plays_shorter():
    import numpy as np

    tone = np.ones(1200)
    assert len(sfx._pitched(tone, 12)) == 600
    assert len(sfx._pitched(tone, -12)) == 2400


@pytest.mark.parametrize(
    ("cue", "said"),
    [
        ('{ effect = "boing", at = 0.0 }', "boing"),
        ('{ effect = "pop" }', "no time"),
        ('{ effect = "pop", at = 0.0, volume = 2 }', "volume"),
    ],
)
def test_a_cue_that_cannot_be_played_is_refused(tmp_path, cue, said):
    body = JINGLE.split("[arrangement.splash]")[0] + (
        f"[arrangement.splash]\ncues = [{cue}]\n"
    )
    with pytest.raises(PolyweaveError) as refused:
        sfx.synth(effects(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == "sound.bad-effect"
    assert said in refused.value.message


def test_a_brief_on_a_mix_reads_back_its_cues(tmp_path):
    from polyweave import brief

    sfx.synth(effects(tmp_path, JINGLE), root=str(tmp_path))
    said = brief.brief("audio/splash.wav", root=str(tmp_path))["declaration"]
    assert said["arrangement"] == "splash"
    assert [c["effect"] for c in said["cues"]] == ["whistle", "pop", "pop"]
