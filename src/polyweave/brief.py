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

from .describe import Param, operation
from .errors import PolyweaveError


def _declared(here: Path):
    """Every readable declaration under the root, with the path it was read from."""
    from . import geometry as G
    from .cli import is_declaration

    for source in sorted(here.rglob("*.toml")):
        if ".polyweave" in source.parts or source.name.endswith(".accept.toml"):
            continue
        if not is_declaration(source):
            continue
        try:
            yield source.relative_to(here).as_posix(), G.read(source, root=here)
        except PolyweaveError:
            continue


def _declarations(here: Path) -> dict[str, str]:
    """Each declared asset's name, with the path of its declaration."""
    return {document["name"]: path for path, document in _declared(here)}


def _declaration(asset: str, here: Path) -> dict | None:
    """The declaration named `asset`, read back in words, where there is one."""
    from .geometry import review

    for path, document in _declared(here):
        if document["name"] == asset:
            said = review.describe(document)
            return {"path": path, "reads": said["reads"], "warnings": said["warnings"]}
    return None


def _builds(here: Path) -> dict[str, list[str]]:
    """What each declaration was built into, as its outputs' records say (§PW298)."""
    from . import provenance

    made: dict[str, list[str]] = {}
    for record in provenance._records(here):
        if record.get("kind") != "mesh":
            continue
        for one in record.get("inputs") or ():
            if one.get("role") == "declaration" and one.get("path"):
                made.setdefault(one["path"], []).append(record["artefact"]["path"])
    return {path: sorted(outputs) for path, outputs in made.items()}


def _parted(
    declaration: str | None, artefact: str | None, here: Path, built: dict | None = None
) -> dict | None:
    """Where a spec's render is of a mesh its asset's declaration does not build.

    A spec written for a mesh the project later replaced with a declaration measures a
    model no player sees, and its artefact still matches its own record (§PW298). None
    where the render's record names no mesh, or the declaration has no recorded build.
    """
    from . import provenance

    if not declaration or not artefact or not (here / artefact).is_file():
        return None
    try:
        record = provenance.read(here / artefact, here)
    except PolyweaveError:
        return None
    rendered = next(
        (i.get("path") for i in record.get("inputs") or () if i.get("role") == "mesh"),
        None,
    )
    made = (_builds(here) if built is None else built).get(declaration) or []
    if not rendered or not made or rendered in made:
        return None
    return {
        "declaration": declaration,
        "built": made,
        "rendered_from": rendered,
        "says": f"{artefact} is a render of {rendered}, and {declaration} builds "
        f"{', '.join(made)}: the spec measures a model the game may no longer draw. "
        "Render the build and point the spec's artefact at it; a bound read off the "
        "old render is a person's to set again",
    }


def _spec(asset: str, here: Path) -> Any:
    from . import accept

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
    from . import cache, provenance
    from .config import load

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
    from . import loop

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
    from . import purchase

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
    from . import project

    if not any(mark in asset for mark in "/.:"):
        return None
    return next((row for row in project._items(here) if row["id"] == asset), None)


def _named(item: dict) -> str:
    """The name an item's spec and ledger use: its file's, without the suffix."""
    return Path(item["artefact"] or item["declaration"] or item["id"]).stem


def _declared_item(item: dict, here: Path) -> dict | None:
    """An item's declaration, read back in the words its kind uses where one does."""
    from .cli import is_declaration

    path = item["declaration"]
    if item["kind"] == "line":
        return _line(item, here)
    if not path:
        return None
    if path.endswith(".toml") and is_declaration(here / path):
        from . import geometry as G
        from .geometry import review

        try:
            said = review.describe(G.read(here / path, root=here))
        except PolyweaveError as refused:
            return {"path": path, "refused": refused.as_dict()}
        return {"path": path, "reads": said["reads"], "warnings": said["warnings"]}
    return {"path": path, "kind": item["kind"]}


def _line(item: dict, here: Path) -> dict:
    """A line of the string table: its text in each locale, who says it, its verdict."""
    from . import words
    from .config import load

    where, locales, table = words.table(here)
    key = item["id"][len("line:") :]
    row = next(one for one in table if one["key"] == key)
    sha = words._digest(row, locales)
    latest = [one for one in words.held(here) if one["key"] == key]
    verdict = latest[-1] if latest else None
    speaker = load(here).get("words.speaker")
    return {
        "path": item["declaration"],
        "key": key,
        "row": row["row"],
        "text": {locale: row["cells"].get(locale) or "" for locale in locales},
        "speaker": (row["cells"].get(speaker) or "").strip() or None,
        "verdict": None
        if verdict is None
        else {
            "approved": verdict.get("approved"),
            **verdict.get("verdict", {}),
            # A verdict on the line as it read then; false once the text moved.
            "on_this_text": verdict.get("sha256") == sha,
        },
    }


def _dependents(path: str | None, here: Path) -> list[dict]:
    """What was made from this file, which a change to it reaches (§PW300)."""
    from . import provenance

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
    from . import loop

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
            (spec and spec.subject) or (declared and declared["path"]),
            artefact and artefact["path"],
            here,
        ),
    }
    answer["dependents"] = _dependents(
        (artefact and artefact["path"]) or (declared and declared.get("path")), here
    )
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
