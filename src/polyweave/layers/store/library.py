"""Fetched media with the ranges a person accepted or rejected, carried into a cut
(§PW714).

`stock.fetch`, `stock.clip` and a copied-in file each leave a record of where a file
came from, and nothing kept what a person then decided about it: in viglet/marketing
VM58 a WordPress clip rejected for blur, one for unrelated text and one for a mistaken
identity were each found again by the next search. A `*.library.toml` keeps it:

```toml
[[source]]
file = "stock/pixabay-123-large.mp4"
sha256 = "9f2c..."        # written by video.library add; a changed file voids it
seconds = 14.2
licence = "Pixabay Content License"
page = "https://pixabay.com/videos/id-123/"
rights = "cleared"        # unreviewed until a person reads the licence; or refused
rights_by = "Ana"         # who read it
tags = ["event:wordcamp"] # people and events a person confirmed

[[source.range]]
start = 2.0               # both left out: the whole file, as a still's is
end = 9.5
verdict = "accepted"      # or rejected, which no later search makes usable again
reason = "the dashboard, in focus"
by = "Ana"
on = 2026-11-23
```

`video.library add=<file>` brings a file in as an unreviewed candidate, with its hash,
length and what its record says of its licence and page; it never decides anything.
A cut naming `[video] library` takes a video or still clip only from a cleared source,
inside one accepted range and touching no rejected one, and its record names the range
and who accepted it. A captured run is the game's own and is not catalogued.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

RIGHTS = ("unreviewed", "cleared", "refused")
VERDICTS = ("accepted", "rejected")
_SOURCE_KEYS = {"file", "sha256", "seconds", "licence", "page", "author", "rights",
                "rights_by", "tags", "range"}
_RANGE_KEYS = {"start", "end", "verdict", "reason", "by", "on", "tags"}


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-library", message, remedy, **extra)


def _at(path: str, here: Path) -> Path:
    return Path(path) if Path(path).is_absolute() else here / path


def read(source: Path, here: Path) -> list[dict]:
    """A library's sources, each range checked; a range with no person, reason or day
    is refused, since a decision nobody made is the agent's own."""
    if not source.is_file():
        raise PolyweaveError(
            "video.no-source", f"there is no library at {source}",
            "name a *.library.toml under the project, or start one with add",
            given=str(source))
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "video.no-source", f"{source.name} is not TOML: {exc}",
            "fix the line the detail names", given=str(source)) from exc
    if set(declared) - {"source"}:
        raise _bad(f"{source.name} has {', '.join(sorted(set(declared) - {'source'}))}",
                   "a library holds only [[source]] tables")
    sources = []
    for n, one in enumerate(declared.get("source", []), 1):
        at = f"source[{n}]"
        stray = sorted(set(one) - _SOURCE_KEYS)
        if stray or not one.get("file") or not one.get("sha256"):
            raise _bad(f"{at} " + (f"has no {stray[0]}" if stray
                                   else "names no file or sha256"),
                       f"a source takes {', '.join(sorted(_SOURCE_KEYS))}; add it "
                       "with video.library add=<file>", at=at)
        if one.get("rights", "unreviewed") not in RIGHTS:
            raise _bad(f"{at}.rights is {one['rights']!r}",
                       f"give one of {', '.join(RIGHTS)}", at=at, given="rights")
        if one.get("rights", "unreviewed") != "unreviewed" and not one.get("rights_by"):
            raise _bad(f"{at} is {one['rights']} with no rights_by",
                       "name the person who read the licence", at=at,
                       given="rights_by")
        ranges = []
        for k, row in enumerate(one.get("range", []), 1):
            where = f"{at}.range[{k}]"
            stray = sorted(set(row) - _RANGE_KEYS)
            short = [key for key in ("verdict", "reason", "by", "on")
                     if not row.get(key)]
            if stray or short:
                raise _bad(f"{where} " + (f"has no {stray[0]}" if stray
                                          else f"names no {', '.join(short)}"),
                           "a range is a person's decision: give verdict, reason, by "
                           "and on, and start and end unless it is the whole file",
                           at=where, given=(stray or short)[0])
            if row["verdict"] not in VERDICTS:
                raise _bad(f"{where}.verdict is {row['verdict']!r}",
                           f"give one of {', '.join(VERDICTS)}", at=where,
                           given="verdict")
            start, end = float(row.get("start", 0.0)), row.get("end")
            end = float(end) if end is not None else None
            if start < 0 or (end is not None and end <= start):
                raise _bad(f"{where} runs {start:g}s to {end}",
                           "give start from 0 and end after it, in seconds",
                           at=where, given="end")
            ranges.append({**row, "start": start, "end": end, "on": str(row["on"])})
        sources.append({**one, "rights": one.get("rights", "unreviewed"),
                        "range": ranges, "path": _at(one["file"], here).resolve()})
    return sources


