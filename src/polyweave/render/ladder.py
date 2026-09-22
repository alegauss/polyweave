"""Which rung of the preview ladder can carry which question.

The evidence is §PW7: a material is read on a sphere, and a sphere renders in three
seconds where a character takes two minutes. That ratio is the whole argument. Judging a
surface on the final mesh pays forty times over for an answer the cheap shape already
gives, and the only reason it keeps happening is that nothing makes the cheap path the
default.

So a caller names what it wants to know, and the ladder answers from the lowest rung
that can carry it. The measure vocabulary is `docs/specs/measurements.md`; the map below
is the claim that each of those names is answerable at that rung and no lower.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..errors import PolyweaveError

#: The three rungs, cheapest first. Their meaning is the plugin's and not the project's:
#: a project chooses which to enable and how big they are, never what `sphere` means.
RUNGS = ("sphere", "preview", "final")

#: What each rung renders, which is the only thing that differs between them. The rig is
#: shared exactly — a cheap answer describing a different scene is worse than no answer.
CARRIES = {
    "sphere": "the material on a primitive, at the sphere size and sample count",
    "preview": "the real mesh decimated, at the preview size and sample count",
    "final": "the real mesh whole, at the final size and sample count",
}

#: The statistic suffixes `measurements.md` appends, stripped before the lookup.
_SUFFIXES = ("_p1", "_p50", "_p99", "_mean", "_std")

#: The lowest rung each measure can be taken at.
#:
#: A surface reads on a primitive, so colour and tone stop at the sphere. A silhouette
#: is the shape itself and needs the real mesh, but not the samples. A comparison
#: between two renders, or a count of what survives a downscale, is about the render and
#: needs all of it.
ANSWERS_AT = {
    "saturation": "sphere",
    "luma": "sphere",
    "hue_spread": "sphere",
    "region_colour": "sphere",
    "delta_e": "sphere",
    "silhouette_iou": "preview",
    "silhouette_centroid_offset": "preview",
    "silhouette_bbox_delta": "preview",
    "alpha_coverage": "preview",
    "distance": "final",
    "changed_fraction": "final",
    "luma_bands": "final",
}


def base_measure(measure: str) -> str:
    """`saturation_p99` is a statistic of `saturation`, and both are answered alike."""
    for suffix in _SUFFIXES:
        if measure.endswith(suffix):
            return measure[: -len(suffix)]
    return measure


def check_rung(rung: str) -> str:
    """Return `rung`, or refuse a name the ladder has no meaning for."""
    if rung not in RUNGS:
        raise PolyweaveError(
            "render.unknown-rung",
            f"there is no rung called {rung!r}",
            f"name one of {', '.join(RUNGS)}; a project chooses which are enabled and "
            f"how big they are, not what they mean",
        )
    return rung


def rung_for(measure: str) -> str:
    """The lowest rung that can answer this measure."""
    base = base_measure(measure)
    try:
        return ANSWERS_AT[base]
    except KeyError:
        raise PolyweaveError(
            "spec.unknown-measure",
            f"{measure!r} is not a measure",
            f"name one of {', '.join(sorted(ANSWERS_AT))}, with a statistic suffix "
            f"where it takes one",
        ) from None


def lowest_rung(measures: Iterable[str], floor: str | None = None) -> str:
    """The cheapest rung that carries every one of `measures`.

    `floor` is the asset's own `rung` from its acceptance spec — the lowest a verdict on
    it may be taken at — so a spec can insist on more than the measures require and
    never on less.
    """
    needed = [rung_for(m) for m in measures]
    if floor is not None:
        needed.append(check_rung(floor))
    if not needed:
        return RUNGS[0]
    return max(needed, key=RUNGS.index)


def enabled(configured: Iterable[str]) -> tuple[str, ...]:
    """The project's rungs, in ladder order, refusing any the ladder cannot render."""
    chosen = {check_rung(r) for r in configured}
    if not chosen:
        raise PolyweaveError(
            "render.no-rungs",
            "this project enables no rungs, so nothing can be rendered",
            f"set `[render] rungs` to some of {', '.join(RUNGS)}",
        )
    return tuple(r for r in RUNGS if r in chosen)
