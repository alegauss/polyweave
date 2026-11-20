"""A spoken take held to its line before a person hears it (§PW323).

A tone between two silences stands in for a voice: what is measured is where the sound
starts and stops and how loud it is, which a tone has exactly. The transcription is
replaced, since faster-whisper is optional and a test downloads no model.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave.layers.sound import sound
from test_sound import RATE, tone, written


def unheard(path, vocabulary=(), language=None):
    """The transcription where faster-whisper is not installed."""
    return None


def take(where, lead=0.5, spoken=1.0, tail=0.8, amplitude=0.5):
    quiet = np.zeros
    samples = np.concatenate([
        quiet(int(lead * RATE)), tone(spoken, amplitude=amplitude),
        quiet(int(tail * RATE)),
    ])
    return written(where, samples)


def test_a_take_says_its_silences_and_its_rate(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", unheard)
    found = sound.speech(take(tmp_path / "t.wav"), "Hold fast")
    assert found["lead_silence"] == pytest.approx(0.5, abs=0.03)
    assert found["tail_silence"] == pytest.approx(0.8, abs=0.03)
    # Eight letters over a second spoken.
    assert found["rate"] == pytest.approx(8.0, rel=0.06)
    assert found["said"] is None and "faster-whisper" in found["unheard"]


def test_the_projects_bounds_name_what_a_take_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", unheard)
    (tmp_path / "polyweave.toml").write_text(
        "[voice]\nlead_silence = 0.25\ntail_silence = 1.0\nrate = [10.0, 20.0]\n",
        encoding="utf-8",
    )
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert [one["measure"] for one in said["failed"]] == ["lead_silence", "rate"]


def test_no_bound_is_no_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", unheard)
    take(tmp_path / "t.wav", lead=2.0)
    assert sound.spoken("t.wav", text="Go", root=str(tmp_path))["failed"] == []


def test_a_misread_name_is_named_and_the_worlds_names_are_expected(
    tmp_path, monkeypatch
):
    asked = {}

    def heard(path, vocabulary=(), language=None):
        asked["vocabulary"] = list(vocabulary)
        return "Hold fast, Captain Aida."

    monkeypatch.setattr(sound, "_transcribed", heard)
    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Captain Ada"\nkind = "character"\n', encoding="utf-8")
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="Hold fast, Captain Ada.", root=str(tmp_path))
    assert said["said"]["missing"] == ["ada"] and said["said"]["extra"] == ["aida"]
    assert said["failed"][-1]["measure"] == "said"
    assert asked["vocabulary"] == ["Captain Ada"]


def test_an_accent_the_transcription_left_off_is_the_same_word():
    """§PW414: "Lá" heard as "la" failed a take that said its line."""
    assert sound._differs("Lá vem ele!", "La vem ele.")["matches"]


def test_an_interjection_is_said_however_it_was_spelled():
    said = sound._differs("Uhuu, vamo lá!", "Woohoo, vamos la!", ("uhuu", "vamo"))
    assert said["matches"]
    # A word that is no interjection is still held to the line.
    said = sound._differs("Uhuu, capataz!", "Woohoo, kapatais!", ("uhuu",))
    assert said["missing"] == ["capataz"] and said["extra"] == ["kapatais"]


def test_a_take_is_transcribed_in_the_language_its_record_names(
    tmp_path, monkeypatch
):
    from polyweave.kernel import provenance

    asked = {}

    def heard(path, vocabulary=(), language=None):
        asked["language"] = language
        return "Aguente firme"

    monkeypatch.setattr(sound, "_transcribed", heard)
    (tmp_path / "polyweave.toml").write_text(
        '[voice]\ninterjections = ["uhuu"]\n', encoding="utf-8")
    where = take(tmp_path / "t.wav")
    provenance.write(provenance.build(
        "sound", where, root=tmp_path,
        extra={"details": {"line": {"key": "HOLD", "locale": "pt_BR"}}},
    ), tmp_path)
    said = sound.spoken("t.wav", text="Aguente firme", root=str(tmp_path))
    assert asked["language"] == "pt" and said["said"]["language"] == "pt"
    assert sound.expected(where, sound.load(tmp_path))["interjections"] == ("uhuu",)


def test_a_sitting_shows_a_takes_speech_and_marks_one_that_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", unheard)
    (tmp_path / "polyweave.toml").write_text(
        "[voice]\nlead_silence = 0.25\n", encoding="utf-8")
    take(tmp_path / "late.wav")
    take(tmp_path / "prompt.wav", lead=0.1)
    laid = sound.sitting(
        [{"name": "late", "new": "late.wav", "line": "Hold fast"},
         {"name": "prompt", "new": "prompt.wav", "line": "Hold fast"}],
        out="sitting", root=str(tmp_path),
    )
    failed = {name: [f["measure"] for f in said["failed"]]
              for name, said in laid["speech"].items()}
    assert failed == {"late": ["lead_silence"], "prompt": []}
    assert (tmp_path / "sitting" / "late.png").is_file()


def test_a_bought_take_lands_with_its_silence_cut_to_the_bound(tmp_path, monkeypatch):
    import hashlib
    import shutil
    import subprocess

    from polyweave.kernel import provenance
    from polyweave.layers.sound import sound_buy
    from polyweave.services import elevenlabs
    from test_sound_buy import PROJECT, Service

    if not shutil.which("ffmpeg"):
        pytest.skip("needs ffmpeg")
    padded = take(tmp_path / "padded.wav", lead=1.0, tail=1.2)
    sent = subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-i", str(padded), "-f", "mp3",
         "pipe:1"], capture_output=True, check=True,
    ).stdout
    (tmp_path / "polyweave.toml").write_text(
        PROJECT.replace('"eleven_text_to_sound_v2" = 0.05',
                        '"eleven_multilingual_v2" = 0.05')
        + "\n[voice]\nlead_silence = 0.2\ntail_silence = 0.3\ntrim = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("POLYWEAVE_TEST_E", "sk-sound")
    monkeypatch.setattr(elevenlabs, "used", lambda base, key: None)
    monkeypatch.setattr(sound, "_transcribed", unheard)
    monkeypatch.setattr(elevenlabs, "post", Service(sent).post)
    found = sound_buy.speak(text="Hold fast", voice="v1", out="vo/hold.wav",
                            root=str(tmp_path))
    assert found["speech"]["failed"] == []
    assert found["speech"]["lead_silence"] == pytest.approx(0.2, abs=0.08)
    assert found["speech"]["tail_silence"] == pytest.approx(0.3, abs=0.08)
    trimmed = provenance.read(str(tmp_path / "vo" / "hold.wav"), root=tmp_path)
    cut = trimmed["details"]["trimmed"]
    assert cut["sent_sha256"] == hashlib.sha256(sent).hexdigest()
    assert cut["lead"] > 0.6


def test_a_lines_audio_tags_are_directions_not_words(tmp_path, monkeypatch):
    """§PW668: Dumont's eleven_v3 take performed [excited] and [laughs] and failed."""
    from polyweave.kernel import provenance

    def heard(path, vocabulary=(), language=None):
        return "Welcome back, friend."

    monkeypatch.setattr(sound, "_transcribed", heard)
    take(tmp_path / "t.wav")
    line = "[excited] Welcome back, [laughs] friend."
    provenance.write(provenance.build(
        "sound", tmp_path / "t.wav",
        engine={"name": "elevenlabs", "model": "eleven_v3"},
        extra={"prompt": line}, root=tmp_path), tmp_path)
    said = sound.spoken("t.wav", root=str(tmp_path))
    assert said["said"]["matches"] is True
    assert said["directions"] == ["[excited]", "[laughs]"]
    assert said["failed"] == []
    # A model that says what it is given is held to every word of it.
    provenance.write(provenance.build(
        "sound", tmp_path / "t.wav",
        engine={"name": "elevenlabs", "model": "eleven_multilingual_v2"},
        extra={"prompt": line}, root=tmp_path), tmp_path)
    assert sound.spoken("t.wav", root=str(tmp_path))["said"]["missing"] == [
        "excited", "laughs"]


