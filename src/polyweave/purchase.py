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

§PW18 is the other half. An agent may not decide that a mesh is worth money, and that
rule is right — but what it constrains is the **ceiling**, not each call, so a person
sets one in `[budget]` and the plugin spends against it without asking and refuses the
call that would pass it. The balance is read either side of a spend, and the difference
between those readings is what the call actually cost — the only form of that claim
anybody can check.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from . import post, provenance
from .config import FILENAME, load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: What a project may buy. `kind` in the record stays `fetch` for all of them.
BOUGHT = ("mesh", "texture")


def where(root: str | Path = ".") -> Path:
    """The ledger's own file, which belongs to the project and is committed with it."""
    config = load(root)
    return config.path("paths.purchases")


@operation("purchase.remaining")
def remaining(
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
    today: Annotated[
        str, Param("the date the ceiling is judged on; today if unset")
    ] = None,
) -> dict:
    """What is left of the ceiling a person set, against what has been spent.

    An agent may not decide that a mesh is worth money, and that rule is right. What it
    actually constrains is the **ceiling**, not each call — so the ceiling is approved
    once, with the whole plan in view, instead of five interruptions.
    """
    if isinstance(today, str):
        # By name the date arrives as text; in process it may already be a date.
        from datetime import date

        today = date.fromisoformat(today)
    declared = load(root).budget(today)
    already = spent(root)
    left = round(float(declared["credits"]) - already, 4)
    return {
        "declared": float(declared["credits"]),
        "spent": already,
        "left": max(0.0, left) if declared["spendable"] else 0.0,
        "expires": declared["expires"],
        "spendable": declared["spendable"] and left > 0,
        "why": declared["why"]
        or ("" if left > 0 else f"the budget of {declared['credits']} is used up"),
    }


@operation("purchase.allow")
def allow(
    cost: Annotated[float, Param("what the spend would cost", lo=0.0, unit="credits")],
    *,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
    today: Annotated[
        str, Param("the date the ceiling is judged on; today if unset")
    ] = None,
) -> dict:
    """Refuse a spend that would pass the ceiling. Never asks; the answer is the file.

    What is given up is the per-call veto. What is bought is an approval made once.
    """
    left = remaining(root, today)
    if not left["spendable"]:
        raise PolyweaveError(
            "fetch.budget-closed",
            f"nothing may be spent: {left['why']}",
            f"set `[budget] credits` and `expires` in {load(root).source or FILENAME}; "
            f"an absent or expired budget is never read as permission",
        )
    if float(cost) > left["left"]:
        raise PolyweaveError(
            "fetch.over-budget",
            f"this would spend {cost} of the {left['left']} credits left",
            f"raise `[budget] credits` above {left['spent'] + float(cost):g}, or ask "
            f"for something that costs less",
        )
    return left


def capture(
    source: bytes | str | Path,
    *,
    out: str | Path,
    task_id: str,
    credits: float = 0.0,
    balance_before: float | None = None,
    balance_after: float | None = None,
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
            given=bought,
            allowed=BOUGHT,
        )
    if not task_id:
        raise PolyweaveError(
            "fetch.no-task",
            "a purchase with no task id cannot be traced back to what was bought",
            "pass the service's own id for the task that produced this",
        )

    # What it really cost is the difference between two readings of the balance, not
    # what the caller believed it would cost. That is also what makes a claim that some
    # call is free verifiable rather than merely asserted.
    measured = (
        round(float(balance_before) - float(balance_after), 4)
        if balance_before is not None and balance_after is not None
        else None
    )
    charged = float(credits) if measured is None else measured

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
        "credits": charged,
        "expected_credits": float(credits),
        "balance_before": balance_before,
        "balance_after": balance_after,
        "bought": bought,
        "prompt": prompt,
    }
    if reference is not None:
        # Not relativised here: `build` does it for every path in `extra`, and this
        # having been the only call site that remembered to is §PW72.
        extra["reference"] = reference
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
        "credits": charged,
        "expected_credits": float(credits),
        "balance_before": balance_before,
        "balance_after": balance_after,
        "surprised": measured is not None and abs(measured - float(credits)) > 1e-9,
        "bought": bought,
        "prompt": prompt,
        # Off the record rather than off `extra`: the record is where a path is spelled
        # the one way both files agree on, and the ledger is committed too (§PW72).
        "reference": record.get("reference"),
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    append(entry, root=here)
    return entry


