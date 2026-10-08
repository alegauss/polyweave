"""A line drafted free on a local engine before a character is billed (§PW324).

No engine need be installed: the engine is replaced by one that writes a tone, which is
what a draft's record and placement are about. The refusal is tested with none on PATH.
"""

from __future__ import annotations

import shutil

import pytest

from polyweave import provenance, purchase, sound, sound_buy
from polyweave.errors import PolyweaveError
from test_sound import tone, written
from test_voice_lines import TABLE, VOICED, WORLD


@pytest.fixture
def local(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(VOICED, encoding="utf-8")
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "strings.csv").write_text(TABLE, encoding="utf-8")
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    monkeypatch.setattr(sound, "_transcribed", lambda path, vocabulary=(): None)
    engine = {"name": "espeak-ng", "path": "x", "voice": "en"}
    monkeypatch.setattr(sound_buy, "_engine", lambda config: engine)
    spoken = []

    def speak(engine, text, wav):
        spoken.append(text)
        written(wav, tone(0.8))

    monkeypatch.setattr(sound_buy, "_local_speech", speak)
    return spoken


def test_a_draft_is_spoken_free_and_recorded_as_one(tmp_path, local):
    found = sound_buy.speak(text="Hold fast", out="vo/hold.wav", rung="draft",
                            root=str(tmp_path))
    assert found["rung"] == "draft" and found["spent"] == 0
    assert local == ["Hold fast"]
    assert purchase.read(tmp_path) == []
    record = provenance.read(str(tmp_path / "vo" / "hold.wav"), root=tmp_path)
    assert record["params"]["rung"] == "draft"
    assert record["engine"] == {"name": "espeak-ng", "draft": True}
    shown = provenance.generated(root=str(tmp_path))
    assert shown["drafts"] == ["vo/hold.wav"] and "vo/hold.wav" not in shown["authored"]


def test_a_draft_never_satisfies_a_line(tmp_path, local):
    if not shutil.which("ffmpeg"):
        pytest.skip("needs ffmpeg")
    sound_buy.speak(text="Hold fast", out="audio/voice/en/HOLD.mp3", rung="draft",
                    root=str(tmp_path))
    plan = sound_buy.lines(locale="en", root=str(tmp_path))
    [hold] = plan["voice"]
    assert hold["key"] == "HOLD" and hold["draft"] is True
    assert plan["current"] == []


def test_no_engine_is_refused_and_the_paid_rung_is_not_taken(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(VOICED, encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    sent = []
    monkeypatch.setattr(sound_buy, "_post", lambda *a: sent.append(a))
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.speak(text="Go", out="vo/go.wav", rung="draft", root=str(tmp_path))
    assert refused.value.code == "sound.no-speech-engine"
    assert "install" in refused.value.remedy
    assert sent == []
