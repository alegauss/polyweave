"""`python -m polyweave build`: a declaration built with no script of the project's.

The evidence is §PW101. Every consumer wrote the same few lines — read the document,
build it, write it, look at it — and a project written in GDScript has no natural place
to keep Python. So the plugin ships them, as a command whose answer is readable by an
agent: the readback, the report, the warnings and the findings, and a non-zero exit on a
refusal. `--json` is the same answer as data.

**A build that changed nothing costs nothing.** Each output gets a provenance record
beside it, and the build a stamp: that record's cache key, over the document, the values
set for it, every file it names, `--preview` and the plugin's version (§PW140). `--all`
skips a document whose stamp still matches, so a project's asset step is one line.

**Blender only where a node needs it.** A voxel build of the grid-native ops never
does; its cubes' mesh is written when Blender is there and left out when it is not.

`python -m polyweave verify` is the second (§PW111): every spec under `[paths] specs`
checked against the artefact it names, with no render, exiting non-zero when one fails
so a CI job can stand on it. Every other subcommand is derived from the registry, one
per operation, in `commands.py` (§PW125).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Annotated, Any

from .describe import Param, operation
from .errors import PolyweaveError

#: What a stamp beside a build's outputs is called.
STAMP = ".build.json"


def _value(text: str) -> Any:
    try:
        return float(text)
    except ValueError:
        return text


def settings(pairs: list[str]) -> dict:
    """`--set name=value`, each value a number where it reads as one."""
    out = {}
    for pair in pairs or ():
        name, equals, value = pair.partition("=")
        if not equals or not name.strip():
            raise PolyweaveError(
                "op.bad-setting",
                f"{pair!r} does not set anything",
                "write it as name=value, e.g. --set wing=3.5",
            )
        out[name.strip()] = _value(value.strip())
    return out


def _named_files(value: Any, root: Path, found: set) -> None:
    """Every string in a document that names a file under the root."""
    if isinstance(value, dict):
        for one in value.values():
            _named_files(one, root, found)
    elif isinstance(value, list):
        for one in value:
            _named_files(one, root, found)
    elif isinstance(value, str) and ("/" in value or "." in value):
        where = root / value
        if where.is_file():
            found.add(where)


def made_from(
    source: Path, document: dict, given: dict, preview: bool, root: Path,
    mesh: bool = True,
) -> dict:
    """What a build's outputs are made from, as a provenance record not yet written.

    One answer to "what made this" (§PW140): the stamp is this record's cache key, so
    the plugin's version and every flag that changes an output are in it, and the
    record written beside each output is the same one. The stamp used to hash the
    inputs alone, and a build was reported cached after the builder that made it had
    been fixed.
    """
    from . import provenance

    named: set = set()
    _named_files(document, root, named)
    inputs = [provenance.source("declaration", source, root)] + [
        provenance.source("named", where, root) for where in sorted(named)
    ]
    params = {"made_by": "geometry.build", "given": given, "preview": preview}
    if not mesh:
        # Only when asked, so every stamp written before §PW226 still matches.
        params["mesh"] = False
    return {"inputs": inputs, "params": params}


def stamp(made: dict) -> str:
    """What a build's outputs were made from, as one hash: the record's cache key."""
    from . import provenance

    return provenance.cache_key(provenance.planned("mesh", **made))


def _recorded(outputs: list[str], made: dict, root: Path) -> None:
    """A provenance record beside each output, like every other producer's."""
    from . import provenance

    for output in outputs:
        suffix = Path(output).suffix.lower()
        kind = "render" if suffix == ".png" else "mesh"
        provenance.write(provenance.build(kind, output, root=root, **made), root=root)


def _has_blender() -> bool:
    return importlib.util.find_spec("bpy") is not None


#: What `mesh` says on the two build operations (§PW226).
_MESH = Param("write the .glb beside a voxel build's cells; false for the cells alone")


