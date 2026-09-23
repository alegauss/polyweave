"""A fuzzy surface asked for as an intent, with the shell construction underneath it.

The evidence is §PW50. The vocabulary can carve, bevel and inflate a shape and a
material can be given shader inputs, and neither of them can make a surface fuzzy.
Cottony's answer is **shell texturing** — the same surface drawn twenty times, each copy
a little further out, each keeping only the strands tall enough to reach it, so the
silhouette breaks into tufts rather than into single hairs. Eight constants describe it
and every one was found by eye, at two minutes a sample.

**Those constants are the answer, not the way to ask.** A `[fluff]` table of them would
be one project's look compiled in, which is the non-goal exactly, and it would help
nobody who wanted fur instead of cotton. So a declaration states two numbers:

```toml
[materials.cotton]
colour = "#F2E4D0"
fuzz   = { depth = 3.0, coarseness = 0.62 }
```

`depth` is how far the fuzz stands off the body, in the declaration's own units, and it
is the one number somebody can see. `coarseness` is the axis between the two failures
the readings actually name: **fibres alone read as velvet** rather than as sherpa, and
**clumps alone give hard beads**. So nought is fibres alone, one is clumps alone, and
what works is between them, where the fibre field is still multiplied into the clumps.
Everything `construction` derives is a function of those two, and `coarseness` is a
plain number rather than a named look so that PW32's search can turn it.

**The shell count is a function of coarseness and not of depth.** A strand needs the
same number of samples along its length whether it is long or short, and deriving the
count from fineness rather than from depth also keeps it free of the declaration's
units — nothing here knows how big one of them is.

What this module does not hold is the noise field itself, which is a shader's. It
produces the stack that field is drawn onto and the threshold each shell cuts it at,
which is the half that is reproducible from the two numbers that asked for it.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..errors import PolyweaveError
from ..post.mesh import as_mesh

__all__ = [
    "band",
    "construction",
    "fuzz",
    "layers",
    "normals",
    "says",
    "spacing",
    "stack",
]

#: What a fuzz may state. Anything else is a typo, and a typo dropped rather than named
#: is a surface that silently came back at a coarseness nobody chose.
ASKS = ("depth", "coarseness")

#: Shells at the fine end of coarseness and at the coarse end. Below the second the
#: stack reads as stripes; above the first each shell costs another full draw of the
#: body for a difference that does not survive to the pixel.
SHELLS = (24, 6)

#: Clump cells across the body, fine end to coarse end: coarser is fewer and broader.
CLUMPS = (64.0, 6.0)

#: Fibre cells across the body, fine end to coarse end. Finer than the clumps it is
#: multiplied into at both ends — a fibre field as coarse as its clumps is the clump
#: field twice.
FIBRE = (900.0, 220.0)

#: How sharply a shell cuts its strands, fine end to coarse end. A fine field needs the
#: sharper cut, or the strands smear back into the flat surface they were cut from,
#: which is the velvet reading.
EDGE = (6.0, 1.6)

#: How far a strand's length wanders, as a fraction of depth, at full coarseness.
#: Clumps are what make lengths differ, so this goes to nothing along with them.
VARY = 0.45

#: How far the body pushes out under a clump, as a fraction of depth, at full
#: coarseness. Velvet is a flat surface with fibres on it and rises nowhere.
RISE = 0.22

#: How far a tip leans towards its clump's crown, as a fraction of depth, at full
#: coarseness. With no clumps there is no crown to lean towards.
LEAN = 0.35

#: What a coarseness reads as in words, each band up to the number beside it. The top
#: band is named for what the readings measured there rather than for a look somebody
#: might want, because a declaration that reads back `beaded` has been warned.
BANDS = ((0.2, "fine"), (0.45, "fibrous"), (0.75, "clumped"), (1.0, "beaded"))


def fuzz(material: Any) -> dict | None:
    """The fuzz a material asks for, or None where it asks for none.

    Takes the whole material table, because that is what a caller holding a node's
    `material` has, and a surface with no fuzz on it is the ordinary case rather than
    an error.
    """
    if not isinstance(material, dict):
        return None
    stated = material.get("fuzz")
    return None if stated is None else _asked(stated)


def _asked(stated: Any) -> dict:
    """One fuzz, checked against what a fuzz is allowed to say."""
    if not isinstance(stated, dict):
        raise PolyweaveError(
            "geom.bad-surface",
            f"a fuzz is stated as a {type(stated).__name__} and not as a table",
            "write it as { depth = 3.0, coarseness = 0.62 }",
        )

    unknown = sorted(set(stated) - set(ASKS))
    if unknown:
        # The constants are the answer to a fuzz and not the way to ask for one, so a
        # declaration reaching for one of them by name is told what to state instead,
        # rather than having the key quietly dropped.
        raise PolyweaveError(
            "geom.bad-surface",
            f"a fuzz takes no {', '.join(unknown)}",
            f"it takes {' and '.join(ASKS)}; the shell count, the cut, the fibre "
            f"field, the wander, the rise and the lean are derived from those two, "
            f"and `construction` reads them back",
        )

    missing = [one for one in ASKS if one not in stated]
    if missing:
        raise PolyweaveError(
            "geom.bad-surface",
            f"a fuzz states no {' and no '.join(missing)}",
            "give it a depth it stands off the body by, and a coarseness from nought "
            "to one; nought is fibres alone and one is clumps alone",
        )

    depth, coarseness = _number(stated, "depth"), _number(stated, "coarseness")
    if depth <= 0:
        raise PolyweaveError(
            "geom.bad-surface",
            f"a fuzz stands {depth:g} off the body, which is no fuzz at all",
            "give it a depth above zero, or take the fuzz off the material",
        )
    if not 0.0 <= coarseness <= 1.0:
        raise PolyweaveError(
            "geom.bad-surface",
            f"a coarseness of {coarseness:g} is outside nought to one",
            "nought is fibres alone, which reads as velvet, and one is clumps alone, "
            "which reads as hard beads; a plush surface is between them",
        )
    return {"depth": depth, "coarseness": coarseness}


def _number(stated: dict, field: str) -> float:
    value = stated[field]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PolyweaveError(
            "geom.bad-surface",
            f"a fuzz's {field} is {value!r}, which is not a number",
            "state it as a number, or as an expression over the document's own "
            "parameters so that a search can turn it",
        )
    return float(value)


def construction(coat: Any) -> dict:
    """The numbers that build the fuzz, derived from the two that asked for it.

    This is the whole of §PW50 in one function: what was found by eye is computed from
    a depth and a coarseness, so a project wanting fur asks in the same two words a
    project wanting cotton asks in, and gets a different surface.
    """
    asked = _asked(coat)
    depth, coarse = asked["depth"], asked["coarseness"]
    return {
        "shells": int(round(_mix(SHELLS, coarse))),
        "depth": depth,
        "edge": _mix(EDGE, coarse),
        "clumps": _mix(CLUMPS, coarse),
        "fibre": _mix(FIBRE, coarse),
        # The finding in one line: at one the clumps stand alone and give beads, at
        # nought the fibres stand alone and give velvet, and sherpa is both at once.
        "fibre_weight": 1.0 - coarse,
        "vary": VARY * coarse,
        "rise": depth * RISE * coarse,
        "lean": depth * LEAN * coarse,
    }


def _mix(pair: tuple[float, float], at: float) -> float:
    """One end of an axis to the other, by a coarseness."""
    low, high = pair
    return float(low) + (float(high) - float(low)) * float(at)


def layers(coat: Any) -> list[dict]:
    """Each copy of the surface: how far out it sits, and what it keeps there.

    `keeps` is the threshold the strand field is cut at on that shell, so only the
    strands tall enough to reach it survive to be drawn on it. It is the height raised
    to one over the edge sharpness: a sharp edge lifts the threshold early, which
    leaves thin distinct strands, and a soft one leaves the broad tufts a clumped
    surface wants.
    """
    made = construction(coat)
    count = made["shells"]
    out = []
    for index in range(count):
        height = (index + 1) / count
        out.append(
            {
                "index": index,
                "at": made["depth"] * height,
                "keeps": height ** (1.0 / made["edge"]),
                # A lean is a bend and not a shear, so it is nothing at the root and
                # all of itself at the tip.
                "lean": made["lean"] * height**2,
            }
        )
    return out


def spacing(coat: Any) -> float:
    """How far apart two neighbouring shells sit.

    What decides whether the stack reads as one surface or as stripes, and the number
    an adopter checks against what their own renderer resolves at the size they bake.
    """
    made = construction(coat)
    return made["depth"] / made["shells"]


def normals(subject: Any) -> np.ndarray:
    """A unit normal per vertex, area-weighted by the faces that meet at it.

    Newell's method per face, which is the one that is right for an n-gon rather than
    only for a triangle, and whose unnormalised length is twice the face's area — so
    accumulating it is the area weighting, with no separate term for it.
    """
    vertices, faces = as_mesh(subject)
    out = np.zeros_like(vertices)
    for face in faces:
        ring = vertices[list(face)]
        normal = np.cross(ring, np.roll(ring, -1, axis=0)).sum(axis=0)
        for one in face:
            out[one] += normal
    length = np.linalg.norm(out, axis=1, keepdims=True)
    return np.divide(out, length, out=np.zeros_like(out), where=length > 1e-12)


def stack(subject: Any, coat: Any) -> list[dict]:
    """The body, then one copy of it per shell, each pushed out along its own normals.

    The body comes first and unchanged, because the shells are drawn over a surface
    that is still there. The `rise` is **not** applied here: where the body pushes out
    is decided by where the clumps fall, and the field that says so belongs to a
    shader. `construction` carries how far, which is the half a declaration fixes.
    """
    vertices, faces = as_mesh(subject)
    if not len(vertices) or not faces:
        raise PolyweaveError(
            "geom.bad-surface",
            f"the body has {len(vertices)} vertices and {len(faces)} faces, so there "
            f"is no surface to draw a shell of",
            "give it a built mesh; a fuzz is a surface on something, and not a shape "
            "of its own",
        )
    along = normals(subject)
    out = [{"vertices": vertices.copy(), "faces": list(faces)}]
    for shell in layers(coat):
        out.append({"vertices": vertices + along * shell["at"], "faces": list(faces)})
    return out


def says(coat: Any) -> str:
    """The surface in words, for a declaration read back before it is built.

    §PW33's principle applied to a surface: "fuzzy 3 deep, clumped" is a sentence
    somebody can disagree with. The band names are the two measured failures and the
    ground between them, rather than a library of looks.
    """
    asked = _asked(coat)
    depth = f"{asked['depth']:.4f}".rstrip("0").rstrip(".") or "0"
    return f"fuzzy {depth} deep, {band(asked['coarseness'])}"


def band(coarseness: float) -> str:
    """What a coarseness reads as, in one word."""
    for upper, named in BANDS:
        if coarseness <= upper:
            return named
    return BANDS[-1][1]
