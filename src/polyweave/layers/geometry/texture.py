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

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: How far around a texel counts as "its surroundings", in texels **per 1024 of the
#: texture's side**, and never fewer than this. Wide enough to see past a painted
#: mark, narrow enough that a texture's own gradients are not the reference. It was 10
#: at any size, a 21-texel window on a 4096 sheet, and Cottony's wand star is dashed in
#: strokes 20 to 40 texels wide: the window's mean was the stroke, nothing was below
#: it, and the dashes rendered round the star's edge (§PW80). Cottony's own pass worked
#: at 21 at 1024, which is the same order once scaled.
REACH = 10

#: How far a mark's own mask is grown, in texels per 1024, to take the antialiased rim
#: of each stroke with it. Below the bar and plainly darker than the candy, the rim was
#: left as an olive outline round every dash once the dash itself was gone (§PW80).
GROW = 2

#: How much darker than its surroundings a marked texel may be and still keep its own
#: hue, as a gain. Past four, it holds under a quarter of their light, and what reads as
#: its hue is the noise the gain multiplies; it takes its unmarked surroundings' colour.
KEEPS_HUE = 4.0

#: The least a texel must be darker than its surroundings to be a mark, in Rec. 709
#: luma. Measured rather than found: ordinary detail on a real 4096-square texture
#: reaches 0.062 at the 99th percentile and painted marks reach 0.372, so this sits
#: above the first and well below the second. A texture may raise it, never lower it.
FLOOR = 0.10

#: How many of the texture's own local variations above the typical texel the bar sits
#: at, where that is higher than the floor. Two, which has a very noisy texture cutting
#: at 0.23 rather than at 0.10 and a quiet one cutting at the floor.
STRICTNESS = 2.0

#: A mark is also **a darker shade of its surroundings' own hue** (§PW80). Cottony's
#: hammer carries its seam as soft purple dashes on pink, which differ from the pink far
#: more in colour than in light, so no luma bar that leaves ordinary detail alone finds
#: them. Read in CIELAB against the local median colour, the dashes and the soft blots
#: along the head's edge sit 7 to 8 L* darker and 10 delta E away, so the bar is 4 L*
#: and 6 delta E, within 25 degrees of the pink's hue, on a
#: ground with chroma over 15. The hue bound is what keeps another colour's island out:
#: a UV sheet packs the brown handle beside the pink head, and brown is darker than pink
#: and nowhere near its hue. The median rather than the mean keeps an island's border
#: from reading as a shade of the mix across it.
SHADE_LIGHTNESS = 4.0
SHADE_DELTA_E = 6.0
SHADE_HUE = 25.0
SHADE_CHROMA = 15.0

#: The thinnest a shade must be to count, in texels per 1024: the few texels a median
#: still leaves along an island's edge are a line, and grown they would be a band of the
#: wrong colour along a seam. An opening takes them and leaves the dashes.
SHADE_OPEN = 0.5

#: Rec. 709, the same weighting `measure` uses, so "darker" means one thing here.
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _local(values: np.ndarray, reach: int) -> np.ndarray:
    """The mean over a square neighbourhood, by summed-area table.

    A median would be the better reference and costs far more on a 4096-square sheet.
    The mean is pulled towards a mark it contains, which makes this **conservative**:
    it understates how much darker a mark is, so it flags fewer of them and never more.
    """
    side = 2 * reach + 1
    return _summed(values, reach) / (side * side)


def _summed(values: np.ndarray, reach: int) -> np.ndarray:
    """The sum over a square neighbourhood, edges extended, laid out as `values` is."""
    pad = np.pad(values, reach + 1, mode="edge")
    whole = pad.cumsum(0).cumsum(1)
    side = 2 * reach + 1
    total = (
        whole[side:, side:]
        - whole[:-side, side:]
        - whole[side:, :-side]
        + whole[:-side, :-side]
    )
    return total[: values.shape[0], : values.shape[1]]


def scaled(per_1024: float, shape: tuple, *, least: int = 0) -> int:
    """A distance stated per 1024 texels, at this texture's longer side."""
    return max(int(least), round(per_1024 * max(shape[:2]) / 1024))


