"""Which files a build ships a paid generator made, and through what (§PW248).

Read off the provenance records and the purchase ledger together, so it is the
services' and not the record format's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.layer import call, shipping
from polyweave.kernel.provenance import (
    ROOT,
    SUFFIX,
    _records,
    read,
    relative,
    sidecar,
)


def _lineage(path: str, where: Path, seen: set[str]) -> tuple[list[str], dict] | None:
    """The chain from `path` back to a purchase, and that purchase's record, if any.

    Walked through each record's inputs, depth first, so the first chain found is the
    one named; an input with no record is where a lineage ends, a file a person made.
    """
    if path in seen:
        return None
    seen.add(path)
    try:
        record = read(path, where)
    except PolyweaveError:
        return None
    if record.get("kind") == "fetch":
        return [path], record
    for one in record.get("inputs") or ():
        if one.get("path"):
            found = _lineage(one["path"], where, seen)
            if found:
                return [path, *found[0]], found[1]
    return None


@operation("provenance.generated")
def generated(
    paths: Annotated[
        list, Param("the files a build ships, or folders of them, under the project")
    ] = (),
    preset: Annotated[
        str, Param("a Godot project's export preset to read what ships off; the first")
    ] = "",
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """Which files a build ships a paid generator made, and through what (§PW248).

    Steam's content survey asks whether a game ships generated content, and the honest
    answer needs every shipped file's lineage: bought from a service directly, or made
    from something that was, through the records' inputs. `generated` lists each such
    file with the chain back to the purchase, the service and what was bought;
    `authored` the files whose lineage reaches no purchase; `unrecorded` the pictures,
    sounds, meshes, fonts and videos with no record, which no one can vouch for either
    way, and `unrecorded_code` the rest, which no generator made (§PW455). Without
    paths, a Godot project answers for what its export `preset` ships, and any other
    for every recorded artefact under it.
    """
    where = Path(root).resolve()
    files: list[str] = []
    # Which files ship is the engine's to say, asked of each layer that answers it for
    # a project of its kind (§PW502).
    for answers in [] if paths else shipping():
        said = call(answers, where, preset)
        if said is not None:
            shipped, paths = said
            break
    else:
        shipped = None
    for one in paths or ():
        target = Path(one)
        target = target if target.is_absolute() else where / target
        found = sorted(target.rglob("*")) if target.is_dir() else [target]
        for file in found:
            if file.is_file() and not file.name.endswith((SUFFIX, ".import", ".uid")):
                files.append(relative(file, where))
    if not paths:
        files = [record["artefact"]["path"] for record in _records(where)]
    made: list[dict] = []
    authored: list[str] = []
    unrecorded: list[str] = []
    drafts: list[str] = []
    known = _known(where)
    for path in dict.fromkeys(files):
        if not sidecar(path, where).is_file():
            unrecorded.append(path)
            continue
        # A free local draft is a placeholder, shown apart so it is never shipped as
        # the line (§PW324).
        if (_sidecar_params(path, where) or {}).get("rung") == "draft":
            drafts.append(path)
            continue
        found = _lineage(path, where, set())
        if found is None:
            authored.append(path)
            continue
        chain, bought = found
        made.append(
            {
                "path": path,
                "chain": chain,
                **_service_of(bought, chain[-1], where, known),
                "bought": bought.get("bought", ""),
                "direct": len(chain) == 1,
            }
        )
    media = [one for one in unrecorded if one.lower().endswith(MEDIA)]
    answer = {"generated": made, "authored": authored, "unrecorded": media,
              "unrecorded_code": [one for one in unrecorded if one not in media],
              "drafts": drafts}
    return {"preset": shipped, **answer} if shipped else answer


#: What a generator could have made, so an unrecorded one needs a person's word.
MEDIA = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".tga", ".exr", ".hdr",
         ".ktx", ".dds", ".wav", ".ogg", ".mp3", ".flac", ".opus", ".glb", ".gltf",
         ".obj", ".fbx", ".blend", ".dae", ".ttf", ".otf", ".woff", ".woff2", ".fnt",
         ".ogv", ".webm", ".mp4")


#: What a record written before services were named put where the name goes.
_UNNAMED = frozenset({"", "service"})


def _known(where: Path) -> tuple[list[str], dict[str, str]]:
    """The services the project declares, and each ledger entry's service by file."""
    from polyweave.kernel.config import load
    from polyweave.services import purchase

    try:
        declared = sorted(load(where).services())
    except PolyweaveError:
        declared = []
    try:
        ledger = {e.get("artefact"): e.get("service") for e in purchase.read(where)
                  if e.get("service")}
    except PolyweaveError:
        ledger = {}
    return declared, ledger


def _service_of(record: dict, path: str, where: Path, known: tuple) -> dict:
    """Which service a purchase's record says made it, or what it can be read off
    (§PW454): the ledger entry for the file, a `<service>:` task id, or a folder named
    for a declared service, each answered with how it was `inferred`. Where nothing
    says, the service is null with why and the remedy, never a placeholder."""
    named = record.get("service") or (record.get("engine") or {}).get("name", "")
    if named not in _UNNAMED:
        return {"service": named}
    declared, ledger = known
    if ledger.get(path):
        return {"service": ledger[path], "inferred": "ledger"}
    prefix = str(record.get("task_id") or "").partition(":")[0]
    if prefix in declared and ":" in str(record.get("task_id")):
        return {"service": prefix, "inferred": "task_id"}
    folders = [part for part in Path(path).parts[:-1] if part in declared]
    if folders:
        return {"service": folders[-1], "inferred": "folder"}
    return {
        "service": None,
        "why": f"the record of {path} names no service, and neither the ledger, its "
        "task id nor its folder says which made it",
        "fix": f'add "service": "<name>" to {relative(sidecar(path, where), where)}',
    }


def _sidecar_params(path: str, where: Path) -> dict | None:
    try:
        held = json.loads(sidecar(path, where).read_text(encoding="utf-8-sig"))
        return held.get("params")
    except (OSError, ValueError):
        return None