@operation("geometry.build")
def build_one(
    source: Annotated[str, Param("the declaration, as a path under the project")],
    *,
    out: Annotated[str, Param("where to write; its own folder if unset")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    given: Annotated[dict, Param("params by name, or fields as voxels.cell")] = None,
    preview: Annotated[bool, Param("also write a cheap look: a silhouette")] = False,
    force: Annotated[bool, Param("build even where the stamp still matches")] = True,
    mesh: Annotated[bool, _MESH] = True,
) -> dict:
    """Build one declaration and say what came out; a refusal is an answer too.

    `given` sets a declared param by name, or a field of the declaration by its table
    and key, such as `voxels.cell`, for this build only (§PW317). The answer's `set`
    says what each one changed, and a key that names nothing is refused.
    """
    return _built(source, out, root, given, preview, force, mesh, strict=True)


def _set(document: dict, given: dict, strict: bool) -> tuple[dict, dict, dict, list]:
    """The declaration with `given` applied: its params, and the fields it overrides.

    A dotted key, `table.key`, overrides a field the declaration already has, with a
    value of the same kind, for this build only. A key that is neither a declared param
    nor such a field is refused where `strict`, and listed as not applied otherwise,
    never dropped without a word (§PW317).
    """
    import copy

    params = set(document.get("params") or {})
    fields = {
        f"{table}.{key}": value
        for table, own in document.items()
        if isinstance(own, dict) and table != "params"
        for key, value in own.items()
        if isinstance(value, int | float | str | bool)
    }
    built = copy.deepcopy(document)
    named: dict = {}
    said: dict = {}
    ignored: list = []
    for key, value in given.items():
        if key in params:
            named[key] = value
            said[key] = {"was": document["params"][key], "now": value}
            continue
        if key in fields and _alike(fields[key], value):
            table, _, field = key.partition(".")
            built[table][field] = value
            said[key] = {"was": fields[key], "now": value}
            continue
        if not strict:
            ignored.append(key)
            continue
        if key in fields:
            raise PolyweaveError(
                "op.bad-setting",
                f"--set {key}={value!r} is not a {type(fields[key]).__name__}, as "
                f"{key} is",
                f"set it to a value like {fields[key]!r}",
                given=key,
            )
        raise PolyweaveError(
            "op.bad-setting",
            f"--set {key} names nothing {document.get('name', 'this declaration')} "
            "declares, so it would change nothing",
            "set a declared param by name, or a field by its table and key, such as "
            "voxels.cell",
            given=key,
            allowed=sorted(params) + sorted(fields),
        )
    return built, named, said, ignored


def _alike(was, now) -> bool:
    """Whether `now` can stand where `was` did: a number for a number, else one kind."""

    def number(one):
        return isinstance(one, int | float) and not isinstance(one, bool)

    return number(was) and number(now) or type(was) is type(now)


def _built(source, out, root, given, preview, force, mesh, *, strict: bool) -> dict:
    from . import geometry as G

    here = Path(root).resolve()
    where = Path(source)
    where = where if where.is_absolute() else here / where
    given = dict(given or {})
    answer: dict = {"document": str(where), "status": "built", "outputs": []}
    try:
        document = G.read(where, root=here)
        document, named, said, ignored = _set(document, given, strict)
        if said:
            answer["set"] = said
        if ignored:
            answer["not_set"] = ignored
        folder = Path(out) if out else where.parent
        folder = folder if folder.is_absolute() else here / folder
        folder.mkdir(parents=True, exist_ok=True)
        mark = folder / f"{document['name']}{STAMP}"
        mesh = mesh and _wants_mesh(document)
        made = made_from(where, document, given, preview, here, mesh)
        given = named
        key = stamp(made)
        if not force and mark.is_file():
            kept = json.loads(mark.read_text(encoding="utf-8"))
            outputs = [str(_under(one, here)) for one in kept.get("outputs", ())]
            if kept.get("stamp") == key and all(Path(one).is_file() for one in outputs):
                return {**answer, "status": "cached", "outputs": outputs}

        # The document and each of its variants (§PW103), one output apiece, named after
        # the member; a document with none is a family of one.
        members = [document] + [
            G.variant(document, one) for one in G.variants(document)
        ]
        built = [_member(one, folder, here, given, preview, mesh) for one in members]
        answer.update({k: v for k, v in built[0].items() if k != "name"})
        if len(built) > 1:
            answer["members"] = built
            answer["outputs"] = [path for one in built for path in one["outputs"]]
        _recorded(answer["outputs"], made, here)
        # The source rides in the stamp so the edit guard can name the declaration to
        # change instead of the file an agent was about to edit by hand (§PW133).
        stamped = {
            "stamp": key,
            "source": _kept(where, here),
            "outputs": [_kept(Path(one), here) for one in answer["outputs"]],
        }
        # One set of bytes on every machine (§PW227): paths relative to the root and a
        # line ending that Windows' text mode does not turn into CRLF, so the stamp can
        # be committed beside the declaration it describes.
        mark.write_text(
            json.dumps(stamped, indent=1) + "\n", encoding="utf-8", newline="\n"
        )
    except PolyweaveError as refused:
        answer["status"] = "refused"
        answer["refusal"] = refused.as_dict()
    return answer


def _kept(path: Path, here: Path) -> str:
    """A path as a stamp keeps it: relative to the root where it is under it (§PW227).

    A path outside the tree stays absolute, since nothing relative could name it.
    """
    resolved = path.resolve()
    if resolved.is_relative_to(here):
        return resolved.relative_to(here).as_posix()
    return str(resolved)


def _under(kept: str, here: Path) -> Path:
    """A stamp's path read back: relative ones against the root, absolute as they are,
    so a stamp written before §PW227 still resolves."""
    path = Path(kept)
    return path if path.is_absolute() else here / path


def _wants_mesh(document: dict) -> bool:
    """Whether a voxel declaration asks for its cubes as a mesh as well (§PW226).

    A Godot project that draws the `.voxels.json` imports any `.glb` in its tree and
    never loads it, so `[voxels] mesh = false` writes the cells alone. A document with
    no cells always writes its mesh, since the mesh is all it makes.
    """
    stated = (document.get("voxels") or {}).get("mesh", True)
    if not isinstance(stated, bool):
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{document['name']}: voxels.mesh is {stated!r}",
            "write mesh = false for the cells alone, or leave it out for both",
        )
    return stated or not document.get("voxels")


