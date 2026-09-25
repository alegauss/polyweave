"""What a project's pictures look like, declared once, and a canon only a person grows.

§PW166: a generator asked for consistency in prose gives consistency by luck. Two
pictures of one character from one prompt differ in palette, line weight and
proportion, and a refinement drifts further from the picture it refines. So the style
is an **input every call carries**, not an adjective in a prompt:

- `[style]` (or `[style.<family>]`, one per asset family) declares a `palette`, as
  values, and a `skeleton`, the style block every structured prompt starts from;
- `picture.buy` composes each structured prompt over the skeleton, and the skeleton
  wins where the prompt says otherwise, because a style overridden per call is the
  drift it exists to stop;
- `canon` is a directory of pictures a person approved, each with its described prompt
  where there is one, and a `canon.json` naming the verdict that admitted it.

**The canon grows only by a person's verdict.** `admit` is not an operation: the one
caller is `verdict.judge`, carrying what a person said. An agent that could add its own
output to the canon would make its drift the standard.
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import date as Date
from pathlib import Path
from typing import Annotated

import numpy as np

from . import provenance
from .config import Config, load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: The file in a canon directory that says why each picture is in it.
LEDGER = "canon.json"


def in_force(config: Config, family: str | None) -> tuple[str, dict] | None:
    """The style a picture is held to, or none where the project declares no style."""
    if not config.states("style") and family is None:
        return None
    return config.style(family)


def compose(json_prompt: dict, style: dict) -> dict:
    """A structured prompt over the family's skeleton, with its palette.

    The skeleton's keys win over the prompt's own style keys; the prompt adds what the
    skeleton leaves unsaid. The palette, where declared, is the palette.
    """
    composed = copy.deepcopy(json_prompt)
    own = dict(composed.get("style_description") or {})
    described = {**own, **copy.deepcopy(style.get("skeleton") or {})}
    if style.get("palette"):
        described["color_palette"] = list(style["palette"])
    if described:
        composed["style_description"] = described
    return composed


@operation("style.read")
def read(
    family: Annotated[str, Param("the asset family; needed only among several")] = None,
    root: Annotated[str, Param("the project whose style this is")] = ".",
) -> dict:
    """One family's declared style and the pictures a person admitted to its canon."""
    name, style = load(root).style(family)
    return {"family": name, **style, "admitted": admitted(style)}


def admitted(style: dict) -> list[dict]:
    """What the canon holds, with the verdict each picture came in on."""
    if not style.get("canon"):
        return []
    text = read_text_retrying(Path(style["canon"]) / LEDGER)
    return json.loads(text) if text else []


def admit(
    picture: str,
    *,
    family: str | None,
    why: str,
    choice: str,
    when: str = "",
    root: str | Path = ".",
) -> dict:
    """Copy an approved picture into its family's canon, with the verdict admitting it.

    Called by `verdict.judge` and by nothing else. The described prompt beside the
    picture (`<name>.prompt.json`, from `picture.describe`) goes with it, so a canon
    picture carries its own terms. Admitting one picture twice is a no-op.
    """
    config = load(root)
    here = config.root
    name, style = config.style(family)
    if not style.get("canon"):
        raise PolyweaveError(
            "style.no-canon",
            f"the {name} style declares no canon, so there is nowhere to admit "
            f"{picture} to",
            f"set canon under [style.{name}] to a directory under the project"
            if name != "default"
            else "set canon under [style] to a directory under the project",
        )
    source = here / picture
    digest, _ = provenance.sha256_of(source)
    canon = Path(style["canon"])
    held = admitted(style)
    already = next((e for e in held if e["sha256"] == digest), None)
    if already:
        return already
    canon.mkdir(parents=True, exist_ok=True)
    landed = canon / source.name
    shutil.copy2(source, landed)
    described = source.with_suffix(".prompt.json")
    prompt = None
    if described.is_file():
        shutil.copy2(described, canon / described.name)
        prompt = described.name
    entry = {
        "picture": landed.name,
        "sha256": digest,
        "from": provenance.relative(source, here),
        "prompt": prompt,
        "verdict": {
            "choice": choice,
            "why": why,
            "when": when or Date.today().isoformat(),
        },
    }
    write_atomic(
        canon / LEDGER, json.dumps([*held, entry], indent=2, sort_keys=True) + "\n"
    )
    return entry


