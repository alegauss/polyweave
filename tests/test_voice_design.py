"""An entity's voice, designed from words and chosen by a person (§PW321).

The service is never reached: its JSON transport is replaced, as the sound tests replace
theirs. A person's verdict is written into the preview's record as the review page
writes it, since only a person may choose a voice.
"""

from __future__ import annotations

import base64
import shutil

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sound_buy
from polyweave.layers.words import world
from polyweave.services import elevenlabs, purchase
from polyweave.surface.quote import quote
from test_sound_buy import PROJECT, mp3

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")

DESIGNED = PROJECT.replace(
    '"eleven_text_to_sound_v2" = 0.05',
    '"eleven_text_to_sound_v2" = 0.05, '
    '"eleven_multilingual_ttv_v2" = { per = "character", rate = 0.001 }',
)

#: Lines past the 100 characters ElevenLabs' voice design takes at least (§PW482).
LINE = ("Shift's over. Go home. The cranes can wait till morning, and so can the "
        "paperwork you keep leaving on my desk.")
LINHA = ("Acabou o turno. Vai pra casa. Os guindastes esperam ate amanha, e a "
         "papelada que voce deixa na minha mesa tambem.")

WORLD = (
    "# The cast.\n[entity.bo]\nname = \"Bo\"\nkind = \"character\"\n\n"
    "[entity.bo.voice]\n"
    "description = \"a dry, tired foreman in his fifties\"  # as the owner said it\n"
    f"sample = \"{LINE}\"\nstability = 0.4\n"
)


class Service:
    def __init__(self, audio: bytes):
        self.audio, self.sent = audio, []

    def asked(self, url, key, payload):
        self.sent.append((url, dict(payload)))
        if url.endswith("/design"):
            clip = base64.b64encode(self.audio).decode("ascii")
            return {"previews": [{"audio_base_64": clip, "generated_voice_id": f"g{i}"}
                                 for i in (1, 2, 3)]}
        return {"voice_id": "saved-bo"}


