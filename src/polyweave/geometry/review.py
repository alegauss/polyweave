"""Reading a shape before building it, because building it is the expensive place.

The evidence is §PW33: two wrong constructions of Cottony's tray seats were built before
the right one, and **both looked entirely reasonable while being written**. Raised bars
between the cells gave a woven basket where the separators read as rungs laid on top of
the tray. Cutting those bars into segments so their bevels would stop fighting turned
them into a ladder of lozenges. Neither was visible until rendered.

A declaration can be read before it is built, which is the point of it being data. Three
checks, in increasing cost:

1. **A structural read that says what the tree does in words** — free, and the one a
   person or an agent looks at before committing to a bake. "sixty-four seats in an
   eight by eight grid, carved out of one plate" is a sentence somebody can disagree
   with.
2. **A preview at the cheapest rung**, which is Block B's ladder and not this module's.
3. **The post-condition that the built mesh is manifold with a plausible face count**,
   which is the only one that costs a build.

None of them replaces judgement. All three catch the class of error where the code did
exactly what it said and what it said was wrong.
"""

from __future__ import annotations

from typing import Any

from ..errors import PolyweaveError
from ..post.mesh import check_manifold, check_mesh
from . import arithmetic, coats, expand, mentions, order, refers_to, uses
from . import surface as F

#: A repeat above this is worth mentioning, because a document rarely means it.
CROWDED = 500


def _number(value: Any) -> str:
    if isinstance(value, int | float):
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, list | tuple):
        return " by ".join(_number(one) for one in value)
    return str(value)


def _fields(node: dict, skip: tuple[str, ...]) -> str:
    said = [
        f"{name} {_number(value)}"
        for name, value in sorted(node.items())
        if name not in skip and not isinstance(value, dict | list)
    ]
    return ", ".join(said)


def _outline_words(stated: Any) -> str:
    if isinstance(stated, dict):
        if "shape" in stated:
            rest = ", ".join(
                f"{k} {_number(v)}" for k, v in sorted(stated.items()) if k != "shape"
            )
            return f"a {stated['shape']}" + (f" of {rest}" if rest else "")
        if "image" in stated:
            return f"the outline traced from {stated['image']}"
        if "points" in stated:
            return f"an outline of {len(stated['points'])} points"
    if isinstance(stated, list):
        return f"an outline of {len(stated)} points"
    return "an outline"


def _says(node: dict, instance: dict, materials: dict | None = None) -> str:
    """One node, in words: what it is, before anything about how many."""
    op = node["op"]
    skip = (
        "id",
        "op",
        "material",
        "repeat",
        "outline",
        "rect",
        "drawing",
        *refers_to(node),
    )
    rest = _fields(instance, skip)
    takes = refers_to(node)

    if op == "prism":
        what = f"{_outline_words(instance.get('outline'))}, extruded"
    elif op == "plate":
        rect = instance.get("rect") or []
        what = (
            f"a plate {_number(rect[2:]) or '?'} at {_number(rect[:2]) or '?'}"
            if len(rect) == 4
            else "a plate"
        )
    elif op == "crowned":
        what = f"{_outline_words(instance.get('outline'))}, extruded with a domed face"
    elif op == "annulus":
        what = "a ring"
    elif op == "primitive":
        what = f"a {instance.get('kind', 'cube')}"
    elif op == "inflate":
        # Two profiles, and which one it gets is worth saying: an outline swells from
        # its edge, a drawing from its own alpha (§PW68).
        what = (
            f"{instance['drawing']}, given volume by its own alpha"
            if instance.get("drawing")
            else f"{_outline_words(instance.get('outline'))}, given volume"
        )
    elif op == "carve":
        what = (
            f"{takes[0]} with {takes[1]} cut out of it" if len(takes) > 1 else "a cut"
        )
    elif op == "union":
        what = f"{' and '.join(takes)} joined" if takes else "a join"
    elif op == "bevel":
        what = f"{takes[0]}, with its edges softened" if takes else "a bevel"
    elif op == "transform":
        what = f"{takes[0]}, moved" if takes else "a transform"
    elif op == "custom":
        what = f"whatever {node.get('fn', 'a project function')} builds"
    elif op == "cells":
        what = _drawing(node)
    elif op == "mesh":
        what = f"the mesh in {instance.get('path', '?')}"
        rest = _fields(instance, (*skip, "path"))
    elif op == "mirror":
        letter = str(node.get("axis", "x")).lower()
        plane = _number(instance.get("plane", 0))
        what = f"{takes[0] if takes else 'nothing'} mirrored across {letter} = {plane}"
        rest = _fields(instance, (*skip, "plane"))
    else:
        what = f"a {op}"

    said = what + (f" ({rest})" if rest else "")
    if node.get("material"):
        said += f", in {node['material']}"
        # A fuzzy surface is the one material property that changes what the shape
        # looks like rather than only what colour it is, so it is said (§PW50).
        coat = F.fuzz((materials or {}).get(node["material"]))
        if coat:
            said += f", {F.says(coat)}"
    return said