def test_timed_words_are_answered_kept_with_the_take_and_read_back(
    tmp_path, monkeypatch
):
    """§PW703: a video's callouts are placed by when each word is said."""
    heard_times = []

    def timed(path, vocabulary=(), language=None):
        heard_times.append(path)
        return {"text": "Hold fast", "words": [
            {"word": "Hold", "start": 0.5, "end": 0.8, "probability": 0.9},
            {"word": "fast", "start": 0.85, "end": 1.4, "probability": 0.8}]}

    monkeypatch.setattr(sound, "_transcribed", timed)
    take(tmp_path / "t.wav")
    first = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert [one["word"] for one in first["words"]] == ["Hold", "fast"]
    assert first["words"][1]["start"] == 0.85
    assert first["words_file"] == "t.wav.words.json" and first["words_cached"] is False
    again = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert again["words_cached"] is True and again["words"] == first["words"]
    assert len(heard_times) == 1
    take(tmp_path / "t.wav", lead=0.7)
    moved = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert moved["words_cached"] is False and len(heard_times) == 2


def test_an_untimed_transcription_keeps_no_words_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sound, "_transcribed", lambda *a, **k: "Hold fast")
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="Hold fast", root=str(tmp_path))
    assert "words" not in said and "words_file" not in said
    assert not (tmp_path / "t.wav.words.json").exists()


def test_each_word_of_the_line_says_how_sure_its_time_is(tmp_path, monkeypatch):
    """§PW703: an uncertain match is a suggestion for a person, never a placed time."""
    def timed(path, vocabulary=(), language=None):
        return {"text": "O word press nasceu em dois mil e tres", "words": [
            {"word": w, "start": s, "end": s + 0.3, "probability": 0.9}
            for w, s in (("O", 0.1), ("word", 0.5), ("press", 0.8), ("nasceu", 1.2),
                         ("em", 1.6), ("dois", 1.8), ("mil", 2.1), ("e", 2.3),
                         ("três", 2.5))]}

    monkeypatch.setattr(sound, "_transcribed", timed)
    (tmp_path / "polyweave.toml").write_text(
        '[voice]\naliases = { WordPress = ["word press"] }\n', encoding="utf-8")
    take(tmp_path / "t.wav")
    said = sound.spoken("t.wav", text="O WordPress nasceu em 2003",
                        root=str(tmp_path))
    by_word = {one["word"]: one for one in said["aligned"]}
    assert by_word["O"]["match"] == "exact"
    alias = by_word["WordPress"]
    assert alias["match"] == "alias" and alias["start"] == 0.5
    assert alias["end"] == pytest.approx(1.1)
    assert by_word["2003"]["match"] == "uncertain" and by_word["2003"]["start"] is None
    [suggested] = said["uncertain"]
    assert suggested["word"] == "2003" and suggested["heard"] == "dois mil e três"
    assert suggested["start"] == 1.8
