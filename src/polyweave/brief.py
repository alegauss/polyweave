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
    from . import cache, provenance
    from .config import load

    if not spec or not spec.artefact:
        return None
    picture = here / spec.artefact
    answer: dict[str, Any] = {"path": spec.artefact, "present": picture.is_file()}
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


@operation("asset.brief")
def brief(
    asset: Annotated[str, Param("the asset, by the name its declaration and spec use")],
    root: Annotated[str, Param("the project the asset is in")] = ".",
) -> dict:
    """Where one asset stands, in one read: shape, bar, artefact, verdict and budget."""
    from . import loop

    here = Path(root).resolve()
    spec = _spec(asset, here)
    artefact = _artefact(spec, here)
    waiting = next(
        (row for row in loop.pending(here)["assets"] if row["asset"] == asset), None
    )
    declared = _declaration(asset, here)
    answer: dict[str, Any] = {
        "asset": asset,
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
        "last_verdict": _last_verdict(asset, here),
        "waiting_on_a_person": bool(waiting and waiting["waiting"]),
        "bought": _bought(artefact, here),
        # A render of a mesh the declaration no longer builds (§PW298).
        "parted": _parted(
            (spec and spec.subject) or (declared and declared["path"]),
            artefact and artefact["path"],
            here,
        ),
    }
    if not any(answer[k] for k in ("declaration", "spec", "last_verdict")):
        raise PolyweaveError(
            "op.unknown-argument",
            f"nothing in {here.name} is called {asset!r}: no declaration, spec or run",
            "name an asset by the name its declaration or its spec gives it",
            given=asset,
            allowed=loop.assets(here),
        )
    answer["digest"] = hashlib.sha256(
        json.dumps(answer, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return answer
