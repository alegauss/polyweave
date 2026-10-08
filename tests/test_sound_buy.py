"""Buying a realistic effect under the project's ceiling (§PW190).

The service is never reached: its transport is replaced, as the picture and mesh tests
replace theirs, so a test spends nothing and can say exactly what would have been sent.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import urllib.error
import urllib.request

import pytest

from polyweave import purchase, sound_buy
from polyweave.errors import PolyweaveError
from test_sound import tone, written

PROJECT = (
    '[paths]\naudio = "game/audio"\n\n'
    '[sound.effects]\ncues = ["footsteps"]\n\n'
    '[service.elevenlabs]\nbase = "https://api.elevenlabs.io"\n'
    'key_env = "POLYWEAVE_TEST_E"\nprices = { "eleven_text_to_sound_v2" = 0.05 }\n\n'
    '[budget.elevenlabs]\namount = 1.0\nunit = "USD"\nexpires = "2099-12-31"\n'
)


def mp3(tmp_path) -> bytes:
    """A real MP3, made by ffmpeg from a tone, as the service would answer."""
    wav = written(tmp_path / "t.wav", tone(1.0))
    done = subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-i", str(wav), "-f", "mp3", "pipe:1"],
        capture_output=True, check=True,
    )
    return done.stdout


class Service:
    """The service as a test sees it: what was sent, and a fixed answer."""

    def __init__(self, answer: bytes = b"ID3fake-mp3"):
        self.answer, self.sent = answer, []

    def post(self, url, key, payload):
        self.sent.append((url, key, dict(payload)))
        return self.answer, "req-1"


@pytest.fixture
def service(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_E", "sk-sound")
    fake = Service()
    monkeypatch.setattr(sound_buy, "_post", fake.post)
    return fake


def test_the_request_carries_the_words_the_model_and_the_shape(tmp_path, service):
    found = sound_buy.buy(prompt="footsteps on gravel", out="sfx/steps.mp3",
                          seconds=2.0, loop=True, root=str(tmp_path))
    url, key, sent = service.sent[0]
    assert url == "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128"
    assert key == "sk-sound"
    assert sent == {
        "text": "footsteps on gravel", "model_id": "eleven_text_to_sound_v2",
        "prompt_influence": 0.3, "duration_seconds": 2.0, "loop": True,
    }
    assert found["file"] == "sfx/steps.mp3"
    assert (tmp_path / "sfx" / "steps.mp3").read_bytes() == b"ID3fake-mp3"


def test_the_purchase_is_ledgered_as_a_sound_at_its_quoted_price(tmp_path, service):
    sound_buy.buy(prompt="glass breaking", out="sfx/glass.mp3", root=str(tmp_path))
    [entry] = purchase.read(tmp_path)
    assert entry["bought"] == "sound"
    assert entry["service"] == "elevenlabs"
    assert entry["task_id"] == "elevenlabs:req-1"


def test_a_spend_past_the_ceiling_never_reaches_the_service(tmp_path, service):
    (tmp_path / "polyweave.toml").write_text(
        PROJECT.replace("amount = 1.0", "amount = 0.01"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        sound_buy.buy(prompt="rain", out="sfx/rain.mp3", root=str(tmp_path))
    assert caught.value.code == "fetch.over-budget"
    assert service.sent == []
    assert purchase.read(tmp_path) == []


def test_a_model_with_no_price_row_is_refused_before_sending(tmp_path, service):
    with pytest.raises(PolyweaveError) as caught:
        sound_buy.buy(prompt="rain", out="sfx/rain.mp3", model="eleven_v9",
                      root=str(tmp_path))
    assert caught.value.code == "fetch.unpriced"
    assert service.sent == []


def test_no_budget_is_no_spend(tmp_path, service):
    closed = PROJECT.split("[budget.elevenlabs]")[0]
    (tmp_path / "polyweave.toml").write_text(closed, encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        sound_buy.buy(prompt="rain", out="sfx/rain.mp3", root=str(tmp_path))
    assert caught.value.code == "fetch.budget-closed"
    assert service.sent == []


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg to transcode with")
def test_a_sound_for_a_declared_cue_lands_there_in_its_format(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_E", "sk-sound")
    monkeypatch.setattr(sound_buy, "_post", Service(mp3(tmp_path)).post)
    found = sound_buy.buy(prompt="footsteps on gravel", cue="footsteps",
                          root=str(tmp_path))
    assert found["file"] == "game/audio/footsteps.wav"
    assert (tmp_path / "game" / "audio" / "footsteps.wav").read_bytes()[:4] == b"RIFF"
    assert found["measured"]["duration"] == pytest.approx(1.0, abs=0.1)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"out": None, "cue": None}, "fetch.missing-field"),
        ({"out": "sfx/a.mp3", "cue": "footsteps"}, "fetch.missing-field"),
        ({"out": None, "cue": "thunder"}, "sound.unknown-cue"),
        ({"out": "sfx/a.png", "cue": None}, "fetch.missing-field"),
        ({"out": "sfx/a.mp3", "cue": None, "prompt": ""}, "fetch.missing-field"),
    ],
)
def test_a_sound_with_nowhere_to_land_is_refused_before_spending(
    tmp_path, service, kwargs, code
):
    asked = {"prompt": "rain", **kwargs}
    with pytest.raises(PolyweaveError) as caught:
        sound_buy.buy(**asked, root=str(tmp_path))
    assert caught.value.code == code
    assert service.sent == []


@pytest.mark.parametrize(
    ("status", "code"),
    [(422, "fetch.prompt-refused"), (429, "fetch.rate-limited"),
     (401, "fetch.service-error")],
)
def test_a_refusal_from_the_service_is_a_code(monkeypatch, status, code):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, status, "no", {},
                                     io.BytesIO(b'{"detail": "no"}'))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(PolyweaveError) as caught:
        sound_buy._post("https://api.elevenlabs.io/v1/sound-generation", "k", {})
    assert caught.value.code == code



BY_CHARACTER = PROJECT.replace(
    '"eleven_text_to_sound_v2" = 0.05',
    '"eleven_text_to_sound_v2" = { per = "character", rate = 0.001 }',
)


@pytest.fixture
def counted(tmp_path, monkeypatch, service):
    """The project priced by the character, and the service's usage readings."""
    (tmp_path / "polyweave.toml").write_text(BY_CHARACTER, encoding="utf-8")
    readings = []
    monkeypatch.setattr(sound_buy, "_used", lambda base, key: readings.pop(0))
    return readings


