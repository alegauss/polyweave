"""A shape stated as data, rather than as a program that produces one.

The evidence is §PW30: Cottony's tray, star, ball and props are four modules of
imperative geometry code. The tray's docstring is excellent and **the shape it describes
is still not readable without running the module**, because the shape exists only as the
result of executing statements. That costs three ways: writing one means writing and
debugging a program, so the unit of work is a file rather than an edit; reviewing one
means rendering it; and nothing else can read it, so no tool can reason about the shape,
vary it or check it.

**Data rather than a new language.** A language needs a grammar, a parser, error
messages and an editor story before it renders its first triangle, and a document in a
format everything already reads needs none of that. What plain data cannot do is
arithmetic, and the tray is a loop over a cell size, so the format adds exactly three
things to TOML: **named parameters**, **expressions over them**, and a **repeat**. Three
features, not a language.

**A flat graph, not a nested tree.** Nodes are a list; each has an `id` and names its
inputs by id. It diffs, because a change touches one table rather than a re-indented
subtree. It is addressable, because a search can point at a node's parameter by name.
And a node can be used twice, which a boolean against a shared cutter needs anyway.

This module is the **document**: reading it, resolving it, expanding its repeats, and
saying what a change to a parameter forces a rebuild of. What each `op` actually builds
is the vocabulary, and it is PW31's.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from . import expr
from .expr import evaluate, mentions, numbers

__all__ = [
    "evaluate",
    "expand",
    "expr",
    "mentions",
    "numbers",
    "parse",
    "read",
    "rebuilds",
]

#: Fields on a node that name other nodes rather than carrying a value.
REFERS = ("into", "cutter", "of", "inputs", "operands", "on")

#: Fields that are the node's own bookkeeping and never an expression to evaluate.
KEEPS = ("id", "op", "material", "repeat", "fn")


def read(path: str | Path, *, root: str | Path = ".") -> dict:
    """Read a declaration off disk."""
    import tomllib

    where = Path(path)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    if not where.is_file():
        raise PolyweaveError(
            "geom.unreadable",
            f"there is no shape at {where}",
            "check the path, or write the declaration before reading it",
        )
    try:
        return parse(tomllib.loads(where.read_text(encoding="utf-8")), named=where.name)
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "geom.unreadable",
            f"{where.name} is not readable as TOML",
            "fix the syntax the detail below points at",
            detail=str(exc),
        ) from exc


def parse(stated: dict, *, named: str = "a declaration") -> dict:
    """Check a document is a shape, without resolving any of its arithmetic yet."""
    nodes = stated.get("nodes") or []
    if not stated.get("name") or not nodes:
        missing = "a name" if not stated.get("name") else "any nodes"
        raise PolyweaveError(
            "geom.malformed",
            f"{named} is TOML and is not a shape: it has no {missing}",
            "give it a name, at least one node, and an output naming one of them",
        )

    seen: set[str] = set()
    for node in nodes:
        one = node.get("id")
        if not one or not node.get("op"):
            raise PolyweaveError(
                "geom.malformed",
                f"{named} has a node with no {'id' if not one else 'op'}",
                "give every node an id and an op",
            )
        if one in seen:
            raise PolyweaveError(
                "geom.duplicate-id",
                f"{named} has two nodes called {one!r}",
                "give each node an id of its own; an id is how every other node refers "
                "to it, and two of them makes every reference ambiguous",
            )
        seen.add(one)

    # TOML puts a bare key after a table header inside that table, so an `output = …`
    # written below the last [[nodes]] belongs to that node and not to the document.
    # It reads as though it were the document's, so it is named rather than ignored.
    for node in nodes:
        if "output" in node:
            raise PolyweaveError(
                "geom.malformed",
                f"{named}: node {node['id']!r} carries an `output` key",
                "move `output` above the first [[nodes]] table; TOML puts a bare key "
                "after a table header inside that table, so written below it names the "
                "node's own field rather than the document's output",
            )

    output = stated.get("output") or nodes[-1]["id"]
    if output not in seen:
        raise PolyweaveError(
            "geom.unknown-node",
            f"{named} names {output!r} as its output, and no node has that id",
            f"name one of {', '.join(sorted(seen))}",
        )
    _refuse_cycles(nodes, seen, named)
    return {
        "name": str(stated["name"]),
        "version": int(stated.get("version", 1)),
        "params": dict(stated.get("params") or {}),
        "materials": dict(stated.get("materials") or {}),
        "nodes": [dict(node) for node in nodes],
        "output": output,
    }


def refers_to(node: dict) -> list[str]:
    """Which nodes this one takes as inputs, whatever field they arrived in."""
    out: list[str] = []
    for field in REFERS:
        value = node.get(field)
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            out += [one for one in value if isinstance(one, str)]
        elif isinstance(value, dict):
            out += [one for one in value.values() if isinstance(one, str)]
    return out


def _refuse_cycles(nodes: list[dict], ids: set[str], named: str) -> None:
    edges = {
        node["id"]: [one for one in refers_to(node) if one in ids] for node in nodes
    }
    for node in nodes:
        for one in refers_to(node):
            if one not in ids:
                raise PolyweaveError(
                    "geom.unknown-node",
                    f"{named}: {node['id']!r} takes {one!r}, and no node has that id",
                    f"name one of {', '.join(sorted(ids))}",
                )
    settled: set[str] = set()
    walking: set[str] = set()

    def walk(one: str, path: list[str]) -> None:
        if one in settled:
            return
        if one in walking:
            circle = " -> ".join([*path, one])
            raise PolyweaveError(
                "geom.cycle",
                f"{named}: the nodes refer to each other in a circle: {circle}",
                "break the circle; a graph of shapes has to have a beginning",
            )
        walking.add(one)
        for other in edges.get(one, ()):
            walk(other, [*path, one])
        walking.discard(one)
        settled.add(one)

    for node in nodes:
        walk(node["id"], [])


# -- repeat, which is the third of the three things ------------------------------------


def ranges(node: dict, names: dict) -> list[tuple[str, list[float]]]:
    """Each variable this node repeats over, and the values it takes.

    `to` is inclusive, because a document saying `to = board - 1` means the last row and
    not the one before it. `step` defaults to one.
    """
    out = []
    for stated in node.get("repeat") or ():
        variable = stated.get("var")
        if not variable or "from" not in stated or "to" not in stated:
            raise PolyweaveError(
                "geom.bad-repeat",
                f"{node['id']}: a repeat range needs a var, a from and a to",
                'write it as { var = "row", from = 0, to = "board - 1" }',
            )
        where = f"{node['id']}.repeat.{variable}"
        start = evaluate(stated["from"], names, where=where)
        stop = evaluate(stated["to"], names, where=where)
        step = evaluate(stated.get("step", 1), names, where=where)
        if step <= 0:
            raise PolyweaveError(
                "geom.bad-repeat",
                f"{where} steps by {step:g}, which never reaches {stop:g}",
                "use a step above zero; a step of zero is a loop that never ends "
                "rather than one that repeats nothing",
            )
        values, at = [], start
        while at <= stop + 1e-9:
            values.append(round(at, 9))
            at += step
        out.append((variable, values))
    return out


def expand(document: dict, **given: Any) -> dict:
    """Resolve the document: every parameter, every expression, every instance.

    A repeated node becomes one instance per point of the cartesian product of its
    ranges, and **its id names the whole set** — which is what makes a tray one boolean
    rather than sixty-four.
    """
    params = {**document["params"], **given}
    resolved = {
        name: evaluate(value, params, where=f"params.{name}")
        for name, value in params.items()
    }

    instanced = []
    for node in document["nodes"]:
        over = ranges(node, resolved)
        points = list(itertools.product(*[values for _, values in over])) or [()]
        made = []
        for point in points:
            scope = {**resolved, **dict(zip([n for n, _ in over], point, strict=True))}
            made.append(_resolve(node, scope))
        instanced.append(
            {
                "id": node["id"],
                "op": node["op"],
                "material": node.get("material", ""),
                "refers_to": refers_to(node),
                "over": [{"var": name, "values": values} for name, values in over],
                "instances": made,
            }
        )
    return {
        "name": document["name"],
        "version": document["version"],
        "params": resolved,
        # A material's own values resolve like a node's, because a surface is declared
        # as an intent over the document's parameters (§PW50) — `fuzz = { depth =
        # "fluff_depth", … }` is only searchable if the name reaches the evaluator.
        "materials": _value(document["materials"], resolved, "materials"),
        "nodes": instanced,
        "output": document["output"],
    }


def _resolve(node: dict, scope: dict) -> dict:
    """One instance: every field of the node with its arithmetic done."""
    out = {}
    for field, value in node.items():
        if field in KEEPS or field in REFERS:
            continue
        out[field] = _value(value, scope, f"{node['id']}.{field}")
    return out


def _value(value: Any, scope: dict, where: str) -> Any:
    if isinstance(value, dict):
        return {k: _value(v, scope, f"{where}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_value(v, scope, f"{where}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return evaluate(value, scope, where=where)
    return _string(value, scope, where)


def _string(value: str, scope: dict, where: str) -> Any:
    """A string is an expression or a name, and what is in scope decides which.

    `depth = "face_depth"` is a parameter and resolves to a number. `shape =
    "rounded_square"` names a generator and stays a string — the vocabulary reads that,
    not this module. A parameter and a shape sharing a name is a document that should
    rename one of them, and the parameter wins.

    The rule is **all or nothing**: every name in scope and it is arithmetic, otherwise
    it is a name. A path is why. `"art/star.png"` parses as a division of two names, and
    a rule that took any `/` for arithmetic would evaluate an image path — which is a
    working document broken by the resolver, the worse of the two mistakes available
    here.

    The other one is a typo inside an expression, and it is now a **warning** rather
    than a refusal: `review.warn` names a field that reads as arithmetic over something
    undeclared, which is exactly the class of error §PW33 is about.
    """
    if not _parses(value):
        return value
    if not mentions(value) <= set(scope):
        return value
    return evaluate(value, scope, where=where)


def _parses(value: str) -> bool:
    try:
        ast.parse(value.strip(), mode="eval")
    except (SyntaxError, ValueError):
        return False
    return True


def arithmetic(value: Any) -> bool:
    """Whether a string *reads* as arithmetic, as against naming one thing.

    **Not** what decides how a value resolves — that is whether its names are in scope,
    and it has to be, because `art/star.png` parses as a division. This is only for the
    review, which warns about a field that looks like a sum over something nothing
    declares.

    A **spaced** operator is the test, because that is how these documents write
    arithmetic (`cell * 0.82`, `board - 1`) and how a path never does. A heuristic, and
    one whose only cost is a warning not printed.
    """
    return isinstance(value, str) and any(
        f" {operator} " in value for operator in "+-*/%"
    )


# -- what a change costs ---------------------------------------------------------------


def uses(node: dict) -> set[str]:
    """Every parameter a node's expressions read, including in its repeat ranges."""
    found: set[str] = set()
    for field, value in node.items():
        if field in KEEPS and field != "repeat":
            continue
        found |= _named(value)
    return found


