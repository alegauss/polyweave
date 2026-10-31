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

#: The filters the API takes, passed through as the service spells them.
FILTERS = ("image_type", "orientation", "min_width", "min_height", "colors",
           "category", "order")


def _reached(config) -> tuple[str, str]:
    about = {"base": BASE, "key_env": KEY_ENV,
             **{k: v for k, v in (config.services().get("pixabay") or {}).items() if v}}
    return client.reached("pixabay", about)


def _asked(base: str, key: str, query: dict, config) -> dict:
    """One search, from the kept answer where it is under a day old (§PW673)."""
    shown = sorted((k, str(v)) for k, v in query.items())
    kept = config.path("paths.work") / "stock" / (
        hashlib.sha256(json.dumps(shown).encode()).hexdigest()[:20] + ".json")
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
    return {
        "id": one.get("id"),
        "width": one.get("imageWidth"),
        "height": one.get("imageHeight"),
        "tags": one.get("tags", ""),
        "author": one.get("user", ""),
        "page": one.get("pageURL", ""),
        "preview": one.get("previewURL", ""),
    }


@operation("stock.find", kind="fetch")
def find(
    words: Annotated[str, Param("what the picture shows: a quiet harbour at dawn")],
    *,
    filters: Annotated[
        dict, Param("the service's own filters: image_type, orientation, min_width…")
    ] = None,
    count: Annotated[int, Param("how many hits, 3 to 200", lo=3, hi=200)] = 20,
    root: Annotated[str, Param("the project the search is kept in")] = ".",
) -> dict:
    """Search Pixabay's photos, illustrations and vectors, downloading nothing.

    Each hit's id, size, tags, author, page and preview, for `stock.fetch` to take by
    id. Safe search is on. A search asked again within a day is answered from the one
    kept, as the service's terms ask.
    """
    config = load(root)
    stray = sorted(set(filters or {}) - set(FILTERS))
    if stray:
        raise PolyweaveError(
            "stock.bad-filter",
            f"Pixabay takes no filter {stray[0]!r}",
            f"pass only {', '.join(FILTERS)}",
            given=stray[0],
            allowed=FILTERS,
        )
    base, key = _reached(config)
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
    root: Annotated[str, Param("the project it is brought into")] = ".",
) -> dict:
    """Bring one Pixabay picture in, recorded with its page, author and licence.

    The largest rendition the key may read is written at `out`, and its record (kind
    `fetch`) names the source page, the author, the Pixabay Content License and no
    credit owed, at no cost: `provenance.credits all=true` then says where it came from,
    and no budget is drawn.
    """
    config = load(root)
    here = config.root
    base, key = _reached(config)
    hits = _asked(base, key, {"id": int(id)}, config).get("hits") or []
    if not hits:
        raise PolyweaveError(
            "stock.no-hit",
            f"Pixabay has no picture {id}",
            "pass an id stock.find answered",
            given=str(id),
        )
    one = hits[0]
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
    record = provenance.write(provenance.build(
        "fetch", target,
        engine={"name": "pixabay"},
        params={"id": int(id), "rendition": link.rsplit("/", 1)[-1]},
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
            "licence": LICENCE, "record": provenance.relative(Path(record), here)}
