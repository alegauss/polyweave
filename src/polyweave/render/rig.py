"""The one rig every rung shares, and the framing maths that places it.

The constraint that makes the ladder worth anything: **the rungs share the rig
exactly**. A cheap answer describing a different scene is worse than no answer, so the
camera, the lights and the film are computed here, once, from the same parameters, and a
rung changes only what is in front of them.

Nothing in this module imports bpy. The framing is arithmetic on a bounding box, and
arithmetic is testable without starting a renderer.

Conventions are `docs/specs/tool-surface.md` §6: **Y up, −Z forward, right-handed**, one
unit is one metre, origin at the centre of the footprint on the ground plane, angles in
degrees. Blender's Z-up is converted on the boundary, in `blender.py`, and nowhere else.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

#: Blender's default sensor width, in millimetres. Named because the framing depends on
#: it and a silent disagreement would change every camera distance.
SENSOR_MM = 36.0

#: What each parameter is measured in. Data rather than a comment, because the failure
#: it exists for is a **name that means something else somewhere else** (§PW63): Cottony
#: calls the fraction of the frame a model fills `fill`, and here `fill` is a light in
#: watts. A port that copies 0.92 across asks for a 0.92-watt fill and gets a nearly
#: black picture, and nothing refuses it, because `fill` is a parameter this really
#: takes.
#:
#: A declared *range* would not catch it, and was tried before being rejected: the rig
#: is legitimately driven with every light at zero — that is how a test proves the
#: lights are what light the subject — so no bound separates 0.92 W from a wattage
#: somebody meant. What is left is to say the unit wherever a value is accepted, so the
#: mistake is visible where it is made rather than in the render it produces.
UNITS: dict[str, str] = {
    "azimuth": "degrees",
    "elevation": "degrees",
    "margin": "× the distance that exactly fits the subject",
    "focal_mm": "mm",
    "key": "W",
    "fill": "W",
    "rim": "W",
    "light_distance": "× the subject's radius",
    "ambient": "the world's own value, not a multiplier",
    "exposure": "stops",
}


def described(name: str) -> str:
    """One parameter's name with what it is measured in, for anything that echoes it."""
    unit = UNITS.get(name)
    return f"{name} ({unit})" if unit else name


@dataclass(frozen=True)
class Rig:
    """Everything the scene is, apart from what is in front of the camera.

    Cottony's rig has fourteen fields whose meaning lives in comments; these are the
    ones the ladder needs to be one scene. The set grows as Block C's search is given
    more to turn, and every addition is a parameter of the operation rather than a
    constant.
    """

    #: Where the camera sits, on a sphere around the subject.
    azimuth: float = 35.0
    elevation: float = 20.0
    #: How far back, as a multiple of the distance that exactly fits the subject.
    margin: float = 1.15
    focal_mm: float = 50.0

    #: The three lights, in watts. A key at the front, a fill opposite it, a rim behind.
    key: float = 400.0
    fill: float = 120.0
    rim: float = 200.0
    #: How far the lights sit, as a multiple of the subject's radius.
    light_distance: float = 3.0

    #: The world, and what the film does with what reaches it.
    ambient: float = 0.25
    exposure: float = 0.0
    transparent: bool = True

    def with_(self, **over) -> Rig:
        return replace(self, **{k: v for k, v in over.items() if v is not None})

    @property
    def fov(self) -> float:
        """The horizontal field of view, in radians."""
        return 2.0 * math.atan(SENSOR_MM / (2.0 * self.focal_mm))


def bounds_of(points) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    xs, ys, zs = zip(*points, strict=True)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def centre_and_radius(lo, hi) -> tuple[tuple[float, float, float], float]:
    """The subject's middle and the radius of the sphere that contains it."""
    centre = tuple((a + b) / 2.0 for a, b in zip(lo, hi, strict=True))
    half = [(b - a) / 2.0 for a, b in zip(lo, hi, strict=True)]
    return centre, math.sqrt(sum(h * h for h in half))


def camera_for(rig: Rig, lo, hi) -> dict:
    """Where the camera goes to frame this subject, in the interface's axes.

    Distance is derived from the bounding sphere and the field of view rather than
    guessed, so the same rig frames a sphere and a character the same way — which is
    what lets a verdict taken at one rung mean anything at another.
    """
    centre, radius = centre_and_radius(lo, hi)
    if radius <= 0.0:
        radius = 1e-6
    distance = (radius / math.sin(rig.fov / 2.0)) * rig.margin
    return {
        "location": _on_sphere(centre, distance, rig.azimuth, rig.elevation),
        "look_at": centre,
        "distance": distance,
        "radius": radius,
        "centre": centre,
        "focal_mm": rig.focal_mm,
    }


def lights_for(rig: Rig, lo, hi) -> list[dict]:
    """The three lights, placed relative to the camera so the ladder shares them."""
    centre, radius = centre_and_radius(lo, hi)
    if radius <= 0.0:
        radius = 1e-6
    reach = radius * rig.light_distance
    return [
        {
            "role": "key",
            "energy": rig.key,
            "location": _on_sphere(
                centre, reach, rig.azimuth - 35.0, rig.elevation + 25.0
            ),
        },
        {
            "role": "fill",
            "energy": rig.fill,
            "location": _on_sphere(centre, reach, rig.azimuth + 75.0, rig.elevation),
        },
        {
            "role": "rim",
            "energy": rig.rim,
            "location": _on_sphere(
                centre, reach, rig.azimuth + 180.0, rig.elevation + 35.0
            ),
        },
    ]


def _on_sphere(centre, distance: float, azimuth: float, elevation: float):
    """A point at `distance` from `centre`, in the Y-up frame §6 fixes.

    Azimuth turns about the up axis and elevation lifts towards +Y. **Azimuth zero is in
    front of the subject** — at +Z, looking along −Z, which §6 fixes as forward — so the
    default rig sees the face of a thing rather than the back of it.
    """
    az = math.radians(azimuth)
    el = math.radians(elevation)
    flat = math.cos(el) * distance
    return (
        centre[0] + flat * math.sin(az),
        centre[1] + distance * math.sin(el),
        centre[2] + flat * math.cos(az),
    )


def as_params(rig: Rig) -> dict:
    """The rig as the provenance record carries it, floats and nothing else."""
    return {
        "azimuth": rig.azimuth,
        "elevation": rig.elevation,
        "margin": rig.margin,
        "focal_mm": rig.focal_mm,
        "key": rig.key,
        "fill": rig.fill,
        "rim": rig.rim,
        "light_distance": rig.light_distance,
        "ambient": rig.ambient,
        "exposure": rig.exposure,
        "transparent": rig.transparent,
    }