def _changed(one: dict) -> str | None:
    """Why a catalogued file is no longer the one decided on, or None."""
    if not one["path"].is_file():
        return "it is gone"
    if provenance.sha256_of(one["path"])[0] != one["sha256"]:
        return "its digest moved"
    return None


def approved(library: Path, here: Path, clips: list[dict]) -> list[dict]:
    """The accepted range each file clip of a cut sits in, refused where it has none."""
    sources = held(library, here)
    shown = [approved_clip(sources, n, clip, here) for n, clip in enumerate(clips, 1)]
    return [one for one in shown if one]


def held(library: Path, here: Path) -> dict[Path, dict]:
    """A library's sources by the file each names."""
    return {one["path"]: one for one in read(library, here)}


def approved_clip(sources: dict[Path, dict], n: int, clip: dict,
                  here: Path) -> dict | None:
    """The accepted range clip `n` sits in; None for a captured run, which is the
    game's own. A still's span is its whole file, held only by a whole-file range."""
    if clip["kind"] == "run":
        return None
    at, named = f"clip[{n}]", provenance.relative(clip["file"], here)
    one = sources.get(Path(clip["file"]).resolve())
    if one is None:
        raise PolyweaveError(
            "video.unapproved", f"{at} shows {named}, which the library does not hold",
            f"add it with video.library add={named}, and have a person accept a range "
            "of it", at=at, given=named)
    moved = _changed(one)
    if moved:
        raise PolyweaveError(
            "video.library-changed", f"{at} shows {named}, which is not the file the "
            f"library's decisions were made on: {moved}",
            "have a person review it again, then add it afresh", at=at, given=named)
    if one["rights"] != "cleared":
        raise PolyweaveError(
            "video.unapproved", f"{at} shows {named}, whose rights are {one['rights']}",
            'a person reads its licence and sets rights = "cleared" with rights_by, or '
            "the clip comes from elsewhere", at=at, given=named)
    whole = clip["kind"] != "video"
    a = 0.0 if whole else clip["start"]
    b = INF if whole else clip["start"] + clip["length"]
    for r in one["range"]:
        if r["verdict"] == "rejected" and b > r["start"] and a < _end(r):
            raise PolyweaveError(
                "video.unapproved", f"{at} shows {named} over a range {r['by']} "
                f"rejected on {r['on']}: {r['reason']}",
                "choose another stretch or source; a rejected range stays rejected",
                at=at, given=named)
    for r in one["range"]:
        inside = r["start"] <= a + 1e-6 and b <= _end(r) + 1e-6
        if r["verdict"] == "accepted" and inside:
            return {"clip": n, "file": named, "range": _span(r), "by": r["by"],
                    "on": r["on"], "reason": r["reason"],
                    **({"tags": one["tags"]} if one.get("tags") else {})}
    shown = "all of" if whole else f"{a:g}s to {b:g}s of"
    raise PolyweaveError(
        "video.unapproved", f"{at} shows {shown} {named}, inside no accepted range",
        "fit the clip inside a range a person accepted, or ask one to review this "
        "stretch", at=at, given=named)


INF = float("inf")


def _end(row: dict) -> float:
    return row["end"] if row["end"] is not None else INF


def _span(row: dict) -> list[float] | str:
    return [row["start"], row["end"]] if row["end"] is not None else "whole"

