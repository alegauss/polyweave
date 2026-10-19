"""A MIDI file drafted as an editable score (§PW559)."""

from __future__ import annotations

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import music, music_draft
from test_music import SCORE


def notes_of(model: dict) -> set[tuple[str, int, int]]:
    return {(n["part"], n["start"], n["pitch"]) for n in model["notes"]}


def round_trip(tmp_path, score: str = SCORE, **knobs):
    model, problems = music.compile_source(score)
    assert problems == []
    (tmp_path / "theme.mid").write_bytes(music.midi_bytes(model))
    found = music_draft.from_midi("theme.mid", root=str(tmp_path), **knobs)
    return model, found


def test_a_score_written_as_midi_drafts_back_to_the_same_notes(tmp_path):
    """Every note the score played comes back at its tick and pitch, valid at once."""
    model, found = round_trip(tmp_path)
    assert found["valid"] is True and found["problems"] == []
    assert found["score"] == "theme.music.toml"
    text = (tmp_path / "theme.music.toml").read_text(encoding="utf-8")
    again, problems = music.compile_source(text)
    assert problems == []
    assert notes_of(again) == notes_of(model)
    assert found["bpm"] == 120 and found["meter"] == [4, 4] and found["bars"] == 3


def test_each_part_is_a_track_and_the_drum_channel_a_drum_track(tmp_path):
    _, found = round_trip(tmp_path)
    tracks = found["tracks"]
    assert set(tracks) == {"lead", "bass", "drums"}
    assert tracks["bass"]["instrument"] == "gm:38"
    assert tracks["drums"]["instrument"] == "drums:0"
    assert all(t["on_grid"] == 1.0 and t["cut_at_bar"] == 0 for t in tracks.values())
    text = (tmp_path / "theme.music.toml").read_text(encoding="utf-8")
    assert "bd" in text and "hh" in text  # drums by the names a person reads


def test_a_phrase_that_comes_back_is_the_same_section_again(tmp_path):
    """Four bars of A then the same four again: the form says A A, written once."""
    score = SCORE.replace('form = ["A", "B"]', 'form = ["A", "A"]').replace(
        "[section.A]\nbars = 2", "[section.A]\nbars = 4")
    model, found = round_trip(tmp_path, score)
    assert found["form"] == ["A", "A"]
    text = (tmp_path / "theme.music.toml").read_text(encoding="utf-8")
    assert text.count("[section.") == 1
    again, _ = music.compile_source(text)
    assert notes_of(again) == notes_of(model)
    # What repeats is written once: the hats, the bass's octaves and its two bars.
    assert 'drums_a = "hh!8, bd ~ sd ~"' in text
    assert 'bass_a = "<[[c2 c3]!4] [[g2 g3]!4]>"' in text


def test_the_key_is_estimated_when_the_file_states_none(tmp_path):
    _, found = round_trip(tmp_path)
    assert found["key_stated"] is False
    assert found["key"].endswith(("major", "minor"))


def _smf0(events: bytes, tpq: int = 480) -> bytes:
    track = events + b"\x00\xff\x2f\x00"
    return (b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big")
            + (1).to_bytes(2, "big") + tpq.to_bytes(2, "big")
            + b"MTrk" + len(track).to_bytes(4, "big") + track)


def test_a_played_file_off_the_grid_says_how_much_was_on_it(tmp_path):
    """Running status, a zero-velocity release and a key signature, as players write."""
    events = (
        b"\x00\xff\x59\x02\x01\x01"  # E minor: one sharp, minor
        b"\x00\x90\x40\x64"  # e4 at 0
        b"\x83\x60\x40\x00"  # released a quarter later, by running status
        b"\x07\x43\x64"  # g4, seven ticks late
        b"\x83\x60\x43\x00"
    )
    (tmp_path / "played.mid").write_bytes(_smf0(events))
    found = music_draft.from_midi("played.mid", root=str(tmp_path))
    assert found["valid"] is True
    assert found["key"] == "E minor" and found["key_stated"] is True
    (track,) = found["tracks"].values()
    assert track["notes"] == 2 and track["on_grid"] == 1.0
    events = events.replace(b"\x07\x43", b"\x50\x43")  # 80 ticks: two-thirds of a step
    (tmp_path / "late.mid").write_bytes(_smf0(events))
    late = music_draft.from_midi("late.mid", root=str(tmp_path))
    assert next(iter(late["tracks"].values()))["on_grid"] == 0.5


def test_a_draft_never_writes_over_a_score_unless_told(tmp_path):
    round_trip(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        music_draft.from_midi("theme.mid", root=str(tmp_path))
    assert refused.value.code == "music.draft-exists"
    again = music_draft.from_midi("theme.mid", root=str(tmp_path), replace=True)
    assert again["valid"] is True


def test_what_is_not_midi_is_refused_by_name(tmp_path):
    (tmp_path / "song.mid").write_bytes(b"RIFF....WAVE")
    with pytest.raises(PolyweaveError) as refused:
        music_draft.from_midi("song.mid", root=str(tmp_path))
    assert refused.value.code == "music.not-midi"
