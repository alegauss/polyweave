"""Stock pictures and footage, brought in with their page, author and licence (§PW673).

A picture found in a browser and saved by hand is recorded by nothing, so
`provenance.credits all=true` lists it under `unstated` and a release cannot say where
it came from. `stock.find` searches without downloading; `stock.fetch` takes one hit by
its id and writes a `fetch` record naming the source page, the author and the
service's licence, at no cost, so no budget is drawn. Pixabay came first (§PW673,
§PW674) and Pexels on the same seam (§PW672): each service is a row of `SERVICES`, and
its answers are read into one shape before anything else touches them.

The APIs' terms are the client's to keep: a search answer is kept for 24 hours and
asked again only after, a call over the rate waits for the window the service names
rather than answering 429, and a file is downloaded, never linked. The key is read from
`[service.<name>] key_env`, the service's own variable where the project declares no
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

#: Each stock service: where it answers, the variable its key is read from where the
#: project declares no `[service.<name>]`, the licence every file of it comes under
#: (none owes a credit), and the filters it takes by kind, as it spells them.
SERVICES = {
    "pixabay": {
        "base": "https://pixabay.com/api/", "key_env": "PIXABAY_API_KEY",
        "licence": "Pixabay Content License",
        "filters": {"picture": ("image_type", "orientation", "min_width", "min_height",
                                "colors", "category", "order"),
                    "video": ("video_type", "min_width", "min_height", "category",
                              "order")},
    },
    "pexels": {
        "base": "https://api.pexels.com/", "key_env": "PEXELS_API_KEY",
        "licence": "Pexels License",
        "filters": {"picture": ("orientation", "size", "color", "locale"),
                    "video": ("orientation", "size", "locale", "min_width",
                              "min_height", "min_duration", "max_duration")},
    },
    # Music (§PW705): every track carries its own Creative Commons licence, read off
    # the answer, so `licence` here is only what a track that names none comes under.
    "jamendo": {
        "base": "https://api.jamendo.com/v3.0/", "key_env": "JAMENDO_CLIENT_ID",
        "licence": "",
        "filters": {"music": ("tags", "fuzzytags", "vocalinstrumental", "speed",
                              "durationbetween", "order", "lang")},
    },
}

#: How long a search answer is kept before it is asked again, as the terms ask.
KEPT = 24 * 3600

#: The longest a call waits for the rate window to reopen before it gives up.
WAIT_MOST = 65

#: A video's renditions, largest first (§PW674).
RENDITIONS = ("large", "medium", "small", "tiny")

KINDS = ("picture", "video", "music")


def _kind_of(service: str, kind: str) -> None:
    """Refuse a kind the service does not sell, naming the ones that do."""
    if kind not in SERVICES[service]["filters"]:
        selling = sorted(name for name, one in SERVICES.items()
                         if kind in one["filters"])
        raise PolyweaveError(
            "stock.bad-kind", f"{service} has no {kind}",
            f"ask {' or '.join(selling)} for {kind}, or {service} for "
            f"{' or '.join(SERVICES[service]['filters'])}",
            given=kind, allowed=selling)


def _cc(url: str) -> str:
    """A Creative Commons licence by name, as its URL spells it:
    `.../licenses/by-nc-sa/3.0/` is `CC BY-NC-SA 3.0`."""
    parts = [one for one in str(url).split("/") if one]
    if "licenses" in parts:
        at = parts.index("licenses")
        terms = parts[at + 1:at + 3]
        if terms:
            return "CC " + terms[0].upper() + (f" {terms[1]}" if len(terms) > 1 else "")
    if "publicdomain" in parts:
        return "CC0 1.0"
    return url


def _reached(config, service: str) -> tuple[str, str]:
    own = SERVICES[service]
    about = {"base": own["base"], "key_env": own["key_env"],
             **{k: v for k, v in (config.services().get(service) or {}).items() if v}}
    return client.reached(service, about)


def _asked(service: str, route: str, query: dict, key: str, config) -> dict:
    """One call, from the kept answer where it is under a day old (§PW673)."""
    shown = sorted((k, str(v)) for k, v in query.items())
    kept = config.path("paths.work") / "stock" / (
        hashlib.sha256(json.dumps([route, shown]).encode()).hexdigest()[:20] + ".json")
    if kept.is_file() and time.time() - kept.stat().st_mtime < KEPT:
        return json.loads(kept.read_text(encoding="utf-8"))
    # Pixabay takes the key in the query, Jamendo as its client id, Pexels in a header
    # (§PW672, §PW705).
    in_query = {"pixabay": "key", "jamendo": "client_id"}
    sent = ({in_query[service]: key, **dict(shown)} if service in in_query
            else dict(shown))
    url = route + (f"?{urllib.parse.urlencode(sent)}" if sent else "")
    headers = {} if service in in_query else {"Authorization": key}
    answer = client.send(url, headers=headers, timeout=client.TIMEOUT)
    if answer.status == 429:
        # Waited out rather than refused: the window the service names reopens. Pexels
        # names it as a time, Pixabay as seconds from now.
        reset = float(answer.headers.get("X-RateLimit-Reset")
                      or answer.headers.get("X-Ratelimit-Reset") or 60)
        wait = max(reset - time.time(), 1.0) if reset > 1e9 else reset
        time.sleep(min(wait, WAIT_MOST))
        answer = client.send(url, headers=headers, timeout=client.TIMEOUT)
    if answer.status == 404:
        return {}
    if answer.status >= 400:
        said = answer.body[:400].decode("utf-8", "replace")
        raise client.unpaid(answer.status, said) or PolyweaveError(
            "fetch.service-error",
            f"{service} answered {answer.status}",
            "read the detail; a 400 names a filter it does not take, and a 401 or 403 "
            f"a key it does not accept, read from {SERVICES[service]['key_env']} "
            f"unless [service.{service}] names another",
            detail=said,
        )
    found = json.loads(answer.body or b"{}")
    kept.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(kept, json.dumps(found))
    return found


def _route(service: str, kind: str, base: str, id: int | None = None) -> str:  # noqa: A002
    """Where a search, or one file by its id, is asked."""
    base = base.rstrip("/") + "/"
    if service == "jamendo":
        return base + "tracks/"
    if service == "pixabay":
        # Videos are searched at their own route beside the pictures' (§PW674).
        return base + ("videos/" if kind == "video" else "")
    if kind == "video":
        return base + (f"videos/videos/{id}" if id else "videos/search")
    return base + (f"v1/photos/{id}" if id else "v1/search")


def _hits(service: str, found: dict) -> list[dict]:
    """A service's answer as the hits it holds, read into one shape."""
    if service == "pixabay":
        return [_pixabay(one) for one in found.get("hits") or ()]
    if service == "jamendo":
        return [_jamendo(one) for one in found.get("results") or ()]
    listed = found.get("photos") or found.get("videos")
    if listed is None and found.get("id"):
        listed = [found]
    return [_pexels(one) for one in listed or ()]


