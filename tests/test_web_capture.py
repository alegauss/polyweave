"""A web page filmed as a clip from a declared visit (§PW690).

The browser is a stand-in for Playwright's sync API, so these run without one; what is
held is what capture.web asks of it and what it does with the answers.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store import web


class _Failure(Exception):
    pass


class _Site:
    """What the stand-in browser shows: selectors present, and what a visit sets off."""

    def __init__(self, shows=(), events=(), images=(), chromium=True):
        self.shows = set(shows)
        self.events = list(events)
        self.images = list(images)
        self.chromium = chromium
        self.visited: list[str] = []
        self.typed: dict[str, str] = {}
        self.waited: list[tuple[str, str]] = []
        self.held: list[float] = []
        self.contexts: list[dict] = []


class _Said:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Page:
    def __init__(self, site: _Site, folder: Path):
        self.site = site
        self.handlers: dict[str, list] = {}
        self.mouse = _Said(wheel=lambda x, y: None)
        self.video = _Said(path=lambda: str(folder / "page.webm"))

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def _fire(self, event, value):
        for handler in self.handlers.get(event, []):
            handler(value)

    def goto(self, url, timeout):
        self.site.visited.append(url)
        for kind, *rest in self.site.events:
            if kind == "console":
                self._fire("console", _Said(type="error", text=rest[0]))
            elif kind == "response":
                self._fire("response", _Said(url=rest[0], status=rest[1]))
            elif kind == "requestfailed":
                self._fire("requestfailed", _Said(url=rest[0]))

    def _there(self, selector):
        if selector not in self.site.shows:
            raise _Failure(f"Timeout 1000ms exceeded.\nwaiting for {selector!r}")

    def click(self, selector, timeout):
        self._there(selector)

    def fill(self, selector, value, timeout):
        self._there(selector)
        self.site.typed[selector] = value

    def wait_for_selector(self, selector, state, timeout):
        self._there(selector)
        self.site.waited.append((selector, state))

    def wait_for_timeout(self, ms):
        self.site.held.append(ms)

    def evaluate(self, script):
        return self.site.images


class _Context:
    def __init__(self, site, folder):
        self.folder = folder
        self.page = _Page(site, folder)

    def new_page(self):
        return self.page

    def close(self):
        (self.folder / "page.webm").write_bytes(b"\x1aE\xdf\xa3webm")


class _Browser:
    version = "130.0.6723.31"

    def __init__(self, site):
        self.site = site

    def new_context(self, viewport, record_video_dir, record_video_size):
        self.site.contexts.append({"viewport": viewport, "size": record_video_size})
        return _Context(self.site, Path(record_video_dir))

    def close(self):
        pass


def _install(monkeypatch, site: _Site) -> None:
    def launch():
        if not site.chromium:
            raise _Failure("Executable doesn't exist at /ms-playwright/chromium")
        return _Browser(site)

    class _Driver:
        chromium = _Said(launch=launch)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = _Driver
    sync_api.Error = _Failure
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)


def _project(tmp_path: Path, visit: str) -> Path:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "scene.web.toml").write_text(visit, encoding="utf-8")
    return tmp_path


_VISIT = """
[web]
url = "http://localhost:2710/"
viewport = [1280, 720]
allow = ["/api/session"]

[[step]]
go = "/console"

[[step]]
type = "#password"
secret = "PW690_PASSWORD"

[[step]]
click = "text=Install"
name = "install"

[[step]]
wait = "#review-queue"

[[step]]
scroll = 600

