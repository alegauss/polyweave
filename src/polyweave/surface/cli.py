"""`python -m polyweave build`: the command line over the geometry build.

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
import json
import sys

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry.make import (  # noqa: F401 - the CLI's own names
    SHAPE_KEYS,
    STAMP,
    build_all,
    build_one,
    compare_two,
    fit_one,
    is_declaration,
    made_from,
    settings,
    stamp,
)


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
    from polyweave.loop import accept

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
    from polyweave import readable

    readable()
    parser = command_line()
    stated = parser.parse_args(argv)
    if stated.command == "verify":
        return _verify(stated)
    if stated.command == "review":
        from polyweave.loop import review

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