# -- drift, measured against the canon (§PW167) -------------------------------------

#: What cannot be seen by number, said in every report rather than left out.
NOT_CHECKED = (
    "whether it is still the same character or subject",
    "the silhouette against a declared outline",
)

#: The least span of lightness, in L*, between a subject's darkest and lightest tones
#: for its darker half to be read as ink. Outlines in a flat drawing are its darkest
#: pixels, and a fixed share of the subject would not find them: a thin outline is
#: under a fifth of a disc and a heavy one over half. So the line is told from the fill
#: by the midpoint between the two, which does not care how much of each there is.
INK = 20.0


@operation("style.drift")
def drift(
    picture: Annotated[str, Param("the picture, under the project")],
    family: Annotated[str, Param("the asset family, needed only among several")] = None,
    root: Annotated[str, Param("the project whose style this is")] = ".",
) -> dict:
    """Refuse a picture that drifts from its family's canon by number, saying which way.

    Palette distance, value and saturation, line weight, edge and light are measured on
    the picture and on every canon picture, each at a percentile. The bar is the canon's
    own spread: how far its approved pictures sit from their median is the floor below
    which a difference means nothing. A canon of fewer than two pictures has no spread,
    and the report says so rather than inventing a floor. A picture that passes is not
    thereby right; `not_checked` says what only a person can see.
    """
    from .image import load as load_image

    config = load(root)
    name, declared = config.style(family)
    floor_alpha = config.tolerances().alpha_floor
    palette = list(declared.get("palette") or [])
    mine = features(load_image(config.root / picture), palette, floor_alpha)
    canon = [
        features(
            load_image(Path(declared["canon"]) / e["picture"]), palette, floor_alpha
        )
        for e in admitted(declared)
    ]
    measures = {
        key: _against(key, value, [c[key] for c in canon if c.get(key) is not None])
        for key, value in mine.items()
        if value is not None and key != "warmth"
    }
    palette_drift = measures.get("palette_delta_e_p95") or {}
    if palette_drift.get("drifted"):
        warmer = mine["warmth"] > float(np.median([c["warmth"] for c in canon]))
        palette_drift["which_way"] = "warmer" if warmer else "cooler"
    judged = len(canon) >= 2
    drifted = sorted(k for k, m in measures.items() if m["drifted"])
    plural = "" if len(canon) == 1 else "s"
    return {
        "family": name,
        "picture": picture,
        "canon": len(canon),
        "judged": judged,
        "floor": f"the spread among {len(canon)} canon pictures"
        if judged
        else f"none: the canon holds {len(canon)} picture{plural}, and a floor is "
        f"the spread among at least two",
        "passed": (not drifted) if judged else None,
        "drifted": drifted,
        "measures": measures,
        "not_checked": list(NOT_CHECKED),
    }


def features(image, palette: list[str], alpha_floor: float) -> dict:
    """What a picture's look is made of, each as a percentile of its subject."""
    from .measure import _hsl, from_hex, to_lab

    mask = image.subject(alpha_floor)
    if not mask.any():
        raise PolyweaveError(
            "style.no-subject",
            f"{image.path} has no pixel above the alpha floor to measure",
            "check the picture is the asset and not an empty frame",
        )
    rgb = image.rgba[..., :3].astype(np.float64) / 255.0
    lab = to_lab(rgb)
    subject = lab[mask]
    saturation = _hsl(rgb[mask])[1] * 100.0
    found: dict = {
        "value_p5": _p(subject[:, 0], 5),
        "value_p95": _p(subject[:, 0], 95),
        "saturation_p5": _p(saturation, 5),
        "saturation_p95": _p(saturation, 95),
        "warmth": round(float(subject[:, 2].mean()), 4),
        "palette_delta_e_p95": None,
    }
    if palette:
        swatches = to_lab(np.array([from_hex(c) for c in palette]))
        nearest = np.linalg.norm(subject[:, None, :] - swatches[None], axis=-1)
        found["palette_delta_e_p95"] = _p(nearest.min(axis=1), 95)
    found["line_weight"] = _line_weight(mask, lab[..., 0])
    found.update(_edge(image, mask, lab, alpha_floor))
    found["light_degrees"] = _light(mask, lab[..., 0])
    return found


def _p(values, q: float) -> float:
    return round(float(np.percentile(values, q)), 4)