def _drawing(node: dict) -> str:
    """`3 layers of 8 by 5, 41 cells in hull and glass` (§PW95)."""
    from .voxels import lattice

    try:
        grid = lattice(node)
    except PolyweaveError as refused:
        return f"cells that cannot be read: {refused.message}"
    wide, tall, deep = grid["size"]
    count = int(grid["filled"].sum())
    worn = [one for one in dict.fromkeys(grid["wears"][grid["filled"]].tolist()) if one]
    said = (
        f"{deep} layer{'' if deep == 1 else 's'} of {wide} by {tall}, "
        f"{count} cell{'' if count == 1 else 's'}"
    )
    return said + (f" in {' and '.join(worn)}" if worn else "")


def _article(word: str) -> str:
    """`an 8 by 8 grid`, not `a 8 by 8 grid`. It is read by people."""
    return "an" if word[:1] in "aeiou18" else "a"


def describe(document: dict, **given: Any) -> dict:
    """What this shape does, in words, without building any of it.

    The cheapest of the three checks and the one worth reading first: a sentence per
    node, in the order they build, saying what each one is and how many there are.
    """
    resolved = expand(document, **given)
    by_id = {node["id"]: node for node in resolved["nodes"]}
    stated = {node["id"]: node for node in document["nodes"]}

    lines = []
    for one in order(document):
        node, first = stated[one], by_id[one]["instances"][0]
        count = len(by_id[one]["instances"])
        grid = " by ".join(str(len(r["values"])) for r in by_id[one]["over"])
        said = _says(node, first, resolved["materials"])
        if count > 1:
            said += f" — {count} of them"
            if len(by_id[one]["over"]) > 1:
                said += f", in {_article(grid)} {grid} grid"
        lines.append({"id": one, "op": node["op"], "instances": count, "says": said})

    return {
        "name": resolved["name"],
        "output": resolved["output"],
        "params": resolved["params"],
        "nodes": lines,
        "reads": [f"{one['id']}: {one['says']}" for one in lines],
        "warnings": warn(document, resolved),
    }


def warn(document: dict, resolved: dict | None = None) -> list[str]:
    """What is odd about this document, found without building it.

    Not errors — a document with any of these still builds. They are the shapes of the
    mistakes that read as reasonable, which is the whole of what this line is about.
    """
    resolved = resolved or expand(document)
    out = []

    wanted = {one for node in document["nodes"] for one in refers_to(node)}
    wanted.add(document["output"])
    for node in document["nodes"]:
        if node["id"] not in wanted:
            out.append(
                f"{node['id']} is built and nothing uses it, so it is not in the output"
            )

    read = set().union(*(uses(node) for node in document["nodes"])) or set()
    read |= set().union(set(), *coats(document).values())
    for name in sorted(set(document["params"]) - read):
        out.append(f"the parameter {name} is declared and no node reads it")

    # An op nothing builds parses, expands and describes itself perfectly well, and
    # then refuses at the build. Naming it here is the cheap half of the same answer,
    # and it reads the builder's own table so the two cannot drift (§PW60).
    from .build import BUILDS

    for node in document["nodes"]:
        if node["op"] not in BUILDS:
            out.append(
                f"{node['id']} has op {node['op']!r}, and nothing builds that, so this "
                f"document describes a shape it cannot produce"
            )

    # A node naming a material nothing declares keeps its colour and loses its fuzz,
    # and loses it quietly — which is the shape of mistake this module is for.
    declared = set(document["materials"])
    for node in document["nodes"]:
        worn = node.get("material")
        if worn and worn not in declared:
            out.append(
                f"{node['id']} is in {worn}, and no material has that name, so "
                f"whatever {worn} was meant to put on it is not there"
            )
        # A drawing's legend names materials the same way, one per character.
        for mark, drawn in sorted((node.get("legend") or {}).items()):
            if drawn and drawn not in declared:
                out.append(
                    f"{node['id']} draws {mark!r} in {drawn}, and no material has that "
                    f"name, so whatever {drawn} was meant to put on it is not there"
                )

    for node in resolved["nodes"]:
        if len(node["instances"]) > CROWDED:
            out.append(
                f"{node['id']} repeats {len(node['instances'])} times, which is more "
                f"than a document usually means"
            )

    out += _typos(document, resolved)
    return out


