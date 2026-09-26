"""Music as a source an agent writes and polyweave checks (§PW186).

The scores here are small cuts of the PW184 spike's chiptune, which a person judged good
enough to ship: the format is the one that made it, and the validator is what an agent
repairs a score against. Every problem comes back at once, on its own line.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from polyweave import music
from polyweave.errors import PolyweaveError

SCORE = """\
[music]
title = "Sugar Rush"
bpm = 120
key = "C major"
form = ["A", "B"]

[section.A]
bars = 2

[section.B]
bars = 1

[pattern]
lead_a = "<[g4 c5 e5 g5@2 e5 g5@2] [f5 e5 d5@2 b4@2 g4@2]>"
lead_b = "c5 _ _ ~"
bass = "<[c2 c3]*4 [g2 g3]*4>"
beat = "[bd ~ sd ~, hh*8]"

[patch.chip_lead]
a_osc_1_shape = -100.0
a_osc_1_width_1 = 25.0

[[track]]
name = "lead"
instrument = "surge:chip_lead"
play = { A = "lead_a", B = "lead_b" }

[[track]]
name = "bass"
instrument = "gm:38"
play = { A = "bass", B = "bass" }

[[track]]
name = "drums"
instrument = "drums:25"
drums = true
groove = 1.0
play = { A = "beat", B = "beat" }
"""


def compiled(text: str = SCORE):
    model, problems = music.compile_source(text)
    assert problems == []
    return model


def lines_of(problems: list[dict]) -> dict[str, int | None]:
    return {p["code"]: p["line"] for p in problems}


def test_a_score_compiles_to_a_piano_shaped_model():
    model = compiled()
    assert model["formatVersion"] == 1
    assert model["timing"]["ticksPerQuarter"] == 480
    assert model["timing"]["tempo"] == [{"tick": 0, "microsecondsPerQuarter": 500_000}]
    assert [p["id"] for p in model["parts"]] == ["lead", "bass", "drums"]
    assert [(s["label"], s["startTick"], s["endTick"]) for s in model["sections"]] == [
        ("A", 0, 3840),
        ("B", 3840, 5760),
    ]
    first = model["notes"][0]
    assert set(first) == {"pitch", "start", "duration", "velocity", "part"}
    ext = model["extensions"][music.EXTENSION]
    assert ext["loop"] == {"startTick": 0, "endTick": 5760}
    assert ext["tracks"]["drums"] == {
        "instrument": "drums:25", "layer": "base", "drums": True,
        "gain": 0.0, "pan": 0.0, "reverb": None, "delay": None,
    }
    assert ext["patches"]["chip_lead"]["a_osc_1_width_1"] == 25.0


def test_the_lead_plays_one_bar_per_alternative_with_its_weights():
    lead = [n for n in compiled()["notes"] if n["part"] == "lead"]
    # Bar one: g4 c5 e5 g5@2 e5 g5@2 in eighths, so g5 lasts a quarter, less the gate.
    assert [(n["start"], n["pitch"]) for n in lead[:4]] == [
        (0, 67), (240, 72), (480, 76), (720, 79),
    ]
    assert lead[3]["duration"] == int(round(480 * 0.9))
    # Bar two starts on f5, and section B's c5 _ _ ~ holds three beats.
    assert (lead[6]["start"], lead[6]["pitch"]) == (1920, 77)
    assert (lead[-1]["start"], lead[-1]["pitch"]) == (3840, 72)
    assert lead[-1]["duration"] == int(round(3 * 480 * 0.9))


def test_the_same_source_always_compiles_to_the_same_notes():
    text = SCORE.replace("groove = 1.0", "groove = 1.0\nwobble = 6.0")
    assert compiled(text) == compiled(text)


def test_the_groove_accents_the_grid():
    notes = compiled()["notes"]
    drums = [n for n in notes if n["part"] == "drums" and n["pitch"] == 42]
    downbeat, off_eighth = drums[0], drums[1]
    assert downbeat["velocity"] > off_eighth["velocity"]


def test_a_bar_in_three_is_three_quarters_long():
    text = SCORE.replace('form = ["A", "B"]', 'form = ["A", "B"]\nmeter = [3, 4]')
    assert compiled(text)["sections"][0]["endTick"] == 2 * 3 * 480


def test_loop_from_skips_an_intro_and_a_stinger_does_not_loop():
    text = SCORE.replace('key = "C major"', 'key = "C major"\nloop_from = "B"')
    assert compiled(text)["extensions"][music.EXTENSION]["loop"]["startTick"] == 3840
    once = SCORE.replace('key = "C major"', 'key = "C major"\nloop = false')
    assert compiled(once)["extensions"][music.EXTENSION]["loop"] is None


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("c4 d4", [(0, 2, 60), (2, 2, 62)]),
        ("c4@3 d4", [(0, 3, 60), (3, 1, 62)]),
        ("c4 _ _ d4", [(0, 3, 60), (3, 1, 62)]),
        ("[c4, e4]", [(0, 4, 60), (0, 4, 64)]),
        ("c4*2", [(0, 2, 60), (2, 2, 60)]),
        ("c4!2 ~", [(0, Fraction(4, 3), 60), (Fraction(4, 3), Fraction(4, 3), 60)]),
        ("f#4 eb4", [(0, 2, 66), (2, 2, 63)]),
    ],
)
def test_the_notation_reads_as_strudel_does(pattern, expected):
    assert music.bars(pattern, 1, Fraction(4))[0] == expected


def test_alternation_nests_and_picks_one_per_bar():
    played = music.bars("<a4 <b4 c5>>", 4, Fraction(4))
    assert [bar[0][2] for bar in played] == [69, 71, 69, 72]


def test_every_problem_comes_back_at_once_on_its_own_line():
    broken = (
        SCORE.replace('key = "C major"', 'key = "C major"\ntempo = 90')
        .replace('form = ["A", "B"]', 'form = ["A", "C"]')
        .replace('lead_b = "c5 _ _ ~"', 'lead_b = "c5 [d5 e5"')
        .replace('A = "bass", B = "bass"', 'A = "bas", B = "bass"')
    )
    model, problems = music.compile_source(broken)
    assert model is None
    found = lines_of(problems)
    text = broken.splitlines()
    assert "tempo" in text[found["music.unknown-key"] - 1]
    assert "form" in text[found["music.unknown-section"] - 1]
    assert "lead_b" in text[found["music.bad-pattern"] - 1]
    assert all(p["remedy"] for p in problems)


def test_a_misspelled_pattern_is_answered_with_the_nearest_name():
    text = SCORE.replace('A = "bass", B = "bass"', 'A = "bas", B = "bass"')
    _, problems = music.compile_source(text)
    assert problems[0]["code"] == "music.unknown-pattern"
    assert "'bass'" in problems[0]["remedy"]


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (('instrument = "gm:38"\n', ""), "music.missing"),
        (("bpm = 120", 'bpm = "fast"'), "music.bad-value"),
        (("bpm = 120", "bpm = 900"), "music.bad-value"),
        (('name = "bass"', 'name = "lead"'), "music.bad-value"),
        (("[section.B]\nbars = 1", "[section.B]\nbars = 0"), "music.bad-value"),
        (('bass = "<[c2 c3]*4 [g2 g3]*4>"', 'bass = "bd sd"'), "music.bad-pattern"),
        (('lead_b = "c5 _ _ ~"', 'lead_b = "c"'), "music.bad-pattern"),
        (('lead_b = "c5 _ _ ~"', 'lead_b = "c11"'), "music.bad-pattern"),
        (('lead_b = "c5 _ _ ~"', 'lead_b = "[c5, c5]"'), "music.overlap"),
        (("[pattern]", "[patterns]"), "music.unknown-key"),
        (("bpm = 120\n", "bpm = 120\nbpm = 90\n"), "music.unreadable"),
        (('instrument = "gm:38"', 'instrument = "piano"'), "music.unknown-instrument"),
        (('instrument = "gm:38"', 'instrument = "gm:300"'), "music.unknown-instrument"),
        (('"gm:38"', '"drums:0"'), "music.unknown-instrument"),
        (("surge:chip_lead", "surge:chip_led"), "music.unknown-instrument"),
        (('"gm:38"', '"gm:38"\npan = 2.0'), "music.bad-value"),
    ],
)
def test_a_score_that_cannot_play_is_refused_with_a_code(change, code):
    _, problems = music.compile_source(SCORE.replace(*change))
    assert code in [p["code"] for p in problems]


def test_notes_of_one_pitch_never_overlap_in_a_track():
    text = SCORE.replace('name = "lead"', 'name = "lead"\ngate = 3.0')
    lead = sorted(
        (n for n in compiled(text)["notes"] if n["part"] == "lead"),
        key=lambda n: (n["pitch"], n["start"]),
    )
    for a, b in zip(lead, lead[1:], strict=False):
        if a["pitch"] == b["pitch"]:
            assert a["start"] + a["duration"] <= b["start"]


def score_in(tmp_path, text: str = SCORE) -> str:
    (tmp_path / "music").mkdir(exist_ok=True)
    (tmp_path / "music" / "sugar.music.toml").write_text(text, encoding="utf-8")
    return "music/sugar.music.toml"


def test_validate_answers_the_length_the_notes_and_the_loop(tmp_path):
    found = music.validate(score_in(tmp_path), root=str(tmp_path))
    assert found["valid"] is True and found["problems"] == []
    assert found["seconds"] == pytest.approx(6.0)
    assert found["notes"]["bass"] == 24
    assert found["source"] == "music/sugar.music.toml"


def test_validate_answers_problems_rather_than_raising(tmp_path):
    found = music.validate(score_in(tmp_path, SCORE.replace("bpm = 120", "")),
                           root=str(tmp_path))
    assert found["valid"] is False
    assert found["problems"][0]["code"] == "music.missing"


def test_a_score_is_read_only_from_inside_the_project(tmp_path):
    with pytest.raises(PolyweaveError) as missing:
        music.validate("music/none.music.toml", root=str(tmp_path))
    assert missing.value.code == "music.unreadable"
    with pytest.raises(PolyweaveError) as outside:
        music.validate("../elsewhere.music.toml", root=str(tmp_path))
    assert outside.value.code == "config.path-outside"


def test_to_midi_writes_a_format_one_file_a_daw_opens(tmp_path):
    found = music.to_midi(score_in(tmp_path), root=str(tmp_path))
    assert found["midi"] == "music/sugar.mid"
    data = (tmp_path / "music" / "sugar.mid").read_bytes()
    assert data[:4] == b"MThd"
    assert int.from_bytes(data[8:10], "big") == 1  # format 1
    assert int.from_bytes(data[10:12], "big") == 4  # conductor and three parts
    assert int.from_bytes(data[12:14], "big") == 480
    assert data.count(b"MTrk") == 4
    assert bytes([0x99, 36]) in data  # the kick, on the drum channel
    assert bytes([0xC1, 38]) in data  # the bass's General MIDI program


def test_to_midi_refuses_a_score_with_problems(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        music.to_midi(score_in(tmp_path, SCORE.replace("bpm = 120", "")),
                      root=str(tmp_path))
    assert refused.value.code == "music.invalid"
    assert "music.validate" in refused.value.remedy
