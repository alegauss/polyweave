"""Every operation asserts its own output before returning.

`docs/specs/tool-surface.md` §2. A success returned over a result nobody checked is the
failure mode this plugin exists partly to remove, and each assertion below is cheap
enough that there is no argument for skipping it:

    post.check("render", path, size=(512, 512))
    post.check("boolean", result, operands=(cut, target))
    post.check("mesh", result, optional=("manifold",))

A failed assertion is an error, never a warning, and its code names the assertion. What
a check returns is what it measured, which is what §PW6 writes beside the artefact.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..errors import PolyweaveError
from .files import ACCEPTS_DOWNLOAD, check_download
from .mesh import (
    ACCEPTS_BOOLEAN,
    ACCEPTS_MESH,
    check_boolean,
    check_manifold,
    check_mesh,
)
from .pixels import (
    ACCEPTS_CAPTURE,
    ACCEPTS_FIELD,
    ACCEPTS_RENDER,
    ACCEPTS_TEXTURE,
    check_capture,
    check_field,
    check_render,
    check_texture,
)

#: What each kind of output is checked for, and which arguments say what was asked for.
#: These always run: §2 admits no operation that produces one of these and asserts
#: nothing.
CHEAP: dict[str, tuple[Any, frozenset[str]]] = {
    "mesh": (check_mesh, ACCEPTS_MESH),
    "boolean": (check_boolean, ACCEPTS_BOOLEAN),
    "render": (check_render, ACCEPTS_RENDER),
    "texture": (check_texture, ACCEPTS_TEXTURE),
    # A field is a texture whose values are data rather than colour, and it is its own
    # kind because only the caller knows which one an image is (§PW38).
    "field": (check_field, ACCEPTS_FIELD),
    "capture": (check_capture, ACCEPTS_CAPTURE),
    "download": (check_download, ACCEPTS_DOWNLOAD),
}

#: What a kind cannot be checked without. A tolerance has one home (§PW40), so no check
#: below invents a value for one — the operation resolves it and passes it down, and a
#: call that states none is refused rather than answered against a number nobody chose.
REQUIRES: dict[str, frozenset[str]] = {
    "render": frozenset({"alpha_floor"}),
    "texture": frozenset({"alpha_floor"}),
    "field": frozenset({"alpha_floor"}),
    "capture": frozenset({"alpha_floor"}),
}

#: Assertions that cost more than the operation on a large enough input, so a project
#: turns them on deliberately. Off by default, and PW5 wires the config that names them.
OPTIONAL: dict[str, tuple[Any, frozenset[str]]] = {
    "manifold": (check_manifold, frozenset({"mesh", "boolean"})),
}


def check(
    produces: str,
    subject: Any,
    *,
    optional: Sequence[str] = (),
    **expected: Any,
) -> dict:
    """Assert what must be true of `subject`, and return what was measured."""
    try:
        checker, accepts = CHEAP[produces]
    except KeyError:
        raise PolyweaveError(
            "post.unknown-output",
            f"nothing is asserted about a {produces!r}",
            f"name one of {', '.join(sorted(CHEAP))}",
        ) from None

    unknown = sorted(set(expected) - set(accepts))
    if unknown:
        # §3: an unknown field is refused, never dropped, or a typo is
        # indistinguishable from a working call.
        raise PolyweaveError(
            "post.unknown-field",
            f"a {produces} check takes no {', '.join(unknown)}",
            f"it takes {', '.join(sorted(accepts)) or 'no arguments'}",
        )

    required = REQUIRES.get(produces, frozenset())
    unstated = sorted(required - set(expected))
    if unstated:
        # §PW40: a check used to default the tolerance to zero while the config said
        # 0.02, so a caller who forgot measured the background as part of the subject
        # and got an answer rather than a refusal. One home for the number now, and
        # a call that names none is a call that has not said which subject it means.
        raise PolyweaveError(
            "post.tolerance-unstated",
            f"a {produces} check needs {', '.join(unstated)}, and none was given",
            "resolve it once with Config.tolerances() and pass it down; a default here "
            "would be a second home for a number that has one",
        )

    measured = checker(subject, **expected)

    for name in optional:
        try:
            extra, applies_to = OPTIONAL[name]
        except KeyError:
            raise PolyweaveError(
                "post.unknown-check",
                f"there is no {name!r} assertion",
                f"name one of {', '.join(sorted(OPTIONAL))}",
            ) from None
        if produces not in applies_to:
            raise PolyweaveError(
                "post.check-misapplied",
                f"{name!r} does not apply to a {produces}",
                f"it applies to {', '.join(sorted(applies_to))}",
            )
        measured.update(extra(subject))
    return measured


__all__ = [
    "CHEAP",
    "OPTIONAL",
    "check",
    "check_boolean",
    "check_capture",
    "check_download",
    "check_field",
    "check_manifold",
    "check_mesh",
    "check_render",
    "check_texture",
]
