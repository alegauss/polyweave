"""What produced an artefact, written beside it.

`docs/specs/provenance.md` is the contract. A path-traced bake is not byte-reproducible:
two runs of one unchanged Cottony scene differed in 29,696 pixels, none by more than
1/255. So when a render changes, nothing in the file says whether the scene moved, a
library moved, or the sampler simply landed elsewhere.

The record answers that, and it is also the cache key — which is why the subset that
goes into the key is stated exactly rather than taken to be "the important fields". A
key that is merely likely to be right returns the wrong picture eventually.

    prov = build("render", "docs/renders/mascot.png", engine=..., seed=...)
    write(prov)                       # docs/renders/mascot.png.prov.json
    cache_key(prov)                   # the same key for the same inputs, anywhere
    verify(root)                      # is every recorded artefact still what it was
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .errors import PolyweaveError

#: What a record may describe. Closed, because a reader branches on it.
KINDS = ("render", "mesh", "capture", "fetch")

SUFFIX = ".prov.json"

#: Floats are rounded to this many places before a key is computed. Without it, 0.1 and
#: 0.10000000000000001 are two keys for one render.
PLACES = 6

_CHUNK = 1 << 20


# -- the record ------------------------------------------------------------------


def sha256_of(path: Path) -> tuple[str, int]:
    """The digest and the byte length of a file, read once."""
    hasher = hashlib.sha256()
    length = 0
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            hasher.update(chunk)
            length += len(chunk)
    return hasher.hexdigest(), length


def relative(path: str | Path, root: Path) -> str:
    """A path as the record spells it: relative to the root, forward slashes.

    A key computed on Windows and one computed elsewhere have to agree, and a backslash
    is the difference between a hit and a second render.
    """
    absolute = Path(path)
    if not absolute.is_absolute():
        absolute = root / absolute
    try:
        return absolute.resolve().relative_to(root).as_posix()
    except ValueError:
        return absolute.resolve().as_posix()


def source(role: str, path: str | Path, root: str | Path = ".") -> dict:
    """One input of an artefact, hashed now.

    The hash is what the key uses and the path is not: a file that moved is the same
    input, and a file that changed is not.
    """
    where = Path(root).resolve()
    absolute = Path(path)
    if not absolute.is_absolute():
        absolute = where / absolute
    if not absolute.is_file():
        raise PolyweaveError(
            "prov.missing-input",
            f"the {role} input is not at {absolute}",
            "record the path the operation actually read",
        )
    digest, _ = sha256_of(absolute)
    return {"role": role, "path": relative(absolute, where), "sha256": digest}


def build(
    kind: str,
    artefact: str | Path,
    *,
    engine: dict | None = None,
    inputs: Sequence[dict] = (),
    params: dict | None = None,
    measurements: dict | None = None,
    rung: str | None = None,
    seed: int | None = None,
    samples: int | None = None,
    elapsed_s: float | None = None,
    extra: dict | None = None,
    root: str | Path = ".",
    produced_at: str | None = None,
) -> dict:
    """The record of one artefact, with the artefact itself hashed.

    `extra` carries what one kind needs and the others do not — a fetch's task id,
    prompt hash and credits consumed go there, in this record rather than a second one.
    """
    if kind not in KINDS:
        raise PolyweaveError(
            "prov.unknown-kind",
            f"there is no record kind {kind!r}",
            f"use one of {', '.join(KINDS)}",
        )
    where = Path(root).resolve()
    path = Path(artefact)
    if not path.is_absolute():
        path = where / path
    if not path.is_file():
        raise PolyweaveError(
            "prov.missing-artefact",
            f"nothing is at {path} to record",
            "write the artefact before recording it; a record of a file that is not "
            "there is what lost a paid mesh",
        )
    digest, length = sha256_of(path)
    record = {
        "artefact": {
            "path": relative(path, where),
            "sha256": digest,
            "bytes": length,
        },
        "kind": kind,
        "produced_at": produced_at or _stamp(),
        "elapsed_s": elapsed_s,
        "producer": {"tool": "polyweave", "version": __version__},
        "engine": dict(engine or {}),
        "rung": rung,
        "seed": seed,
        "samples": samples,
        "inputs": [dict(i) for i in inputs],
        "params": dict(params or {}),
        "measurements": dict(measurements or {}),
    }
    if extra:
        record.update(extra)
    return record


def planned(
    kind: str,
    *,
    engine: dict | None = None,
    inputs: Sequence[dict] = (),
    params: dict | None = None,
    rung: str | None = None,
    seed: int | None = None,
    samples: int | None = None,
) -> dict:
    """The record of work about to be done, for a key computed before it is paid for.

    The key's subset excludes the artefact, so it can be known before the artefact
    exists — which is the whole of what makes a cache lookup cheaper than a render.
    `cache_key(planned(…))` equals `cache_key(build(…))` for the same work.
    """
    if kind not in KINDS:
        raise PolyweaveError(
            "prov.unknown-kind",
            f"there is no record kind {kind!r}",
            f"use one of {', '.join(KINDS)}",
        )
    return {
        "artefact": None,
        "kind": kind,
        "producer": {"tool": "polyweave", "version": __version__},
        "engine": dict(engine or {}),
        "rung": rung,
        "seed": seed,
        "samples": samples,
        "inputs": [dict(i) for i in inputs],
        "params": dict(params or {}),
    }


def sidecar(artefact: str | Path, root: str | Path = ".") -> Path:
    """Where the record for `artefact` lives: beside it, named after it."""
    where = Path(root).resolve()
    path = Path(artefact)
    if not path.is_absolute():
        path = where / path
    return path.with_name(path.name + SUFFIX)


def write(record: dict, root: str | Path = ".") -> Path:
    """Write the record beside the artefact it describes, and return where."""
    where = Path(root).resolve()
    path = sidecar(record["artefact"]["path"], where)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def read(path: str | Path, root: str | Path = ".") -> dict:
    """Read a record, by its own path or by the path of the artefact it describes."""
    where = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = where / candidate
    if candidate.suffix != ".json" or not candidate.name.endswith(SUFFIX):
        candidate = sidecar(candidate, where)
    if not candidate.is_file():
        raise PolyweaveError(
            "prov.no-record",
            f"there is no record at {candidate}",
            "the artefact was produced without one, or beside a different file",
        )
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolyweaveError(
            "prov.malformed",
            f"{candidate} is not readable as a record",
            "the file was edited or truncated; produce the artefact again",
            detail=str(exc),
        ) from exc


# -- the key ---------------------------------------------------------------------


def key_subset(record: dict) -> dict:
    """Exactly the fields the key is computed over.

    Stating the subset is what makes returning a hit safe rather than merely likely to
    be right. Out: when it was made, how long it took, where it landed, what it
    measured, and every input's path.
    """
    engine = record.get("engine") or {}
    return {
        "kind": record.get("kind"),
        "producer_version": (record.get("producer") or {}).get("version"),
        "engine_name": engine.get("name"),
        "engine_version": engine.get("version"),
        "engine_bindings": engine.get("bindings"),
        # The colour pipeline changes what lands in the file, so two installations that
        # disagree about it must not share a key. §PW43 is what that costs when it is
        # not noticed.
        "engine_view_transform": engine.get("view_transform"),
        "engine_display_device": engine.get("display_device"),
        "rung": record.get("rung"),
        "seed": record.get("seed"),
        "samples": record.get("samples"),
        "inputs": [
            {"role": i.get("role"), "sha256": i.get("sha256")}
            for i in record.get("inputs") or []
        ],
        "params": record.get("params") or {},
    }


def canonical(value: Any) -> str:
    """The one serialisation two machines agree on.

    Keys sorted, arrays in declaration order, no insignificant whitespace, floats
    rounded — each rule is here because its absence splits the cache.
    """
    return json.dumps(
        _round(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def cache_key(record: dict) -> str:
    """The sha256 that identifies this work, wherever it is computed."""
    return hashlib.sha256(canonical(key_subset(record)).encode("utf-8")).hexdigest()


def _round(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, PLACES)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_round(v) for v in value]
    return value


# -- verification ------------------------------------------------------------------


def verify(root: str | Path = ".") -> dict:
    """Is every artefact the records claim to hold present, and still what it was.

    A report rather than a refusal: the answer to "what is missing" is a list, and one
    broken record should not hide the next.
    """
    where = Path(root).resolve()
    ok: list[str] = []
    missing: list[dict] = []
    changed: list[dict] = []
    unreadable: list[dict] = []

    for found in sorted(where.rglob(f"*{SUFFIX}")):
        try:
            record = read(found, where)
        except PolyweaveError as exc:
            unreadable.append({"record": relative(found, where), "why": exc.message})
            continue
        claimed = (record.get("artefact") or {}).get("path")
        if not claimed:
            unreadable.append(
                {"record": relative(found, where), "why": "it names no artefact"}
            )
            continue
        artefact = where / claimed
        if not artefact.is_file():
            missing.append({"record": relative(found, where), "artefact": claimed})
            continue
        digest, length = sha256_of(artefact)
        if digest != record["artefact"].get("sha256"):
            changed.append(
                {
                    "record": relative(found, where),
                    "artefact": claimed,
                    "recorded": record["artefact"].get("sha256"),
                    "found": digest,
                    "bytes": length,
                }
            )
            continue
        ok.append(claimed)

    return {
        "root": str(where),
        "checked": len(ok) + len(missing) + len(changed) + len(unreadable),
        "sound": not (missing or changed or unreadable),
        "ok": ok,
        "missing": missing,
        "changed": changed,
        "unreadable": unreadable,
    }


def _stamp() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
