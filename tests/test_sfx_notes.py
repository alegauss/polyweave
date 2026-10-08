"""An effect declared at a note, and its pitch measured back (§PW333).

The worker on Starship worked out from the source that sfxr's pitch is 3528 x
(base_freq^2 + 0.001) Hz. These tests synthesise effects declared by note and measure
what came out, so the formula is checked by ear rather than by reading.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave import sfx, sfxr, sound
from polyweave.errors import PolyweaveError

#: A held square tone: no envelope attack, a long sustain, so the pitch is clear.
HELD = {"wave": "square", "env_attack": 0.0, "env_sustain": 0.6, "env_decay": 0.1}


def pitch(audio: np.ndarray, start: float, end: float) -> float:
    rate = sfxr.RATE
    return sound._fundamental(audio[int(start * rate) : int(end * rate)], rate)


@pytest.mark.parametrize(
    "note, expected", [("A5", 880.0), ("E5", 659.26), (440, 440.0)]
)
def test_an_effect_sounds_at_the_note_it_declares(note, expected):
    audio, _, _ = sfx._made("tone", {**HELD, "note": note})
    assert pitch(audio, 0.05, 0.25) == pytest.approx(expected, rel=0.02)


def test_an_arp_jumps_to_its_note_at_its_time():
    table = {**HELD, "note": "A5", "arp": {"to": "E6", "at": 0.1}}
    audio, _, _ = sfx._made("arp", table)
    assert pitch(audio, 0.01, 0.09) == pytest.approx(880.0, rel=0.02)
    assert pitch(audio, 0.15, 0.3) == pytest.approx(1318.5, rel=0.02)


def test_a_slide_reaches_its_note_after_its_time():
    table = {**HELD, "note": "A5", "slide": {"to": "A4", "over": 0.3}}
    audio, _, _ = sfx._made("slide", table)
    assert pitch(audio, 0.28, 0.32) == pytest.approx(440.0, rel=0.05)


def test_measure_names_the_note_an_effect_landed_on(tmp_path):
    from test_sound import written

    audio, _, _ = sfx._made("tone", {**HELD, "note": "A5"})
    found = sound.measure(written(tmp_path / "a5.wav", audio))
    assert found["note"].startswith("A5")


@pytest.mark.parametrize("table", [
    {**HELD, "note": "H5"},
    {**HELD, "note": "A5", "base_freq": 0.4},
    {**HELD, "arp": {"to": "E6", "at": 0.1}},
    {**HELD, "note": "A5", "arp": {"to": "A9", "at": 0.1}},
    {**HELD, "note": 20000},
])
def test_a_note_that_cannot_be_played_is_refused(table):
    with pytest.raises(PolyweaveError) as refused:
        sfx._checked("bad", table)
        sfx._made("bad", table)
    assert refused.value.code == "sound.bad-effect"
