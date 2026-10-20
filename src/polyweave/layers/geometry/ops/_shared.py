"""What more than one op builds with (§PW513)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from .. import outline as O

#: The fields that name another node, for the ops that take one (§PW146).
TAKES = ("inputs", "operands", "of", "on")

#: A bevel's profile by the word a declaration writes, as Blender's profile and how
#: many segments it forces (§PW493): a chamfer is one flat cut whatever is asked.
PROFILES = {"round": (0.5, None), "chamfer": (0.5, 1)}

#: The angle, in degrees, an edge's faces must turn past before a bevel rounds it: the
#: crease `sharp_edge_share` counts (§PW566). A torus's facets turn under 23 degrees,
#: and rounding them too split each into strips: Spinhold's half arch went from 0.059
#: sharp to 0.086 under a bevel meant to soften it.
CREASE = 30.0


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


def _edge(stated: Any, root: Any) -> Any:
    return stated if isinstance(stated, int | float) else O.resolve(stated, root=root)


def _alpha(named: Any, root: Any) -> Any:
    """A drawing's own alpha, as the array the profile is read off."""
    from polyweave.kernel.image import load as load_image

    where = Path(named)
    if not where.is_absolute():
        where = Path(root) / where
    return load_image(where).rgba[..., 3] / 255.0


def _beveled(node: dict, instance: dict) -> dict:
    """How a node's bevel rounds: its `segments` and its `profile`, each checked."""
    said = instance.get("profile", "round")
    if said not in PROFILES:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} bevels with a {said!r} profile, which is not one",
            "write profile as round or chamfer",
            given=said,
            allowed=tuple(PROFILES),
        )
    # A parameter resolves to a float, so a whole one is a count.
    segments = instance.get("segments", 3)
    whole = isinstance(segments, int | float) and not isinstance(segments, bool) and (
        float(segments).is_integer())
    if not whole or segments < 1:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} bevels in {segments!r} segments",
            "give segments as a whole number from 1; more is rounder",
        )
    # Only edges sharper than this are rounded, so a smooth body is left alone (§PW566);
    # 0 rounds every edge, as a bevel did before.
    crease = instance.get("crease", CREASE)
    if isinstance(crease, bool) or not isinstance(crease, int | float) or not (
            0 <= crease < 180):
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} bevels edges sharper than {crease!r} degrees",
            f"give crease in degrees from 0 to under 180; {CREASE:g} is the default, "
            "and 0 rounds every edge",
        )
    profile, forced = PROFILES[said]
    return {"segments": forced or int(segments), "profile": profile,
            "crease": float(crease)}