def _cell_said(model: dict, warnings: list[str]) -> list[str]:
    """Which cell a voxel build used, and a warning where it drifts from the project's.

    The project's `[voxels] cell` exists so every actor is built on one cell (§PW229),
    so a document stating its own that differs is the drift to report.
    """
    cell, project = model["cell"], model.get("project_cell") or 0.0
    if model.get("cell_from") == "project":
        return [f"cell {cell:g}, the project's"]
    if project and abs(cell - project) > 1e-9:
        warnings.append(
            f"cell {cell:g} is this declaration's own, and the project's is "
            f"{project:g}: its cubes will not match the other actors'"
        )
    return []


def _unwanted(where: Path) -> None:
    """A mesh an earlier build wrote and this one was asked not to, taken back out.

    Only one polyweave recorded, so a hand-made `.glb` of the same name is left alone.
    """
    record = where.with_name(where.name + ".prov.json")
    if where.is_file() and record.is_file():
        where.unlink()
        record.unlink()


def _member(
    document: dict, folder: Path, here: Path, given: dict, preview: bool,
    wanted: bool = True,
) -> dict:
    """One member of a family built and written, and what it said."""
    from .geometry import review

    said = review.describe(document, root=here, **given)
    answer: dict = {
        "name": document["name"],
        "reads": said["reads"],
        "warnings": list(said["warnings"]),
    }
    mesh = folder / f"{document['name']}.glb"
    if document.get("voxels"):
        from .geometry import voxels

        if not wanted:
            _unwanted(mesh)
        written = voxels.write(
            document, mesh, root=here, mesh=wanted and _has_blender(), sheet=preview,
            **given,
        )
        answer["says"] = written["says"]
        answer["reads"] += _cell_said(written["model"], answer["warnings"])
        answer["findings"] = [
            f"{one['check']}: {one['says']}"
            for one in written["model"]["checks"]["findings"]
        ]
        answer["outputs"] = [
            written[key] for key in ("artefact", "voxels", "sheet") if written.get(key)
        ]
        return answer
    from .geometry.build import write

    written = write(document, mesh, root=here, **given)
    answer["warnings"] += [
        one for one in written["report"]["warnings"] if one not in answer["warnings"]
    ]
    answer["says"] = f"a mesh of {len(written['output']['faces'])} faces"
    answer["outputs"] = [written["artefact"]]
    if preview:
        answer["outputs"].append(_silhouette(written["output"], folder, document))
    return answer


