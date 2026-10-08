"""A string table voiced as a set, each line in its speaker's voice (§PW322).

The service is never reached: its transport is replaced, and answers a real MP3 so each
take can be measured on the sitting it lands in.
"""

from __future__ import annotations

import shutil

import pytest

from polyweave import provenance, purchase, sound_buy
from polyweave.errors import PolyweaveError
from test_sound_buy import PROJECT, Service, mp3

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")

VOICED = PROJECT.replace(
    '"eleven_text_to_sound_v2" = 0.05',
    '"eleven_multilingual_v2" = { per = "character", rate = 0.001 }',
) + '\n[words]\ntable = "text/strings.csv"\nvoiced = "audio/voice/{locale}/{key}.mp3"\n'

TABLE = (
    "keys,en,pt_BR,_speaker\n"
    "HOLD,Hold fast,Aguente firme,ada\n"
    "GO,Go home,Vai pra casa,bo\n"
    "START,Start,Iniciar,\n"
)

WORLD = (
    '[entity.ada]\nname = "Ada"\nkind = "character"\n\n'
    '[entity.ada.voice]\nid = "ada-voice"\n\n'
    '[entity.bo]\nname = "Bo"\nkind = "character"\n'
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(VOICED, encoding="utf-8")
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "strings.csv").write_text(TABLE, encoding="utf-8")
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_E", "sk-sound")
    monkeypatch.setattr(sound_buy, "_used", lambda base, key: None)
    fake = Service(mp3(tmp_path))
    monkeypatch.setattr(sound_buy, "_post", fake.post)
    return fake


def test_the_plan_prices_every_line_and_sends_nothing(tmp_path, project):
    plan = sound_buy.lines(root=str(tmp_path))
    said = {(one["key"], one["locale"]): one for one in plan["voice"]}
    assert set(said) == {("HOLD", "en"), ("HOLD", "pt_BR")}
    assert said[("HOLD", "pt_BR")]["price"] == pytest.approx(13 * 0.001)
    assert plan["characters"] == len("Hold fast") + len("Aguente firme")
    # Bo has no voice, so his line is reported and not voiced in a default.
    unvoiced = {(o["key"], o["code"]) for o in plan["unvoiced"]}
    assert unvoiced == {("GO", "world.no-voice")}
    assert project.sent == []
    assert purchase.read(tmp_path) == []


def test_spent_lines_land_once_and_a_changed_row_is_offered_again(tmp_path, project):
    done = sound_buy.lines(locale="en", spend=True, root=str(tmp_path))
    assert [one["out"] for one in done["voiced"]] == ["audio/voice/en/HOLD.mp3"]
    assert done["sitting"]
    assert "/text-to-speech/ada-voice?" in project.sent[0][0]
    again = sound_buy.lines(locale="en", root=str(tmp_path))
    assert again["voice"] == [] and again["current"][0]["key"] == "HOLD"
    # Another row's edit leaves the take current; its own row's edit does not.
    table = tmp_path / "text" / "strings.csv"
    table.write_text(TABLE.replace("Go home", "Go home now"), "utf-8")
    assert provenance.outdated(root=str(tmp_path))["outdated"] == []
    table.write_text(TABLE.replace("Hold fast", "Hold the line"), "utf-8")
    stale = provenance.outdated(root=str(tmp_path))["outdated"]
    assert [one["artefact"] for one in stale] == ["audio/voice/en/HOLD.mp3"]
    assert sound_buy.lines(locale="en", root=str(tmp_path))["voice"][0]["key"] == "HOLD"


def test_the_ceiling_stops_the_set_and_names_what_was_not_voiced(tmp_path, project):
    (tmp_path / "polyweave.toml").write_text(
        VOICED.replace("amount = 1.0", "amount = 0.01"), encoding="utf-8")
    done = sound_buy.lines(spend=True, root=str(tmp_path))
    assert [one["locale"] for one in done["voiced"]] == ["en"]
    assert [one["locale"] for one in done["not_voiced"]] == ["pt_BR"]
    assert "stopped_by" in done


def test_a_project_with_nowhere_to_put_takes_is_refused(tmp_path, project):
    (tmp_path / "polyweave.toml").write_text(
        VOICED.replace('voiced = "audio/voice/{locale}/{key}.mp3"\n', ""), "utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.lines(root=str(tmp_path))
    assert refused.value.code == "words.no-voiced"
