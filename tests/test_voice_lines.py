"""A string table voiced as a set, each line in its speaker's voice (§PW322).

The service is never reached: its transport is replaced, and answers a real MP3 so each
take can be measured on the sitting it lands in.
"""

from __future__ import annotations

import json
import shutil

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sound_buy
from polyweave.services import elevenlabs, purchase
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
    monkeypatch.setattr(elevenlabs, "used", lambda base, key: None)
    fake = Service(mp3(tmp_path))
    monkeypatch.setattr(elevenlabs, "post", fake.post)
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
    # Priced all the same, so the set's cost is known before Bo has a voice (§PW414).
    assert plan["unvoiced_characters"] == len("Go home") + len("Vai pra casa")
    assert plan["unvoiced_price"] == pytest.approx(19 * 0.001)
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


def test_the_takes_sitting_is_laid_in_the_work_area_or_out_never_the_root(
    tmp_path, project
):
    """§PW416: it landed in voices/ beside game/, and Godot imported its sheets."""
    done = sound_buy.lines(locale="en", spend=True, root=str(tmp_path))
    assert done["sitting"].startswith(".polyweave/voices/lines/")
    assert not (tmp_path / "voices").exists()
    (tmp_path / "audio" / "voice" / "en" / "HOLD.mp3").unlink()
    done = sound_buy.lines(locale="en", spend=True, out="art/review/lines",
                           root=str(tmp_path))
    assert done["sitting"].startswith("art/review/lines/")


def test_a_model_that_can_be_held_to_a_language_is_told_the_column(tmp_path, project):
    """Left to guess, an English-designed voice read Portuguese with an English mouth
    (§PW412): a model that takes `language_code` is told the column's, one that refuses
    it is never sent it."""
    (tmp_path / "polyweave.toml").write_text(VOICED.replace(
        '"eleven_multilingual_v2" = { per = "character", rate = 0.001 }',
        '"eleven_multilingual_v2" = { per = "character", rate = 0.001 }, '
        '"eleven_v3" = { per = "character", rate = 0.001 }'), encoding="utf-8")
    sound_buy.lines(spend=True, model="eleven_v3", root=str(tmp_path))
    sent = {payload["text"]: payload for _, _, payload in project.sent}
    assert sent["Aguente firme"]["language_code"] == "pt"
    assert sent["Hold fast"]["language_code"] == "en"
    project.sent.clear()
    (tmp_path / "text" / "strings.csv").write_text(
        TABLE.replace("Hold fast", "Hold it"), "utf-8")
    sound_buy.lines(locale="en", spend=True, root=str(tmp_path))
    assert "language_code" not in project.sent[0][2]


def test_each_column_is_spoken_in_its_own_locale_voice(tmp_path, project):
    """A locale's own voice speaks its column, the shared one the rest, and a new voice
    for one language leaves the other's takes current (§PW413)."""
    world_file = tmp_path / "game.world.toml"
    world_file.write_text(WORLD.replace(
        '[entity.ada.voice]\nid = "ada-voice"\n',
        '[entity.ada.voice]\nid = "ada-voice"\n\n'
        '[entity.ada.voice.pt_BR]\nid = "ada-br"\n'),
        encoding="utf-8")
    sound_buy.lines(spend=True, root=str(tmp_path))
    routes = {payload["text"]: url for url, _, payload in project.sent}
    assert "/text-to-speech/ada-voice?" in routes["Hold fast"]
    assert "/text-to-speech/ada-br?" in routes["Aguente firme"]
    world_file.write_text(world_file.read_text("utf-8").replace("ada-br", "ada-br-2"),
                          encoding="utf-8")
    again = sound_buy.lines(root=str(tmp_path))
    offered = [(one["key"], one["locale"]) for one in again["voice"]]
    assert offered == [("HOLD", "pt_BR")]
    assert [one["locale"] for one in again["current"]] == ["en"]
    stale = provenance.outdated(root=str(tmp_path))["outdated"]
    assert [one["artefact"] for one in stale] == ["audio/voice/pt_BR/HOLD.mp3"]


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


# -- a plain lines file, outside a game (§PW665) -------------------------------------

