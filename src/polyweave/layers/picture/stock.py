"""Stock pictures from Pixabay, brought in with their page, author and licence (§PW673).

A picture found in a browser and saved by hand is recorded by nothing, so
`provenance.credits all=true` lists it under `unstated` and a release cannot say where
it came from. `stock.find` searches without downloading; `stock.fetch` takes one hit by
its id and writes a `fetch` record naming the source page, the author and the Pixabay
Content License, at no cost, so no budget is drawn.

The API's terms are the client's to keep: a search answer is kept for 24 hours and
asked again only after, a call over the rate waits for the window the service names
rather than answering 429, and a picture is downloaded, never linked. The key is read
from `[service.pixabay] key_env`, `PIXABAY_API_KEY` where the project declares no
table, and is never written to a record.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic
from polyweave.services import client

#: Where the service answers, and the variable its key is read from, where the project
#: declares no `[service.pixabay]`.
BASE = "https://pixabay.com/api/"
KEY_ENV = "PIXABAY_API_KEY"

#: The licence every Pixabay picture comes under; it owes no credit.
LICENCE = "Pixabay Content License"

#: How long a search answer is kept before it is asked again, as Pixabay's terms ask.
KEPT = 24 * 3600

#: The longest a call waits for the rate window to reopen before it gives up.
WAIT_MOST = 65

#: The filters the API takes, passed through as the service spells them, by kind.
FILTERS = ("image_type", "orientation", "min_width", "min_height", "colors",
           "category", "order")
VIDEO_FILTERS = ("video_type", "min_width", "min_height", "category", "order")

#: A video's renditions, largest first (§PW674).
RENDITIONS = ("large", "medium", "small", "tiny")

KINDS = ("picture", "video")


def _reached(config, kind: str = "picture") -> tuple[str, str]:
    about = {"base": BASE, "key_env": KEY_ENV,
             **{k: v for k, v in (config.services().get("pixabay") or {}).items() if v}}
    base, key = client.reached("pixabay", about)
    # Videos are searched at their own route beside the pictures' (§PW674).
    return (base.rstrip("/") + "/videos/" if kind == "video" else base), key


def _asked(base: str, key: str, query: dict, config) -> dict:
    """One search, from the kept answer where it is under a day old (§PW673)."""
    shown = sorted((k, str(v)) for k, v in query.items())
    kept = config.path("paths.work") / "stock" / (
        hashlib.sha256(json.dumps([base, shown]).encode()).hexdigest()[:20] + ".json")
    if kept.is_file() and time.time() - kept.stat().st_mtime < KEPT:
        return json.loads(kept.read_text(encoding="utf-8"))
    url = f"{base}?{urllib.parse.urlencode({'key': key, **dict(shown)})}"
    answer = client.send(url, timeout=client.TIMEOUT)
    if answer.status == 429:
        # Waited out rather than refused: the window the service names reopens.
        wait = float(answer.headers.get("X-RateLimit-Reset") or 60)
        time.sleep(min(wait, WAIT_MOST))
        answer = client.send(url, timeout=client.TIMEOUT)
    if answer.status >= 400:
        said = answer.body[:400].decode("utf-8", "replace")
        raise client.unpaid(answer.status, said) or PolyweaveError(
            "fetch.service-error",
            f"Pixabay answered {answer.status}",
            "read the detail; a 400 names a filter it does not take, and a 401 or 403 "
            f"a key it does not accept, read from {KEY_ENV} unless [service.pixabay] "
            "names another",
            detail=said,
        )
    found = json.loads(answer.body or b"{}")
    kept.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(kept, json.dumps(found))
    return found


def _hit(one: dict) -> dict:
    if "videos" in one:
        # Every rendition the service holds, so a caller picks by length and height
        # without a download (§PW674).
        return {
            "id": one.get("id"),
            "duration": one.get("duration"),
            "renditions": {
                name: {"width": got.get("width"), "height": got.get("height"),
                       "bytes": got.get("size")}
                for name, got in _renditions(one).items()},
            "tags": one.get("tags", ""),
            "author": one.get("user", ""),
            "page": one.get("pageURL", ""),
        }
    return {
        "id": one.get("id"),
        "width": one.get("imageWidth"),
        "height": one.get("imageHeight"),
        "tags": one.get("tags", ""),
        "author": one.get("user", ""),
        "page": one.get("pageURL", ""),
        "preview": one.get("previewURL", ""),
    }


def _renditions(one: dict) -> dict:
    """A video hit's renditions that carry a link, largest first."""
    held = one.get("videos") or {}
    return {name: held[name] for name in RENDITIONS
            if (held.get(name) or {}).get("url")}


