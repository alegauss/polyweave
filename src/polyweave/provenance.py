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
from fnmatch import fnmatch
from pathlib import Path, PurePath, PurePosixPath
from typing import Any

from . import __version__
from .errors import PolyweaveError

#: What a record may describe. Closed, because a reader branches on it.
KINDS = ("render", "mesh", "capture", "fetch")

SUFFIX = ".prov.json"

#: Floats are rounded to this many places before a key is computed. Without it, 0.1 and
#: 0.10000000000000001 are two keys for one render.
PLACES = 6

#: The `extra` keys that carry a path (§PW72). Declared here rather than remembered at
#: each call site, because remembering is what failed: `purchase` relativised its one
#: and `capture` did not, so a record committed beside a screenshot named a drive letter
#: while the artefact two keys above it was relative. A value that is already a `Path`
#: is rewritten whatever it is called, so a key added later and not listed here still
#: comes out right as long as it arrives as a path rather than as a string.
PATHS = ("script", "reference")

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
    tolerances: dict | None = None,
    elapsed_s: float | None = None,
    extra: dict | None = None,
    root: str | Path = ".",
    produced_at: str | None = None,
) -> dict:
    """The record of one artefact, with the artefact itself hashed.

    `extra` carries what one kind needs and the others do not — a fetch's task id,
    prompt hash and credits consumed go there, in this record rather than a second one.
    A path among them is written the way the rest of the record writes one, relative to
    the root; `PATHS` names the keys that carry one, and a `Path` is rewritten whatever
    it is called (§PW72).

    `tolerances` is what the numbers in `measurements` were taken against (§PW51).
    Without it two records can carry the same measurement and mean different things,
    because the alpha floor that decided what counted as the subject sat in a file that
    has since been edited — and reading the config back recovers the project's numbers
    now, not the artefact's. An operation resolves all six with `Config.tolerances()`
    and passes `as_dict()` here. A record whose measurements were taken against nothing
    carries no field, by the same rule that keeps a normalisation free of a seed.
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
        "inputs": [dict(i) for i in inputs],
        "params": dict(params or {}),
        "measurements": dict(measurements or {}),
    }
    # One vocabulary for every kind, with what does not apply **absent rather than
    # empty** (§PW46). A normalisation has no engine, no rung, no seed and no sampler,
    # and a record carrying four nulls for them says it has them and they are unknown —
    # which is a different claim, and the wrong one. The key reads these with `.get`,
    # so an absent field and a null one key identically and nothing is invalidated.
    for name, value in (
        ("engine", dict(engine or {})),
        ("rung", rung),
        ("seed", seed),
        ("samples", samples),
        ("tolerances", dict(tolerances or {})),
    ):
        if value or value == 0:
            record[name] = value
    if extra:
        record.update(_placed(extra, where))
    return record


def _placed(extra: dict, where: Path) -> dict:
    """`extra`, with every path in it spelled the way the rest of the record is.

    The record is read on a machine that is not the one that wrote it — that is most of
    what it is for — and it is committed beside the artefact it describes. A path in it
    that survives a clone and one that does not cannot sit two keys apart.
    """
    return {
        name: relative(value, where)
        if value is not None and (name in PATHS or isinstance(value, PurePath))
        else value
        for name, value in extra.items()
    }


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

    **Tolerances are deliberately out** (§PW51). A tolerance is read after the pixels
    exist, so a render made at one alpha floor is byte-identical to the same render at
    another, and keying on one would spend a path trace to recompute a number that can
    be recomputed from the file already on disk. What does go stale is the verdict, and
    `remeasure` is where that is answered.
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


def remeasure(record: dict, now: Any) -> list[str]:
    """Which tolerances this record's measurements are no longer valid under.

    Empty means the verdict written beside the artefact still stands and its numbers can
    be read as they are. A name in the list is a bar that has moved since, so what sits
    under it was measured against something else.

    **A record carrying no tolerances at all returns every name asked about**, because a
    measurement whose bar nobody wrote down cannot be shown to still hold. Reading that
    silence as agreement is what keeps a stale verdict, and it is the symptom §PW51 is
    about — so the answer for a record written before the field existed is the honest
    "unknown", spelled as the same list a caller already has to handle.

    Compared at the key's own rounding, so a float that survived a JSON round trip does
    not read as a bar somebody moved.
    """
    wanted = now.as_dict() if hasattr(now, "as_dict") else dict(now or {})
    taken = record.get("tolerances") or {}
    if not taken:
        return sorted(wanted)
    return sorted(
        name
        for name, value in wanted.items()
        if name not in taken
        or round(float(taken[name]), PLACES) != round(float(value), PLACES)
    )


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


#: What a rerun can say about the one before it. Closed, because a caller branches on
#: it.
#:
#: `differs` is the only one that is news. `different-work` is a byte difference the key
#: already explains, and saying nothing about it would make the interesting case harder
#: to spot rather than easier.
AGAIN = ("first", "reproduced", "differs", "different-work")


def reproduced(record: dict, root: str | Path = ".") -> dict:
    """This artefact against the last one recorded in its place (§PW71).

    The key says what counts as the same work, and the artefact's own hash is left out
    of it deliberately — so a record whose key matches the one already beside the
    artefact, and whose digest does not, is the same work having produced a different
    file. Nothing in the project could say that before: both runs wrote a record, both
    records stated the same params, and the second simply overwrote the first.

    It is worth saying because it is not always expected. Three of Cottony's four
    captures are byte-identical across runs and the fourth is not, and the difference
    between a screenshot worth reviewing and one that is only noise is this answer.

    **Called before the new record is written**, since writing it is what destroys the
    evidence. `capture.run` does that and carries the answer back.

    This is a report and never a refusal, for the reason `verify` is: the plugin cannot
    make an engine deterministic and should not pretend to. What it can do is say so.

    The comparison is the key's, so two different scripts writing to one artefact under
    one set of params read as the same work — which they are not, but they are also
    overwriting each other, and that is a different fault from this one.
    """
    now = (record.get("artefact") or {}).get("sha256")
    path = sidecar(record["artefact"]["path"], root)
    if not path.is_file():
        return _again("first", record, None, "")
    try:
        before = read(path, root)
    except PolyweaveError as unreadable:
        why = f"{path.name} could not be read: {unreadable.message}"
        return _again("first", record, None, why)
    was = (before.get("artefact") or {}).get("sha256")
    since = before.get("produced_at")
    if cache_key(before) != cache_key(record):
        return _again("different-work", record, before, "")
    if was == now:
        return _again("reproduced", record, before, "")
    return _again(
        "differs",
        record,
        before,
        # ASCII, deliberately: this sentence is printed to a terminal, and stdout on a
        # Windows desk here is cp1252, where an em dash arrives as a replacement
        # character. §PW73 is the same defect in the twenty other strings that have one.
        f"{PurePosixPath(record['artefact']['path']).name}: the same declared settings "
        f"produced different bytes; {(was or '?')[:12]} on "
        f"{since or 'an unknown date'}, {(now or '?')[:12]} now",
    )


def _again(verdict: str, record: dict, before: dict | None, why: str) -> dict:
    """One verdict, in the shape every caller of this reads."""
    return {
        "verdict": verdict,
        "artefact": record["artefact"]["path"],
        "key": cache_key(record),
        "was": ((before or {}).get("artefact") or {}).get("sha256"),
        "now": (record.get("artefact") or {}).get("sha256"),
        "since": (before or {}).get("produced_at"),
        "why": why,
    }


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


#: Which directories hold produced artefacts, and what the plugin writes into each. The
#: other half of §PW41's question is asked over these: a file here with one of these
#: suffixes and no sidecar was produced by something that did not record it.
PRODUCED: dict[str, tuple[str, ...]] = {
    "paths.meshes": (".glb", ".gltf"),
    "paths.renders": (".png",),
}


def unrecorded(root: str | Path = ".") -> list[dict]:
    """Produced files carrying no record — the half `verify` could not ask about.

    §PW41. `verify` walks the records and checks their artefacts; it cannot walk the
    artefacts and check their records, because nothing told it which files are supposed
    to have one. So a mesh that was paid for, downloaded, committed and never recorded
    is invisible to it, and the project reads as sound.

    That is the more expensive half of the same failure. A recorded artefact that went
    missing costs a re-render; an unrecorded one that was paid for costs the credits
    again, and nothing says which of the meshes in the tree those are.

    `[provenance] handmade` is how a project says which files here it made itself. A
    project puts hand-made art in these directories too, and calling each of them a
    defect makes the report useless within a week.
    """
    from .config import load as load_config

    settings = load_config(root)
    where = settings.root
    excused = [str(p) for p in settings.get("provenance.handmade")]
    out: list[dict] = []
    for address, suffixes in PRODUCED.items():
        directory = settings.path(address)
        if not directory.is_dir():
            continue
        for found in sorted(directory.rglob("*")):
            if not found.is_file() or found.suffix.lower() not in suffixes:
                continue
            here = relative(found, where)
            if sidecar(found, where).is_file() or _excused(here, excused):
                continue
            out.append(
                {"artefact": here, "expected": relative(sidecar(found, where), where)}
            )
    return out


def _excused(path: str, patterns: Sequence[str]) -> bool:
    """Whether the project already said this one is hand-made.

    Matched against the path as written and against its name alone, so `*.png` excuses
    a whole directory's worth without anybody spelling out the directory.
    """
    name = PurePosixPath(path).name
    return any(fnmatch(path, pattern) or fnmatch(name, pattern) for pattern in patterns)


def verify(root: str | Path = ".") -> dict:
    """Is every artefact the records claim to hold present, and still what it was.

    A report rather than a refusal: the answer to "what is missing" is a list, and one
    broken record should not hide the next.

    Both directions are asked (§PW41): every record's artefact is checked, **and** every
    produced file is checked for a record. The second is the expensive half — a paid
    mesh with no sidecar used to read as a sound project.
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

    nowhere = unrecorded(where)
    return {
        "root": str(where),
        "checked": len(ok) + len(missing) + len(changed) + len(unreadable),
        "sound": not (missing or changed or unreadable or nowhere),
        "ok": ok,
        "missing": missing,
        "changed": changed,
        "unreadable": unreadable,
        "unrecorded": nowhere,
    }


def _stamp() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