@operation("purchase.adopt")
def adopt(
    entries: Annotated[
        Any, Param("another ledger's entries, or the file holding them")
    ],
    *,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Bring a ledger somebody else kept into this one, spending nothing (§PW55).

    A project adopting the plugin already has a record of what it bought, in whatever
    shape its own client wrote — Cottony's is a `meshy.lock.json` holding a task id, the
    exact request, the cost and the sha256 of what went in and what came out. Replaying
    it is what stops one spend being recorded twice, and it costs nothing, because every
    claim in such a file is about a file already on disk.

    Each entry needs an `artefact`, a `sha256` and a `task_id`; the rest of the ledger's
    own fields are carried across where they are given. Mapping a foreign file's field
    names onto those is the caller's, and deliberately so: the service's format is not
    this plugin's to hard-code, and a project's own paths are the thing that must never
    be compiled in.

    **An entry is adopted only where the file is there and still hashes to what it
    claims.** The ledger is written last precisely so that it can never name an asset
    that is not there (§PW17), and importing past that rule would hand the project back
    the failure it started with: a receipt for a mesh nobody has. So a claim that no
    longer holds is reported instead, which is also the first time anything asks that
    question mechanically — a lock file records a hash and nothing ever compares it.

    Adopting twice is a no-op. The match is on the hash, never the remote id, for the
    same reason nothing else here keys off one: it is the identifier that stops
    existing.
    """
    here = Path(root).resolve()
    already_held = {e.get("sha256") for e in read(here)}
    report: dict[str, list] = {
        "adopted": [],
        "missing": [],
        "changed": [],
        "already": [],
    }
    fresh: list[dict] = []

    for stated in entries:
        entry = dict(stated)
        claimed = entry.get("sha256")
        if not entry.get("task_id"):
            raise PolyweaveError(
                "fetch.no-task",
                f"the entry for {entry.get('artefact')!r} carries no task id",
                "map the service's own id for the task onto `task_id`; an entry "
                "without one cannot be traced back to what was bought",
            )
        if not entry.get("artefact") or not claimed:
            raise PolyweaveError(
                "fetch.ledger-malformed",
                f"an entry for task {entry['task_id']!r} names no artefact or no hash",
                "map the file it bought onto `artefact` and its digest onto `sha256`; "
                "everything downstream keys off the local file and its hash",
            )

        artefact = here / entry["artefact"]
        if not artefact.is_file():
            report["missing"].append({**entry, "expected_at": str(artefact)})
            continue
        digest, length = provenance.sha256_of(artefact)
        if digest != claimed:
            report["changed"].append({**entry, "found": digest, "recorded": claimed})
            continue
        if claimed in already_held:
            report["already"].append(entry)
            continue

        already_held.add(claimed)
        fresh.append(_adopted(entry, length, here))

    if fresh:
        write_atomic(
            where(here), json.dumps(read(here) + fresh, indent=2, sort_keys=True) + "\n"
        )
        report["adopted"] = fresh
    report["credits"] = round(sum(float(e["credits"]) for e in fresh), 4)
    report["sound"] = not (report["missing"] or report["changed"])
    return report


def _adopted(entry: dict, length: int, root: Path) -> dict:
    """One foreign entry in this ledger's shape, with a record beside its artefact.

    A sidecar that already exists is left alone. This is a replay of something that
    happened, so a record somebody already wrote is the better account of it than one
    reconstructed from a lock file.
    """
    artefact = root / entry["artefact"]
    if not provenance.sidecar(artefact, root).is_file():
        provenance.write(
            provenance.build(
                "fetch",
                artefact,
                inputs=[provenance.source("reference", entry["reference"], root=root)]
                if entry.get("reference") and (root / entry["reference"]).is_file()
                else [],
                extra={
                    "task_id": entry["task_id"],
                    "credits": float(entry.get("credits", 0.0)),
                    "prompt": entry.get("prompt"),
                    "adopted": True,
                },
                root=root,
            ),
            root=root,
        )
    return {
        "artefact": provenance.relative(artefact, root),
        "sha256": entry["sha256"],
        "bytes": length,
        "task_id": entry["task_id"],
        "credits": float(entry.get("credits", 0.0)),
        "expected_credits": float(
            entry.get("expected_credits", entry.get("credits", 0.0))
        ),
        "balance_before": entry.get("balance_before"),
        "balance_after": entry.get("balance_after"),
        "surprised": bool(entry.get("surprised", False)),
        "bought": entry.get("bought", "mesh"),
        "prompt": entry.get("prompt"),
        "reference": entry.get("reference"),
        "at": entry.get("at")
        or datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        # What separates a replay from a spend. `spent` reads this, so money that was
        # gone before the ceiling existed does not eat it.
        "adopted": True,
    }


def append(entry: dict, *, root: str | Path = ".") -> Path:
    """Add one entry, rewriting the whole file so a reader never sees half a line."""
    path = where(root)
    held = read(root)
    held.append(entry)
    write_atomic(path, json.dumps(held, indent=2, sort_keys=True) + "\n")
    return path


@operation("purchase.ledger")
def read(
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> list[dict]:
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


@operation("purchase.spent")
def spent(
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> float:
    """What this project has spent against its ceiling, according to its own ledger.

    **An adopted entry does not count** (§PW55). A project bringing an existing ledger
    in bought those meshes before it had a ceiling here, and charging them to the one a
    person set for today would refuse the next call over money already gone. They stay
    in the ledger, because `held` is about assets and every one of them is an asset.
    """
    return round(
        sum(float(e.get("credits", 0.0)) for e in read(root) if not e.get("adopted")), 4
    )


@operation("purchase.find")
def find(
    sha: Annotated[str, Param("the sha256 of the file bought")],
    *,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict | None:
    """The entry for a file, looked up by **its hash rather than a remote id**.

    The remote id is the one that stops existing, so nothing downstream keys off it.
    """
    return next((e for e in read(root) if e.get("sha256") == sha), None)


@operation("purchase.held")
def held(root: Annotated[str, Param("the project whose ledger this is")] = ".") -> dict:
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
        # Every entry, adopted or not: this is the question about assets, and a mesh
        # bought before the ledger was adopted cost just as much as one bought after.
        "credits": round(sum(float(e.get("credits", 0.0)) for e in entries), 4),
        "against_ceiling": spent(here),
        "sound": not (missing or changed),
        "present": [e["artefact"] for e in present],
        "missing": missing,
        "changed": changed,
        "lost_credits": round(sum(float(e.get("credits", 0.0)) for e in missing), 4),
    }


def as_dict(entry: Any) -> dict:  # pragma: no cover - a convenience for callers
    return dict(entry)
