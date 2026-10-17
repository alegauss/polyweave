"""Renders are content-addressed, so the same picture is paid for once.

The evidence is §PW14: a search revisits neighbourhoods and a caller re-runs the same
render across sessions, and without a cache every one of those is paid again at the full
price of a path trace.

The key is the provenance record's own subset — the input hashes, the parameter values,
the renderer version, the colour pipeline and the seed. Everything that can change the
output is in it and nothing that cannot, which is what makes a hit **safe to return**
rather than merely likely to be right.

    key = provenance.cache_key(provenance.planned(...))   # before anything is rendered
    hit = look(key, work=...)                             # or None
    put(key, artefact, record, work=...)                  # after a miss

Two things matter more than they look. **A hit is reported as a hit**, because a caller
timing a sweep needs to know what it actually measured. And **preview rungs are cached
too**, since those are the renders a search asks for thousands of times while the full
ones are asked for once.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import time
from pathlib import Path

from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: Under the project, so it can be inspected and deleted by hand. `[paths] work` is the
#: only location the plugin chooses for itself, and it belongs in `.gitignore`.
DIRECTORY = "cache"

#: What a project may hold before the least recently used are dropped.
MAX_BYTES = 8_000_000_000


def where(work: str | Path) -> Path:
    return Path(work) / DIRECTORY


def slot(key: str, work: str | Path, suffix: str = ".png") -> tuple[Path, Path]:
    """The artefact and its record, fanned out by the key's first two characters."""
    if not key or len(key) < 4:
        raise PolyweaveError(
            "prov.bad-key",
            f"{key!r} is not a cache key",
            "compute it with cache_key over a provenance record",
        )
    folder = where(work) / key[:2]
    return folder / f"{key}{suffix}", folder / f"{key}.json"


def look(key: str, *, work: str | Path, suffix: str = ".png") -> dict | None:
    """What this key holds, or nothing.

    A record whose artefact is missing is **dropped rather than repaired**: half an
    entry is a hit waiting to return a file that is not there.
    """
    artefact, record = slot(key, work, suffix)
    if not record.is_file():
        return None
    if not artefact.is_file():
        with contextlib.suppress(OSError):
            record.unlink()
        return None
    text = read_text_retrying(record)
    if text is None:  # pragma: no cover - removed between the two reads
        return None
    try:
        held = json.loads(text)
    except json.JSONDecodeError:
        with contextlib.suppress(OSError):
            record.unlink()
            artefact.unlink()
        return None
    _touch(artefact)
    return {
        "key": key,
        "artefact": artefact,
        "record": held,
        "bytes": artefact.stat().st_size,
    }


def put(key: str, artefact: str | Path, record: dict, *, work: str | Path) -> dict:
    """Keep this artefact under its key, with the record that says what produced it."""
    source = Path(artefact)
    if not source.is_file():
        raise PolyweaveError(
            "prov.missing-artefact",
            f"nothing is at {source} to cache",
            "write the artefact before caching it",
        )
    held, beside = slot(key, work, source.suffix or ".png")
    held.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, held)
    write_atomic(beside, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return {"key": key, "artefact": held, "bytes": held.stat().st_size}


def take(hit: dict, out: str | Path) -> Path:
    """Copy a hit out to where the caller wanted it written."""
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hit["artefact"], destination)
    return destination


def entries(work: str | Path) -> list[dict]:
    """Every entry, newest use first."""
    found = []
    root = where(work)
    if not root.is_dir():
        return found
    for record in root.rglob("*.json"):
        key = record.stem
        artefact = next(
            (p for p in record.parent.glob(f"{key}.*") if p.suffix != ".json"), None
        )
        if artefact is None:
            with contextlib.suppress(OSError):
                record.unlink()
            continue
        stat = artefact.stat()
        found.append(
            {
                "key": key,
                "artefact": artefact,
                "record": record,
                "bytes": stat.st_size + record.stat().st_size,
                "used": stat.st_mtime,
            }
        )
    return sorted(found, key=lambda e: e["used"], reverse=True)


def stats(work: str | Path) -> dict:
    held = entries(work)
    return {
        "entries": len(held),
        "bytes": sum(e["bytes"] for e in held),
        "where": str(where(work)),
    }


def evict(*, work: str | Path, max_bytes: int = MAX_BYTES) -> dict:
    """Drop the least recently used until the store is under its ceiling."""
    held = entries(work)
    total = sum(e["bytes"] for e in held)
    dropped = []
    for entry in reversed(held):  # oldest use first
        if total <= max_bytes:
            break
        for path in (entry["artefact"], entry["record"]):
            with contextlib.suppress(OSError):
                path.unlink()
        total -= entry["bytes"]
        dropped.append(entry["key"])
    return {"dropped": dropped, "bytes": total, "entries": len(held) - len(dropped)}


def forget(key: str, *, work: str | Path, suffix: str = ".png") -> bool:
    artefact, record = slot(key, work, suffix)
    gone = False
    for path in (artefact, record):
        if path.is_file():
            with contextlib.suppress(OSError):
                path.unlink()
                gone = True
    return gone


def _touch(path: Path) -> None:
    """Mark an entry as used now, which is what least-recently-used is measured on."""
    with contextlib.suppress(OSError):
        now = time.time()
        os.utime(path, (now, now))