def _quoted(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


@operation("video.library")
def library(
    path: Annotated[str, Param("the *.library.toml, as a path under the project")],
    *,
    add: Annotated[
        str, Param("a fetched file to add as an unreviewed candidate")
    ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Read a library of fetched media and the ranges people accepted or rejected, or
    add a file to it as an unreviewed candidate (§PW714).

    The answer gives each source's rights, its accepted and rejected ranges with who
    decided and why, and `changed` where the file is no longer the one decided on. A
    file added that is already there answers its entry, rejected ranges and all, so a
    new search does not make it new. Only a person sets rights or a range's verdict; a
    cut naming `[video] library` is held to them.
    """
    from polyweave.kernel.config import load

    here = load(root).root
    target = _at(path, here)
    if not target.name.endswith(".library.toml"):
        raise _bad(f"the library is {target.name}", "name it <name>.library.toml",
                   given="path")
    added = None
    if add:
        file = _at(add, here)
        if not file.is_file():
            raise PolyweaveError("video.no-source", f"there is no file at {add}",
                                 "name a file stock.fetch or stock.clip wrote",
                                 given=add)
        held = read(target, here) if target.is_file() else []
        known = next((one for one in held if one["path"] == file.resolve()), None)
        if known is None:
            added = _added(target, file, here)
    sources = read(target, here) if target.is_file() else []
    shown = [_shown(one, here) for one in sources]
    named = provenance.relative(_at(add, here), here) if add else ""
    return {
        "library": provenance.relative(target, here),
        "sources": shown,
        **({"added": added} if added else {}),
        **({"held": next(s for s in shown if s["file"] == named)}
           if add and not added else {}),
        "says": (f"{named} added, unreviewed; a person sets its rights and accepts a "
                 "range before a cut may show it" if added
                 else f"{named} is already in the library, as answered in held"
                 if add else f"{len(shown)} source(s); "
                 f"{sum(1 for s in shown if s['usable'])} usable by a cut"),
    }


def _added(target: Path, file: Path, here: Path) -> dict:
    """Append one unreviewed source, with what the file's record says of it."""
    from polyweave.layers.store.video import _seconds

    named = provenance.relative(file, here)
    try:
        record = provenance.read(named, root=str(here))
    except PolyweaveError:
        record = {}
    entry: dict[str, Any] = {"file": named, "sha256": provenance.sha256_of(file)[0]}
    # The store's own probe: a layer reads only the layers it declares it uses. A
    # still, or no ffprobe, leaves a source with no length, still catalogued.
    with contextlib.suppress(PolyweaveError):
        entry["seconds"] = round(_seconds(file), 3)
    for key, said in (("licence", "licence"), ("page", "source_page"),
                      ("author", "author")):
        if record.get(said):
            entry[key] = record[said]
    entry["rights"] = "unreviewed"
    block = "\n[[source]]\n" + "".join(f"{k} = {_quoted(v)}\n"
                                       for k, v in entry.items())
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        block = ("# Fetched media and the ranges a person accepted or rejected "
                 "(video.library).\n" + block)
    with target.open("a", encoding="utf-8", newline="\n") as written:
        written.write(block)
    return {**entry, "on": _dt.date.today().isoformat(),
            **({"recorded": True} if record else {"recorded": False})}


def _shown(one: dict, here: Path) -> dict:
    moved = _changed(one)
    return {
        "file": provenance.relative(one["path"], here),
        "rights": one["rights"],
        **({"licence": one["licence"]} if one.get("licence") else {}),
        **({"tags": one["tags"]} if one.get("tags") else {}),
        "accepted": [{"range": _span(r), "by": r["by"], "on": r["on"],
                      "reason": r["reason"]} for r in one["range"]
                     if r["verdict"] == "accepted"],
        "rejected": [{"range": _span(r), "by": r["by"], "on": r["on"],
                      "reason": r["reason"]} for r in one["range"]
                     if r["verdict"] == "rejected"],
        **({"changed": moved} if moved else {}),
        "usable": not moved and one["rights"] == "cleared" and any(
            r["verdict"] == "accepted" for r in one["range"]),
    }
