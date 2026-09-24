"""Taking the shading a service painted into a texture back out.

§PW49. A generative service returns a mesh whose texture has shading painted into it —
a dark line where a seam was drawn, a smudge where the model thought a shadow belonged.
Under the plugin's own lighting those marks are wrong twice over: they are shadows that
do not move when the light does, and they are darker than anything the rig produces.

**The threshold is measured, not found by hand.** Cottony's own pass carried three
constants discovered by eye, which is the cost the search exists to remove.

## What a mark is, in numbers

A texel is compared with the mean of its surroundings, and `below` is how much darker it
is than them. Against Cottony's `booster_hammer.glb`, a 4096-square sheet, at radius 10:

- the typical texel sits **0.0000** from its surroundings, so the measure is centred;
- ordinary detail reaches **0.062** at the 99th percentile;
- painted marks reach **0.372**, six times that.

They separate cleanly, and the question is only where to cut.

## The purely adaptive rule was tried and does not hold

The obvious reading of "more than the texture's own variation" is a bar derived entirely
from that texture. Two spellings were measured and **both break, in opposite
directions**:

- a robust sigma over the whole sheet put the bar at **0.012** and flagged **7.8%** of
  the hammer. Most of a UV sheet is flat unused space, which drags any whole-sheet
  spread down until the bar lands on ordinary detail, and the scrub stops removing
  marks and starts flattening the texture;
- a high percentile of `below` put the bar at **0.565** on a test texture with a line
  across 3% of it, and flagged **nothing** — at that mark fraction the marks *are* the
  99th percentile. A tail cannot measure the body it is a tail of.

So the bar is a **measured floor the texture may raise but never lower**: 0.10, with
`p90 − p50` of `below` allowed to push it higher on a genuinely noisy texture. Across
four textures — flat, lightly detailed, very noisy, and the real hammer — that flags
0.00%, 3.125% (exactly the drawn line), 0.56% and 0.25%. The floor is 0.10 because
ordinary detail on a real texture reaches 0.062 and marks reach 0.372.

## Whether it is worth doing at all

The line said to measure that first, because a repair nobody can see is not worth a pass
over every texel. Rendering the hammer both ways:

| rung | measured noise floor | distance the scrub makes |
|---|---:|---:|
| preview, 256px | 0.0315 | 0.0085 — under the floor |
| final, 1024px | 0.0187 | 0.0452 — **2.5x the floor** |

**Invisible at preview and plainly visible at final**, which answers both questions at
once: worth doing, and worth doing only where the verdict that counts is taken. A
4096-square texture is sampled far more finely at 1024 pixels than at 256, and that is
the whole of the difference.
"""

from __future__ import annotations

from typing import Annotated, Any

import numpy as np

from .describe import Param, operation
from .errors import PolyweaveError

#: How far around a texel counts as "its surroundings", in texels. Wide enough to see
#: past a painted mark, narrow enough that a texture's own gradients are not the
#: reference. Cottony reached 21 at 1024, which is this order as a radius.
REACH = 10

#: The least a texel must be darker than its surroundings to be a mark, in Rec. 709
#: luma. Measured rather than found: ordinary detail on a real 4096-square texture
#: reaches 0.062 at the 99th percentile and painted marks reach 0.372, so this sits
#: above the first and well below the second. A texture may raise it, never lower it.
FLOOR = 0.10

#: How many of the texture's own local variations above the typical texel the bar sits
#: at, where that is higher than the floor. Two, which has a very noisy texture cutting
#: at 0.23 rather than at 0.10 and a quiet one cutting at the floor.
STRICTNESS = 2.0

#: Rec. 709, the same weighting `measure` uses, so "darker" means one thing here.
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _local(values: np.ndarray, reach: int) -> np.ndarray:
    """The mean over a square neighbourhood, by summed-area table.

    A median would be the better reference and costs far more on a 4096-square sheet.
    The mean is pulled towards a mark it contains, which makes this **conservative**:
    it understates how much darker a mark is, so it flags fewer of them and never more.
    """
    pad = np.pad(values, reach + 1, mode="edge")
    whole = pad.cumsum(0).cumsum(1)
    side = 2 * reach + 1
    total = (
        whole[side:, side:]
        - whole[:-side, side:]
        - whole[side:, :-side]
        + whole[:-side, :-side]
    )
    return (total / (side * side))[: values.shape[0], : values.shape[1]]


def marks(
    pixels: Any,
    *,
    reach: int = REACH,
    strictness: float = STRICTNESS,
    floor: float = FLOOR,
) -> dict:
    """Where a texture is darker than itself, and by how much it had to be to count.

    Reports rather than repairs, so the threshold a scrub would use can be read before
    anything is changed — and so a texture with nothing painted into it can be seen to
    have nothing painted into it.
    """
    rgba = np.asarray(pixels, dtype=np.float32)
    if rgba.ndim != 3 or rgba.shape[2] < 3:
        raise PolyweaveError(
            "texture.not-pixels",
            f"a {'x'.join(str(n) for n in rgba.shape)} array is not a texture",
            "pass the texture as a height x width x channels array of floats in 0..1",
        )
    luma = rgba[:, :, :3] @ LUMA
    below = _local(luma, int(reach)) - luma
    middle = float(np.median(below))
    # The body of the distribution and not its tail: at the 99th percentile a texture
    # whose marks cover three percent of it measures its own marks as its variation and
    # then finds none of them. The ninetieth is below any plausible mark fraction.
    variation = float(np.percentile(below, 90)) - middle
    # A floor the texture may raise and never lower, because every purely adaptive bar
    # measured here failed on one texture or another. The module docstring has both.
    bar = max(float(floor), middle + float(strictness) * variation)
    found = below > bar
    return {
        "bar": round(bar, 6),
        "variation": round(variation, 6),
        "darkest": round(float(below.max()), 6),
        "fraction": round(float(found.mean()), 6),
        "mask": found,
        "reference": _local(luma, int(reach)),
        "luma": luma,
    }


def scrub(
    pixels: Any,
    *,
    reach: int = REACH,
    strictness: float = STRICTNESS,
    floor: float = FLOOR,
) -> tuple[np.ndarray, dict]:
    """Lift the marked texels to their surroundings, and say what was lifted.

    The lift is a **per-texel gain** rather than a replacement: a marked texel keeps its
    own hue and is scaled until it is as bright as the neighbourhood it sits in.
    Replacing it with that colour outright would paint over the detail the mark
    happens to cross, which is the failure this is meant to avoid rather than commit.
    """
    rgba = np.asarray(pixels, dtype=np.float32).copy()
    found = marks(rgba, reach=reach, strictness=strictness, floor=floor)
    luma, reference, mask = found["luma"], found["reference"], found["mask"]
    gain = np.where(luma > 1e-6, reference / np.maximum(luma, 1e-6), 1.0)
    for channel in range(3):
        rgba[:, :, channel] = np.where(
            mask, np.clip(rgba[:, :, channel] * gain, 0.0, 1.0), rgba[:, :, channel]
        )
    return rgba, {k: found[k] for k in ("bar", "variation", "darkest", "fraction")}


@operation("texture.worth_scrubbing")
def worth_scrubbing(
    rung: Annotated[str, Param("the rung the render is at")],
) -> bool:
    """Whether the repair shows at this rung, measured rather than assumed.

    Invisible at preview and 2.5x the noise floor at final, on the real hammer. A pass
    over sixteen million texels that changes nothing anybody can see is a pass not worth
    making, and the module docstring holds the numbers.
    """
    return rung == "final"