def test_a_price_by_the_character_is_the_rate_times_the_words(tmp_path, counted):
    """§PW320: a short tag and a paragraph were priced the same."""
    counted.extend([None, None])
    sound_buy.buy(prompt="rain on a tin roof", out="sfx/rain.mp3", root=str(tmp_path))
    [entry] = purchase.read(tmp_path)
    assert entry["credits"] == pytest.approx(18 * 0.001)
    assert entry["measured"] is False


def test_a_spend_by_the_character_is_measured_where_the_service_says(
    tmp_path, counted
):
    counted.extend([1000, 1025])
    sound_buy.buy(prompt="rain on a tin roof", out="sfx/rain.mp3", root=str(tmp_path))
    [entry] = purchase.read(tmp_path)
    assert entry["credits"] == pytest.approx(25 * 0.001)
    assert entry["expected_credits"] == pytest.approx(18 * 0.001)
    assert entry["measured"] is True


def test_a_long_text_over_the_ceiling_is_refused_with_its_count(tmp_path, counted):
    with pytest.raises(PolyweaveError) as caught:
        sound_buy.buy(prompt="x" * 2000, out="sfx/long.mp3", root=str(tmp_path))
    assert caught.value.code == "fetch.over-budget"
    assert "2000 characters at 0.001 each" in caught.value.message


def test_a_quote_counts_the_text_the_call_would_send(tmp_path, counted):
    said = purchase.quote("sound.buy", {"prompt": "x" * 40}, root=str(tmp_path))
    assert said["price"] == pytest.approx(0.04)
    assert (said["per"], said["count"], said["rate"]) == ("character", 40, 0.001)
    with pytest.raises(PolyweaveError) as refused:
        purchase.quote("sound.buy", {}, root=str(tmp_path))
    assert refused.value.code == "fetch.uncounted"


@pytest.mark.parametrize(
    "row", ['{ per = "word", rate = 0.1 }', '{ per = "character" }',
            '{ per = "character", rate = 0.1, cap = 3 }'],
)
def test_a_row_by_the_unit_that_says_it_wrong_is_refused(tmp_path, row):
    from polyweave.config import load

    (tmp_path / "polyweave.toml").write_text(
        PROJECT.replace("0.05", row), encoding="utf-8"
    )
    with pytest.raises(PolyweaveError) as refused:
        load(tmp_path)
    assert refused.value.code == "config.bad-type"


SPEECH = PROJECT.replace(
    '"eleven_text_to_sound_v2" = 0.05',
    '"eleven_text_to_sound_v2" = 0.05, '
    '"eleven_multilingual_v2" = { per = "character", rate = 0.0003 }',
)


@pytest.fixture
def voiced(tmp_path, monkeypatch, service):
    (tmp_path / "polyweave.toml").write_text(SPEECH, encoding="utf-8")
    monkeypatch.setattr(sound_buy, "_used", lambda base, key: None)
    return service


