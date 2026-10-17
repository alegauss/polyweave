"""What a project declares, read the same way by accept and by the brief (§PW506).

A geometry declaration is the geometry layer's to read and to recognise, so it is asked
for by part; an effect's table is plain TOML any layer's item can name.
"""

from __future__ import annotations

from pathlib import Path

from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.layer import call, part


def _declared(here: Path):
    """Every readable declaration under the root, with the path it was read from."""
    read, declaring = part("declaration.read"), part("declaration.is")
    for source in sorted(here.rglob("*.toml")) if read and declaring else ():
        if ".polyweave" in source.parts or source.name.endswith(".accept.toml"):
            continue
        if not call(declaring, source):
            continue
        try:
            yield source.relative_to(here).as_posix(), call(read, source, root=here)
        except PolyweaveError:
            continue


def _declarations(here: Path) -> dict[str, str]:
    """Each declared asset's name, with the path of its declaration."""
    return {document["name"]: path for path, document in _declared(here)}


def _builds(here: Path) -> dict[str, list[str]]:
    """What each declaration was built into, as its outputs' records say (§PW298)."""
    from polyweave.kernel import provenance

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
    from polyweave.kernel import provenance

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


def _effect(item: dict, path: str, record: dict, here: Path) -> dict:
    """An sfx or vfx effect as its table declares it, and what a built one measures."""
    import tomllib

    tables = tomllib.loads((here / path).read_text(encoding="utf-8-sig")).get("effect")
    tables = tables if isinstance(tables, dict) else {}
    params = record.get("params") or {}
    if params.get("arrangement"):
        # A mix of several effects reads back as the cues it was mixed from (§PW313).
        return {"path": path, "arrangement": params["arrangement"],
                "cues": params.get("cues") or []}
    # The record names its effect; one written before it did is matched by its file.
    name = params.get("effect") or Path(item["id"]).stem
    if name not in tables:
        return {"path": path, "effects": sorted(tables)}
    return {"path": path, "effect": name, "table": tables[name]}