def _named(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(_named(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_named(v) for v in value)) if value else set()
    return mentions(value)


def coats(document: dict) -> dict[str, set[str]]:
    """Which parameters each material's own values read.

    A surface is declared over the same parameters a shape is (§PW50), so a material
    reading one is a reason to rebuild and a reason not to warn that nothing reads it.
    """
    return {
        name: _named(table) for name, table in (document.get("materials") or {}).items()
    }


def rebuilds(document: dict, parameter: str) -> list[str]:
    """Which nodes a change to this parameter forces a rebuild of, transitively.

    The search needs this: rebuilding geometry costs more than re-rendering it, so a
    mixed search over shape and light orders its sampling to rebuild as rarely as it
    can. A node that reads the parameter rebuilds, and so does everything downstream.

    A node wearing a material whose own values read the parameter rebuilds too. Turning
    a fuzz's coarseness changes the surface of whatever wears it, and a search told
    that nothing rebuilds would sample the shape it already had.
    """
    worn = coats(document)
    direct = {
        node["id"]
        for node in document["nodes"]
        if parameter in uses(node)
        or parameter in worn.get(node.get("material", ""), ())
    }
    dirty = set(direct)
    changed = True
    while changed:
        changed = False
        for node in document["nodes"]:
            if node["id"] in dirty:
                continue
            if dirty & set(refers_to(node)):
                dirty.add(node["id"])
                changed = True
    return sorted(dirty)


def order(document: dict) -> list[str]:
    """The nodes in an order where every input is built before what needs it."""
    edges = {node["id"]: set(refers_to(node)) for node in document["nodes"]}
    out: list[str] = []
    while len(out) < len(edges):
        ready = sorted(
            one for one, needs in edges.items() if one not in out and needs <= set(out)
        )
        # `parse` already refused a cycle, so something is always ready.
        out += ready
    return out