def test_a_line_is_spoken_in_the_voice_named(tmp_path, voiced):
    """§PW314: no operation spoke a line, so a studio tag could not be voiced."""
    found = sound_buy.speak(text="Viglet Games", voice="voice/7", out="vo/tag.mp3",
                            stability=0.4, speed=0.9, root=str(tmp_path))
    url, key, sent = voiced.sent[0]
    assert url == (
        "https://api.elevenlabs.io/v1/text-to-speech/voice%2F7"
        "?output_format=mp3_44100_128"
    )
    assert sent == {
        "text": "Viglet Games", "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "speed": 0.9},
    }
    assert found["file"] == "vo/tag.mp3"
    [entry] = purchase.read(tmp_path)
    assert entry["credits"] == pytest.approx(12 * 0.0003)
    assert entry["prompt"] == "Viglet Games"


def test_the_record_keeps_what_makes_the_take_again(tmp_path, voiced):
    from polyweave import provenance

    sound_buy.speak(
        text="Go", voice="v1", out="vo/go.mp3", style=0.2, root=str(tmp_path)
    )
    record = provenance.read(tmp_path / "vo" / "go.mp3")
    details = record["details"]
    assert details["voice"] == "v1"
    assert details["delivery"] == {"style": 0.2}
    assert record["engine"]["model"] == "eleven_multilingual_v2"


@pytest.mark.parametrize("text, voice", [("", "v1"), ("Go", None)])
def test_a_line_without_words_or_a_voice_is_refused_before_sending(
    tmp_path, voiced, text, voice
):
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.speak(text=text, voice=voice, out="vo/x.mp3", root=str(tmp_path))
    assert refused.value.code == "fetch.missing-field"
    assert voiced.sent == []


def test_a_spoken_line_is_quoted_by_its_characters(tmp_path, voiced):
    said = purchase.quote("sound.speak", {"text": "x" * 100}, root=str(tmp_path))
    assert said["price"] == pytest.approx(0.03)
    assert said["count"] == 100


WORLD = (
    '[entity.ada]\nname = "Captain Ada"\nkind = "character"\n\n'
    '[entity.ada.voice]\nid = "ada-voice"\nstability = 0.3\nspeed = 0.9\n\n'
    '[entity.bo]\nname = "Bo"\nkind = "character"\n\n'
    '[entity.bo.voice]\ndescription = "a dry, tired foreman"\n'
)


@pytest.fixture
def cast(tmp_path, voiced):
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    return voiced


def test_an_entitys_line_is_spoken_in_the_voice_the_world_gives_it(tmp_path, cast):
    """§PW321: each line sounded like whichever voice its call happened to name."""
    sound_buy.speak(text="Hold fast", entity="ada", out="vo/ada.mp3", speed=1.1,
                    root=str(tmp_path))
    url, _, sent = cast.sent[0]
    assert "/v1/text-to-speech/ada-voice?" in url
    # The voice's own delivery, and the line's override of one setting.
    assert sent["voice_settings"] == {"stability": 0.3, "speed": 1.1}


def test_a_changed_voice_makes_its_lines_outdated_and_a_look_does_not(tmp_path, cast):
    from polyweave import provenance

    sound_buy.speak(text="Hold fast", entity="ada", out="vo/ada.mp3",
                    root=str(tmp_path))
    world = tmp_path / "game.world.toml"
    world.write_text(WORLD + '\n[entity.ada.look]\ndescription = "tall"\n', "utf-8")
    assert provenance.outdated(root=str(tmp_path))["outdated"] == []
    world.write_text(WORLD.replace('"ada-voice"', '"other"'), "utf-8")
    stale = provenance.outdated(root=str(tmp_path))["outdated"]
    assert [one["artefact"] for one in stale] == ["vo/ada.mp3"]


def test_an_entity_with_no_voice_id_is_refused_not_guessed(tmp_path, cast):
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.speak(text="Shift's over", entity="bo", out="vo/bo.mp3",
                        root=str(tmp_path))
    assert refused.value.code == "world.no-voice"
    assert "only words about one" in refused.value.message
    assert cast.sent == []


def test_a_call_that_names_another_voice_for_an_entity_is_refused(tmp_path, cast):
    with pytest.raises(PolyweaveError) as refused:
        sound_buy.speak(text="Hold fast", entity="ada", voice="impostor",
                        out="vo/ada.mp3", root=str(tmp_path))
    assert refused.value.code == "world.voice-mismatch"
    assert cast.sent == []


def test_a_voice_the_world_says_wrong_is_found(tmp_path):
    from polyweave import world

    (tmp_path / "game.world.toml").write_text(
        WORLD.replace("speed = 0.9", "speed = 3\npitch = 2"), encoding="utf-8"
    )
    found = world.validate(root=str(tmp_path))
    codes = sorted(one["code"] for one in found["findings"])
    assert codes == ["world.bad-value", "world.unknown-key"]