def _silhouette(mesh: dict, folder: Path, document: dict) -> str:
    """A mesh's front outline as a picture, the cheapest look at it: no renderer."""
    import numpy as np
    from PIL import Image

    from .normalise import project

    mask = project(mesh, grid=256)
    picture = Image.fromarray(np.where(mask, 40, 244).astype(np.uint8), "L")
    where = folder / f"{document['name']}.preview.png"
    picture.save(where)
    return str(where)


#: The top-level keys that make a TOML file a declaration rather than a config, a spec
#: or a lock. Decided before any refusal, so a shape that fails is reported (§PW123).
SHAPE_KEYS = ("nodes", "voxels")


def is_declaration(source: Path) -> bool:
    """Whether a TOML file is meant as a shape, whatever else is wrong with it.

    A file that does not parse is counted as one: it cannot say it is something else,
    and passing over it silently is how an asset drops out of the build.
    """
    import tomllib

    try:
        stated = tomllib.loads(source.read_text(encoding="utf-8-sig"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return True
    return any(key in stated for key in SHAPE_KEYS)


@operation("geometry.build_all")
def build_all(
    folder: Annotated[str, Param("the folder whose declarations are built")],
    *,
    out: Annotated[str, Param("where to write; each one's folder if unset")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    given: Annotated[dict, Param("params or fields, for every declaration")] = None,
    preview: Annotated[bool, Param("also write a cheap look for each")] = False,
    mesh: Annotated[bool, _MESH] = True,
) -> list[dict]:
    """Every declaration under a folder, skipping the ones whose stamp still matches.

    Only files that are not shapes at all are passed over. §PW123: the walk used to
    skip any file `read` refused, so a declaration with a misspelt key vanished from
    the build with nothing printed and an exit of 0 — on the one path a project's asset
    step actually runs. A declaration that fails now comes back `refused`, as a single
    build does.
    """
    here = Path(root).resolve()
    under = Path(folder)
    under = under if under.is_absolute() else here / under
    return [
        # A key one declaration does not take is said on its answer, not refused: the
        # same `given` goes to every declaration in the folder.
        _built(source, out, root, given, preview, False, mesh, strict=False)
        for source in sorted(under.rglob("*.toml"))
        if is_declaration(source)
    ]


@operation("geometry.fit")
def fit_one(
    source: Annotated[str, Param("the voxel declaration, as a path under the project")],
    reference: Annotated[
        str, Param("a drawing or a mesh under the project to fit its proportions to")
    ],
    *,
    views: Annotated[
        list, Param("the views scored, of front, side and top; a drawing is front only")
    ] = None,
    budget: Annotated[int, Param("how many samples the search may build", lo=1)] = 400,
    points: Annotated[int, Param("the grid points per parameter", lo=2)] = 7,
    sheet: Annotated[str, Param("where the best model's contact sheet goes")] = None,
    write: Annotated[
        bool, Param("put the best values into the declaration's [params]")
    ] = False,
    boxed: Annotated[
        bool, Param("score shape inside each view's box, not the box itself")
    ] = False,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Fit a voxel declaration's [search] parameters to a drawing or a mesh (§PW230).

    Answers the best values, the overlap per view and the model's reading; `write` puts
    the best values into the declaration, so the next build is the fitted model. Each
    view's aspect gap and the values bound by their ranges are named (§PW263).
    """
    from . import geometry as G
    from .geometry import voxel_fit

    here = Path(root).resolve()
    where = Path(source)
    where = where if where.is_absolute() else here / where
    document = G.read(where, root=here)
    found = voxel_fit.fit(
        document, reference, views=tuple(views or ("front",)), root=here,
        budget=budget, points=points, sheet=sheet, boxed=boxed,
    )
    answer = {k: v for k, v in found.items() if k != "model"}
    answer.update(document=_kept(where, here), reference=reference, written=[])
    if write:
        answer["written"] = _write_params(where, found["best"], here)
    return answer


@operation("geometry.compare")
def compare_two(
    first: Annotated[
        str, Param("a .voxels.json, or a voxel declaration to build, under the project")
    ],
    second: Annotated[str, Param("the other one, either kind")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Two voxel models compared cell by cell, materials by name (§PW240).

    Answers whether they hold the same cells wearing the same materials, the cells only
    in one and those repainted, and how the grids differ. A rewrite of a declaration
    holds `same` to prove it changed nothing.
    """
    from .geometry import voxel_compare

    return voxel_compare.compared(first, second, root=root)


def _write_params(where: Path, best: dict, here: Path) -> list[str]:
    """The best values put into the declaration's [params], the rest of it untouched.

    Each fitted line keeps its comment and the file keeps its own line endings; the
    declaration is read again afterwards, and restored if it no longer reads.
    """
    import re

    from . import geometry as G

    original = where.read_bytes()
    lines = original.decode("utf-8-sig").splitlines(keepends=True)
    start = next((n for n, line in enumerate(lines)
                  if re.match(r"\s*\[params\]\s*(#.*)?$", line.rstrip("\r\n"))), None)
    if start is None:
        raise PolyweaveError(
            "geom.bad-fit",
            f"{where.name} keeps its parameters somewhere other than a [params] table",
            "write them as a [params] table, one per line, and fit again",
        )
    end = next((n for n in range(start + 1, len(lines))
                if re.match(r"\s*\[", lines[n])), len(lines))
    written = []
    for name, value in best.items():
        pattern = re.compile(
            rf"^(\s*{re.escape(name)}\s*=\s*)([^#\r\n]*?)(\s*(#.*)?)(\r?\n?)$"
        )
        for n in range(start + 1, end):
            match = pattern.match(lines[n])
            if match:
                lead, _, tail, _, ending = match.groups()
                lines[n] = f"{lead}{float(value):.6g}{tail}{ending}"
                written.append(name)
                break
    where.write_bytes("".join(lines).encode("utf-8"))
    try:
        G.read(where, root=here)
    except PolyweaveError:
        where.write_bytes(original)
        raise
    return written


def _printed(answer: dict) -> list[str]:
    lines = [f"{answer['status']:<8} {answer['document']}"]
    if answer["status"] == "refused":
        refusal = answer["refusal"]
        lines.append(f"  {refusal['code']}: {refusal['message']}")
        if refusal.get("remedy"):
            lines.append(f"  do: {refusal['remedy']}")
        return lines
    for member in answer.get("members") or [answer]:
        if answer.get("members"):
            lines.append(f"  {member['name']}:")
        indent = "    " if answer.get("members") else "  "
        lines += [f"{indent}{one}" for one in member.get("reads", ())]
        if member.get("says"):
            lines.append(f"{indent}= {member['says']}")
        lines += [f"{indent}warning: {one}" for one in member.get("warnings", ())]
        lines += [f"{indent}finding: {one}" for one in member.get("findings", ())]
        lines += [f"{indent}wrote {one}" for one in member.get("outputs", ())]
    return lines


def _verify(stated: argparse.Namespace) -> int:
    """`verify`: the specs as a gate, one line per spec, non-zero when one fails."""
    from . import accept

    found = accept.verify(stated.root, under=stated.specs)
    if stated.json:
        print(json.dumps(found, indent=1))
    else:
        for one in found["specs"]:
            print(f"{one['status']:<10} {one['spec']}")
            for line in one.get("failed", ()):
                print(f"  {line}")
            if one["status"] == "refused":
                print(f"  {one['refusal']['code']}: {one['refusal']['message']}")
            if one["status"] == "missing":
                print(f"  no file at {one['artefact']}")
            if one["status"] == "unanchored":
                print("  names no artefact; add `artefact = <path>` to hold it to this")
            screen = one.get("screen") or {}
            for line in screen.get("failed", ()):
                print(f"  on screen: {line}")
            if screen.get("status") == "refused":
                print(f"  on screen: {screen['refusal']['message']}")
            if one.get("disagree"):
                print(f"  {one['disagree']}")
        counted = [f"{n} {k}" for k, n in found["counts"].items() if n]
        print(", ".join(counted) or "no specs")
    return 0 if found["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    """The command line; returns the exit status."""
    from . import readable

    readable()
    parser = command_line()
    stated = parser.parse_args(argv)
    if stated.command == "verify":
        return _verify(stated)
    if stated.command == "review":
        from . import review

        return review.run(stated.root, stated.port)
    if stated.command != "build":
        from . import commands as derived

        return derived.run(stated)

    if bool(stated.document) == bool(stated.folder):
        parser.error("name one document, or a folder with --all")
    try:
        given = settings(stated.set)
    except PolyweaveError as refused:
        print(
            f"{refused.code}: {refused.message}\n  do: {refused.remedy}",
            file=sys.stderr,
        )
        return 2
    how = {
        "out": stated.out,
        "root": stated.root,
        "given": given,
        "preview": stated.preview,
        "mesh": not stated.no_mesh,
    }
    # Blender's exporter logs its progress to stdout, and stdout is where the answer
    # goes, so a `--json` answer came out with export chatter in front of it. The work
    # talks to stderr; stdout carries the answer alone.
    with contextlib.redirect_stdout(sys.stderr):
        answers = (
            build_all(stated.folder, **how)
            if stated.folder
            else [build_one(stated.document, **how)]
        )
    if stated.json:
        print(json.dumps(answers if stated.folder else answers[0], indent=1))
    else:
        for answer in answers:
            print("\n".join(_printed(answer)))
    return 1 if any(one["status"] == "refused" for one in answers) else 0


def command_line() -> argparse.ArgumentParser:
    """Every command and flag, built without running anything, so a document that
    spells a command can be parsed against it (§PW138)."""
    parser = argparse.ArgumentParser(prog="python -m polyweave")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser(
        "build", help="build a declaration, or every one under a folder"
    )
    build.add_argument("document", nargs="?", help="the declaration to build")
    build.add_argument(
        "--all", dest="folder", help="build every declaration under a folder"
    )
    build.add_argument(
        "--out", help="where to write; the document's own folder by default"
    )
    build.add_argument(
        "--root", default=".", help="the project the paths resolve against"
    )
    build.add_argument(
        "--set", action="append", default=[], help="name=value, repeatable"
    )
    build.add_argument("--preview", action="store_true", help="also write a cheap look")
    build.add_argument(
        "--no-mesh", action="store_true", help="a voxel build's cells alone, no .glb"
    )
    build.add_argument("--json", action="store_true", help="print the answer as data")
    verify = commands.add_parser(
        "verify", help="check every committed artefact against its acceptance spec"
    )
    verify.add_argument(
        "--root", default=".", help="the project the paths resolve against"
    )
    verify.add_argument("--specs", help="where the specs are; [paths] specs by default")
    verify.add_argument("--json", action="store_true", help="print the answer as data")
    review = commands.add_parser(
        "review", help="serve one local page to look at sittings and answer them"
    )
    review.add_argument(
        "--root", default=".", help="the project the paths resolve against"
    )
    review.add_argument(
        "--port", type=int, default=0, help="the port on 127.0.0.1; any free one if 0"
    )
    # Every registered operation, and the first reads, derived from the registry
    # (§PW125); `build` and `verify` keep their own shape, since consumers call them.
    from . import commands as derived

    derived.add_operations(commands)
    return parser