def _pixabay(one: dict) -> dict:
    held = one.get("videos") or {}
    return {
        "id": one.get("id"), "page": one.get("pageURL", ""),
        "author": one.get("user", ""),
        "author_page": f"https://pixabay.com/users/{one.get('user', '')}-"
                       f"{one.get('user_id', '')}/",
        "tags": one.get("tags", ""), "duration": one.get("duration"),
        "width": one.get("imageWidth"), "height": one.get("imageHeight"),
        "preview": one.get("previewURL", ""),
        "link": one.get("imageURL") or one.get("fullHDURL") or one.get("largeImageURL"),
        "renditions": {name: {"width": held[name].get("width"),
                              "height": held[name].get("height"),
                              "bytes": held[name].get("size"),
                              "url": held[name]["url"]}
                       for name in RENDITIONS if (held.get(name) or {}).get("url")},
    }


def _pexels(one: dict) -> dict:
    # Pexels lists a video's files by quality and size; the four tallest are named as
    # Pixabay names its renditions, so one `rendition` reads both (§PW672).
    files = sorted((f for f in one.get("video_files") or () if f.get("link")),
                   key=lambda f: -(f.get("height") or 0))
    tallest, seen = [], set()
    for each in files:
        if each.get("height") not in seen:
            seen.add(each.get("height"))
            tallest.append(each)
    user = one.get("user") or {}
    return {
        "id": one.get("id"), "page": one.get("url", ""),
        "author": one.get("photographer") or user.get("name", ""),
        "author_page": one.get("photographer_url") or user.get("url", ""),
        "tags": one.get("alt", ""), "duration": one.get("duration"),
        "width": one.get("width"), "height": one.get("height"),
        "preview": (one.get("src") or {}).get("small") or one.get("image", ""),
        "link": (one.get("src") or {}).get("original"),
        "renditions": {name: {"width": got.get("width"), "height": got.get("height"),
                              "bytes": None, "url": got["link"]}
                       for name, got in zip(RENDITIONS, tallest, strict=False)},
    }


