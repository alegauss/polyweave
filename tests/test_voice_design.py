"""An entity's voice, designed from words and chosen by a person (§PW321).

The service is never reached: its JSON transport is replaced, as the sound tests replace
theirs. A person's verdict is written into the preview's record as the review page
writes it, since only a person may choose a voice.
"""

from __future__ import annotations

import base64
import shutil

import pytest

from polyweave import provenance, purchase, sound_buy, world
from polyweave.errors import PolyweaveError
from test_sound_buy import PROJECT, mp3

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")

DESIGNED = PROJECT.replace(
    '"eleven_text_to_sound_v2" = 0.05',
    '"eleven_text_to_sound_v2" = 0.05, '
    '"eleven_multilingual_ttv_v2" = { per = "character", rate = 0.001 }',
)

WORLD = (
    "# The cast.\n[entity.bo]\nname = \"Bo\"\nkind = \"character\"\n\n"
    "[entity.bo.voice]\n"
    "description = \"a dry, tired foreman in his fifties\"  # as the owner said it\n"
    "sample = \"Shift's over. Go home.\"\nstability = 0.4\n"
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
    monkeypatch.setattr(sound_buy, "_used", lambda base, key: None)
    fake = Service(mp3(tmp_path))
    monkeypatch.setattr(sound_buy, "_asked", fake.asked)
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
    assert sent["text"] == "Shift's over. Go home."
    assert len(found["previews"]) == 3
    assert found["sitting"]
    spent = purchase.read(tmp_path)
    assert len(spent) == 3
    assert sum(e["credits"] for e in spent) == pytest.approx(22 * 0.001, abs=1e-5)


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


def test_an_entity_with_no_voice_table_gets_one(tmp_path, service):
    from polyweave.world import keep_voice

    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Ada"\nkind = "character"\n', encoding="utf-8")
    keep_voice("ada", "v-ada", "voices/ada_1.mp3", None, tmp_path)
    voice = world.read(entity="ada", root=str(tmp_path))["entity"]["voice"]
    assert voice == {"id": "v-ada", "chosen_from": "voices/ada_1.mp3"}


def test_a_voice_with_no_words_cannot_be_designed(tmp_path, service):
    (tmp_path / "game.world.toml").write_text(
        '[entity.ada]\nname = "Ada"\nkind = "character"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.design(entity="ada", root=str(tmp_path))
    assert refused.value.code == "world.no-voice"
    assert service.sent == []
