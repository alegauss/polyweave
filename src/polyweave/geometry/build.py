"""The twenty lines between a declaration and a mesh.

The evidence is §PW60. Every piece either side of this was built and nothing composed
them: each `op` is a function in `solid`, `solver` or `custom`; `expand` resolves every
expression and instances every repeat; `order` returns the nodes in an order where each
input is built before what needs it — a walker's scaffolding with no walker on it — and
`review.report` takes the built meshes from its caller, which every test supplied by
hand. So `docs/specs/geometry.md` described a build that no call in the package could
perform, and nothing under `src/` imported `polyweave.geometry` at all.

**One table, read twice.** `BUILDS` maps an `op` to the adapter that shapes a node's own
fields into the call, and it is the only list of op names in the package that decides
anything. `review` reads it too, so a document naming an op nothing builds is a warning
before it is a refusal rather than a surprise at build time — the alternative was a
second enumeration in `review._says`, which would have drifted from this one.

**A repeated node's id names the whole set.** Sixty-four seats build as sixty-four
meshes and are joined into the one mesh their id stands for, which is what lets the tray
be one boolean rather than sixty-four.

**`at` places an instance and is applied last**, because it is the field that makes a
repeat mean anything: a seat differs from its sixty-three siblings in nothing but where
it sits. `transform` is the exception, since `at` is its own argument there.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError
from . import custom, expand, order, refers_to, solver
from . import outline as O
from . import solid as S

__all__ = ["BUILDS", "build", "builds"]


def _outline(instance: dict, root: Any, field: str = "outline") -> np.ndarray:
    stated = instance.get(field)
    if stated is None:
        raise PolyweaveError(
            "geom.bad-outline",
            f"this node has no {field} to build from",
            f"give it an `{field}` naming a shape, an image or points",
        )
    return O.resolve(stated, root=root)


def _rest(instance: dict, *skip: str) -> dict:
    """A node's remaining fields, as keyword arguments to the op that takes them.

    An op's own optional arguments — `steps`, `front`, `profile`, `resolution` — are
    written on the node beside its required ones, so they arrive the same way.
    """
    kept = ("steps", "front", "profile", "resolution", "crown")
    return {k: v for k, v in instance.items() if k in kept and k not in skip}


def _primitive(node, instance, built, root):
    return S.primitive(
        str(instance.get("kind", "cube")),
        float(instance.get("size", 1.0)),
        **_rest(instance, "front", "profile", "resolution", "crown"),
    )


def _prism(node, instance, built, root):
    return S.prism(
        _outline(instance, root), float(instance["depth"]), **_rest(instance, "steps")
    )


def _plate(node, instance, built, root):
    return S.plate(
        instance["rect"],
        float(instance["depth"]),
        float(instance.get("corner", 0.0)),
        **_rest(instance, "steps"),
    )


def _crowned(node, instance, built, root):
    return S.crowned(
        _outline(instance, root),
        float(instance["depth"]),
        float(instance["crown"]),
        **_rest(instance, "crown"),
    )


def _annulus(node, instance, built, root):
    # A number is a radius and anything else is an outline (§PW65), so the two edges
    # resolve the same way every other outline on a node does.
    return S.annulus(
        _edge(instance["outer"], root),
        _edge(instance["inner"], root),
        float(instance["depth"]),
        **_rest(instance, "profile", "resolution", "crown"),
    )


def _edge(stated: Any, root: Any) -> Any:
    return stated if isinstance(stated, int | float) else O.resolve(stated, root=root)


def _inflate(node, instance, built, root):
    return S.inflate(
        _outline(instance, root),
        float(instance["thickness"]),
        **_rest(instance, "steps", "front", "crown"),
    )


def _union(node, instance, built, root):
    return S.union(*(built[one] for one in refers_to(node)))


def _transform(node, instance, built, root):
    return S.transform(
        built[refers_to(node)[0]],
        at=instance.get("at", (0, 0, 0)),
        scale=instance.get("scale", (1, 1, 1)),
        rotate=instance.get("rotate", (0, 0, 0)),
    )


def _carve(node, instance, built, root):
    return solver.build(
        built[node["into"]],
        cutter=built[node["cutter"]],
        bevel_by=float(instance.get("bevel", 0.0)),
    )


def _bevel(node, instance, built, root):
    return solver.build(
        built[refers_to(node)[0]], bevel_by=float(instance.get("bevel", 0.0))
    )


def _custom(node, instance, built, root):
    return custom.build(node, instance, built, root=root)


#: Every op a declaration may name, and what turns its fields into a mesh. The one list
#: of op names in the package that decides anything; `review` reads it rather than
#: keeping a second.
BUILDS: dict[str, Callable] = {
    "primitive": _primitive,
    "prism": _prism,
    "plate": _plate,
    "crowned": _crowned,
    "annulus": _annulus,
    "inflate": _inflate,
    "union": _union,
    "transform": _transform,
    "carve": _carve,
    "bevel": _bevel,
    "custom": _custom,
}

#: The ops that consume `at` themselves, so the placement below leaves them alone.
PLACES = ("transform",)


def builds(op: str) -> bool:
    """Whether anything here builds that op. What `review` asks before warning."""
    return op in BUILDS


def build(
    document: dict, *, root: str | Path = ".", manifold: bool = False, **given: Any
) -> dict:
    """The mesh a declaration describes, with the report that says what came out.

    Walks `order`, dispatches on `op`, collects into `built`, and hands the lot to
    `review.report` — which is the whole of what was missing. A shape that can only be
    checked by looking at a render is one whose construction errors are found in the
    expensive place, so the report comes back with the mesh and not on request.
    """
    from .review import report

    here = Path(root).resolve()
    resolved = expand(document, **given)
    stated = {node["id"]: node for node in document["nodes"]}
    instanced = {node["id"]: node for node in resolved["nodes"]}

    built: dict[str, dict] = {}
    for one in order(document):
        node, made = stated[one], []
        how = BUILDS.get(node["op"])
        if how is None:
            raise PolyweaveError(
                "geom.unknown-op",
                f"{one!r} has op {node['op']!r}, and nothing builds that",
                f"name one of {', '.join(sorted(BUILDS))}, or write it as a `custom` "
                f"node pointing at a function of your own",
            )
        for instance in instanced[one]["instances"]:
            made.append(_placed(node, instance, how(node, instance, built, here)))
        # A repeated node's id names the whole set, which is what makes the tray one
        # boolean rather than sixty-four.
        whole = made[0] if len(made) == 1 else S.union(*made)
        worn = _worn(node, whole, built)
        built[one] = {**whole, "groups": worn} if worn else whole

    return {
        "output": built[document["output"]],
        "built": built,
        "report": report(document, built, manifold=manifold, **given),
    }


def _worn(node: dict, made: dict, built: dict) -> list[dict]:
    """Which faces of this mesh wear which material (§PW67).

    A material sits on a node and a document names one output, so a model in two
    materials — Cottony's cream rope rim on its cushion face — could only be handed back
    as a join, and the join kept one material or none. The colours were in the document,
    survived `expand`, were read back by the review, and were gone from the mesh.

    Faces, because that is the one thing a join really does know: `union` lays its
    operands out in order, so where each one's faces landed is arithmetic. It is also
    what a renderer wants, since a material slot is assigned per polygon.

    **A boolean keeps what it cut into and nothing finer.** The cutter is gone from the
    result and the solver does not preserve face correspondence, so a carve or a bevel
    over one material is one group and over several is none. Claiming a range the solver
    reordered would be worse than saying nothing.
    """
    if node.get("material"):
        return [{"material": node["material"], "faces": [0, len(made["faces"])]}]
    if node["op"] == "union":
        groups, at = [], 0
        for one in refers_to(node):
            part = built[one]
            for group in part.get("groups") or ():
                start, stop = group["faces"]
                groups.append(
                    {"material": group["material"], "faces": [start + at, stop + at]}
                )
            at += len(part["faces"])
        return groups
    if node["op"] in ("carve", "bevel"):
        source = node.get("into") or (refers_to(node) or [""])[0]
        worn = {g["material"] for g in built.get(source, {}).get("groups") or ()}
        if len(worn) == 1:
            return [{"material": worn.pop(), "faces": [0, len(made["faces"])]}]
    return []


def _placed(node: dict, instance: dict, made: dict) -> dict:
    """One instance where its own `at` puts it, which is what a repeat varies."""
    at = instance.get("at")
    if at is None or node["op"] in PLACES:
        return made
    return S.transform(made, at=at)