def _jamendo(one: dict) -> dict:
    tags = ((one.get("musicinfo") or {}).get("tags") or {})
    url = one.get("license_ccurl") or ""
    return {
        "id": one.get("id"), "page": one.get("shareurl", ""),
        "title": one.get("name", ""),
        "author": one.get("artist_name", ""),
        "author_page": f"https://www.jamendo.com/artist/{one.get('artist_id', '')}",
        "tags": ", ".join([*tags.get("genres", ()), *tags.get("vartags", ())]),
        "duration": one.get("duration"), "width": None, "height": None,
        "preview": one.get("audio", ""),
        # A track whose owner allows no download has no file to bring in.
        "link": one.get("audiodownload") if one.get("audiodownload_allowed", True)
        else None,
        "licence": _cc(url) if url else "", "licence_url": url,
        "renditions": {},
    }


def _shown(hit: dict, kind: str) -> dict:
    if kind == "music":
        return {k: hit[k] for k in ("id", "title", "duration", "tags", "author",
                                    "page", "licence")}
    if kind == "video":
        # Every rendition the service holds, so a caller picks by length and height
        # without a download (§PW674).
        return {"id": hit["id"], "duration": hit["duration"],
                "renditions": {name: {k: v for k, v in got.items() if k != "url"}
                               for name, got in hit["renditions"].items()},
                "tags": hit["tags"], "author": hit["author"], "page": hit["page"]}
    return {k: hit[k] for k in ("id", "width", "height", "tags", "author", "page",
                                "preview")}


def _rendition(hit: dict, rendition: str | None, height: int | None) -> tuple:
    """The rendition to download, and what the answer says where it is not the one
    asked: an empty one falls to the next one down, never in silence (§PW674)."""
    held = hit["renditions"]
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


_SERVICE = Param("the stock service", choices=tuple(SERVICES))
_KIND = Param("a picture or a video", choices=KINDS)


@operation("stock.find", kind="fetch")
def find(
    words: Annotated[str, Param("what it shows: a quiet harbour at dawn")],
    *,
    kind: Annotated[str, _KIND] = "picture",
    service: Annotated[str, _SERVICE] = "pixabay",
    filters: Annotated[dict, Param("the service's own filters, as it spells them")] = (
        None
    ),
    count: Annotated[int, Param("how many hits, 3 to 80", lo=3, hi=80)] = 20,
    root: Annotated[str, Param("the project the search is kept in")] = ".",
) -> dict:
    """Search a stock service's pictures or videos, downloading nothing.

    Each hit's id, size, tags, author and page, for `stock.fetch`; a video's gives its
    duration and each rendition's size and bytes (§PW674). A search is kept a day.
    """
    config = load(root)
    _kind_of(service, kind)
    taken = SERVICES[service]["filters"][kind]
    stray = sorted(set(filters or {}) - set(taken))
    if stray:
        raise PolyweaveError(
            "stock.bad-filter",
            f"{service} takes no {kind} filter {stray[0]!r}",
            f"pass only {', '.join(taken)}",
            given=stray[0],
            allowed=taken,
        )
    base, key = _reached(config, service)
    asked = (
        {"q": words, "safesearch": "true", "per_page": count} if service == "pixabay"
        else {"search": words, "limit": count, "format": "json", "include": "musicinfo",
              "audiodownload_allowed": "true"} if service == "jamendo"
        else {"query": words, "per_page": count})
    found = _asked(service, _route(service, kind, base), {**asked, **(filters or {})},
                   key, config)
    return {"words": words, "service": service,
            "total": found.get("totalHits", found.get("total_results", (
                found.get("headers") or {}).get("results_count", 0))),
            "hits": [_shown(hit, kind) for hit in _hits(service, found)],
            "says": "take one with stock.fetch id=<id> out=<path>"}


