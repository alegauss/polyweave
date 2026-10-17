"""One client for every paid service's plumbing (§PW516)."""

from __future__ import annotations

import ast
import io
import urllib.error
from pathlib import Path

import pytest

from polyweave.services import client

LAYERS = Path(client.__file__).parents[1] / "layers"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [one.name for one in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def test_no_layer_opens_a_connection_of_its_own():
    opening = [str(path.relative_to(LAYERS)) for path in LAYERS.rglob("*.py")
               if any(one.startswith("urllib.request") or one == "urllib.error"
                      for one in _imports(path))]
    assert opening == []


def test_the_sound_layer_buys_without_the_picture_layer():
    said = _imports(LAYERS / "sound" / "sound_buy.py")
    assert not [one for one in said if one.startswith("polyweave.layers.picture")]


class _Answer(io.BytesIO):
    status = 200
    headers = {"request-id": "r1"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_a_refusal_is_answered_with_its_status_and_body(monkeypatch):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 402, "no", {}, io.BytesIO(b"broke"))

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    said = client.send("https://example.test/x")
    assert (said.status, said.body) == (402, b"broke")


def test_an_answer_carries_the_agent_and_the_headers(monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen["agent"] = request.get_header("User-agent")
        return _Answer(b"ok")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    said = client.send("https://example.test/x", headers={"Api-Key": "k"})
    assert said.body == b"ok" and said.headers["request-id"] == "r1"
    assert seen["agent"] == client.AGENT


def test_nothing_answering_is_unreached_with_the_reason(monkeypatch):
    def unreachable(request, timeout):
        raise urllib.error.URLError("no such host")

    monkeypatch.setattr("urllib.request.urlopen", unreachable)
    with pytest.raises(client.Unreached) as refused:
        client.send("https://example.test/x")
    assert refused.value.reason == "no such host"
