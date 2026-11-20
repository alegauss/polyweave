"""An editorial HTML card rendered to a still before the cut (§PW700).

Chromium is stood in for, as test_web_capture does: what is held is what capture.card
asks of the browser and what it does with the answers.
"""

from __future__ import annotations

import io
import sys
import types
from pathlib import Path

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store.card import card


class _Failure(Exception):
    pass


class _Said:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Page:
    def __init__(self, site):
        self.site = site
        self.handlers: dict[str, list] = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def goto(self, url, wait_until):
        self.site["visited"].append(url)
        for loaded in self.site["requests"]:
            for handler in self.handlers.get("request", []):
                handler(_Said(url=loaded))
        for text in self.site["errors"]:
            for handler in self.handlers.get("console", []):
                handler(_Said(type="error", text=text))

    def evaluate(self, script, arg=None):
        if "createTreeWalker" in script:
            return self.site["guarded"]
        if "fonts.ready" in script:
            return 1
        if "naturalWidth" in script:
            return []
        return [{"selector": one, "found": self.site["bounds"].get(one, [])}
                for one in arg]

    def screenshot(self, path):
        held = io.BytesIO()
        Image.new("RGB", (64, 36), (10, 20, 30)).save(held, format="PNG")
        Path(path).write_bytes(held.getvalue())


def _install(monkeypatch, site):
    class _Context:
        def new_page(self):
            return _Page(site)

        def close(self):
            pass

    class _Browser:
        version = "130.0.6723.31"

        def new_context(self, viewport, device_scale_factor):
            site["contexts"].append((viewport, device_scale_factor))
            return _Context()

        def close(self):
            pass

    class _Driver:
        chromium = _Said(launch=lambda: _Browser())

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = _Driver
    sync_api.Error = _Failure
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "cards").mkdir()
    (tmp_path / "cards" / "timeline.html").write_text("<h1>2003</h1>", "utf-8")
    (tmp_path / "cards" / "jakarta.woff2").write_bytes(b"wOF2")
    site = {
        "visited": [], "contexts": [], "errors": [], "guarded": [],
        "requests": [(tmp_path / "cards" / "jakarta.woff2").resolve().as_uri(),
                     "https://cdn.example/elsewhere.css"],
        "bounds": {".mark": [{"box": [1900, 40, 2010, 120], "visible": True}],
                   "h1": [{"box": [400, 400, 1600, 560], "visible": True}]},
    }
    _install(monkeypatch, site)
    return tmp_path, site


def test_a_card_is_rendered_and_recorded_with_what_it_loaded(project):
    root, site = project
    said = card("cards/timeline.html", "cards/timeline.png", viewport=[2048, 1152],
                bounds=["h1"], root=str(root))
    assert said["file"] == "cards/timeline.png" and said["passed"] is True
    assert site["contexts"] == [({"width": 2048, "height": 1152}, 1.0)]
    assert said["loaded"] == ["cards/jakarta.woff2"]
    record = provenance.read("cards/timeline.png", root)
    assert {one["role"] for one in record["inputs"]} == {"card", "loaded"}
    assert record["params"]["viewport"] == [2048, 1152]
    assert said["elements"][0]["box"] == [400, 400, 1600, 560]


def test_named_elements_are_held_to_a_safe_area(project):
    root, _ = project
    said = card("cards/timeline.html", "cards/t.png", viewport=[2048, 1152],
                bounds=[".mark", "h1", ".missing"], safe=[60, 60, 1988, 1092],
                root=str(root))
    assert said["passed"] is False
    assert said["missing"] == [".missing"]
    [crossed] = said["crossed"]
    assert crossed["selector"] == ".mark"
    assert crossed["crosses"][0] == {"area": "safe", "by_px": 22.0}


def test_a_card_that_broke_while_rendering_is_refused_and_not_written(project):
    root, site = project
    site["errors"].append("Failed to load font")
    with pytest.raises(PolyweaveError) as refused:
        card("cards/timeline.html", "cards/x.png", root=str(root))
    assert refused.value.code == "web.broken-page"
    assert not (root / "cards" / "x.png").exists()
    allowed = card("cards/timeline.html", "cards/x.png", allow=["font"],
                   root=str(root))
    assert allowed["file"] == "cards/x.png"


def test_a_missing_card_or_a_wrong_out_is_refused(project):
    root, _ = project
    with pytest.raises(PolyweaveError) as refused:
        card("cards/none.html", "cards/x.png", root=str(root))
    assert refused.value.code == "web.bad-card"
    with pytest.raises(PolyweaveError) as refused:
        card("cards/timeline.html", "cards/x.jpg", root=str(root))
    assert refused.value.code == "web.bad-card"


def test_an_unchanged_card_is_not_rendered_again_and_a_changed_font_is(project):
    root, site = project
    first = card("cards/timeline.html", "cards/c.png", bounds=["h1"], root=str(root))
    again = card("cards/timeline.html", "cards/c.png", bounds=["h1"], root=str(root))
    assert first["cached"] is False and again["cached"] is True
    assert len(site["contexts"]) == 1
    assert again["elements"] == first["elements"]
    (root / "cards" / "jakarta.woff2").write_bytes(b"wOF2-new")
    moved = card("cards/timeline.html", "cards/c.png", bounds=["h1"], root=str(root))
    assert moved["cached"] is False and len(site["contexts"]) == 2
    other = card("cards/timeline.html", "cards/c.png", bounds=["h1"], scale=2.0,
                 root=str(root))
    assert other["cached"] is False


def test_guarded_text_names_each_fault_by_element(project):
    root, site = project
    site["guarded"] = [
        {"selector": "h1", "index": 0, "text": "Nossa hist?ria",
         "box": [10, 10, 500, 80], "faults": ["broken letter"]},
        {"selector": "p", "index": 0, "text": "o WordPress cresceu",
         "box": [10, 90, 300, 200], "faults": ["'WordPress' split across lines"]},
        {"selector": "p", "index": 1, "text": "tudo certo",
         "box": [10, 210, 300, 260], "faults": []},
    ]
    said = card("cards/timeline.html", "cards/g.png", guard=["h1", "p"],
                names=["WordPress"], root=str(root))
    assert said["guarded"] == 3 and said["passed"] is False
    assert [(one["selector"], one["index"]) for one in said["faults"]] == [
        ("h1", 0), ("p", 0)]
    assert said["faults"][1]["faults"] == ["'WordPress' split across lines"]
