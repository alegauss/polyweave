"""An editorial HTML card rendered to a still before the cut (§PW700).

A narrated video's timeline cards, dates and diagrams are HTML a project writes with
its own fonts, and `video.cut` takes stills, not pages; `capture.web` films a visit.
Japode drew its cards through a Playwright script of its own. `capture.card` renders one
local HTML file at a declared viewport to a PNG, after its fonts and pictures have
loaded, refuses a page that broke on the way (a console error, a failed request, a
broken picture), records the page and every local file it loaded as inputs, and answers
the bounds of the elements the call names, held to a safe area by the same check
`video.safe_area` holds subtitles to.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import unquote, urlparse

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

from . import safe as safe_area
from . import web

#: Resolves once the page's fonts have loaded, so a card is never shot in a fallback.
_FONTS = "() => document.fonts.ready.then(() => document.fonts.size)"

#: Each selector's elements: their box in CSS px and whether a viewer sees them.
_BOUNDS = """(selectors) => selectors.map(selector => ({
  selector,
  found: Array.from(document.querySelectorAll(selector)).map(e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return {box: [r.left, r.top, r.right, r.bottom],
            visible: r.width > 0 && r.height > 0 && s.display !== 'none'
                     && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0};
  })
}))"""


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("web.bad-card", message, remedy, **extra)


def _local(url: str, here: Path) -> Path | None:
    """The file a file:// request read, where it is under the project."""
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    path = Path(unquote(parsed.path.lstrip("/") if ":" in parsed.path[:4]
                        else parsed.path))
    try:
        path.resolve().relative_to(here)
    except ValueError:
        return None
    return path if path.is_file() else None


def _shoot(page_url: str, target: Path, viewport: list, scale: float,
           selectors: list[str], allow: list[str]) -> tuple[list, list, list, str]:
    """The page rendered to `target`; what broke, the files it read, the bounds and
    the browser's version."""
    sync_playwright, failure = web._playwright()
    broken: list[str] = []
    read: list[str] = []
    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except failure as missing:
            raise PolyweaveError(
                "web.no-playwright", "Playwright is installed but its Chromium is not",
                "python -m playwright install chromium", detail=str(missing)[:400],
            ) from None
        version = browser.version
        context = browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=scale)
        page = context.new_page()

        def broke(said: str, against: str) -> None:
            if not web._allowed(against, allow):
                broken.append(said)

        page.on("console", lambda m: m.type == "error"
                and broke(f"console error: {m.text}", m.text))
        page.on("pageerror", lambda e: broke(f"page error: {e}", str(e)))
        page.on("requestfailed", lambda r: broke(f"request failed: {r.url}", r.url))
        page.on("request", lambda r: read.append(r.url))
        try:
            page.goto(page_url, wait_until="load")
            page.evaluate(_FONTS)
            broken += [f"broken image: {src}" for src in page.evaluate(
                web._BROKEN_IMAGES) if not web._allowed(src, allow)]
            bounds = page.evaluate(_BOUNDS, selectors) if selectors else []
            if not broken:
                page.screenshot(path=str(target))
        finally:
            context.close()
            browser.close()
    return broken, read, bounds, version


@operation("capture.card", kind="capture")
def card(
    html: Annotated[str, Param("the card's HTML file, under the project")],
    out: Annotated[str, Param("where the still is written, as a .png")],
    *,
    viewport: Annotated[
        list, Param("its width and height in CSS px, as [2048, 1152]")
    ] = (1920, 1080),
    scale: Annotated[float, Param("device pixels per CSS px", lo=0.5)] = 1.0,
    bounds: Annotated[
        list, Param("CSS selectors whose elements' boxes are answered")
    ] = None,
    safe: Annotated[
        list, Param("the box the named elements stay in, [l, t, r, b] in CSS px")
    ] = None,
    exclude: Annotated[
        dict, Param("areas the elements must not reach, by name, [l, t, r, b]")
    ] = None,
    allow: Annotated[
        list, Param("URL parts or console words that may fail without refusing it")
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Render a local HTML card to a still, after its fonts and pictures have loaded.

    A console error, a page error, a failed request or a broken picture refuses the
    still, unless `allow` names it. The record has the page and each local file it
    loaded (fonts, pictures, styles) as inputs, the viewport, scale and browser. Each
    selector in `bounds` answers every element it matches, with its box and whether a
    viewer sees it; a selector matching nothing is named in `missing`. Where `safe` or
    `exclude` is given, the elements are held to them as `video.safe_area` holds a
    subtitle line, and those that cross are in `crossed`.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    page = here / html
    if not page.is_file():
        raise _bad(f"there is no HTML card at {html}", "name an .html file under the "
                   "project", given=html)
    target = here / out
    if target.suffix.lower() != ".png":
        raise _bad(f"the still is written as {target.name}", "write it as a .png",
                   given="out")
    if not (isinstance(viewport, list | tuple) and len(viewport) == 2
            and all(isinstance(v, int) and v > 0 for v in viewport)):
        raise _bad(f"viewport is {viewport!r}", "give viewport as [width, height] in "
                   "whole CSS px")
    selectors = [str(one) for one in bounds or ()]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="polyweave-card-") as folder:
        shot = Path(folder) / "card.png"
        broken, read, found, version = _shoot(page.resolve().as_uri(), shot,
                                              list(viewport), float(scale), selectors,
                                              list(allow or ()))
        if broken:
            raise PolyweaveError(
                "web.broken-page",
                f"the card broke {len(broken)} time{'s' if len(broken) > 1 else ''} "
                f"while it rendered, first: {broken[0]}",
                "fix the card, or name what may fail in allow",
                detail="\n".join(broken[:20]),
            )
        target.write_bytes(shot.read_bytes())
    loaded = sorted({p for p in (_local(url, here) for url in read) if p is not None
                     and p.resolve() != page.resolve()})
    elements, missing, crossed = [], [], []
    kept = list(safe) if safe else [0, 0, viewport[0], viewport[1]]
    for one in found:
        if not one["found"]:
            missing.append(one["selector"])
        for n, element in enumerate(one["found"]):
            box = [round(v, 1) for v in element["box"]]
            elements.append({"selector": one["selector"], "index": n, "box": box,
                             "visible": element["visible"]})
            hits = safe_area._crossings(box, kept, exclude or {})
            if hits and (safe or exclude):
                crossed.append({"selector": one["selector"], "index": n, "box": box,
                                "crosses": hits})
    provenance.write(provenance.build(
        "capture", target,
        engine={"name": "capture.card", "browser": f"chromium {version}"},
        inputs=[provenance.source("card", page, here)]
        + [provenance.source("loaded", one, here) for one in loaded],
        params={"viewport": list(viewport), "scale": float(scale),
                "bounds": selectors, "safe": safe, "exclude": exclude},
        root=here), root=here)
    return {
        "file": provenance.relative(target, here),
        "loaded": [provenance.relative(one, here) for one in loaded],
        "elements": elements, "missing": missing, "crossed": crossed,
        "passed": not crossed and not missing,
    }