SCRIPT = """{
 "voice": "narrator-voice", "out": "demo/narration/{locale}/{key}.mp3", "speed": 0.95,
 "lines": [
  {"key": "chapter-1", "locale": "en", "text": "Search, without a plugin."},
  {"key": "chapter-1", "locale": "pt_BR", "text": "Busca, sem um plugin."}
 ]
}"""


def test_a_lines_file_is_spoken_and_a_current_take_is_not_bought_again(
    tmp_path, project
):
    """Dumont's narration was spoken by a loop of its own over sound.speak."""
    script = tmp_path / "demo" / "script.json"
    script.parent.mkdir()
    script.write_text(SCRIPT, encoding="utf-8")
    plan = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert [(one["key"], one["locale"]) for one in plan["voice"]] == [
        ("chapter-1", "en"), ("chapter-1", "pt_BR")]
    assert project.sent == []
    done = sound_buy.lines(script="demo/script.json", locale="en", spend=True,
                           root=str(tmp_path))
    assert [one["out"] for one in done["voiced"]] == ["demo/narration/en/chapter-1.mp3"]
    url, _, sent = project.sent[0]
    assert "/text-to-speech/narrator-voice?" in url
    assert sent["voice_settings"] == {"speed": 0.95}
    again = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert [one["locale"] for one in again["current"]] == ["en"]
    assert [one["locale"] for one in again["voice"]] == ["pt_BR"]
    script.write_text(SCRIPT.replace('"speed": 0.95', '"speed": 1.0'), "utf-8")
    redone = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert redone["current"] == []


