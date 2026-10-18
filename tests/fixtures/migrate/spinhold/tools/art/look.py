"""Put the five models in front of a person, each held to a bar that says where it came from.

Run:  python tools/art/look.py            render, check, lay out the sitting and turntables
      python tools/art/look.py --turns 0  the same without turntables, which cost 9 renders
      python -m polyweave review         then look, and answer on the page

Everything here is polyweave's (RK94). Each model is rendered at the preview rung through
the project's own rig into `art/renders/`, and checked against `art/accept/<name>.accept.
toml`. A spec that does not exist yet is written from that render: every bound is the
measured value with room around it, `origin = "margin"` with `measured` beside it, so a
later model is held to today's look and a person who disagrees moves the bound through a
verdict, never by editing the number.

`verdict.sitting` lays the five out as one family on one sheet, and `shape.turntable` turns
each at the rig's own camera, so the review page shows every model whole. Nothing here
decides a look.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from polyweave import accept, measure, readable, render, shape, verdict

ROOT = Path(__file__).resolve().parents[2]
MODELS = ("ship", "drone", "gunship", "keeper", "seeker")

#: How far each bound sits from what today's render measured. Coverage may shrink by a
#: fifth before a model is called too small in its frame; the median brightness of the
#: subject may move by a tenth either way; the untextured grey stays nearly unsaturated.
ROOM = {"coverage": 0.8, "luma": 0.1, "saturation": 0.1}


class Quiet:
    """Nothing is watching a bake from here but this script's own printout."""

    def stage(self, stage, *, progress=None, note=None):
        """Not reported."""

    def progress(self, value, *, note=None):
        """Not reported."""

    def note(self, text):
        """Not reported."""


def spec_from(name: str, picture: Path) -> str:
    """A first spec for a model, every bound set from its own render."""
    found = measure.summarise(
        measure.measure(picture, ["alpha_coverage"], region="frame", alpha_floor=0.02)
        + measure.measure(
            picture, ["luma_p50", "saturation_p99"], region="subject", alpha_floor=0.02
        )
    )
    cover, luma, sat = (
        found["alpha_coverage"],
        found["luma_p50"],
        found["saturation_p99"],
    )

    def bound(value: float, measured: float) -> str:
        return (
            f'{{ value = {round(value, 4)}, origin = "margin", '
            f"measured = {round(measured, 4)} }}"
        )

    return f'''asset    = "{name}"
artefact = "art/renders/{name}.png"
rung     = "preview"

# the model fills its frame: set from the render of {name}.glb that RK94 took
[[predicate]]
id      = "fills-its-frame"
measure = "alpha_coverage"
region  = "frame"
min     = {bound(cover * ROOM["coverage"], cover)}

# the subject's median brightness stays where the neon material put it
[[predicate]]
id      = "brightness-holds"
measure = "luma_p50"
region  = "subject"
min     = {bound(max(0.0, luma - ROOM["luma"]), luma)}
max     = {bound(min(1.0, luma + ROOM["luma"]), luma)}

# the preview is untextured: a saturated subject is a texture nobody asked for
[[predicate]]
id      = "stays-untextured"
measure = "saturation_p99"
region  = "subject"
max     = {bound(min(1.0, sat + ROOM["saturation"]), sat)}
'''


def main(argv: list[str] | None = None) -> int:
    readable()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--turns", type=int, default=8, help="turntable frames; 0 skips")
    stated = parser.parse_args(argv)

    members = []
    for name in MODELS:
        picture = ROOT / "art" / "renders" / f"{name}.png"
        render.bake(
            Quiet(),
            out=str(picture),
            model=str(ROOT / "assets" / "models" / f"{name}.glb"),
            rung="preview",
            root=str(ROOT),
            inline=False,
        )
        spec = ROOT / "art" / "accept" / f"{name}.accept.toml"
        if not spec.is_file():
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(spec_from(name, picture), encoding="utf-8")
            print(f"  {name}: wrote {spec.relative_to(ROOT)} from its render")
        held = accept.check(accept.read(spec), picture, root=ROOT)
        print(f"  {name}: {'holds' if held['passed'] else 'FAILS'} its spec")
        members.append(
            {
                "name": name,
                "spec": f"art/accept/{name}.accept.toml",
                "new": f"art/renders/{name}.png",
                "shown": [128, 128],
            }
        )
        if stated.turns:
            shape.turntable(
                f"assets/models/{name}.glb",
                out=f".polyweave/turns/{name}",
                root=ROOT,
                frames=stated.turns,
            )

    laid = verdict.sitting({"models": members}, out="art/review", root=str(ROOT))
    print(laid["says"])
    print("look with: python -m polyweave review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
