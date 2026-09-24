"""A family stated, not scripted (§PW120).

Cottony has three port scripts, about a hundred lines each, and they are one skeleton:
build or ingest the models, search their rig against their specs, bake the accepted ones
where the game reads them, and record the run. Every later family would be another copy
with its own small mistakes, such as a cache hit charged as a render. So a family file
states only what differs, and `port` runs the skeleton:

    family = "stars"
    rig    = "searched"                  # or "given", with [given]
    budget = 24

    [search.exposure]
    min = -1.0
    max = 1.0

    [[member]]
    name  = "star_dim"
    spec  = "docs/accept/star_dim.accept.toml"
    model = "assets/3d/star.glb"         # or declaration = "shapes/star.toml"
    fixes = { material = { base_color = "#FFC43F" } }
    out   = ".polyweave/stars/star_dim.png"
    bake  = "sprites/star_dim.png"

One rig is searched against every member at once (`search.family`), every bake counts
itself into the ledger run when one is open (`loop.recording`), and nothing is baked
unless every member passes. Whether the look is right stays a person's verdict.
"""

from __future__ import annotations

import contextlib
import tomllib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Annotated

from . import accept, loop, search
from .describe import Param, operation
from .errors import PolyweaveError

#: How a family's rig is arrived at.
RIGS = ("searched", "given")

#: What a family file and each of its members may say.
FAMILY_KEYS = ("family", "rig", "budget", "search", "given", "member")
MEMBER_KEYS = ("name", "spec", "model", "declaration", "fixes", "out", "bake")


def read(path: str | Path, root: str | Path = ".") -> dict:
    """A family file, refused where it could not be ported as written."""
    where = Path(path)
    where = where if where.is_absolute() else Path(root) / where
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PolyweaveError(
            "search.bad-family",
            f"there is no family file at {where}",
            "write one naming the family, its rig and its members",
        ) from None
    unknown = sorted(set(declared) - set(FAMILY_KEYS))
    if unknown:
        _refuse(f"a family file has no {', '.join(unknown)}", ", ".join(FAMILY_KEYS))
    rig = declared.get("rig", "searched")
    if rig not in RIGS:
        _refuse(f"rig {rig!r} is neither of {', '.join(RIGS)}", "searched or given")
    if rig == "searched" and not declared.get("search"):
        _refuse("a searched rig names no axis", "add a [search.<param>] range")
    if rig == "given" and not declared.get("given"):
        _refuse(
            "a given rig gives no values", "add a [given] table of the rig's values"
        )
    members = declared.get("member") or []
    if not members:
        _refuse("a family with no members ports nothing", "add a [[member]]")
    for one in members:
        extra = sorted(set(one) - set(MEMBER_KEYS))
        if extra:
            _refuse(f"a member has no {', '.join(extra)}", ", ".join(MEMBER_KEYS))
        missing = [k for k in ("name", "spec", "out") if k not in one]
        if missing or ("model" in one) == ("declaration" in one):
            _refuse(
                f"member {one.get('name', '?')!r} does not say "
                + (
                    ", ".join(missing)
                    if missing
                    else "exactly one of model and declaration"
                ),
                "give each member a name, a spec, an out, and a model or a declaration",
            )
    return {**declared, "rig": rig, "path": where}


def _refuse(message: str, takes: str) -> None:
    raise PolyweaveError("search.bad-family", message, f"it takes {takes}")