@pytest.fixture
def service(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(DESIGNED, encoding="utf-8")
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_E", "sk-sound")
    monkeypatch.setattr(elevenlabs, "used", lambda base, key: None)
    fake = Service(mp3(tmp_path))
    monkeypatch.setattr(elevenlabs, "asked_json", fake.asked)
    return fake


def accepted(tmp_path, preview, choice="accept"):
    """A person's verdict on a preview, kept in its record as the page keeps it."""
    where = tmp_path / preview
    record = provenance.read(str(where), root=tmp_path)
    record["verdicts"] = [{"choice": choice, "why": "that's him",
                           "sha256": provenance.sha256_of(where)[0]}]
    provenance.write(record, tmp_path)


def test_previews_of_a_described_voice_are_laid_out_for_a_person(tmp_path, service):
    found = sound_buy.design(entity="bo", root=str(tmp_path))
    url, sent = service.sent[0]
    assert url.endswith("/v1/text-to-voice/design")
    assert sent["voice_description"] == "a dry, tired foreman in his fifties"
    assert sent["text"] == LINE
    assert len(found["previews"]) == 3
    assert found["sitting"]
    spent = purchase.read(tmp_path)
    assert len(spent) == 3
    assert sum(e["credits"] for e in spent) == pytest.approx(len(LINE) * 0.001,
                                                             abs=1e-5)


def test_a_sample_shorter_than_the_service_takes_is_refused_before_the_call(
        tmp_path, service):
    """§PW482: a two-word tag came back a 422 after the call, and its price unseen."""
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.design(entity="bo", sample="Viglet Games!", root=str(tmp_path))
    assert refused.value.code == "fetch.sample-short"
    assert "13 characters" in refused.value.message
    assert "at least 100" in refused.value.message
    assert service.sent == []
    assert purchase.read(tmp_path) == []


def test_a_voice_call_is_quoted_from_the_entitys_own_sample(tmp_path, service):
    quoted = quote("voice.design", {"entity": "bo"}, root=str(tmp_path))
    assert quoted["price"] == pytest.approx(len(LINE) * 0.001, abs=1e-6)
    given = quote("voice.design", {"entity": "bo", "sample": "x" * 120},
                           root=str(tmp_path))
    assert given["price"] == pytest.approx(0.12, abs=1e-6)


def test_a_voice_no_person_accepted_is_not_kept(tmp_path, service):
    found = sound_buy.design(entity="bo", root=str(tmp_path))
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.choose(found["previews"][1], root=str(tmp_path))
    assert refused.value.code == "world.voice-unchosen"
    accepted(tmp_path, found["previews"][1], choice="look")
    with pytest.raises(PolyweaveError):
        sound_buy.choose(found["previews"][1], root=str(tmp_path))
    assert len(service.sent) == 1


def test_the_accepted_preview_is_saved_and_written_into_the_world(tmp_path, service):
    found = sound_buy.design(entity="bo", root=str(tmp_path))
    accepted(tmp_path, found["previews"][1])
    kept = sound_buy.choose(found["previews"][1], root=str(tmp_path))
    assert kept["voice"] == "saved-bo"
    assert service.sent[-1][1]["generated_voice_id"] == "g2"
    text = (tmp_path / "game.world.toml").read_text("utf-8")
    # The person's words and comments survive the write.
    assert "# as the owner said it" in text and text.startswith("# The cast.")
    voice = world.read(entity="bo", root=str(tmp_path))["entity"]["voice"]
    assert voice["id"] == "saved-bo"
    assert voice["chosen_from"] == found["previews"][1]
    assert voice["stability"] == 0.4


def test_a_preview_accepted_on_the_review_page_is_kept_as_a_sound(tmp_path, service):
    """The page judges a preview's sitting member, whose `line` is the words it says:
    that is a sound heard, not a line of the string table read (§PW411)."""
    import json

    from polyweave.loop import verdict

    found = sound_buy.design(entity="bo", root=str(tmp_path))
    sitting = json.loads((tmp_path / found["sitting"]).read_text("utf-8"))
    members = next(iter(sitting["families"].values()))["members"]
    assert members[0].get("line") and members[0].get("sound")
    verdict.judge(members[:1], "accept", "that's him", root=str(tmp_path))
    kept = sound_buy.choose(members[0]["new"], root=str(tmp_path))
    assert kept["voice"] == "saved-bo"


def test_the_previews_are_one_pick_and_the_pick_reaches_choose(tmp_path, service):
    """Spinhold's owner accepted all three studio voices, one card each (§PW547): the
    previews are now one family of alternatives, an accept names the one picked, and
    voice.choose takes the sitting and saves that one."""
    import json

    from polyweave.loop import review, verdict

    found = sound_buy.design(entity="bo", root=str(tmp_path))
    sitting = json.loads((tmp_path / found["sitting"]).read_text("utf-8"))
    [(family, laid)] = sitting["families"].items()
    assert family == "bo" and laid["pick"] == "one" and len(laid["members"]) == 3
    assert (tmp_path / laid["sheet"]).is_file()
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.choose(found["sitting"], root=str(tmp_path))
    assert refused.value.code == "world.voice-unchosen"
    body = {"sitting": found["sitting"], "family": "bo", "choice": "accept",
            "why": "the second"}
    with pytest.raises(PolyweaveError) as refused:
        review.answer(tmp_path, body)
    assert refused.value.code == "loop.pick-one"
    second = laid["members"][1]["name"]
    said = review.answer(tmp_path, {**body, "member": second})
    assert [one["name"] for one in said["members"]] == [second]
    assert said["answer"]["chosen"] == second
    assert verdict.answers(root=str(tmp_path))["answers"][-1]["chosen"] == second
    folder = found["sitting"].rsplit("/", 1)[0]
    kept = sound_buy.choose(folder, root=str(tmp_path))
    assert kept["from"] == found["previews"][1]
    assert service.sent[-1][1]["generated_voice_id"] == "g2"


def test_an_accepted_take_is_placed_where_the_game_loads_it(tmp_path, service):
    """Spinhold copied its studio tag and record by hand, and the copied record named
    the review copy, so provenance.verify never checked the game's file (§PW549)."""
    import json

    from polyweave.loop import review, verdict

    found = sound_buy.design(entity="bo", root=str(tmp_path))
    laid = json.loads((tmp_path / found["sitting"]).read_text("utf-8"))
    second = laid["families"]["bo"]["members"][1]["name"]
    with pytest.raises(PolyweaveError) as refused:
        verdict.place(found["sitting"], second, "game/audio/BO.mp3", root=str(tmp_path))
    assert refused.value.code == "verdict.unaccepted"
    review.answer(tmp_path, {"sitting": found["sitting"], "family": "bo",
                             "choice": "accept", "why": "the second", "member": second})
    with pytest.raises(PolyweaveError) as refused:
        verdict.place(found["sitting"], second, "../outside.mp3", root=str(tmp_path))
    assert refused.value.code == "verdict.bad-place"
    said = verdict.place(found["sitting"], second, "game/audio/BO.mp3",
                         root=str(tmp_path))
    game = tmp_path / "game" / "audio" / "BO.mp3"
    assert game.read_bytes() == (tmp_path / found["previews"][1]).read_bytes()
    record = provenance.read(str(game), root=tmp_path)
    assert record["artefact"]["path"] == "game/audio/BO.mp3"
    assert record["placed"]["from"] == found["previews"][1]
    assert record["placed"]["verdict"]["choice"] == "accept"
    assert any(one["role"] == "placed" for one in record["inputs"])
    # what it was bought in stays in the game's record
    assert record["details"]["voice_preview"] == "g2"
    assert said["placed"] == "game/audio/BO.mp3"
    checked = provenance.verify(root=str(tmp_path))
    assert "game/audio/BO.mp3" in json.dumps(checked)


def test_an_entity_with_no_voice_table_gets_one(tmp_path, service):
    from polyweave.layers.words.world import keep_voice

    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Ada"\nkind = "character"\n', encoding="utf-8")
    keep_voice("ada", "v-ada", "voices/ada_1.mp3", None, tmp_path)
    voice = world.read(entity="ada", root=str(tmp_path))["entity"]["voice"]
    assert voice == {"id": "v-ada", "chosen_from": "voices/ada_1.mp3"}


def test_a_locale_has_a_voice_born_in_it(tmp_path, service):
    """A voice designed in English read Portuguese with an English mouth (§PW413): a
    locale's own table is designed from, and the chosen preview is kept in it alone."""
    (tmp_path / "game.world.toml").write_text(
        WORLD + '\n[entity.bo.voice.pt_BR]\n'
        'description = "um capataz cansado, paulista"\n'
        f'sample = "{LINHA}"\n', encoding="utf-8")
    found = sound_buy.design(entity="bo", locale="pt_BR", root=str(tmp_path))
    assert service.sent[0][1]["voice_description"] == "um capataz cansado, paulista"
    assert service.sent[0][1]["text"] == LINHA
    assert all("bo_pt_BR_" in one for one in found["previews"])
    accepted(tmp_path, found["previews"][0])
    kept = sound_buy.choose(found["previews"][0], root=str(tmp_path))
    assert kept["locale"] == "pt_BR"
    bo = world.read(entity="bo", root=str(tmp_path))["entity"]
    assert bo["voice"]["pt_BR"]["id"] == "saved-bo"
    assert "id" not in {k for k, v in bo["voice"].items() if not isinstance(v, dict)}
    # The shared delivery carries into the locale's voice; its own words win there.
    spoken = world.voice_in(bo, "pt_BR")
    assert spoken["id"] == "saved-bo" and spoken["stability"] == 0.4
    assert world.voice_in(bo, "en").get("id") is None


def test_a_voice_with_no_words_cannot_be_designed(tmp_path, service):
    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Ada"\nkind = "character"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.design(entity="ada", root=str(tmp_path))
    assert refused.value.code == "world.no-voice"
    assert service.sent == []
