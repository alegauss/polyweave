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