def _allowed(config, service: str, licence: str | None = None) -> str:
    """The service's licence, or the file's own where it carries one (§PW705), refused
    where the project lists the ones it ships under and this is not among them
    (§PW672)."""
    licence = licence if licence is not None else SERVICES[service]["licence"]
    allowed = (config.services().get(service) or {}).get("licences") or []
    if allowed and licence not in allowed:
        raise PolyweaveError(
            "stock.licence-refused",
            f"{service}'s files come under the {licence}, which "
            f"[service.{service}] licences does not allow",
            f"add {licence!r} to [service.{service}] licences, or take the file from "
            "a service the project allows",
            given=licence,
            allowed=allowed,
        )
    return licence


#: The licence words a public video must report to be taken where the project names
#: none: a video is not stock because it is public (§PW701).
REUSABLE = ("Creative Commons",)


def _run(argv: list[str]) -> str:
    """One yt-dlp call, its standard output; a failure is a code with what it said."""
    import shutil
    import subprocess

    found = shutil.which(argv[0])
    if not found:
        raise PolyweaveError(
            "stock.no-yt-dlp", "a public video is fetched with yt-dlp, which is not on "
            "PATH", "pip install yt-dlp, or put its binary on PATH")
    done = subprocess.run([found, *argv[1:]], capture_output=True, text=True,
                          encoding="utf-8", timeout=900, check=False)
    if done.returncode != 0:
        raise PolyweaveError(
            "fetch.service-error", f"yt-dlp failed on {argv[-1]}",
            "read the detail; a video that is private or gone cannot be fetched",
            detail=(done.stderr or "")[-400:])
    return done.stdout


@operation("stock.clip", kind="fetch")
def clip(
    url: Annotated[str, Param("the public video's page, as a YouTube watch URL")],
    out: Annotated[str, Param("where the excerpt is written, as an .mp4")],
    *,
    start: Annotated[float, Param("seconds into the video it begins", lo=0.0)] = 0.0,
    end: Annotated[float, Param("seconds into the video it ends", lo=0.0)] = None,
    root: Annotated[str, Param("the project it is brought into")] = ".",
) -> dict:
    """Bring one excerpt of a public video in, refused unless its licence allows reuse.

    The video's own metadata is read first, for nothing: its title, channel and the
    licence it reports. A video reporting no licence, or one the project does not allow
    (`[service.youtube] licences`, or any Creative Commons licence where none is
    listed), is refused before anything is downloaded. Only `start` to `end` is fetched.
    The record names the page, title, channel, licence, in and out points and the
    credit the licence asks, so `provenance.credits` owes it.
    """
    config = load(root)
    here = config.root
    if end is not None and end <= start:
        raise PolyweaveError(
            "stock.bad-excerpt", f"the excerpt ends at {end:g}s, not after {start:g}s",
            "give end after start, in seconds into the video")
    target = Path(out) if Path(out).is_absolute() else here / out
    if target.suffix.lower() != ".mp4":
        raise PolyweaveError("stock.bad-excerpt", f"the excerpt is written as "
                             f"{target.name}", "write it as an .mp4", given="out")
    said = json.loads(_run(["yt-dlp", "-J", "--no-playlist", url]) or "{}")
    licence = str(said.get("license") or "")
    allowed = (config.services().get("youtube") or {}).get("licences") or []
    if not licence or (licence not in allowed if allowed
                       else not any(word in licence for word in REUSABLE)):
        raise PolyweaveError(
            "stock.licence-refused",
            f"{said.get('title') or url} reports "
            + (f"the licence {licence!r}, which" if licence else "no licence, and")
            + " the project does not allow it",
            "take a video its owner licensed for reuse, or add its licence to "
            "[service.youtube] licences once a person has read it",
            given=licence or None, allowed=allowed or list(REUSABLE))
    length = float(said.get("duration") or 0)
    until = end if end is not None else length
    if length and until > length + 0.5:
        raise PolyweaveError(
            "stock.bad-excerpt", f"the video runs {length:g}s, and the excerpt ends at "
            f"{until:g}s", "give end within the video's length")
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(["yt-dlp", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
          "--download-sections", f"*{start:g}-{until:g}", "--force-keyframes-at-cuts",
          "--force-overwrites", "-o", str(target), url])
    if not target.is_file():
        raise PolyweaveError(
            "fetch.nothing-arrived", f"yt-dlp wrote nothing at {out}",
            "read what it said with yt-dlp itself; nothing was recorded")
    from polyweave.layers.reference.reference_register import _probe

    probed = _probe(target)
    page = said.get("webpage_url") or url
    channel = said.get("channel") or said.get("uploader") or ""
    title = said.get("title") or ""
    record = provenance.write(provenance.build(
        "fetch", target,
        engine={"name": "youtube", "fetcher": "yt-dlp"},
        params={"id": said.get("id"), "start": start, "end": until},
        measurements=probed,
        extra={"task_id": f"youtube:{said.get('id')}:{start:g}-{until:g}",
               "credits": 0.0, "licence": licence,
               "credit": f"“{title}”, {channel}, {licence}: {page}",
               "source_page": page, "author": channel, "title": title,
               "author_page": said.get("channel_url") or ""},
        root=here,
    ), root=here)
    return {"file": provenance.relative(target, here), "title": title,
            "channel": channel, "licence": licence, "page": page,
            "start": start, "end": until,
            "record": provenance.relative(Path(record), here), **probed}