def port(
    path: str | Path,
    *,
    root: str | Path = ".",
    run: dict | None = None,
    bake: Callable | None = None,
    build: Callable | None = None,
) -> dict:
    """Run a family's port: build, search or take the rig, bake if every member passes.

    `bake` is the renderer, `render.bake` unless a test stands one in; `build` turns a
    declaration into a mesh, `cli.build_one` by default. With `run` open, every bake
    counts itself into it; the run is still judged and closed by whoever gave the
    verdict.
    """
    from . import render as R
    from .cli import build_one

    here = Path(root).resolve()
    family = read(path, here)
    draw = bake or R.bake
    making = build or build_one
    # The axes are the family's, not any one member's: each spec is handed them, and a
    # given rig is its values held as ranges of one point.
    axes = family.get("search") or {
        name: {"min": value, "max": value} for name, value in family["given"].items()
    }
    members, specs = [], {}
    for one in family["member"]:
        model = one.get("model") or _built(making, one, here)
        spec = replace(accept.read(one["spec"], here), search=dict(axes))
        specs[one["name"]] = (spec, model, one)
        fixed = {**(one.get("fixes") or {}), "model": model}
        members.append(
            {
                "name": one["name"],
                "spec": spec,
                "evaluate": search.renderer(
                    spec, out=one["out"], root=here, fixed=fixed, bake=draw
                ),
            }
        )

    recording = loop.recording(run) if run is not None else contextlib.nullcontext()
    with recording:
        if family["rig"] == "searched":
            found = search.family(
                members,
                name=family.get("family", "family"),
                ranges=family["search"],
                budget=int(family.get("budget", search.BUDGET)),
            )
            values, passed = found["best"], found["passed"]
        else:
            values = dict(family["given"])
            answers = {m["name"]: m["evaluate"](values) for m in members}
            found = {
                "members": answers,
                "passed": all(a["passed"] for a in answers.values()),
            }
            passed = found["passed"]
        baked = _baked(draw, specs, values, here) if passed else []

    return {
        "family": family.get("family"),
        "rig": family["rig"],
        "values": values,
        "passed": passed,
        "members": {
            name: {
                "passed": answer.get("passed"),
                "failed": answer.get("failed", []),
            }
            for name, answer in found.get("members", {}).items()
        },
        **({"conflict": found["conflict"]} if found.get("conflict") else {}),
        "baked": baked,
        "says": (
            f"every member passed; baked {len(baked)} for a person to look at"
            if passed
            else "not every member passed, so nothing was baked"
        ),
    }


@operation("port.run", kind="search")
def ported(
    family: Annotated[str, Param("the family file, as a path under the project")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    run: Annotated[dict, Param("an open loop run every render counts into")] = None,
) -> dict:
    """Port a family from its file: build, search as one, bake if every member passes.

    The verdict on the look stays a person's, given with `verdict.judge`.
    """
    return port(family, root=root, run=run)


def _built(making: Callable, member: dict, here: Path) -> str:
    """A declared member's mesh, built the way `python -m polyweave build` builds it."""
    answer = making(member["declaration"], root=here, force=False)
    if answer.get("status") == "refused":
        raise PolyweaveError.from_dict(answer["refusal"])
    meshes = [p for p in answer.get("outputs", ()) if str(p).endswith(".glb")]
    if not meshes:
        raise PolyweaveError(
            "search.bad-family",
            f"{member['declaration']} built no mesh for {member['name']}",
            "give the member a model, or a declaration that writes a .glb",
        )
    return str(Path(meshes[0]).resolve().relative_to(here).as_posix())


def _baked(draw: Callable, specs: dict, values: dict, here: Path) -> list[dict]:
    """Every member with a `bake` target rendered there at the top rung, and checked."""

    class Quiet:
        def stage(self, stage, *, progress=None, note=None):
            return None

        def progress(self, value, *, note=None):
            return None

        def note(self, text):
            return None

    out = []
    for name, (spec, model, one) in specs.items():
        if not one.get("bake"):
            continue
        draw(
            Quiet(),
            out=one["bake"],
            rung="final",
            root=str(here),
            inline=False,
            model=model,
            **(one.get("fixes") or {}),
            **values,
        )
        checked = accept.check(spec, here / one["bake"], root=here)
        out.append({"name": name, "artefact": one["bake"], "passed": checked["passed"]})
    return out
