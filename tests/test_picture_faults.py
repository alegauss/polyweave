"""A bought photo checked for the faults generated photos have (§PW696).

The local vision server is stood in for: `client.send` answers as Ollama's
/api/generate does, so what is held is what is asked, kept and marked.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture.faults import faults
from polyweave.services import client, purchase

PROJECT = '[vision]\nmodel = "qwen2.5vl:7b"\n'


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    (tmp_path / "art").mkdir()
    for name in ("physio.png", "office.png"):
        Image.new("RGB", (32, 32), (200, 180, 160)).save(tmp_path / "art" / name)
    drawn = (tmp_path / "art" / "physio.png").read_bytes()
    purchase.capture(drawn, out="art/physio.png", task_id="ideogram:g1",
                     bought="image", root=tmp_path)
    asked = []

    def send(url, **how):
        sent = json.loads(how["data"])
        asked.append((url, sent))
        found = ([{"kind": "fused-limbs", "where": "centre", "note": "arm into hands"},
                  {"kind": "not-a-kind", "where": "", "note": ""}]
                 if len(asked) == 1 else [])
        return client.Answer(200, json.dumps(
            {"response": json.dumps({"faults": found})}).encode(), {})

    monkeypatch.setattr(client, "send", send)
    return tmp_path, asked


def test_a_fault_is_named_kept_on_the_record_and_marks_the_purchase(project):
    root, asked = project
    said = faults(["art/physio.png", "art/office.png"], root=str(root))
    url, sent = asked[0]
    assert url == "http://localhost:11434/api/generate"
    assert sent["model"] == "qwen2.5vl:7b" and sent["images"]
    first, second = said["pictures"]
    assert [f["kind"] for f in first["faults"]] == ["fused-limbs"]
    assert first["usable"] is False and first["ledger"] is True
    assert "keep people apart" in first["advice"][0]
    assert second["usable"] is True and said["faulty"] == ["art/physio.png"]
    record = provenance.read("art/physio.png", root=root)
    assert record["faults"]["found"][0]["kind"] == "fused-limbs"
    [entry] = purchase.read(root)
    assert entry["usable"] is False and entry["faults"] == ["fused-limbs"]


def test_a_vision_server_elsewhere_is_refused_before_anything_is_sent(project):
    root, asked = project
    (root / "polyweave.toml").write_text(
        PROJECT + 'url = "https://api.example.com"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        faults(["art/physio.png"], root=str(root))
    assert refused.value.code == "picture.vision-not-local"
    assert asked == []


def test_no_model_named_says_how_to_add_one(project):
    root, _ = project
    (root / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        faults(["art/physio.png"], root=str(root))
    assert refused.value.code == "picture.no-vision"
    assert "ollama pull" in refused.value.remedy


def test_a_large_photo_goes_small_and_a_dropped_answer_is_asked_again(
    project, monkeypatch
):
    """§PW696: a 1536 px photo overflowed a local model's context, and its runner
    dropped one answer mid-set."""
    import base64
    import io

    root, _ = project
    Image.new("RGB", (1536, 1024), (90, 90, 90)).save(root / "art" / "big.png")
    calls = []

    def send(url, **how):
        sent = json.loads(how["data"])
        calls.append(sent)
        if len(calls) == 1:
            return client.Answer(500, b"runner dropped", {})
        return client.Answer(200, json.dumps({"response": '{"faults": []}'}).encode(),
                             {})

    monkeypatch.setattr(client, "send", send)
    said = faults(["art/big.png"], root=str(root))
    assert len(calls) == 2 and said["pictures"][0]["usable"] is True
    with Image.open(io.BytesIO(base64.b64decode(calls[1]["images"][0]))) as sent:
        assert max(sent.size) == 1024
    assert calls[1]["options"]["num_ctx"] == 8192


def test_a_picture_the_server_cannot_read_is_named_unchecked_not_passed(
    project, monkeypatch
):
    root, _ = project
    calls = []

    def send(url, **how):
        calls.append(1)
        if len(calls) == 1:
            return client.Answer(200, json.dumps(
                {"response": '{"faults": []}'}).encode(), {})
        return client.Answer(500, b"runner dropped", {})

    monkeypatch.setattr(client, "send", send)
    said = faults(["art/office.png", "art/physio.png"], root=str(root))
    assert [one["picture"] for one in said["pictures"]] == ["art/office.png"]
    assert said["unchecked"][0]["picture"] == "art/physio.png"
