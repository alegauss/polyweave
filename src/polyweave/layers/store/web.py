"""A web page filmed as a clip, from a declared visit (§PW690).

A product video's browser scenes were filmed by a project script around Playwright, so
the clip `video.cut` took had no record of the page and steps it came from, and every
project wrote the same broken-page checks again. The visit is declared in a
`*.web.toml`:

```toml
[web]
url      = "http://localhost:2710/"     # where the visit starts; a step's path joins it
viewport = [1920, 1080]                 # two whole numbers; the clip is this size
out      = "video/scenes/install.webm"  # beside the visit as <name>.webm otherwise
timeout  = 15                           # seconds one step may take
allow    = ["/api/session"]             # what may fail: part of a URL or console text

[[step]]
go = "/console"                         # a path under url, or a whole URL

[[step]]
type   = "#password"                    # a selector, and text or a secret's variable
secret = "SHIO_PASSWORD"

[[step]]
click = "text=Install"
name  = "install"                       # the step's mark, for a clip's start

[[step]]
wait  = "#review-queue"                 # a condition: a selector reaching a state
state = "visible"

[[step]]
scroll = 600                            # pixels down; negative is up
seconds = 3                             # eased over; 200 px a second if unset

[[step]]
hold = 2.0                              # seconds the camera stays on the page
```

A visit is filmed the way a person moves (§PW704): `[web] pointer = true` draws a
pointer and carries it to each click and type target along a minimum-jerk path, with a
ring where it clicks; a scroll eases over its `seconds`; typing goes at `pace`
characters a second (12 if unset) rather than appearing whole.

`capture.web` plays the steps in Chromium while Playwright records, and writes the WebM
with its record: the URL, the viewport and the steps, each with the second it started
and ended. A browser records in real time with no fixed tick, so there is no frame
sequence. A page that logs an error, fails a request, answers one with an error status
or shows a broken image is refused, unless `allow` names it.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urljoin

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

_WEB_KEYS = {"url", "viewport", "out", "timeout", "allow", "pointer", "instance"}
#: What each step does, by the key that names it; exactly one per step.
DOES = ("go", "click", "type", "wait", "scroll", "hold")
_STEP_KEYS = {*DOES, "text", "secret", "state", "name", "seconds", "pace"}

#: How a person moves, which a product scene is filmed at (§PW704): a scroll eases over
#: this many pixels a second, typing goes at this many characters a second, and the
#: drawn pointer travels to its target in this many seconds, at this many frames each.
SCROLL_SPEED = 200.0
TYPE_PACE = 12.0
POINTER_SECONDS = 0.6
FRAMES = 30

#: A pointer drawn over the page, since a headless browser draws none: it follows the
#: mouse, and a ring opens where a button goes down.
_POINTER = """(() => {
  const draw = () => {
    if (document.getElementById('polyweave-pointer')) return;
    const p = document.createElement('div');
    p.id = 'polyweave-pointer';
    p.style.cssText = 'position:fixed;left:0;top:0;width:18px;height:18px;'
      + 'z-index:2147483647;pointer-events:none;border-radius:50%;'
      + 'background:rgba(20,20,20,.85);border:2px solid #fff;'
      + 'transform:translate(-50%,-50%)';
    document.documentElement.appendChild(p);
    addEventListener('mousemove', e => { p.style.left = e.clientX + 'px';
                                         p.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;width:18px;height:18px;border-radius:50%;'
        + 'border:3px solid #ff5a1f;pointer-events:none;z-index:2147483646;'
        + 'transform:translate(-50%,-50%);transition:all .45s ease-out;opacity:1;'
        + `left:${e.clientX}px;top:${e.clientY}px`;
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.width = r.style.height = '56px';
                                    r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.documentElement) draw();
  addEventListener('DOMContentLoaded', draw);
})();"""


def _eased(t: float) -> float:
    """Minimum jerk: how far along a move is at `t` of its time, from rest to rest."""
    return t * t * t * (10 - 15 * t + 6 * t * t)
#: The states a wait may hold out for, as Playwright names them.
STATES = ("visible", "hidden", "attached", "detached")

_BROKEN_IMAGES = (
    "() => Array.from(document.images)"
    ".filter(i => i.complete && i.naturalWidth === 0)"
    ".map(i => i.currentSrc || i.src)"
)


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("web.bad-visit", message, remedy, **extra)


def _step(row: Any, at: str) -> dict:
    if not isinstance(row, dict):
        raise _bad(f"{at} is not a table", "write each step as a [[step]] table")
    unknown = sorted(set(row) - _STEP_KEYS)
    if unknown:
        raise _bad(
            f"{at} has {unknown[0]!r}, which a step does not take",
            f"name one of {', '.join(DOES)}, with text, secret, state or name",
            given=unknown[0],
            allowed=sorted(_STEP_KEYS),
        )
    does = [one for one in DOES if one in row]
    if len(does) != 1:
        raise _bad(
            f"{at} names {' and '.join(does) or 'nothing to do'}",
            f"give each step exactly one of {', '.join(DOES)}",
            at=at,
        )
    do = does[0]
    what = row[do]
    step: dict[str, Any] = {"do": do}
    if do in ("scroll", "hold"):
        if isinstance(what, bool) or not isinstance(what, int | float) or (
            do == "hold" and what <= 0
        ):
            raise _bad(
                f"{at}.{do} is {what!r}",
                "give scroll as pixels, and hold as seconds above 0",
                at=at,
            )
        step[do] = float(what)
    elif not isinstance(what, str) or not what.strip():
        raise _bad(
            f"{at}.{do} is {what!r}, and it is "
            + ("a path or URL" if do == "go" else "a selector"),
            # A wait given seconds is the sleep this format leaves out (§PW690).
            "wait on a selector reaching a state; hold is how long the camera stays"
            if do == "wait" else f"give {do} as a string",
            at=at,
        )
    else:
        step[do] = what
    if do == "type":
        given = [k for k in ("text", "secret") if k in row]
        if len(given) != 1:
            raise _bad(
                f"{at} types {'both text and a secret' if given else 'nothing'}",
                "give text, or secret naming the environment variable that holds it",
                at=at,
            )
        if not isinstance(row[given[0]], str):
            raise _bad(f"{at}.{given[0]} is not a string", f"give {given[0]} as text")
        step[given[0]] = row[given[0]]
    else:
        stray = [k for k in ("text", "secret") if k in row]
        if stray:
            raise _bad(f"{at} has {stray[0]}, which only a type step takes",
                       f"drop {stray[0]}, or make the step a type", at=at)
    if "state" in row:
        if do != "wait" or row["state"] not in STATES:
            raise _bad(
                f"{at}.state is {row['state']!r}",
                f"give state on a wait, as one of {', '.join(STATES)}",
                at=at,
            )
        step["state"] = row["state"]
    elif do == "wait":
        step["state"] = "visible"
    if "name" in row:
        if not isinstance(row["name"], str) or not row["name"]:
            raise _bad(f"{at}.name is {row['name']!r}", "name a step with a word")
        step["name"] = row["name"]
    # How a person moves (§PW704): a scroll eased over seconds, typing at a pace.
    for key, owner, default in (("seconds", "scroll", None),
                                ("pace", "type", TYPE_PACE)):
        if key in row:
            value = row[key]
            if do != owner or isinstance(value, bool) or not isinstance(
                    value, int | float) or value <= 0:
                raise _bad(f"{at}.{key} is {value!r}",
                           f"give {key} on a {owner} step, as a number above 0", at=at)
            step[key] = float(value)
        elif do == owner:
            step[key] = (default if default is not None
                         else round(max(abs(step["scroll"]) / SCROLL_SPEED, 0.2), 3))
    return step


def read(source: Path) -> dict:
    """The visit a *.web.toml declares, checked before a browser opens."""
    if not source.is_file():
        raise PolyweaveError(
            "web.no-source",
            f"there is no visit at {source}",
            "name a *.web.toml under the project",
            given=str(source),
        )
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise PolyweaveError(
            "web.no-source",
            f"{source.name} is not TOML",
            "fix the line the detail names",
            detail=str(broken),
        ) from None
    unknown = sorted(set(declared) - {"web", "step"})
    if unknown:
        raise _bad(f"{source.name} has [{unknown[0]}]",
                   "declare only [web] and [[step]]",
                   given=unknown[0])
    web = declared.get("web", {})
    stray = sorted(set(web) - _WEB_KEYS)
    if stray:
        raise _bad(f"[web] has {stray[0]!r}, which it does not take",
                   f"use only {', '.join(sorted(_WEB_KEYS))}", given=stray[0],
                   allowed=sorted(_WEB_KEYS))
    url = web.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise _bad(f"[web] url is {url!r}", "give url as an http:// or https:// URL")
    viewport = web.get("viewport", [1920, 1080])
    if (
        not isinstance(viewport, list)
        or len(viewport) != 2
        or not all(isinstance(n, int) and not isinstance(n, bool) and n >= 64
                   for n in viewport)
    ):
        raise _bad(f"[web] viewport is {viewport!r}",
                   "give viewport as two whole numbers of pixels, at least 64")
    timeout = web.get("timeout", 15)
    if isinstance(timeout, bool) or not isinstance(timeout, int | float) or (
        timeout <= 0
    ):
        raise _bad(f"[web] timeout is {timeout!r}", "give timeout as seconds above 0")
    allow = web.get("allow", [])
    if not isinstance(allow, list) or not all(isinstance(a, str) and a for a in allow):
        raise _bad(f"[web] allow is {allow!r}",
                   "give allow as a list of URL parts or console words")
    out = web.get("out", "")
    if not isinstance(out, str):
        raise _bad(f"[web] out is {out!r}", "give out as a path ending in .webm")
    rows = declared.get("step", [])
    if not isinstance(rows, list) or not rows:
        raise _bad(f"{source.name} declares no [[step]]",
                   "declare at least one step; the first is usually a go")
    steps = [_step(row, f"step[{n}]") for n, row in enumerate(rows, 1)]
    for step in steps:
        if "secret" in step and step["secret"] not in os.environ:
            raise _bad(
                f"the environment has no {step['secret']}, which a type step reads",
                f"set {step['secret']} before the capture; its value is never recorded",
                given=step["secret"],
            )
    pointer = web.get("pointer", False)
    if not isinstance(pointer, bool):
        raise _bad(f"[web] pointer is {pointer!r}", "give pointer as true or false")
    instance = web.get("instance", "")
    if not isinstance(instance, str):
        raise _bad(f"[web] instance is {instance!r}",
                   "give instance as the *.instance.toml the visit films (§PW710)")
    return {"url": url, "viewport": viewport, "timeout": float(timeout),
            "allow": allow, "out": out, "steps": steps, "pointer": pointer,
            "instance": instance}


def _playwright() -> tuple[Any, type[Exception]]:
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise PolyweaveError(
            "web.no-playwright",
            "a web page is filmed with Playwright, which is not installed here",
            "pip install playwright (or polyweave-gamekit[web]), then "
            "python -m playwright install chromium",
        ) from None
    return sync_playwright, Error


def _allowed(what: str, allow: list[str]) -> bool:
    return any(part in what for part in allow)


def _point(page: Any, selector: str, at: dict, timeout_ms: float) -> None:
    """The drawn pointer carried to the middle of `selector` along a minimum-jerk path,
    from wherever it last was (§PW704)."""
    box = page.locator(selector).first.bounding_box(timeout=timeout_ms)
    if not box:
        return
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    frames = max(1, round(POINTER_SECONDS * FRAMES))
    for n in range(1, frames + 1):
        part = _eased(n / frames)
        page.mouse.move(at["x"] + (x - at["x"]) * part, at["y"] + (y - at["y"]) * part)
        page.wait_for_timeout(1000 / FRAMES)
    at.update(x=x, y=y)


def _play(page: Any, step: dict, base: str, timeout_ms: float,
          at: dict | None = None) -> None:
    """One step, as a person would make it: with `at`, the pointer is drawn and goes to
    each click and type first; a scroll eases over its seconds and typing keeps its
    pace (§PW704)."""
    do = step["do"]
    if do == "go":
        page.goto(urljoin(base, step["go"]), timeout=timeout_ms)
    elif do == "click":
        if at is not None:
            _point(page, step["click"], at, timeout_ms)
        page.click(step["click"], timeout=timeout_ms)
    elif do == "type":
        value = os.environ[step["secret"]] if "secret" in step else step["text"]
        if at is not None:
            _point(page, step["type"], at, timeout_ms)
        page.fill(step["type"], "", timeout=timeout_ms)
        page.type(step["type"], value, delay=1000 / step.get("pace", TYPE_PACE),
                  timeout=timeout_ms)
    elif do == "wait":
        page.wait_for_selector(step["wait"], state=step["state"], timeout=timeout_ms)
    elif do == "scroll":
        frames = max(1, round(step.get("seconds", 0.2) * FRAMES))
        done = 0.0
        for n in range(1, frames + 1):
            to = step["scroll"] * _eased(n / frames)
            page.mouse.wheel(0, to - done)
            done = to
            page.wait_for_timeout(1000 / FRAMES)
    else:  # hold: the camera stays on what the page shows, for the viewer
        page.wait_for_timeout(step["hold"] * 1000)


def _film(visit: dict, folder: Path) -> tuple[Path, list[dict], list[str], str]:
    """Play the visit in Chromium, recording; the video, each step's marks, what broke
    and the browser's version."""
    sync_playwright, failure = _playwright()
    width, height = visit["viewport"]
    size = {"width": width, "height": height}
    broken: list[str] = []
    marks: list[dict] = []
    allow = visit["allow"]

    def console(message: Any) -> None:
        if message.type == "error" and not _allowed(message.text, allow):
            broken.append(f"console error: {message.text}")

    def failed(request: Any) -> None:
        if not _allowed(request.url, allow):
            broken.append(f"request failed: {request.url}")

    def answered(response: Any) -> None:
        if response.status >= 400 and not _allowed(response.url, allow):
            broken.append(f"{response.status} from {response.url}")

    def thrown(error: Any) -> None:
        if not _allowed(str(error), allow):
            broken.append(f"page error: {error}")

    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except failure as missing:
            raise PolyweaveError(
                "web.no-playwright",
                "Playwright is installed but its Chromium is not",
                "python -m playwright install chromium",
                detail=str(missing)[:400],
            ) from None
        version = browser.version
        context = browser.new_context(
            viewport=size, record_video_dir=str(folder), record_video_size=size
        )
        at = None
        if visit.get("pointer"):
            # Before the page's own scripts, so every page of the visit draws it.
            context.add_init_script(_POINTER)
            at = {"x": width / 2, "y": height / 2}
        page = context.new_page()
        page.on("console", console)
        page.on("pageerror", thrown)
        page.on("requestfailed", failed)
        page.on("response", answered)
        began = time.monotonic()
        try:
            for n, step in enumerate(visit["steps"], 1):
                start = time.monotonic() - began
                try:
                    _play(page, step, visit["url"], visit["timeout"] * 1000, at)
                except failure as stopped:
                    raise PolyweaveError(
                        "web.step-failed",
                        f"step {n} ({step['do']} {step[step['do']]!r}) did not finish",
                        "read the detail, which is what the browser said; a wait or "
                        "click that timed out names a selector the page never showed",
                        at=f"step[{n}]",
                        detail=str(stopped).splitlines()[0][:400],
                    ) from None
                images = page.evaluate(_BROKEN_IMAGES)
                broken += [f"broken image: {src}" for src in images
                           if not _allowed(src, allow)]
                # A secret is kept by its variable's name; its value is read only
                # when typed, so it never reaches the step, the record or an answer.
                marks.append({**step, "at": round(start, 3),
                              "done": round(time.monotonic() - began, 3)})
            video = page.video
        finally:
            context.close()
            browser.close()
        recorded = Path(video.path())
    return recorded, marks, list(dict.fromkeys(broken)), version


@operation("capture.web", kind="capture")
def web(
    source: Annotated[str, Param("the *.web.toml, as a path under the project")],
    *,
    out: Annotated[
        str, Param("where the WebM is written; the visit's own out otherwise")
    ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Film a web page as a clip, playing the declared steps in a recording browser.

    The steps go to a page, click, type text or a secret from the environment, wait on
    a selector, scroll and hold. A console error, a failed request, an error status or
    a broken image refuses the clip unless allow names it. The WebM is a video clip for
    video.cut, and its record names the URL, the steps and when each one ran.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    path = Path(source) if Path(source).is_absolute() else here / source
    visit = read(path)
    where = (
        out
        or visit["out"]
        or path.with_name(path.name.removesuffix(".web.toml") + ".webm").as_posix()
    )
    target = Path(where) if Path(where).is_absolute() else here / where
    if target.suffix.lower() != ".webm":
        raise _bad(f"the clip is written as {target.name}", "write it as a .webm",
                   given="out")
    filmed, fixture = None, None
    if visit.get("instance"):
        # The instance it films, ready and named by its containers and images; it is
        # never reset here, only by capture.instance (§PW710).
        from . import instance as fixtures

        fixture = fixtures.read(here / visit["instance"], here)
        fixtures.waited(fixture)
        filmed = {"fixture": visit["instance"], "project": fixture["project"],
                  "containers": fixtures.identity(fixture)}
    with tempfile.TemporaryDirectory(prefix="polyweave-web-") as folder:
        recorded, marks, broken, version = _film(visit, Path(folder))
        if broken:
            raise PolyweaveError(
                "web.broken-page",
                f"the page broke {len(broken)} time{'s' if len(broken) > 1 else ''} "
                f"while it was filmed, first: {broken[0]}",
                "fix the page, or name what may fail in [web] allow",
                detail="\n".join(broken[:20]),
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(recorded), target)
    seconds = marks[-1]["done"] if marks else 0.0
    record = provenance.write(
        provenance.build(
            "capture",
            target,
            engine={"name": "capture.web", "browser": f"chromium {version}"},
            inputs=[provenance.source("visit", path, root=here)]
            + ([provenance.source("instance", fixture["source"], root=here),
                provenance.source("compose", fixture["compose"], root=here)]
               if fixture else []),
            params={
                "visit": provenance.relative(path, here),
                "url": visit["url"],
                "viewport": visit["viewport"],
                "allow": visit["allow"],
                "steps": marks,
                **({"instance": filmed} if filmed else {}),
            },
            root=here,
        ),
        root=here,
    )
    named = {m["name"]: m["at"] for m in marks if "name" in m}
    return {
        "file": provenance.relative(target, here),
        "record": provenance.relative(Path(record), here),
        "steps": len(marks),
        "seconds": seconds,
        **({"marks": named} if named else {}),
        "says": f"{len(marks)} steps over {seconds:g}s; cut it with video.cut as "
        f'video = "{provenance.relative(target, here)}"',
    }