def _interior(mask):
    """The pixels of a mask whose four neighbours are in it too."""
    grown = np.pad(mask, 1)
    return (
        mask & grown[:-2, 1:-1] & grown[2:, 1:-1] & grown[1:-1, :-2] & grown[1:-1, 2:]
    )


def _line_weight(mask, lightness) -> float | None:
    """Stroke width of the ink, from how many erosions each ink pixel survives."""
    dark, light = np.percentile(lightness[mask], [5, 95])
    if light - dark < INK:
        return None  # no line darker than the fill: nothing to measure a width of
    ink = mask & (lightness <= (dark + light) / 2.0)
    if ink.sum() < 4:
        return None
    depth = np.zeros(ink.shape, dtype=np.int32)
    left = ink.copy()
    for _ in range(64):
        if not left.any():
            break
        depth += left
        left = _interior(left)
    # A stroke w pixels wide reaches depth about w/2 at its spine, so the deepest
    # pixels, not the typical one, say how wide the strokes are.
    return round(2.0 * float(np.percentile(depth[ink], 90)) - 1.0, 4)


def _edge(image, mask, lab, alpha_floor: float) -> dict:
    """How wide the soft edge is, and how far its colour sits from the subject's."""
    if not image.had_alpha:
        return {"fringe_width": None, "halo_delta_e": None}
    alpha = image.alpha.astype(np.float64) / 255.0
    fringe = (alpha > alpha_floor) & (alpha < 0.98)
    inside = _interior(mask)
    boundary = mask & ~inside
    width = float(fringe.sum()) / max(1.0, float(boundary.sum()))
    core = inside & ~fringe
    halo = (
        float(np.linalg.norm(lab[fringe].mean(0) - lab[core].mean(0)))
        if fringe.any() and core.any()
        else 0.0
    )
    return {"fringe_width": round(width, 4), "halo_delta_e": round(halo, 4)}


def _light(mask, lightness) -> float | None:
    """Where the light comes from, in degrees anticlockwise from the right."""
    rows, columns = np.gradient(lightness)
    inside = _interior(_interior(mask))
    if inside.sum() < 16:
        return None
    across, down = float(columns[inside].mean()), float(rows[inside].mean())
    if np.hypot(across, down) < 1e-3:
        return None  # flat shading: no direction to drift from
    return round(float(np.degrees(np.arctan2(-down, across))) % 360.0, 2)


#: What a difference in each measure is called, larger then smaller.
_WAYS = {
    "value_p5": ("lighter shadows", "darker shadows"),
    "value_p95": ("lighter highlights", "darker highlights"),
    "saturation_p5": ("more saturated", "duller"),
    "saturation_p95": ("more saturated", "duller"),
    "palette_delta_e_p95": ("further from the palette", "closer to the palette"),
    "line_weight": ("thicker lines", "thinner lines"),
    "fringe_width": ("a softer edge", "a harder edge"),
    "halo_delta_e": ("a stronger halo", "less halo"),
}


def _against(key: str, value: float, canon: list[float]) -> dict:
    """One measure held to the canon's spread, and which way it went if it drifted."""
    if len(canon) < 2:
        return {"value": value, "canon": canon, "floor": None, "drifted": False}
    circular = key == "light_degrees"
    middle = float(np.median(canon))
    floor = max(abs(_gap(c, middle, circular)) for c in canon)
    gap = _gap(value, middle, circular)
    # Closer to the palette than the canon is, is not drift: that measure has a side.
    drifted = abs(gap) > floor + 1e-6 and (key != "palette_delta_e_p95" or gap > 0)
    found = {
        "value": value,
        "canon": round(middle, 4),
        "floor": round(floor, 4),
        "off": round(gap, 4),
        "drifted": drifted,
    }
    if drifted:
        if circular:
            turn = "anticlockwise" if gap > 0 else "clockwise"
            found["which_way"] = f"light turned {abs(gap):.0f} degrees {turn}"
        else:
            found["which_way"] = _WAYS[key][0 if gap > 0 else 1]
            if key == "line_weight" and middle > 0:
                found["which_way"] += f", {value / middle:.1f} times the canon's"
    return found


def _gap(value: float, middle: float, circular: bool) -> float:
    gap = value - middle
    return (gap + 180.0) % 360.0 - 180.0 if circular else gap
