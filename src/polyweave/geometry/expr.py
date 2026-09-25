"""The arithmetic a declaration is allowed to do, and nothing else.

Plain data cannot do arithmetic, and the shapes that matter here are arithmetic — a
sixty-four seat tray is a loop over a cell size the game holds as a constant. So the
format adds expressions over named parameters, which is one of the three things it adds
to TOML.

**Nothing here evaluates arbitrary code**, and that is a determinism requirement before
it is a security one: an expression whose value can depend on anything but its
parameters breaks the cache key. Python's own parser produces the tree, and then every
node of that tree is checked against a list — a name, a number, one of six operators,
one of nine functions. A call to anything else, an attribute, a comparison, a subscript,
a lambda or a literal that is not a number is refused where it is read rather than where
it is evaluated.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from ..errors import PolyweaveError

#: The operators. Division by zero is the caller's arithmetic and is reported as such.
BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

#: Every function an expression may call. A shape's arithmetic needs no more than this,
#: and each one added is a thing the cache key has to stay deterministic across.
FUNCTIONS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": lambda value, digits=0: round(value, int(digits)),
    "floor": lambda value: float(math.floor(value)),
    "ceil": lambda value: float(math.ceil(value)),
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "radians": math.radians,
}

#: The grammar, for a refusal that can name it.
GRAMMAR = (
    "numbers, parameter names, repeat variables, + - * / %, parentheses, and "
    f"{', '.join(sorted(FUNCTIONS))}"
)


def evaluate(source: Any, names: dict, *, where: str = "") -> float:
    """One expression, against the parameters and repeat variables in scope.

    A number passes straight through: a document that writes `corner = 28` means 28, and
    making it say `"28"` would be ceremony.
    """
    if isinstance(source, bool):
        return source
    if isinstance(source, int | float):
        return float(source)
    if not isinstance(source, str):
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} is a {type(source).__name__}, not an expression",
            f"write it as a number or as a string holding one of: {GRAMMAR}",
        )
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as exc:
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} is not an expression",
            f"write it with: {GRAMMAR}",
            detail=str(exc),
        ) from exc
    return _walk(tree.body, names, source, where)


def _at(where: str) -> str:
    return f"{where}: " if where else ""


def _walk(node: ast.AST, names: dict, source: str, where: str) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise PolyweaveError(
                "geom.bad-expression",
                f"{_at(where)}{node.value!r} in {source!r} is not a number",
                f"write it with: {GRAMMAR}",
            )
        return float(node.value)

    if isinstance(node, ast.Name):
        if node.id not in names:
            near = ", ".join(sorted(names)[:8]) or "nothing"
            raise PolyweaveError(
                "geom.unknown-name",
                f"{_at(where)}{source!r} names {node.id!r}, which is not in scope",
                f"declare it in [params], or name a variable this node repeats over; "
                f"in scope here: {near}",
                given=node.id,
                allowed=names,
            )
        return float(names[node.id])

    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left = _walk(node.left, names, source, where)
        right = _walk(node.right, names, source, where)
        try:
            return float(BINARY[type(node.op)](left, right))
        except ZeroDivisionError as exc:
            raise PolyweaveError(
                "geom.bad-expression",
                f"{_at(where)}{source!r} divides by zero",
                "check the parameter in the denominator; it resolved to zero",
            ) from exc

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return float(UNARY[type(node.op)](_walk(node.operand, names, source, where)))

    if isinstance(node, ast.Call):
        return _call(node, names, source, where)

    raise PolyweaveError(
        "geom.bad-expression",
        f"{_at(where)}{source!r} uses {type(node).__name__}, which this does not "
        f"evaluate",
        f"write it with: {GRAMMAR}; nothing here runs arbitrary code, because a value "
        f"that can depend on anything but its parameters breaks the cache key",
    )


def _call(node: ast.Call, names: dict, source: str, where: str) -> float:
    if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
        called = getattr(node.func, "id", type(node.func).__name__)
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} calls {called!r}, which is not a function here",
            f"call one of {', '.join(sorted(FUNCTIONS))}",
        )
    if node.keywords:
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} passes a keyword argument",
            "pass the arguments in order",
        )
    arguments = [_walk(one, names, source, where) for one in node.args]
    try:
        return float(FUNCTIONS[node.func.id](*arguments))
    except (TypeError, ValueError) as exc:
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} does not work: {exc}",
            f"check the arguments to {node.func.id}",
        ) from exc


def numbers(source: Any, names: dict, *, where: str = "") -> list[float]:
    """An array of expressions, each evaluated.

    Where any element of an array is an expression the format asks for them all as
    strings, so a caller never has to reason about a mixed-type array — but a list of
    plain numbers is still a list of numbers and is taken as one.
    """
    if isinstance(source, str | int | float):
        return [evaluate(source, names, where=where)]
    try:
        return [
            evaluate(one, names, where=f"{where}[{index}]" if where else "")
            for index, one in enumerate(source)
        ]
    except TypeError as exc:
        raise PolyweaveError(
            "geom.bad-expression",
            f"{_at(where)}{source!r} is not a list of expressions",
            "write it as an array, with every element a string where any one of them "
            "is an expression",
        ) from exc


def mentions(source: Any) -> set[str]:
    """Every name an expression reads, for working out what a change rebuilds.

    Read off the tree rather than by matching text, so a parameter called `pad` is not
    found inside a function called `padding`.
    """
    if not isinstance(source, str):
        return set()
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError:
        return set()
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id not in FUNCTIONS
    }