def _typos(document: dict, resolved: dict) -> list[str]:
    """Fields that read as arithmetic over a name nothing declares.

    A value resolves as arithmetic only where every name in it is in scope, because a
    path like `art/star.png` parses as a division and must not be evaluated. That leaves
    `"pad + cel"` looking like a name rather than a typo — so it is warned about here,
    which is the same class of error this whole module is for: it reads reasonable.
    """
    declared = set(resolved["params"])
    out = []
    for node in document["nodes"]:
        over = {r["var"] for r in _repeats(node)}
        for field, value in node.items():
            if field in ("id", "op", "material", "fn", "layers", "legend"):
                continue
            for where, text in _strings(value, f"{node['id']}.{field}"):
                names = mentions(text)
                if arithmetic(text) and names and not names <= declared | over:
                    missing = ", ".join(sorted(names - declared - over))
                    out.append(
                        f"{where} reads as arithmetic over {missing}, which nothing "
                        f"declares, so it is being kept as the text {text!r}"
                    )
    return out


def _repeats(node: dict) -> list[dict]:
    return [one for one in (node.get("repeat") or ()) if isinstance(one, dict)]


def _strings(value: Any, where: str):
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, dict):
        for name, one in value.items():
            yield from _strings(one, f"{where}.{name}")
    elif isinstance(value, list):
        for index, one in enumerate(value):
            yield from _strings(one, f"{where}[{index}]")


def _overlapping_mirrors(document: dict, resolved: dict, built: dict) -> list[str]:
    """A mirror whose half already reaches across its plane (§PW96).

    Mirrored, that half lands on itself: the faces there are doubled for nothing, and
    something already symmetric was mirrored again. Found off the built half's bounds,
    which is why it is here and not in the free read.
    """
    from . import solid as S

    out = []
    instanced = {node["id"]: node for node in resolved["nodes"]}
    for node in document["nodes"]:
        if node["op"] != "mirror" or not refers_to(node):
            continue
        half = built.get(refers_to(node)[0])
        if half is None or not len(half["vertices"]):
            continue
        try:
            along = S.axis(node.get("axis", "x"))
        except PolyweaveError:
            continue
        plane = float(instanced[node["id"]]["instances"][0].get("plane", 0.0))
        low, high = check_mesh(half)["bounds"]
        if low[along] < plane - 1e-6 and high[along] > plane + 1e-6:
            letter = "xyz"[along]
            out.append(
                f"{node['id']} mirrors {refers_to(node)[0]}, which already reaches "
                f"both sides of {letter} = {_number(plane)}, so the two halves overlap "
                f"there"
            )
    return out


# -- the one that costs a build --------------------------------------------------------


def report(
    document: dict, built: dict, *, manifold: bool = False, **given: Any
) -> dict:
    """What came out, per node, so a boolean that returned nothing is visible.

    The per-node face count is the whole point: it is what catches a cut that silently
    produced nothing, and it is readable before anybody looks at a render.
    """
    resolved = expand(document, **given)
    rows, warnings = [], []
    for one in order(document):
        mesh = built.get(one)
        if mesh is None:
            warnings.append(f"{one} was declared and not built")
            continue
        found = check_mesh(mesh)
        row = {
            "id": one,
            "op": next(n["op"] for n in document["nodes"] if n["id"] == one),
            "faces": found["faces"],
            "vertices": found["vertices"],
            "instances": len(
                next(n for n in resolved["nodes"] if n["id"] == one)["instances"]
            ),
        }
        if manifold:
            try:
                row["manifold"] = check_manifold(mesh)["manifold"]
            except PolyweaveError as refused:
                row["manifold"] = False
                warnings.append(f"{one}: {refused.message}")
        rows.append(row)

    warnings += _overlapping_mirrors(document, resolved, built)
    output = built.get(document["output"])
    bounds = check_mesh(output)["bounds"] if output is not None else None
    return {
        "output": document["output"],
        "params": resolved["params"],
        "nodes": rows,
        "bounds": [*bounds[0], *bounds[1]] if bounds else None,
        "warnings": warnings + warn(document, resolved),
    }