def _rendition(one: dict, rendition: str | None, height: int | None) -> tuple:
    """The rendition to download, and what the answer says where it is not the one
    asked: an empty one falls to the next one down, never in silence (§PW674)."""
    held = _renditions(one)
    if not held:
        return None, None
    if height:
        # The smallest at or above it: a 4K file a 1080p cut scales down is a gigabyte
        # nobody needed.
        tall = [n for n in reversed(RENDITIONS)
                if n in held and (held[n].get("height") or 0) >= height]
        if tall:
            return tall[0], None
        best = next(iter(held))
        return best, f"no rendition is {height} px tall; {best} is the tallest"
    asked = rendition or "large"
    for name in RENDITIONS[RENDITIONS.index(asked):]:
        if name in held:
            return name, (None if name == asked
                          else f"{asked} is empty for this video; {name} came instead")
    best = next(iter(held))
    return best, f"nothing at or below {asked}; {best} came instead"


@operation("stock.find", kind="fetch")
def find(
    words: Annotated[str, Param("what it shows: a quiet harbour at dawn")],
    *,
    kind: Annotated[str, Param("a picture or a video", choices=KINDS)] = "picture",
    filters: Annotated[
        dict, Param("the service's own filters: image_type, orientation, min_width…")
    ] = None,
    count: Annotated[int, Param("how many hits, 3 to 200", lo=3, hi=200)] = 20,
    root: Annotated[str, Param("the project the search is kept in")] = ".",
) -> dict:
    """Search Pixabay's photos, illustrations, vectors or videos, downloading nothing.

    Each hit's id, size, tags, author and page, for `stock.fetch`; a video's gives its
    duration and each rendition's size and bytes (§PW674). A search is kept a day.
    """
    config = load(root)
    taken = VIDEO_FILTERS if kind == "video" else FILTERS
    stray = sorted(set(filters or {}) - set(taken))
    if stray:
        raise PolyweaveError(
            "stock.bad-filter",
            f"Pixabay takes no {kind} filter {stray[0]!r}",
            f"pass only {', '.join(taken)}",
            given=stray[0],
            allowed=taken,
        )
    base, key = _reached(config, kind)
    found = _asked(base, key, {"q": words, "safesearch": "true", "per_page": count,
                               **(filters or {})}, config)
    return {"words": words, "total": found.get("totalHits", 0),
            "hits": [_hit(one) for one in found.get("hits") or ()],
            "says": "take one with stock.fetch id=<id> out=<path>"}


@operation("stock.fetch", kind="fetch")
def fetch(
    id: Annotated[int, Param("the hit's id, as stock.find answered it")],  # noqa: A002
    out: Annotated[str, Param("where it is written, under the project")],
    *,
    kind: Annotated[str, Param("a picture or a video", choices=KINDS)] = "picture",
    rendition: Annotated[
        str, Param("a video's rendition; large if neither this nor height",
                   choices=RENDITIONS)
    ] = None,
    height: Annotated[
        int, Param("a video's smallest rendition at least this tall, in px")
    ] = None,
    root: Annotated[str, Param("the project it is brought into")] = ".",
) -> dict:
    """Bring one Pixabay picture or video in, recorded with its page and licence.

    A video is the `rendition` named, or the smallest `height` tall; an empty one falls
    to the next, with `fell` saying so (§PW674). The record names the page, the author
    and the licence, at no cost.
    """
    config = load(root)
    here = config.root
    base, key = _reached(config, kind)
    hits = _asked(base, key, {"id": int(id)}, config).get("hits") or []
    if not hits:
        raise PolyweaveError(
            "stock.no-hit",
            f"Pixabay has no {kind} {id}",
            "pass an id stock.find answered, with the same kind",
            given=str(id),
        )
    one = hits[0]
    fell, chosen = None, None
    if kind == "video":
        chosen, fell = _rendition(one, rendition, height)
        link = (one.get("videos") or {}).get(chosen, {}).get("url") if chosen else None
    else:
        link = one.get("imageURL") or one.get("fullHDURL") or one.get("largeImageURL")
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"Pixabay answered picture {id} with no link to download",
            "ask again; nothing was written",
            given=str(id),
        )
    target = Path(out) if Path(out).is_absolute() else here / out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(client.download(link))
    probed = {}
    if kind == "video":
        # What the cut and the reference layer read, in reference.register's shape.
        from polyweave.layers.reference.reference_register import _probe

        probed = _probe(target)
    record = provenance.write(provenance.build(
        "fetch", target,
        engine={"name": "pixabay"},
        params={"id": int(id), "kind": kind,
                "rendition": chosen or link.rsplit("/", 1)[-1]},
        measurements=probed,
        extra={"task_id": f"pixabay:{id}", "credits": 0.0, "licence": LICENCE,
               "credit": "", "source_page": one.get("pageURL", ""),
               "author": one.get("user", ""),
               "author_page": f"https://pixabay.com/users/{one.get('user', '')}-"
                              f"{one.get('user_id', '')}/",
               "tags": one.get("tags", "")},
        root=here,
    ), root=here)
    return {"file": provenance.relative(target, here), "id": int(id),
            "author": one.get("user", ""), "page": one.get("pageURL", ""),
            "licence": LICENCE, "record": provenance.relative(Path(record), here),
            **({"rendition": chosen, **probed} if kind == "video" else {}),
            **({"fell": fell} if fell else {})}