[[step]]
hold = 1.5
"""

_SHOWS = ("#password", "text=Install", "#review-queue")


def test_a_visit_is_filmed_with_its_steps_marked_and_its_secret_kept_by_name(
    tmp_path, monkeypatch
):
    here = _project(tmp_path, _VISIT)
    monkeypatch.setenv("PW690_PASSWORD", "hunter2-not-for-the-record")
    site = _Site(shows=_SHOWS, events=[("response", "http://x/api/session", 401)])
    _install(monkeypatch, site)

    said = web.web("scene.web.toml", root=str(here))

    assert said["file"] == "scene.webm"
    assert (here / "scene.webm").read_bytes().startswith(b"\x1aE\xdf\xa3")
    assert site.visited == ["http://localhost:2710/console"]
    assert site.typed == {"#password": "hunter2-not-for-the-record"}
    assert site.waited == [("#review-queue", "visible")]
    assert site.held == [1500.0]
    assert site.contexts == [{"viewport": {"width": 1280, "height": 720},
                              "size": {"width": 1280, "height": 720}}]
    assert said["steps"] == 6 and "install" in said["marks"]
    record_text = (here / said["record"]).read_text(encoding="utf-8")
    assert "hunter2" not in record_text and "hunter2" not in json.dumps(said)
    record = json.loads(record_text)
    params = record["params"]
    assert params["url"] == "http://localhost:2710/"
    assert params["viewport"] == [1280, 720]
    assert [s["do"] for s in params["steps"]] == [
        "go", "type", "click", "wait", "scroll", "hold"]
    assert params["steps"][1]["secret"] == "PW690_PASSWORD"
    assert all(s["done"] >= s["at"] >= 0 for s in params["steps"])
    assert record["engine"]["name"] == "capture.web"
    assert [i["role"] for i in record["inputs"]] == ["visit"]


@pytest.mark.parametrize(
    "event, says",
    [
        (("response", "http://x/api/users", 500), "500 from http://x/api/users"),
        (("console", "Uncaught TypeError: x is undefined"), "console error"),
        (("requestfailed", "http://x/app.js"), "request failed"),
    ],
)
def test_a_page_that_breaks_is_refused_and_no_clip_is_kept(
    tmp_path, monkeypatch, event, says
):
    here = _project(tmp_path, _VISIT)
    monkeypatch.setenv("PW690_PASSWORD", "x")
    _install(monkeypatch, _Site(shows=_SHOWS, events=[event]))

    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))

    assert refused.value.code == "web.broken-page"
    assert says in refused.value.message
    assert not (here / "scene.webm").exists()


def test_a_broken_image_is_refused_unless_allow_names_it(tmp_path, monkeypatch):
    visit = '[web]\nurl = "https://example.test/"\n[[step]]\ngo = "/"\n'
    here = _project(tmp_path, visit)
    _install(monkeypatch, _Site(images=["https://example.test/missing.png"]))
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.broken-page"
    assert "broken image" in refused.value.message

    (here / "scene.web.toml").write_text(
        visit.replace("\n[[step]]", '\nallow = ["missing.png"]\n[[step]]'), "utf-8")
    assert web.web("scene.web.toml", root=str(here))["steps"] == 1


def test_a_wait_is_a_condition_never_seconds(tmp_path, monkeypatch):
    here = _project(tmp_path, '[web]\nurl = "http://a/"\n[[step]]\nwait = 2\n')
    _install(monkeypatch, _Site())
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.bad-visit"
    assert "hold" in refused.value.remedy


@pytest.mark.parametrize(
    "visit",
    [
        '[web]\nurl = "http://a/"\n',  # no step
        '[web]\nurl = "ftp://a/"\n[[step]]\ngo = "/"\n',
        '[web]\nurl = "http://a/"\nviewport = [1280]\n[[step]]\ngo = "/"\n',
        '[web]\nurl = "http://a/"\n[[step]]\ngo = "/"\nclick = "#b"\n',
        '[web]\nurl = "http://a/"\n[[step]]\ntype = "#q"\n',
        '[web]\nurl = "http://a/"\n[[step]]\ntype = "#q"\nsecret = "PW690_UNSET"\n',
        '[web]\nurl = "http://a/"\nout = "a.mp4"\n[[step]]\ngo = "/"\n',
        '[web]\nurl = "http://a/"\nspeed = 2\n[[step]]\ngo = "/"\n',
    ],
)
def test_a_visit_it_cannot_play_is_refused_before_a_browser_opens(
    tmp_path, monkeypatch, visit
):
    here = _project(tmp_path, visit)
    monkeypatch.delenv("PW690_UNSET", raising=False)
    site = _Site()
    _install(monkeypatch, site)
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.bad-visit"
    assert site.contexts == []


def test_a_step_the_page_never_shows_is_named(tmp_path, monkeypatch):
    here = _project(tmp_path,
                    '[web]\nurl = "http://a/"\n[[step]]\ngo = "/"\n'
                    '[[step]]\nclick = "#gone"\n')
    _install(monkeypatch, _Site())
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.step-failed"
    assert "step 2" in refused.value.message and "#gone" in refused.value.message


def test_without_playwright_or_its_browser_the_refusal_names_the_install(
    tmp_path, monkeypatch
):
    here = _project(tmp_path, '[web]\nurl = "http://a/"\n[[step]]\ngo = "/"\n')
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.no-playwright"
    assert "pip install playwright" in refused.value.remedy

    _install(monkeypatch, _Site(chromium=False))
    with pytest.raises(PolyweaveError) as refused:
        web.web("scene.web.toml", root=str(here))
    assert refused.value.code == "web.no-playwright"
    assert "playwright install chromium" in refused.value.remedy
