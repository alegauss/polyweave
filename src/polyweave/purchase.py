"""Taking delivery of something that was paid for.

The evidence is §PW17: the service deletes a task's assets seventy-two hours after it
completes. One Cottony run recorded the settings it had proved and did not commit the
mesh or its ledger entry, and the mesh is now gone: thirty credits spent for a receipt.

That is a design problem rather than a discipline one, so the order is fixed here:

    1. the bytes land on disk and are asserted against what the response declared
    2. they are hashed, and the record is written beside them
    3. only then is the ledger entry appended

**The ledger is written last, so it can never claim an asset that is not there.** The
reverse — a file on disk that nothing recorded — is what `provenance.verify` finds, and
between the two there is no window in which a session can believe an asset is safe
because a ledger mentions it.

Everything downstream keys off **the local file and its hash**, never the remote id,
which is the identifier that stops existing.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import post, provenance
from .config import load
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: What a project may buy. `kind` in the record stays `fetch` for all of them.
BOUGHT = ("mesh", "texture")


def where(root: str | Path = ".") -> Path:
    """The ledger's own file, which belongs to the project and is committed with it."""
    config = load(root)
    return config.path("paths.purchases")


def capture(
    source: bytes | str | Path,
    *,
    out: str | Path,
    task_id: str,
    credits: float = 0.0,
    prompt: str | None = None,
    reference: str | Path | None = None,
    bought: str = "mesh",
    declared_length: int | None = None,
    sha256: str | None = None,
    engine: dict | None = None,
    root: str | Path = ".",
) -> dict:
    """Put a bought artefact somewhere it will outlive the service, and write it down.

    Returns the ledger entry. The call completes only once the file is on disk, hashed,
    recorded and ledgered — a fetch that fails partway leaves no entry claiming it.
    """
    if bought not in BOUGHT:
        raise PolyweaveError(
            "fetch.unknown-purchase",
            f"there is no such thing to buy as a {bought!r}",
            f"name one of {', '.join(BOUGHT)}",
        )
    if not task_id:
        raise PolyweaveError(
            "fetch.no-task",
            "a purchase with no task id cannot be traced back to what was bought",
            "pass the service's own id for the task that produced this",
        )

    here = Path(root).resolve()
    landed = Path(out)
    if not landed.is_absolute():
        landed = here / landed
    landed.parent.mkdir(parents=True, exist_ok=True)

    # 1. The bytes, and what the response said about them. An assertion here is the
    #    difference between a short download and a mesh that loads with half its faces.
    if isinstance(source, bytes | bytearray):
        landed.write_bytes(source)
    else:
        arriving = Path(source)
        if not arriving.is_file():
            raise PolyweaveError(
                "fetch.nothing-arrived",
                f"nothing is at {arriving} to take delivery of",
                "the transfer never completed; ask the service again before recording "
                "anything",
            )
        shutil.copy2(arriving, landed)
    checked = post.check(
        "download", landed, declared_length=declared_length, sha256=sha256
    )

    # 2. The record, beside the artefact, carrying what the service charged for it.
    extra = {
        "task_id": task_id,
        "credits": float(credits),
        "bought": bought,
        "prompt": prompt,
    }
    if reference is not None:
        extra["reference"] = provenance.relative(reference, here)
    record = provenance.build(
        "fetch",
        landed,
        engine=engine or {"name": "service"},
        inputs=[provenance.source("reference", reference, root=here)]
        if reference is not None
        else [],
        measurements=checked,
        extra=extra,
        root=here,
    )
    provenance.write(record, root=here)

    # 3. The ledger, last, so it never names a file that is not there.
    entry = {
        "artefact": record["artefact"]["path"],
        "sha256": record["artefact"]["sha256"],
        "bytes": record["artefact"]["bytes"],
        "task_id": task_id,
        "credits": float(credits),
        "bought": bought,
        "prompt": prompt,
        "reference": extra.get("reference"),
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    append(entry, root=here)
    return entry


def append(entry: dict, *, root: str | Path = ".") -> Path:
    """Add one entry, rewriting the whole file so a reader never sees half a line."""
    path = where(root)
    held = read(root)
    held.append(entry)
    write_atomic(path, json.dumps(held, indent=2, sort_keys=True) + "\n")
    return path


def read(root: str | Path = ".") -> list[dict]:
    """Everything this project has bought, oldest first."""
    path = where(root)
    text = read_text_retrying(path)
    if text is None:
        return []
    try:
        held = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolyweaveError(
            "fetch.ledger-malformed",
            f"{path} is not readable as a ledger",
            "the file was edited by hand; restore it from version control, where it "
            "belongs",
            detail=str(exc),
        ) from exc
    return list(held)


def spent(root: str | Path = ".") -> float:
    """What this project has spent, according to its own ledger."""
    return round(sum(float(e.get("credits", 0.0)) for e in read(root)), 4)


def find(sha: str, *, root: str | Path = ".") -> dict | None:
    """The entry for a file, looked up by **its hash rather than a remote id**.

    The remote id is the one that stops existing, so nothing downstream keys off it.
    """
    return next((e for e in read(root) if e.get("sha256") == sha), None)


def held(root: str | Path = ".") -> dict:
    """Is everything this project paid for still here, and still what it was.

    The question §PW17 says nothing could answer: `provenance.verify` walks the records,
    and this narrows it to the ones that cost money.
    """
    here = Path(root).resolve()
    entries = read(here)
    missing, changed, present = [], [], []
    for entry in entries:
        artefact = here / entry["artefact"]
        if not artefact.is_file():
            missing.append(entry)
            continue
        digest, _ = provenance.sha256_of(artefact)
        (present if digest == entry.get("sha256") else changed).append(entry)
    return {
        "entries": len(entries),
        "credits": spent(here),
        "sound": not (missing or changed),
        "present": [e["artefact"] for e in present],
        "missing": missing,
        "changed": changed,
        "lost_credits": round(sum(float(e.get("credits", 0.0)) for e in missing), 4),
    }


def as_dict(entry: Any) -> dict:  # pragma: no cover - a convenience for callers
    return dict(entry)
