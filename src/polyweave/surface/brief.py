"""An asset's brief in one read (§PW131).

An asset's state is spread over four files: the geometry declaration, the acceptance
spec, the provenance record beside the artefact and the loop ledger. An agent starting
work opened each before it could say what was left. Roadkeep's `brief` starts a task in
one call; this starts an asset:

    python -m polyweave asset.brief --asset star_dim

One bounded answer: the declaration read back one line per part; each predicate with
its bound and where that bound came from; whether the artefact still matches its record
and whether the cache holds it; the last verdict and the predicates it failed; what the
budget has left where the asset was bought; and whether it waits on a person. A
`digest` over the answer lets a session holding it ask whether anything moved. It reads
files that exist and writes nothing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.layer import call, needed, part, sections
from polyweave.loop.declared import (
    _declared,
    _effect,
    _parted,
)


def _declaration(asset: str, here: Path) -> dict | None:
    """The declaration named `asset`, read back in words, where there is one."""
    for path, document in _declared(here):
        if document["name"] == asset:
            said = call(needed("declaration.describe"), document)
            return {"path": path, "reads": said["reads"], "warnings": said["warnings"]}
    return None


def _spec(asset: str, here: Path) -> Any:
    from polyweave.loop import accept

    for found in sorted(here.rglob(f"*{accept.SUFFIX}")):
        if ".polyweave" in found.parts:
            continue
        try:
            spec = accept.read(found)
        except PolyweaveError:
            continue
        if spec.asset == asset:
            return spec
    return None


def _predicates(spec: Any) -> list[dict]:
    out = []
    for p in spec.predicates:
        one: dict[str, Any] = {"id": p.id, "measure": p.measure}
        for side, value in (("min", p.minimum), ("max", p.maximum)):
            if value is not None:
                origin = p.origins.get(side) or {}
                one[side] = {"value": value, **origin} if origin else value
        out.append(one)
    return out


def _artefact(spec: Any, here: Path) -> dict | None:
    if not spec or not spec.artefact:
        return None
    return _artefact_at(spec.artefact, here)


def _artefact_at(path: str, here: Path) -> dict:
    """One artefact on disk against its record, and whether the cache holds it."""
    from polyweave.kernel import cache, provenance
    from polyweave.kernel.config import load

    picture = here / path
    answer: dict[str, Any] = {"path": path, "present": picture.is_file()}
    if not answer["present"]:
        return answer
    try:
        record = provenance.read(picture, here)
    except PolyweaveError:
        return {**answer, "recorded": False}
    digest, _ = provenance.sha256_of(picture)
    key = provenance.cache_key(record)
    work = load(here).path("paths.work")
    return {
        **answer,
        "recorded": True,
        "matches_record": digest == (record.get("artefact") or {}).get("sha256"),
        "rung": record.get("rung"),
        "made": record.get("produced_at"),
        "cached": cache.look(key, work=work) is not None,
        "sha256": digest,
    }


def _last_verdict(asset: str, here: Path) -> dict | None:
    from polyweave.loop import loop

    verdicts = [
        (run.get("way"), one)
        for run in loop.read(here)
        if run["asset"] == asset
        for one in run.get("verdicts", ())
    ]
    if not verdicts:
        return None
    way, last = max(verdicts, key=lambda pair: pair[1].get("at", 0.0))
    return {
        "way": way,
        "tool_passed": last["tool_passed"],
        "person_accepted": last["person_accepted"],
        "why": last.get("why", ""),
        "failed": [p["id"] for p in last.get("predicates", ()) if not p["passed"]],
    }


def _bought(artefact: dict | None, here: Path) -> dict | None:
    from polyweave.services import purchase

    if not artefact or not artefact.get("sha256"):
        return None
    entry = purchase.find(artefact["sha256"], root=str(here))
    if not entry:
        return None
    # The ceiling of the service this was bought from, never another one's (§PW162).
    # An entry nothing can attribute gets no ceiling rather than a guessed one.
    try:
        budget = purchase.remaining(str(here), service=entry.get("service"))
    except PolyweaveError as refused:
        if refused.code not in ("fetch.unknown-service", "fetch.service-unnamed"):
            raise
        budget = None
    return {"entry": entry, "budget": budget}


def _item(asset: str, here: Path) -> dict | None:
    """The inventory's row whose id this is, where it names one (§PW300).

    An id is a path or `line:<key>`, and a name is neither, so a name costs no walk.
    """
    from polyweave.surface import project

    if not any(mark in asset for mark in "/.:"):
        return None
    return next((row for row in project._items(here) if row["id"] == asset), None)


def _named(item: dict) -> str:
    """The name an item's spec and ledger use: its file's, without the suffix."""
    return Path(item["artefact"] or item["declaration"] or item["id"]).stem


def _declared_item(item: dict, here: Path) -> dict | None:
    """An item's declaration, read back in the words its kind uses (§PW300).

    A shape in its parts, a line in its locales, a cue as music.validate says it, an
    effect as its own table, and a picture as the style family it is held to.
    """
    path = item["declaration"]
    record = {} if item["kind"] == "line" else _record_of(item, here)
    # Read in its own layer's words, where a layer reads that kind (§PW505); a
    # reader that answers None leaves the item to what follows.
    reader = part(f"brief.read:{item['kind']}")
    if reader:
        said = call(reader, item, record, here)
        if said is not None or item["kind"] in ("line", "picture"):
            return said
    if not path:
        return None
    try:
        if item["kind"] == "sound" and path.endswith(".toml"):
            return _effect(item, path, record, here)
    except PolyweaveError as refused:
        return {"path": path, "refused": refused.as_dict()}
    read, described = part("declaration.read"), part("declaration.describe")
    declaring = part("declaration.is")
    if (path.endswith(".toml") and read and described and declaring
            and call(declaring, here / path)):
        try:
            said = call(described, call(read, here / path, root=here))
        except PolyweaveError as refused:
            return {"path": path, "refused": refused.as_dict()}
        return {"path": path, "reads": said["reads"], "warnings": said["warnings"]}
    return {"path": path, "kind": item["kind"]}


def _record_of(item: dict, here: Path) -> dict:
    """The record beside an item's artefact, or nothing where it has none."""
    from polyweave.kernel import provenance

    if not item["artefact"] or item["record"] in ("unrecorded", "missing"):
        return {}
    try:
        return provenance.read(here / item["artefact"], here)
    except PolyweaveError:
        return {}