def _median_colour(rgb: np.ndarray) -> np.ndarray:
    """Each texel's surroundings as their per-channel median, at REACH per 1024.

    Taken at 1024 and brought back up: a median over a 81-texel window on a 4096 sheet
    is a minute, and at a quarter of the size it is seconds and the same answer for a
    reference that only has to know what colour a neighbourhood is.
    """
    from PIL import Image as PILImage
    from PIL import ImageFilter

    tall, wide = rgb.shape[:2]
    shrink = max(1, max(tall, wide) // 1024)
    picture = PILImage.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
    if shrink > 1:
        picture = picture.resize((wide // shrink, tall // shrink), PILImage.BOX)
    window = 2 * REACH + 1
    found = []
    for channel in picture.split():
        settled = channel.filter(ImageFilter.MedianFilter(window))
        if shrink > 1:
            settled = settled.resize((wide, tall), PILImage.BILINEAR)
        found.append(np.asarray(settled, dtype=np.float32))
    return np.stack(found, axis=-1) / 255.0


def shades(pixels: Any) -> np.ndarray:
    """Where a texel is a darker shade of its surroundings' own hue (§PW80)."""
    from polyweave.loop.measure import to_lab

    rgb = np.asarray(pixels, dtype=np.float32)[:, :, :3]
    lab = to_lab(rgb.astype(np.float64))
    ground = to_lab(_median_colour(rgb).astype(np.float64))
    darker = lab[:, :, 0] - ground[:, :, 0] < -SHADE_LIGHTNESS
    away = np.linalg.norm(lab - ground, axis=-1) > SHADE_DELTA_E
    hue = np.degrees(np.arctan2(lab[:, :, 2], lab[:, :, 1]))
    ground_hue = np.degrees(np.arctan2(ground[:, :, 2], ground[:, :, 1]))
    near = np.abs((hue - ground_hue + 180.0) % 360.0 - 180.0) < SHADE_HUE
    coloured = np.hypot(ground[:, :, 1], ground[:, :, 2]) > SHADE_CHROMA
    found = darker & away & near & coloured
    thin = scaled(SHADE_OPEN, found.shape)
    if thin > 0 and found.any():
        side = (2 * thin + 1) ** 2
        kept = _summed(found.astype(np.float32), thin) > side - 0.5
        found = _summed(kept.astype(np.float32), thin) > 0.5
    return found


def marks(
    pixels: Any,
    *,
    reach: int | None = None,
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
    reach = scaled(REACH, rgba.shape, least=REACH) if reach is None else int(reach)
    below = _local(luma, reach) - luma
    middle = float(np.median(below))
    # The body of the distribution and not its tail: at the 99th percentile a texture
    # whose marks cover three percent of it measures its own marks as its variation and
    # then finds none of them. The ninetieth is below any plausible mark fraction.
    variation = float(np.percentile(below, 90)) - middle
    # A floor the texture may raise and never lower, because every purely adaptive bar
    # measured here failed on one texture or another. The module docstring has both.
    bar = max(float(floor), middle + float(strictness) * variation)
    shaded = shades(rgba)
    found = (below > bar) | shaded
    return {
        "bar": round(bar, 6),
        "variation": round(variation, 6),
        "darkest": round(float(below.max()), 6),
        "fraction": round(float(found.mean()), 6),
        "mask": found,
        "shaded": shaded,
        "reference": _local(luma, reach),
        "reach": reach,
        "luma": luma,
    }


def scrub(
    pixels: Any,
    *,
    reach: int | None = None,
    strictness: float = STRICTNESS,
    floor: float = FLOOR,
    grow: int | None = None,
) -> tuple[np.ndarray, dict]:
    """Lift the marked texels to their surroundings, and say what was lifted.

    A marked texel keeps its own hue where it can, as a **per-texel gain** that scales
    it until it is as bright as the neighbourhood it sits in, so the detail a mark
    crosses survives it. Where it holds under a quarter of that light (`KEEPS_HUE`) its
    hue is noise, and it takes the mean colour of the unmarked texels around it
    instead: Cottony's wand star was dashed in near-black, and lifted by a gain each
    dash came back olive (§PW80). The mask is grown by `grow` first, so the rim of a
    stroke goes with it rather than staying as an outline.
    """
    rgba = np.asarray(pixels, dtype=np.float32).copy()
    found = marks(rgba, reach=reach, strictness=strictness, floor=floor)
    luma, reference, mask = found["luma"], found["reference"], found["mask"]
    reach = found["reach"]
    grow = scaled(GROW, rgba.shape) if grow is None else int(grow)
    # A shade of the ground's own hue is a mark by colour, so it keeps no hue of its own
    # worth a gain: lifted, a purple dash on pink stayed a lighter purple (§PW80).
    marked = mask & ~found["shaded"]
    if grow > 0 and mask.any():
        mask = _summed(mask.astype(np.float32), grow) > 0.5
    gain = np.where(luma > 1e-6, reference / np.maximum(luma, 1e-6), np.inf)
    clean = (~mask).astype(np.float32)
    # The colour a texel takes is read as near it as there is clean colour to read: a
    # UV sheet packs islands of other colours side by side, and read over the whole
    # reach, the star's edge came back flecked with the trail's green and pink (§PW80).
    near = max(2 * grow, 2)
    close, around = _summed(clean, near), _summed(clean, reach)
    # A rim is the stroke's own edge, never detail it crosses, so it takes the colour
    # round it; lifted by a gain it stayed a shade darker, an outline (§PW80).
    lost = mask & ((gain > KEEPS_HUE) | ~marked) & (around > 0)
    lifted = mask & ~lost
    for channel in range(3):
        values = rgba[:, :, channel]
        mean = np.where(
            close > 0,
            _summed(values * clean, near) / np.maximum(close, 1.0),
            _summed(values * clean, reach) / np.maximum(around, 1.0),
        )
        raised = np.clip(values * np.minimum(gain, KEEPS_HUE), 0.0, 1.0)
        values = np.where(lifted, raised, values)
        rgba[:, :, channel] = np.where(lost, mean, values)
    said = {k: found[k] for k in ("bar", "variation", "darkest", "reach")}
    return rgba, {**said, "fraction": round(float(mask.mean()), 6), "grow": grow}


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