def test_a_lines_file_with_no_voice_is_refused_by_name(tmp_path, project):
    (tmp_path / "script.toml").write_text(
        'out = "vo/{key}.mp3"\n[[lines]]\nkey = "a"\nlocale = "en"\ntext = "Hi"\n',
        encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.lines(script="script.toml", root=str(tmp_path))
    assert refused.value.code == "sound.bad-script"
    assert "no voice" in refused.value.message


# -- takes sound.speak bought, taken over (§PW691) -----------------------------------


def _spoken(tmp_path, text, out, **kw):
    sound_buy.speak(text=text, out=out, root=str(tmp_path), **kw)
    return tmp_path / out


def test_a_take_sound_speak_bought_is_adoptable_and_adopt_takes_it_over(
    tmp_path, project
):
    """The marketing repository's 18 takes were all offered to buy again (§PW691)."""
    script = tmp_path / "demo" / "script.json"
    script.parent.mkdir()
    script.write_text(SCRIPT, encoding="utf-8")
    # sound.speak keeps the words unstripped; voice.lines strips a line.
    take = _spoken(tmp_path, "Busca, sem um plugin. ",
                   "demo/narration/pt_BR/chapter-1.mp3", voice="narrator-voice",
                   speed=0.95)
    sent = len(project.sent)
    record = provenance.read(str(take), root=str(tmp_path))

    plan = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert plan["adoptable"] == [{
        "key": "chapter-1", "locale": "pt_BR",
        "out": "demo/narration/pt_BR/chapter-1.mp3", "bought_by": "sound.speak",
        "language_held": None}]
    # Without adopt it is still a buy, and nothing is written or counted current.
    assert [one["locale"] for one in plan["voice"]] == ["en", "pt_BR"]
    assert plan["current"] == []
    assert provenance.read(str(take), root=str(tmp_path)) == record

    taken = sound_buy.lines(script="demo/script.json", adopt=True, root=str(tmp_path))
    assert taken["current"] == [{"key": "chapter-1", "locale": "pt_BR",
                                 "out": "demo/narration/pt_BR/chapter-1.mp3",
                                 "adopted": True}]
    assert [one["locale"] for one in taken["voice"]] == ["en"]
    assert len(project.sent) == sent
    adopted = provenance.read(str(take), root=str(tmp_path))
    assert adopted["details"]["adopted"] is True
    assert adopted["details"]["line"]["script"] == "demo/script.json"
    assert "words" in [one["role"] for one in adopted["inputs"]]
    again = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert [one["locale"] for one in again["current"]] == ["pt_BR"]
    assert "adoptable" not in again


def test_a_take_in_another_delivery_a_draft_or_an_edited_file_is_never_adoptable(
    tmp_path, project
):
    script = tmp_path / "script.json"
    script.write_text(SCRIPT, encoding="utf-8")
    out = "demo/narration/pt_BR/chapter-1.mp3"
    take = _spoken(tmp_path, "Busca, sem um plugin.", out, voice="narrator-voice")

    def offered():
        return sound_buy.lines(script="script.json", locale="pt_BR",
                               root=str(tmp_path)).get("adoptable", [])

    assert offered() == []  # spoken at the voice's own speed, not the file's 0.95
    take.unlink()
    take = _spoken(tmp_path, "Busca, sem um plugin.", out, voice="other-voice",
                   speed=0.95)
    assert offered() == []
    take.unlink()
    take = _spoken(tmp_path, "Busca, sem plugin.", out, voice="narrator-voice",
                   speed=0.95)
    assert offered() == []
    take.unlink()
    take = _spoken(tmp_path, "Busca, sem um plugin.", out, voice="narrator-voice",
                   speed=0.95)
    assert len(offered()) == 1
    sidecar = provenance.sidecar(take, tmp_path)
    kept = sidecar.read_text(encoding="utf-8")
    drafted = json.loads(kept)
    drafted["params"] = {"rung": "draft"}
    sidecar.write_text(json.dumps(drafted), encoding="utf-8")
    assert offered() == []
    sidecar.write_text(kept, encoding="utf-8")
    take.write_bytes(take.read_bytes() + b"\0")
    assert offered() == []
    assert sound_buy.lines(script="script.json", adopt=True,
                           root=str(tmp_path))["current"] == []


def test_a_take_spoken_for_an_entity_is_adoptable_for_its_table_row(tmp_path, project):
    take = _spoken(tmp_path, "Aguente firme", "audio/voice/pt_BR/HOLD.mp3",
                   entity="ada")
    plan = sound_buy.lines(locale="pt_BR", root=str(tmp_path))
    assert [(o["key"], o["speaker"], o["bought_by"]) for o in plan["adoptable"]] == [
        ("HOLD", "ada", "sound.speak")]
    taken = sound_buy.lines(locale="pt_BR", adopt=True, root=str(tmp_path))
    assert taken["current"][0]["adopted"] is True and taken["voice"] == []
    line = provenance.read(str(take), root=str(tmp_path))["details"]["line"]
    assert line["table"] == "text/strings.csv" and line["key"] == "HOLD"
    assert provenance.outdated(root=str(tmp_path))["outdated"] == []


# -- an opening's first proof, held before anything is bought (§PW706) ----------------

OPENING = """voice = "narrator-voice"
out = "vo/{locale}/{key}.mp3"

[opening]
proof = "proof"
word = 3
max_seconds = 6
wpm = { en = 150, pt = 140 }
preamble = ["neste video"]

[[lines]]
key = "hook"
locale = "en"
text = "[excited] Thirty thousand merges a day."

[[lines]]
key = "proof"
locale = "en"
text = "Git did not hold, and here is the graph."

[[lines]]
key = "hook"
locale = "pt_BR"
text = "Trinta mil merges por dia."

[[lines]]
key = "proof"
locale = "pt_BR"
text = "O Git não aguentou, e aqui está o gráfico."
"""


def test_an_opening_in_time_is_planned_with_its_estimate(tmp_path, project):
    (tmp_path / "script.toml").write_text(OPENING, encoding="utf-8")
    plan = sound_buy.lines(script="script.toml", root=str(tmp_path))
    # Five words of the hook, the [excited] tag unspoken, then three into the proof.
    assert plan["opening"]["en"] == {"words": 8, "seconds": 3.2, "max": 6.0}
    assert plan["opening"]["pt_BR"]["words"] == 8
    assert project.sent == []


def test_a_late_proof_is_refused_before_a_plan_or_a_purchase(tmp_path, project):
    (tmp_path / "script.toml").write_text(
        OPENING.replace("max_seconds = 6", "max_seconds = 3"), encoding="utf-8")
    for spend in (False, True):
        with pytest.raises(PolyweaveError) as refused:
            sound_buy.lines(script="script.toml", spend=spend, root=str(tmp_path))
        assert refused.value.code == "sound.opening-late"
        assert "3.2s" in refused.value.message
    assert project.sent == [] and purchase.read(tmp_path) == []


def test_a_declared_preamble_is_refused_and_a_missing_translation_named(
    tmp_path, project
):
    (tmp_path / "script.toml").write_text(
        OPENING.replace("Trinta mil", "Neste vídeo, trinta mil"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.lines(script="script.toml", root=str(tmp_path))
    assert refused.value.code == "sound.opening-preamble"
    (tmp_path / "script.toml").write_text(
        OPENING.replace('key = "proof"\nlocale = "pt_BR"', 'key = "prova"\n'
                        'locale = "pt_BR"'), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.lines(script="script.toml", root=str(tmp_path))
    assert refused.value.code == "sound.opening-late"
    assert "pt_BR" in refused.value.message


# -- a delivery setting the model ignores (§PW717) ------------------------------------


def _on_v3(tmp_path):
    (tmp_path / "polyweave.toml").write_text(VOICED.replace(
        '"eleven_multilingual_v2" = { per = "character", rate = 0.001 }',
        '"eleven_multilingual_v2" = { per = "character", rate = 0.001 }, '
        '"eleven_v3" = { per = "character", rate = 0.001 }'), encoding="utf-8")
    script = tmp_path / "demo" / "script.json"
    script.parent.mkdir(exist_ok=True)
    return script


def test_a_speed_eleven_v3_ignores_is_refused_before_anything_is_bought(
    tmp_path, project
):
    """viglet/marketing paid for three takes at speeds eleven_v3 never applied."""
    script = _on_v3(tmp_path)
    script.write_text(SCRIPT.replace('"speed": 0.95', '"speed": 1.12, "model": '
                                     '"eleven_v3"'), encoding="utf-8")
    for spend in (False, True):
        with pytest.raises(PolyweaveError) as refused:
            sound_buy.lines(script="demo/script.json", spend=spend, root=str(tmp_path))
        assert refused.value.code == "sound.setting-ignored"
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.speak(text="Hold fast", voice="v", model="eleven_v3", speed=1.1,
                        out="vo/a.mp3", root=str(tmp_path))
    assert refused.value.code == "sound.setting-ignored"
    assert project.sent == []


def test_a_take_recorded_with_an_ignored_speed_is_still_current_without_it(
    tmp_path, project
):
    from polyweave.kernel import provenance

    script = _on_v3(tmp_path)
    script.write_text(SCRIPT.replace('"speed": 0.95', '"model": "eleven_v3"'),
                      encoding="utf-8")
    sound_buy.lines(script="demo/script.json", locale="en", spend=True,
                    root=str(tmp_path))
    take = tmp_path / "demo" / "narration" / "en" / "chapter-1.mp3"
    record = provenance.read(str(take), root=str(tmp_path))
    record["details"]["delivery"] = {"speed": 1.12}  # as a take bought before §PW717
    provenance.write(record, root=str(tmp_path))
    again = sound_buy.lines(script="demo/script.json", root=str(tmp_path))
    assert [one["locale"] for one in again["current"]] == ["en"]

# -- a narrator found in the library and heard against others (§PW719) -----------------


def test_the_library_is_searched_once_a_day_and_spends_nothing(
    tmp_path, project, monkeypatch
):
    import urllib.parse

    from polyweave.layers.sound import voices
    from polyweave.services import client

    asked = []

    def send(url, **kw):
        asked.append((url, kw.get("headers") or {}))
        return client.Answer(200, json.dumps({"voices": [
            {"voice_id": "v-young", "name": "Lia", "age": "young", "gender": "female",
             "accent": "brazilian", "use_case": "narrative_story", "locale": "pt-BR",
             "extra": "dropped"}]}).encode(), {})

    monkeypatch.setattr(client, "send", send)
    said = voices.find(language="pt", locale="pt-BR", age="young", root=str(tmp_path))
    assert said["voices"] == [{"voice_id": "v-young", "name": "Lia", "accent":
                               "brazilian", "age": "young", "gender": "female",
                               "use_case": "narrative_story", "locale": "pt-BR"}]
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(asked[0][0]).query))
    assert query == {"language": "pt", "locale": "pt-BR", "age": "young",
                     "page_size": "20"}
    assert asked[0][1]["xi-api-key"] == "sk-sound"
    voices.find(language="pt", locale="pt-BR", age="young", root=str(tmp_path))
    assert len(asked) == 1
    assert project.sent == []


def test_one_line_in_several_voices_is_priced_then_laid_as_one_choice(
    tmp_path, project
):
    from polyweave.layers.sound import voices

    plan = voices.compare(text="O primeiro bug", voices=["v-a", "v-b", "v-a"],
                          out="samples", root=str(tmp_path))
    assert plan["voices"] == ["v-a", "v-b"] and plan["spent"] is False
    assert plan["price"] == pytest.approx(2 * len("O primeiro bug") * 0.001)
    assert project.sent == []
    done = voices.compare(text="O primeiro bug", voices=["v-a", "v-b"], out="samples",
                          spend=True, root=str(tmp_path))
    assert [url.split("/text-to-speech/")[1].split("?")[0]
            for url, _, _ in project.sent] == ["v-a", "v-b"]
    assert done["takes"] == ["samples/v-a.mp3", "samples/v-b.mp3"]
    assert done["sitting"].startswith("samples")
    with pytest.raises(PolyweaveError) as refused:
        voices.compare(text="O primeiro bug", voices=["v-a"], root=str(tmp_path))
    assert refused.value.code == "fetch.missing-field"

# -- a current take bought again, on a person's word (§PW720) --------------------------


def test_a_current_take_is_retaken_with_its_reason_and_the_old_kept_beside(
    tmp_path, project
):
    """urdido moved takes aside by hand so voice.lines would buy a drifted one again."""
    script = tmp_path / "demo" / "script.json"
    script.parent.mkdir()
    script.write_text(SCRIPT, encoding="utf-8")
    sound_buy.lines(script="demo/script.json", locale="en", spend=True,
                    root=str(tmp_path))
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.lines(script="demo/script.json", locale="en", retake=["chapter-1"],
                        root=str(tmp_path))
    assert refused.value.code == "fetch.missing-field"
    plan = sound_buy.lines(script="demo/script.json", locale="en",
                           retake=["chapter-1"], reason="drifted into European "
                           "Portuguese at 0:28", root=str(tmp_path))
    assert plan["current"] == [] and plan["voice"][0]["retake"] is True
    sent = len(project.sent)
    sound_buy.lines(script="demo/script.json", locale="en", retake=["chapter-1"],
                    reason="drifted at 0:28", spend=True, root=str(tmp_path))
    assert len(project.sent) == sent + 1
    folder = tmp_path / "demo" / "narration" / "en"
    kept = sorted(p.name for p in folder.glob("chapter-1.retake-*.mp3"))
    assert len(kept) == 1
    assert (folder / (kept[0] + ".prov.json")).is_file()
    record = provenance.read(str(folder / "chapter-1.mp3"), root=str(tmp_path))
    assert record["details"]["retake"] == {
        "reason": "drifted at 0:28",
        "replaced": f"demo/narration/en/{kept[0]}"}
    again = sound_buy.lines(script="demo/script.json", locale="en", root=str(tmp_path))
    assert [one["locale"] for one in again["current"]] == ["en"]


def test_a_retake_that_cannot_be_bought_puts_the_old_take_back(
    tmp_path, project, monkeypatch
):
    script = tmp_path / "demo" / "script.json"
    script.parent.mkdir()
    script.write_text(SCRIPT, encoding="utf-8")
    sound_buy.lines(script="demo/script.json", locale="en", spend=True,
                    root=str(tmp_path))
    take = tmp_path / "demo" / "narration" / "en" / "chapter-1.mp3"
    before = take.read_bytes()

    def refused(*_, **__):
        raise PolyweaveError("fetch.service-error", "down", "later")

    monkeypatch.setattr(sound_buy, "_bought", refused)
    with pytest.raises(PolyweaveError):
        sound_buy.lines(script="demo/script.json", locale="en", retake=["chapter-1"],
                        reason="drifted", spend=True, root=str(tmp_path))
    assert take.read_bytes() == before
    assert not list(take.parent.glob("chapter-1.retake-*"))