def _loop(path: str | None, here: Path) -> bool:
    """Whether a sound is a loop, as sound.sitting decides: its cue's family says so."""
    from polyweave.kernel.config import load

    if not path:
        return False
    config = load(here)
    looped = {
        (Path(sound["folder"]) / f"{cue}.{sound['format']}").resolve()
        for sound in config.sounds().values()
        if sound["kind"] == "loop"
        for cue in sound["cues"]
    }
    return (here / path).resolve() in looped


def _dependents(path: str | None, here: Path) -> list[dict]:
    """What was made from this file, which a change to it reaches (§PW300)."""
    from polyweave.kernel import provenance

    if not path or path.startswith("line:"):
        return []
    return provenance.dependents(path, root=str(here))["artefacts"]


@operation("asset.brief")
def brief(
    asset: Annotated[
        str, Param("the asset's name, or an id project.inventory gave the item")
    ],
    root: Annotated[str, Param("the project the asset is in")] = ".",
) -> dict:
    """Where one item stands, in one read: shape, bar, artefact, verdict and budget.

    `asset` is a name, or any id `project.inventory` lists (§PW300): a picture, a
    sound, an effect or a line then answers with its row as `item`, and every answer
    names the artefacts made from it as `dependents`.
    """
    from polyweave.loop import loop

    here = Path(root).resolve()
    item = _item(asset, here)
    name = _named(item) if item and item["kind"] != "line" else asset
    spec = None if item and item["kind"] == "line" else _spec(name, here)
    artefact = (
        _artefact_at(item["artefact"], here)
        if item and item["artefact"]
        else _artefact(spec, here)
    )
    waiting = next(
        (row for row in loop.pending(here)["assets"] if row["asset"] == name), None
    )
    declared = _declared_item(item, here) if item else _declaration(asset, here)
    answer: dict[str, Any] = {
        "asset": asset,
        "item": item,
        "declaration": declared,
        "spec": None
        if spec is None
        else {
            "path": spec.path.relative_to(here).as_posix() if spec.path else None,
            "rung": spec.needs_rung(),
            "subject": spec.subject,
            "predicates": _predicates(spec),
        },
        "artefact": artefact,
        "last_verdict": _last_verdict(name, here),
        "waiting_on_a_person": bool(
            item["pending"] if item else waiting and waiting["waiting"]
        ),
        "bought": _bought(artefact, here),
        # A render of a mesh the declaration no longer builds (§PW298).
        "parted": _parted(
            (spec and spec.subject) or (declared and declared.get("path")),
            artefact and artefact["path"],
            here,
        ),
    }
    answer["dependents"] = _dependents(
        (artefact and artefact["path"]) or (declared and declared.get("path")), here
    )
    path = artefact and artefact["path"]
    # The window shows a picture's last gate beside it and loops a loop (§PW304); a
    # layer's own part of the brief is under its key (§PW505).
    for key, target in sections("brief").items():
        answer[key] = call(target, path, here)
    answer["loop"] = _loop(path, here)
    from polyweave.loop import extend

    # A bar or a build that rests on the project's own extension says so (§PW519).
    leaning = extend.depended(
        [p.measure for p in spec.predicates] if spec else [], path, here)
    if leaning:
        answer["extensions"] = leaning
    if not any(answer[k] for k in ("item", "declaration", "spec", "last_verdict")):
        raise PolyweaveError(
            "op.unknown-argument",
            f"nothing in {here.name} is called {asset!r}: no declaration, spec or run",
            "name an asset by the name its declaration or its spec gives it, or "
            "pass an id project.inventory lists",
            given=asset,
            allowed=loop.assets(here),
        )
    answer["digest"] = hashlib.sha256(
        json.dumps(answer, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return answer
