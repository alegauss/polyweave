"""A kit of built pieces taken to a sitting in one call (§PW568).

Spinhold's Playdeck is twelve declarations, and each one went through the same shell
loop: build it, read its cost, render it, write its spec from the triangles it came to,
check it, and at the end type the members of a sitting by hand. Its `tools/art/look.py`
was the same loop again for its five models. This is that loop, kept:

- each declaration under `folder` is built as `geometry.build_all` builds it, a stamp
  that still matches building nothing;
- each mesh it writes is rendered at `rung` into `renders`, `<piece>.png`;
- a piece with no spec in `specs` is given a first one, `<piece>.accept.toml`: its
  triangles as measured with `headroom` over them, and every bound `bounds` names,
  each read off the mesh. A spec already there is the project's and is never touched;
- each render is checked against its spec, and the kit is laid out as one family on
  the review page.

A spec written here is a starting point a person tightens, which is why the answer
says which ones it wrote. Whether the pieces look right stays the person's verdict.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: The share over a piece's measured triangles its first spec allows, so a small edit
#: does not fail it and a doubling does.
HEADROOM = 0.25


def _first_spec(name: str, mesh: str, render: str, triangles: int, headroom: float,
                bounds: dict) -> str:
    """A piece's first spec as TOML: its triangle budget and the bounds asked for."""
    lines = [
        "# Written by geometry.kit from what the piece measured; tighten it",
        f"asset    = {json.dumps(name)}",
        f"artefact = {json.dumps(render)}",
        "",
        "[[predicate]]",
        'id      = "triangles"',
        'measure = "triangles"',
        f"of      = {json.dumps(mesh)}",
        f"max     = {math.ceil(triangles * (1.0 + headroom))}",
    ]
    for measure, bound in bounds.items():
        lines += ["", "[[predicate]]", f"id      = {json.dumps(measure)}",
                  f"measure = {json.dumps(measure)}", f"of      = {json.dumps(mesh)}"]
        lines += [f"{side:<7} = {float(value):g}" for side, value in bound.items()]
    return "\n".join(lines) + "\n"


def _bounds(stated: dict | None) -> dict:
    """`bounds` as {measure: {min, max}}, a bare number read as a max."""
    found = {}
    for measure, bound in (stated or {}).items():
        if isinstance(bound, int | float) and not isinstance(bound, bool):
            bound = {"max": bound}
        if not isinstance(bound, dict) or not bound or set(bound) - {"min", "max"}:
            raise PolyweaveError(
                "geom.bad-kit",
                f"the bound on {measure} is {bound!r}, not a min or a max",
                'give bounds as {"sharp_edge_share": {"max": 0.02}}, or a number for '
                "a max",
                given=measure,
            )
        found[str(measure)] = bound
    return found


class _Quiet:
    """The reporter a render inside the kit is handed: the kit reports for it."""

    def stage(self, stage, *, progress=None, note=None):
        return None

    def progress(self, value, *, note=None):
        return None

    def note(self, text):
        return None


@operation("geometry.kit", kind="bake", injects=("report",))
def kit(
    report,
    folder: Annotated[str, Param("the folder whose declarations make the kit")],
    *,
    out: Annotated[str, Param("where the meshes go; beside each if unset")] = None,
    renders: Annotated[str, Param("where the renders go; [paths] renders if unset")
                       ] = None,
    specs: Annotated[str, Param("where the specs are; [paths] specs if unset")] = None,
    rung: Annotated[str, Param("the rung each piece is rendered at",
                               choices=("sphere", "preview", "final"))] = "preview",
    headroom: Annotated[float, Param("the share over its triangles a first spec allows",
                                     lo=0.0)] = HEADROOM,
    bounds: Annotated[dict, Param('more bounds a first spec holds, as '
                                  '{"sharp_edge_share": {"max": 0.02}}')] = None,
    sitting: Annotated[str, Param("the sitting's folder; <work>/kit/<folder> if unset")
                       ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Build, render, spec and check every piece of a kit, and sit them for a person.

    A piece with no spec gets a first one from what it measured; one already written is
    left as it is. Answers each piece's verdict and where the sitting is.
    """
    from polyweave.kernel.config import load
    from polyweave.loop import accept, verdict

    from . import render as R
    from .make import _built, is_declaration

    config = load(root)
    here = config.root
    under = Path(folder)
    under = under if under.is_absolute() else here / under
    if not under.is_dir():
        raise PolyweaveError("geom.bad-kit", f"there is no folder at {folder}",
                             "name the folder holding the kit's declarations")
    wanted = _bounds(bounds)
    family = under.name
    drawn = Path(renders) if renders else config.path("paths.renders")
    held = Path(specs) if specs else config.path("paths.specs")
    drawn, held = (p if p.is_absolute() else here / p for p in (drawn, held))
    laid = Path(sitting) if sitting else config.path("paths.work") / "kit" / family
    laid = laid if laid.is_absolute() else here / laid

    def named(path: Path) -> str:
        return path.resolve().relative_to(here).as_posix()

    sources = [s for s in sorted(under.rglob("*.toml")) if is_declaration(s)]
    if not sources:
        raise PolyweaveError("geom.bad-kit", f"{folder} holds no declaration",
                             "name the folder the pieces' .toml declarations are in")
    report.stage("building", note=f"{len(sources)} declarations")
    pieces, refused, members, written = {}, {}, [], []
    for index, source in enumerate(sources):
        report.progress(index / len(sources), note=source.name)
        built = _built(source, out, str(here), None, False, False, True, strict=True)
        if built["status"] == "refused":
            refused[named(source)] = built["refusal"]
            continue
        for mesh in (Path(p) for p in built["outputs"] if str(p).endswith(".glb")):
            name = mesh.stem
            picture = drawn / f"{name}.png"
            R.bake(_Quiet(), out=named(picture) if picture.is_relative_to(here)
                   else str(picture), model=named(mesh), rung=rung, inline=False,
                   root=str(here))
            spec = held / f"{name}.accept.toml"
            if not spec.is_file():
                from .cost import read as costs

                spec.parent.mkdir(parents=True, exist_ok=True)
                spec.write_text(_first_spec(
                    name, named(mesh), named(picture), int(costs(mesh)["triangles"]),
                    float(headroom), wanted), encoding="utf-8", newline="\n")
                written.append(named(spec))
            checked = accept.check(accept.read(spec, here), picture, rung=rung,
                                   root=here)
            pieces[name] = {
                "mesh": named(mesh), "render": named(picture), "spec": named(spec),
                "passed": checked["passed"],
                **({"failed": checked["failed"]} if checked.get("failed") else {}),
            }
            members.append({"name": name, "spec": named(spec), "new": named(picture)})
    report.progress(1.0, note="laying the kit out for a person")
    sat = verdict.sitting({family: members}, out=str(laid), root=str(here)) \
        if members else None
    failing = sorted(n for n, p in pieces.items() if not p["passed"])
    return {
        "family": family,
        "pieces": pieces,
        "specs_written": written,
        **({"refused": refused} if refused else {}),
        "passed": not failing and not refused,
        **({"sitting": sat["manifest"], "page": sat["page"]} if sat else {}),
        "says": (f"{len(pieces)} pieces, {len(failing)} failing"
                 + (f" ({', '.join(failing)})" if failing else "")
                 + (f", {len(refused)} refused" if refused else "")
                 + (f"; {len(written)} first specs written, tighten them"
                    if written else "")
                 + (f"; the kit waits at {sat['page']} on the review page"
                    if sat else "")),
    }
