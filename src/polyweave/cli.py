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
    source: Path, document: dict, given: dict, preview: bool, root: Path
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
    return {
        "inputs": inputs,
        "params": {"made_by": "geometry.build", "given": given, "preview": preview},
    }


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


@operation("geometry.build")
def build_one(
    source: Annotated[str, Param("the declaration, as a path under the project")],
    *,
    out: Annotated[str, Param("where to write; its own folder if unset")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    given: Annotated[dict, Param("values set for the declaration's params")] = None,
    preview: Annotated[bool, Param("also write a cheap look: a silhouette")] = False,
    force: Annotated[bool, Param("build even where the stamp still matches")] = True,
) -> dict:
    """Build one declaration and say what came out; a refusal is an answer too."""
    from . import geometry as G

    here = Path(root).resolve()
    where = Path(source)
    where = where if where.is_absolute() else here / where
    given = dict(given or {})
    answer: dict = {"document": str(where), "status": "built", "outputs": []}
    try:
        document = G.read(where, root=here)
        folder = Path(out) if out else where.parent
        folder = folder if folder.is_absolute() else here / folder
        folder.mkdir(parents=True, exist_ok=True)
        mark = folder / f"{document['name']}{STAMP}"
        made = made_from(where, document, given, preview, here)
        key = stamp(made)
        if not force and mark.is_file():
            kept = json.loads(mark.read_text(encoding="utf-8"))
            if kept.get("stamp") == key and all(
                Path(one).is_file() for one in kept.get("outputs", ())
            ):
                return {**answer, "status": "cached", "outputs": kept["outputs"]}

        # The document and each of its variants (§PW103), one output apiece, named after
        # the member; a document with none is a family of one.
        members = [document] + [
            G.variant(document, one) for one in G.variants(document)
        ]
        built = [_member(one, folder, here, given, preview) for one in members]
        answer.update({k: v for k, v in built[0].items() if k != "name"})
        if len(built) > 1:
            answer["members"] = built
            answer["outputs"] = [path for one in built for path in one["outputs"]]
        _recorded(answer["outputs"], made, here)
        # The source rides in the stamp so the edit guard can name the declaration to
        # change instead of the file an agent was about to edit by hand (§PW133).
        stamped = {
            "stamp": key,
            "source": where.relative_to(here).as_posix()
            if where.is_relative_to(here)
            else str(where),
            "outputs": [str(Path(one).resolve()) for one in answer["outputs"]],
        }
        mark.write_text(json.dumps(stamped, indent=1) + "\n", encoding="utf-8")
    except PolyweaveError as refused:
        answer["status"] = "refused"
        answer["refusal"] = refused.as_dict()
    return answer


def _member(
    document: dict, folder: Path, here: Path, given: dict, preview: bool
) -> dict:
    """One member of a family built and written, and what it said."""
    from .geometry import review

    said = review.describe(document, **given)
    answer: dict = {
        "name": document["name"],
        "reads": said["reads"],
        "warnings": list(said["warnings"]),
    }
    mesh = folder / f"{document['name']}.glb"
    if document.get("voxels"):
        from .geometry import voxels

        written = voxels.write(
            document, mesh, root=here, mesh=_has_blender(), sheet=preview, **given
        )
        answer["says"] = written["says"]
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
    given: Annotated[dict, Param("values set for every declaration's params")] = None,
    preview: Annotated[bool, Param("also write a cheap look for each")] = False,
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
        build_one(
            source, out=out, root=root, given=given, preview=preview, force=False
        )
        for source in sorted(under.rglob("*.toml"))
        if is_declaration(source)
    ]


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
