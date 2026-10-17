"""A fuzzy surface, asked for as an intent over shells (§PW50).

The bake builds no shells from it yet, and glTF carries none, so it reaches neither
target: the review sheet says it, and `targets` is empty rather than silent.
"""

from __future__ import annotations

from .. import surface
from . import Look


def _says(material) -> str:
    coat = surface.fuzz(material)
    return surface.says(coat) if coat else ""


LOOK = Look(
    name="fuzz",
    asks=("fuzz",),
    asked=lambda material: surface.fuzz(material) is not None,
    says=_says,
)