@operation("stock.fetch", kind="fetch")
def fetch(
    id: Annotated[int, Param("the hit's id, as stock.find answered it")],  # noqa: A002
    out: Annotated[str, Param("where it is written, under the project")],
    *,
    kind: Annotated[str, _KIND] = "picture",
    service: Annotated[str, _SERVICE] = "pixabay",
    rendition: Annotated[
        str, Param("a video's rendition; large if neither this nor height",
                   choices=RENDITIONS)
    ] = None,
    height: Annotated[
        int, Param("a video's smallest rendition at least this tall, in px")
    ] = None,
    root: Annotated[str, Param("the project it is brought into")] = ".",
) -> dict:
    """Bring one stock picture, video or piece of music in, recorded with its page and
    licence.

    A video is the `rendition` named, or the smallest `height` tall; an empty one falls
    to the next, with `fell` saying so (§PW674). The record names the page, the author
    and the licence, at no cost. A piece of music carries its own Creative Commons
    licence, held to `[service.jamendo] licences` where the project lists them, and the
    attribution it asks is its `credit`, which `provenance.credits` owes (§PW705).
    """
    config = load(root)
    here = config.root
    _kind_of(service, kind)
    licence = _allowed(config, service) if kind != "music" else ""
    base, key = _reached(config, service)
    by_id = ({"id": int(id)} if service == "pixabay"
             else {"id": int(id), "format": "json", "include": "musicinfo"}
             if service == "jamendo" else {})
    route = _route(service, kind, base, None if by_id else int(id))
    hits = _hits(service, _asked(service, route, by_id, key, config))
    if not hits:
        raise PolyweaveError(
            "stock.no-hit",
            f"{service} has no {kind} {id}",
            "pass an id stock.find answered, with the same kind and service",
            given=str(id),
        )
    hit = hits[0]
    credit = ""
    if kind == "music":
        if not hit["licence"]:
            raise PolyweaveError(
                "stock.licence-refused", f"{service} names no licence for track {id}",
                "take a track whose licence the service states", given=str(id))
        licence = _allowed(config, service, hit["licence"])
        # The attribution a CC licence asks: title, author, source and licence.
        credit = (f"“{hit['title']}” by {hit['author']} ({hit['page']}), licensed "
                  f"under {licence} ({hit['licence_url']})")
    fell, chosen = None, None
    if kind == "video":
        chosen, fell = _rendition(hit, rendition, height)
        link = hit["renditions"][chosen]["url"] if chosen else None
    else:
        link = hit["link"]
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"{service} answered {kind} {id} with no link to download",
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
    elif kind == "music":
        probed = {"seconds": hit["duration"]}
    record = provenance.write(provenance.build(
        "fetch", target,
        engine={"name": service},
        params={"id": int(id), "kind": kind,
                "rendition": chosen or link.rsplit("/", 1)[-1].split("?")[0]},
        measurements=probed,
        extra={"task_id": f"{service}:{id}", "credits": 0.0, "licence": licence,
               "credit": credit, "source_page": hit["page"], "author": hit["author"],
               "author_page": hit["author_page"], "tags": hit["tags"],
               **({"title": hit["title"], "licence_url": hit["licence_url"]}
                  if kind == "music" else {})},
        root=here,
    ), root=here)
    return {"file": provenance.relative(target, here), "id": int(id),
            "author": hit["author"], "page": hit["page"], "licence": licence,
            "record": provenance.relative(Path(record), here),
            **({"rendition": chosen, **probed} if kind == "video" else {}),
            **({"title": hit["title"], "credit": credit, **probed}
               if kind == "music" else {}),
            **({"fell": fell} if fell else {})}
