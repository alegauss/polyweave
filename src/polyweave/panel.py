"""A menu panel built from a declaration, as nine-patch textures (§PW316).

Starship's menus needed a kit of holo-glass frames: a bevelled edge, corner brackets
and scan lines in the logo's palette, each with a focus, pressed and disabled state. The
only way to have one was a hand-written canvas shader whose numbers were chosen in code
and held by nothing but a verdict on a screenshot.

A `*.panel.toml` declares the frame's parts instead:

    [panel.holo]
    size = [96, 64]                 # the texture, in pixels
    margin = 16                     # nine-patch margin, or [left, top, right, bottom]
    fill = "#0a1a2acc"
    cut = 6                         # each corner cut off at 45 degrees
    # radius = 6                    # or rounded, never both
    edge = { width = 2, colour = "#3fe0ff" }
    brackets = { length = 12, width = 3, colour = "#ff4fd8" }
    scan = { pitch = 3, colour = "#3fe0ff26" }

    [panel.holo.states.focus]
    edge = { colour = "#ffffff" }

`panel.build` draws each state to `<name>.<state>.png`, with a record naming the
declaration, and a Godot `StyleBoxTexture` beside it holding the margins. Whatever sits
at a corner has to fit inside the margin, or the stretch would bend it, so a cut or a
bracket reaching past the margin is refused. Scan lines tile rather than stretch, so
their pitch holds at any height. A picture built here is a picture like any other: a
spec holds its contrast, its edge and its palette.
"""

from __future__ import annotations

import difflib
import math
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a panel's table may hold, and what each part's own table may hold.
PARTS = {
    "size": None,
    "margin": None,
    "fill": None,
    "cut": None,
    "radius": None,
    "outline": None,
    "edge": ("width", "colour"),
    "piping": ("width", "colour", "raise"),
    "brackets": ("length", "width", "colour"),
    "scan": ("pitch", "colour"),
    "tick": ("length", "width", "colour"),
    "states": None,
}

#: The states a panel may declare besides `normal`, as Godot's controls name them.
STATES = ("normal", "hover", "focus", "pressed", "disabled")

#: How many times larger a panel is drawn before it is brought down, for clean edges.
SUPER = 4

#: The most points an outline may have: the shader holds them in a fixed array.
OUTLINE_MOST = 128

_COLOUR = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?")


def _bad(name: str, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("compose.bad-panel", f"panel {name}: {what}", remedy, **extra)


def _colour(name: str, at: str, value: Any) -> tuple[int, int, int, int]:
    found = _COLOUR.fullmatch(value) if isinstance(value, str) else None
    if not found:
        raise _bad(name, f"{at} is {value!r}, which is not a colour",
                   "write it as #rrggbb, or #rrggbbaa with its alpha")
    rgb, alpha = found.group(1), found.group(2) or "ff"
    return (*(int(rgb[i:i + 2], 16) for i in (0, 2, 4)), int(alpha, 16))


def _whole(name: str, at: str, value: Any, least: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < least:
        raise _bad(name, f"{at} is {value!r}",
                   f"write {at} as a whole number from {least}")
    return value


def _keys(name: str, at: str, table: Any, allowed) -> dict:
    if not isinstance(table, dict):
        raise _bad(name, f"{at} is not a table", f"write {at} as a table")
    for key in table:
        if key not in allowed:
            near = difflib.get_close_matches(key, allowed, n=1)
            raise _bad(name, f"{at} has no key {key!r}",
                       f"did you mean {near[0]!r}?" if near
                       else f"it takes {', '.join(allowed)}",
                       given=key, allowed=sorted(allowed))
    return table


def _merged(base: dict, over: dict) -> dict:
    """A state: the panel, with each part it names replaced key by key."""
    out = dict(base)
    for key, value in over.items():
        out[key] = {**base.get(key, {}), **value} if isinstance(value, dict) else value
    return out


def declared(name: str, table: Any, root: Path | str = ".") -> dict[str, dict]:
    """Every state of one panel, each checked whole, refused unless it can be drawn."""
    table = _keys(name, f"[panel.{name}]", table, list(PARTS))
    for part, keys in PARTS.items():
        if keys and part in table:
            _keys(name, part, table[part], list(keys))
    states = _keys(name, "states", table.get("states") or {}, list(STATES))
    base = {k: v for k, v in table.items() if k != "states"}
    out = {"normal": _checked(name, "normal", base, root)}
    for state, over in states.items():
        if state == "normal":
            continue
        _keys(name, f"states.{state}", over, [p for p in PARTS if p != "states"])
        out[state] = _checked(name, state, _merged(base, over), root)
    return out


def _outlined(name: str, state: str, panel: dict, size: tuple[int, int],
              root: Path | str) -> tuple[int, int, bool, list | None]:
    """How the panel is outlined: cut, rounded, a pill, or an outline of its own."""
    cut = _whole(name, "cut", panel.get("cut", 0))
    stated = panel.get("radius", 0)
    pill = stated == "pill"
    if isinstance(stated, str) and not pill:
        raise _bad(name, f"radius is {stated!r}",
                   'write radius as a whole number from 0, or "pill"')
    radius = min(size) // 2 if pill else _whole(name, "radius", stated)
    ring = _fitted(name, panel["outline"], root) if "outline" in panel else None
    given = [k for k, v in (("cut", cut), ("radius", radius), ("outline", ring)) if v]
    if len(given) > 1:
        raise _bad(name, f"in state {state}, {' and '.join(given)} each shape it",
                   "a panel is cut, rounded or outlined: keep one of them")
    return cut, radius, pill, ring


def _fitted(name: str, stated: Any, root: Path | str) -> list[tuple[float, float]]:
    """A geometry outline, stretched over the panel's box, in shares of its size."""
    from .geometry import outline as geometry

    try:
        ring = geometry.resolve(stated, root=root)
    except PolyweaveError as exc:
        raise _bad(name, f"outline: {exc.message}", exc.remedy) from exc
    ring = ring * np.array([1.0, -1.0])  # an outline counts y up, a picture down
    low, span = ring.min(axis=0), np.ptp(ring, axis=0)
    if (span <= 1e-9).any():
        raise _bad(name, "outline is flat, with no width or no height",
                   "give it a shape that encloses something")
    if len(ring) > OUTLINE_MOST:
        raise _bad(name, f"outline has {len(ring)} points and the shader takes "
                   f"{OUTLINE_MOST}", "ask the shape for fewer steps, or trace with a "
                   "larger tolerance")
    return [(float(x), float(y)) for x, y in (ring - low) / span]


def _checked(name: str, state: str, panel: dict, root: Path | str = ".") -> dict:
    size = panel.get("size")
    if not (isinstance(size, list) and len(size) == 2):
        raise _bad(name, "has no size", "write size = [width, height] in pixels")
    width, height = (_whole(name, "size", v, 8) for v in size)
    cut, radius, pill, ring = _outlined(name, state, panel, (width, height), root)
    # An outline is drawn at its size and never stretched, so its margin means nothing.
    margin = panel.get("margin", 1 if ring else 0)
    margins = [margin] * 4 if not isinstance(margin, list) else margin
    if len(margins) != 4:
        raise _bad(name, f"margin is {margin!r}",
                   "write margin as one number, or [left, top, right, bottom]")
    left, top, right, bottom = (_whole(name, "margin", v, 1) for v in margins)
    if left + right >= width or top + bottom >= height:
        raise _bad(name, f"margins {margins} leave no middle in {width}x{height}",
                   "make the panel larger, or the margins smaller")
    edge = panel.get("edge") or {}
    brackets = panel.get("brackets") or {}
    scan = panel.get("scan") or {}
    out = {
        "size": (width, height),
        "margin": (left, top, right, bottom),
        "fill": _colour(name, "fill", panel.get("fill", "#00000000")),
        "cut": cut,
        "radius": radius,
        "pill": pill,
        "outline": ring,
        "stretch": _stretch(ring, pill, width, height),
        "edge": {"width": _whole(name, "edge.width", edge.get("width", 0)),
                 "colour": _colour(name, "edge.colour",
                                   edge.get("colour", "#00000000"))},
        "piping": None,
        "brackets": None,
        "scan": None,
        "tick": None,
    }
    out["piping"] = _piping(name, panel.get("piping") or {})
    out["material"] = _finish(name, panel.get("material") or {})
    out["seam"] = _seam(name, panel.get("seam") or {})
    tick = panel.get("tick") or {}
    if tick:
        out["tick"] = {
            "length": _whole(name, "tick.length", tick.get("length", 0), 1),
            "width": _whole(name, "tick.width", tick.get("width", 1), 1),
            "colour": _colour(name, "tick.colour", tick.get("colour")),
        }
    # Only one of the two is ever set, and either is how far the corner's shape goes.
    corner = cut + radius
    reach = corner + max(out["edge"]["width"],
                         out["piping"]["width"] if out["piping"] else 0)
    if brackets and ring:
        raise _bad(name, f"in state {state}, it has brackets and an outline",
                   "brackets sit on a box's corners: drop them, or outline the panel "
                   "with cut or radius")
    if brackets:
        out["brackets"] = {
            "length": _whole(name, "brackets.length", brackets.get("length", 0), 1),
            "width": _whole(name, "brackets.width", brackets.get("width", 1), 1),
            "colour": _colour(name, "brackets.colour", brackets.get("colour")),
        }
        reach = max(reach, corner + out["brackets"]["length"], out["brackets"]["width"])
    if scan:
        out["scan"] = {
            "pitch": _whole(name, "scan.pitch", scan.get("pitch", 0), 2),
            "colour": _colour(name, "scan.colour", scan.get("colour")),
        }
    # A corner's parts are only drawn true where the nine-patch never stretches them,
    # which for a pill is only across its length.
    held = {"none": (), "width": (left, right), "height": (top, bottom),
            "both": (left, top, right, bottom)}[out["stretch"]]
    if held and reach > min(held):
        raise _bad(
            name,
            f"in state {state}, its corner reaches {reach} px and the smallest margin "
            f"is {min(held)} px, so stretching would bend it",
            "make the margin at least as wide as the cut or radius plus the bracket, "
            "or shorten the bracket",
        )
    return out


def _stretch(ring: list | None, pill: bool, width: int, height: int) -> str:
    """Which way a nine-patch may grow it: a pill keeps its round ends only along its
    length, and an outline of its own is no nine-patch at all."""
    if ring:
        return "none"
    if pill:
        return "width" if width >= height else "height"
    return "both"


def _piping(name: str, piping: dict) -> dict | None:
    """A raised rim inside the outline, the way stuffed fabric is finished (§PW472)."""
    if not piping:
        return None
    rise = piping.get("raise", 0.3)
    number = isinstance(rise, int | float) and not isinstance(rise, bool)
    if not number or not 0 <= rise <= 1:
        raise _bad(name, f"piping.raise is {rise!r}",
                   "write piping.raise from 0, flat, to 1, lit to white")
    return {
        "width": _whole(name, "piping.width", piping.get("width", 0), 1),
        "colour": _colour(name, "piping.colour", piping.get("colour")),
        "raise": float(rise),
    }


#: A material's numbers and what each is when left out: all of them off, so a material
#: names no finish of its own and a project's felt or candy is its declaration (§PW473).
FINISH = {
    "light": (0.36, 0.30),  # where the light falls, in shares of the panel's box
    "lift": 0.0,            # how far the lit top is lightened, 0 to 1
    "shade": 0.0,           # how far the foot falls into its own hue, 0 to 1
    "core": 0.0,            # how strongly the light's spot glows, 0 to 1
    "vivid": 0.0,           # 0 lightens what is lit (felt), 1 saturates it (candy)
    "gloss": 0.0,           # a soft white highlight at the light, 0 to 1
    "grain": 0.0,           # fibre grain across the body, 0 to 1
    "grain_size": 2.0,      # the grain's cell, in the panel's pixels
    "weave": 0.0,           # a woven cross-hatch, 0 to 1
    "weave_pitch": 6.0,     # the weave's period, in the panel's pixels
    "seed": 0,              # which grain
}
PARTS["material"] = tuple(FINISH)

#: A seam's numbers. The four effects are each 0 for off and 1 for the look a craft
#: game's owner read as sewn rather than as a road marking (§PW474).
SEAM = {
    "inset": 4,         # how far in from the outline, in pixels
    "dash": 4.0,        # a stitch's length, in pixels
    "gap": 3.0,         # the space between stitches, in pixels
    "width": 1.5,       # the thread's thickness, in pixels
    "thread": None,     # its colour, which a seam must name
    "shading": 1.0,     # lit along its upper side, shaded along its lower, with plies
    "shadow": 1.0,      # the soft shadow each stitch lays on the cloth
    "holes": 1.0,       # a needle hole past either end, where the thread goes under
    "jitter": 1.0,      # a seeded wander, regular without being ruled
    "seed": 0,
}
PARTS["seam"] = tuple(SEAM)


def _finish(name: str, table: dict) -> dict | None:
    """A fill's material, every number checked, each left out at its default."""
    if not table:
        return None
    def number(value: Any) -> bool:
        return isinstance(value, int | float) and not isinstance(value, bool)

    out = dict(FINISH)
    for key, value in table.items():
        at = f"material.{key}"
        if key == "seed":
            out[key] = _whole(name, at, value)
        elif key == "light":
            if not (isinstance(value, list) and len(value) == 2
                    and all(number(v) for v in value)):
                raise _bad(name, f"{at} is {value!r}",
                           "write light = [x, y], each a share of the panel, 0 to 1")
            out[key] = (float(value[0]), float(value[1]))
        else:
            sized = key.endswith(("_size", "_pitch"))
            low, high = (1, math.inf) if sized else (0, 1)
            if not number(value) or not low <= value <= high:
                said = "pixels from 1" if sized else "from 0 to 1"
                raise _bad(name, f"{at} is {value!r}", f"write {key} as {said}")
            out[key] = float(value)
    return out


def _seam(name: str, table: dict) -> dict | None:
    """A seam, every number checked, each left out at its default."""
    if not table:
        return None
    out = dict(SEAM)
    for key, value in table.items():
        at = f"seam.{key}"
        number = isinstance(value, int | float) and not isinstance(value, bool)
        if key == "thread":
            out[key] = _colour(name, at, value)
        elif key in ("inset", "seed"):
            out[key] = _whole(name, at, value)
        elif key in ("dash", "gap", "width"):
            if not number or value < 0.5:
                raise _bad(name, f"{at} is {value!r}",
                           f"write {key} in pixels from 0.5")
            out[key] = float(value)
        else:
            if not number or not 0 <= value <= 1:
                raise _bad(name, f"{at} is {value!r}", f"write {key} from 0, off, to 1")
            out[key] = float(value)
    if out["thread"] is None:
        raise _bad(name, "seam has no thread", 'name its colour, thread = "#rrggbb"')
    return out


def _stitches(path: np.ndarray, seam: dict, scale: float) -> list[np.ndarray]:
    """The seam's stitches along a closed path, evenly spaced by arc length, each a
    short polyline, with the jitter a hand sews with."""
    closed = np.vstack([path, path[:1]])
    lengths = np.hypot(*np.diff(closed, axis=0).T)
    along = np.concatenate([[0.0], np.cumsum(lengths)])
    total = float(along[-1])
    if total <= 0:
        return []
    period = (seam["dash"] + seam["gap"]) * scale
    count = max(1, round(total / period))
    period = total / count  # whole stitches round the loop, none clipped
    dash = seam["dash"] / (seam["dash"] + seam["gap"]) * period
    rng = np.random.default_rng(seam["seed"])
    width = seam["width"] * scale
    out = []
    steps = max(2, int(dash / (3 * SUPER)) + 2)
    for index in range(count):
        at = index * period + np.linspace(0.0, dash, steps)
        stitch = np.stack([np.interp(at, along, closed[:, 0]),
                           np.interp(at, along, closed[:, 1])], axis=1)
        middle = stitch.mean(axis=0)
        ends = stitch[-1] - stitch[0]
        normal = np.array([-ends[1], ends[0]]) / (float(np.hypot(*ends)) or 1.0)
        turn = rng.normal(0.0, 0.05) * seam["jitter"]
        shove = rng.normal(0.0, width * 0.10) * seam["jitter"]
        c, s = math.cos(turn), math.sin(turn)
        turned = (stitch - middle) @ np.array([[c, s], [-s, c]])
        stitch = turned + middle + normal * shove
        # A touch shorter than its dash, so the needle holes show past its ends.
        out.append(middle + (stitch - middle) * (1.0 - 0.14 * seam["holes"]))
    return out


def _sewn(seam: dict, stitches: list[np.ndarray], cloth: tuple, big: tuple[int, int]):
    """Thread sewn through cloth: round and lit, standing off it, going through it."""
    from PIL import Image, ImageDraw, ImageFilter

    width = seam["width"] * SUPER
    light = np.array([-0.40, -0.92])  # from the upper left, as the material's is

    def stroke(points_of, thick: float, shift=(0.0, 0.0)) -> Image.Image:
        mask = Image.new("L", big, 0)
        pen = ImageDraw.Draw(mask)
        r = thick / 2
        for stitch in points_of:
            moved = [tuple(p + shift) for p in stitch]
            pen.line(moved, fill=255, width=max(1, round(thick)), joint="curve")
            for x, y in (moved[0], moved[-1]):
                pen.ellipse((x - r, y - r, x + r, y + r), fill=255)
        return mask

    def darker(t: float) -> tuple[int, int, int]:
        return tuple(round(part * (1.0 - 0.66 * min(t, 1.0))) for part in cloth[:3])

    layer = Image.new("RGBA", big, (0, 0, 0, 0))
    if seam["shadow"]:
        cast = stroke(stitches, width * 1.15, (width * 0.18, width * 0.42))
        cast = cast.filter(ImageFilter.GaussianBlur(width * 0.35))
        tint = Image.new("RGBA", big, (*darker(0.75), 255))
        tint.putalpha(cast.point(lambda a: round(a * 0.55 * seam["shadow"])))
        layer = Image.alpha_composite(layer, tint)
    if seam["holes"]:
        pits = Image.new("L", big, 0)
        pen = ImageDraw.Draw(pits)
        r = width * 0.36
        for stitch in stitches:
            tangent = stitch[-1] - stitch[0]
            tangent = tangent / (float(np.hypot(*tangent)) or 1.0)
            for end, sign in ((stitch[0], -1.0), (stitch[-1], 1.0)):
                x, y = end + tangent * sign * width * 0.45
                pen.ellipse((x - r, y - r, x + r, y + r), fill=255)
        tint = Image.new("RGBA", big, (*darker(1.1), 255))
        tint.putalpha(pits.point(lambda a: round(a * 0.85 * seam["holes"])))
        layer = Image.alpha_composite(layer, tint)
    body = stroke(stitches, width)
    thread = np.zeros((big[1], big[0], 3)) + np.array(seam["thread"][:3], dtype=float)
    if seam["shading"]:
        # Lit along the side the light comes from, shaded along the other, plies across.
        up, down = light * width * 0.22, -light * width * 0.24
        upper = np.asarray(stroke(stitches, width * 0.5, up)) / 255.0
        lower = np.asarray(stroke(stitches, width * 0.55, down)) / 255.0
        yy, xx = np.mgrid[0:big[1], 0:big[0]]
        plies = np.sin((xx + yy) * (2.0 * math.pi / (width * 1.1)))
        k = seam["shading"]
        gain = 1.0 + k * (0.18 * upper - 0.22 * lower * (1 - upper) + 0.05 * plies)
        thread = thread * gain[..., None]
        thread = thread + (255.0 - thread) * (upper * 0.25 * k)[..., None]
    rgba = np.concatenate([np.clip(thread, 0, 255),
                           np.asarray(body, dtype=float)[..., None]
                           * seam["thread"][3] / 255.0], axis=2)
    return Image.alpha_composite(layer, Image.fromarray(rgba.round().astype(np.uint8),
                                                        "RGBA"))


def _hash(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """A lattice point's value from 0 to 1, in the integer sum the shader does too."""
    with np.errstate(over="ignore"):
        h = (x.astype(np.uint32) * np.uint32(374761393)
             + y.astype(np.uint32) * np.uint32(668265263)
             + np.uint32(seed) * np.uint32(2246822519))
        h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
        h = h ^ (h >> np.uint32(16))
    return (h & np.uint32(0xFFFFFF)).astype(np.float64) / 16777216.0


def _finished(fill: tuple, finish: dict, big: tuple[int, int]) -> np.ndarray:
    """The fill as a material, drawn `big` and lit the way the shader lights it."""
    width, height = big[0] / SUPER, big[1] / SUPER
    px = (np.arange(big[0]) + 0.5) / SUPER
    py = (np.arange(big[1]) + 0.5) / SUPER
    x, y = np.meshgrid(px, py)
    u, v = x / width, y / height
    base = np.array(fill[:3], dtype=float) / 255.0
    warm = np.array([1.0, 0.985, 0.95])

    def lit(amount: float) -> np.ndarray:
        # Felt lightens towards a warm white; candy saturates instead, or the lit part
        # is the one with the least colour in it.
        lum = float(base @ [0.2126, 0.7152, 0.0722])
        pale = base + (warm - base) * amount
        vivid = np.clip(lum + (base - lum) * (1.0 + amount * 2.5), 0.0, 1.0)
        return pale + (vivid - pale) * finish["vivid"]

    top, glow = lit(finish["lift"]), lit(min(finish["lift"] * 1.8, 1.0))
    foot = base * (1.0 - 0.66 * finish["shade"])  # its own hue, never grey
    ramp = np.clip((v + 0.12) / 1.22, 0.0, 1.0)[..., None]
    rgb = top + (foot - top) * ramp
    lx, ly = finish["light"]
    spot = np.hypot(u - lx, v - ly)
    core = (np.clip(1.0 - spot / 0.92, 0.0, 1.0) ** 1.7 * finish["core"])[..., None]
    rgb = rgb + (glow - rgb) * core
    oval = np.hypot((u - lx) / 0.26, (v - ly) / 0.17)
    shine = 1.0 - np.clip((oval - 0.6) / 0.4, 0, 1)
    shine = (shine * shine * (3.0 - 2.0 * shine) * finish["gloss"] * 0.55)[..., None]
    rgb = rgb + (np.array([1.0, 0.995, 0.97]) - rgb) * shine
    if finish["grain"]:
        qx, qy = x / finish["grain_size"], y / finish["grain_size"]
        ix, iy = np.floor(qx), np.floor(qy)
        fx, fy = qx - ix, qy - iy
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        seed = finish["seed"]
        a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
        c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
        top_row, low_row = a + (b - a) * sx, c + (d - c) * sx
        noise = (top_row + (low_row - top_row) * sy) * 2.0 - 1.0
        rgb = rgb * (1.0 + noise * 0.1 * finish["grain"])[..., None]
    if finish["weave"]:
        pitch = finish["weave_pitch"]
        warp = np.sin(x / pitch * math.pi) * np.sin(y / pitch * math.pi)
        rgb = rgb * (1.0 + warp * 0.035 * finish["weave"])[..., None]
    alpha = np.full(rgb.shape[:2] + (1,), fill[3] / 255.0)
    return np.round(np.clip(np.concatenate([rgb, alpha], axis=2), 0, 1) * 255).astype(
        np.uint8)


def _drawn(panel: dict):
    """One state drawn large and brought down, so its diagonals are smooth."""
    from PIL import Image, ImageDraw

    width, height = panel["size"]
    big = (width * SUPER, height * SUPER)
    cut = panel["cut"] * SUPER
    radius = panel["radius"] * SUPER
    corner = cut + radius

    def outline(inset: float) -> list[tuple[float, float]]:
        x0, y0, x1, y1 = inset, inset, big[0] - inset, big[1] - inset
        c = max(0.0, cut - inset * 0.414)
        return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
                (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]

    ring = np.asarray(panel["outline"]) * big if panel["outline"] else None

    def inside(pen, inset: float, fill) -> None:
        """The outline drawn `inset` big pixels in, filled."""
        if ring is not None:
            pen.polygon([tuple(p) for p in _inset(ring, inset)], fill=fill)
        elif radius:
            far = (big[0] - 1 - inset, big[1] - 1 - inset)
            pen.rounded_rectangle((inset, inset, *far), radius=max(0, radius - inset),
                                  fill=fill)
        else:
            pen.polygon(outline(inset), fill=fill)

    edge = panel["edge"]["width"] * SUPER
    shape = Image.new("L", big, 0)
    inside(ImageDraw.Draw(shape), 0, 255)
    picture = Image.new("RGBA", big, (0, 0, 0, 0))
    if panel["material"]:
        fill = Image.fromarray(_finished(panel["fill"], panel["material"], big), "RGBA")
    else:
        fill = Image.new("RGBA", big, panel["fill"])
    picture.paste(fill, (0, 0), shape)
    if panel["scan"]:
        lines = Image.new("RGBA", big, (0, 0, 0, 0))
        pen = ImageDraw.Draw(lines)
        pitch = panel["scan"]["pitch"] * SUPER
        for y in range(0, big[1], pitch):
            pen.rectangle((0, y, big[0], y + SUPER - 1), fill=panel["scan"]["colour"])
        clipped = Image.new("RGBA", big, (0, 0, 0, 0))
        clipped.paste(lines, (0, 0), shape)
        picture = Image.alpha_composite(picture, clipped)
    if panel["piping"]:
        # Ring by ring from the outline in, each shaded where it sits across the tube.
        rings = Image.new("RGBA", big, (0, 0, 0, 0))
        pen = ImageDraw.Draw(rings)
        across = panel["piping"]["width"] * SUPER
        for step in range(across):
            inside(pen, step, _tube(panel["piping"]["colour"], panel["piping"]["raise"],
                                    (step + 0.5) / across))
        hole = Image.new("L", big, 0)
        inside(ImageDraw.Draw(hole), across, 255)
        rings.paste((0, 0, 0, 0), (0, 0), hole)
        picture = Image.alpha_composite(picture, rings)
    if panel["seam"]:
        inset = panel["seam"]["inset"] * SUPER
        if ring is not None:
            path = _inset(ring, inset)
        elif radius:
            path = _rounded((big[0] - 2 * inset, big[1] - 2 * inset),
                            max(0, radius - inset)) + inset
        else:
            path = np.asarray(outline(inset), dtype=float)
        stitches = _stitches(path, panel["seam"], SUPER)
        sewn = _sewn(panel["seam"], stitches, panel["fill"], big)
        clipped = Image.new("RGBA", big, (0, 0, 0, 0))
        clipped.paste(sewn, (0, 0), shape)
        picture = Image.alpha_composite(picture, clipped)
    if edge:
        rim = Image.new("RGBA", big, (0, 0, 0, 0))
        if radius:
            # Drawn inward from the outline, so the rim follows the fill's own curve.
            ImageDraw.Draw(rim).rounded_rectangle(
                (0, 0, big[0] - 1, big[1] - 1), radius=radius,
                outline=panel["edge"]["colour"], width=edge)
        else:
            points = ([tuple(p) for p in _inset(ring, edge / 2)] if ring is not None
                      else outline(edge / 2))
            ImageDraw.Draw(rim).line([*points, points[0]],
                                     fill=panel["edge"]["colour"], width=edge,
                                     joint="curve")
        picture = Image.alpha_composite(picture, rim)
    if panel["brackets"]:
        marks = Image.new("RGBA", big, (0, 0, 0, 0))
        pen = ImageDraw.Draw(marks)
        thick = panel["brackets"]["width"] * SUPER
        reach = corner + panel["brackets"]["length"] * SUPER
        colour = panel["brackets"]["colour"]
        for x, y, dx, dy in ((0, 0, 1, 1), (big[0], 0, -1, 1),
                             (0, big[1], 1, -1), (big[0], big[1], -1, -1)):
            # Along the top or bottom edge and down or up the side, past the corner.
            pen.rectangle(_box(x + dx * corner, y, x + dx * reach, y + dy * thick),
                          fill=colour)
            pen.rectangle(_box(x, y + dy * corner, x + dx * thick, y + dy * reach),
                          fill=colour)
        picture = Image.alpha_composite(picture, marks)
    return picture.resize(panel["size"], Image.Resampling.BOX)


def _rounded(size: tuple[float, float], radius: float) -> np.ndarray:
    """A rounded rectangle's outline from its top-left corner, clockwise on screen."""
    from .geometry import outline as geometry

    ring = geometry.rounded_square(list(size), radius, steps=16)
    return ring + np.array(size) / 2


def _inset(ring: np.ndarray, by: float) -> np.ndarray:
    """An outline moved `by` inward, whichever way round its points were written."""
    from .geometry import outline as geometry

    if by <= 0:
        return ring
    one, two = geometry.offset(ring, by), geometry.offset(ring, -by)
    return one if geometry.area(one) < geometry.area(two) else two


def _tube(colour: tuple, rise: float, across: float) -> tuple[int, int, int, int]:
    """A piping's colour `across` its width (0 to 1): lit along its crown, shaded at
    its flanks, darkened in its own hue rather than towards grey. The shader does the
    same sum."""
    lift = rise * (2.0 * math.sin(math.pi * across) - 1.0)
    rgb = [part + (255 - part) * lift if lift > 0 else part * (1.0 + lift)
           for part in colour[:3]]
    return (*(round(part) for part in rgb), colour[3])


def _box(x0: float, y0: float, x1: float, y1: float) -> tuple[float, ...]:
    return (min(x0, x1), min(y0, y1), max(x0, x1) - 1, max(y0, y1) - 1)


#: Godot's StyleBoxTexture: the texture, its margins, and how the middle is filled.
_STYLEBOX = """[gd_resource type="StyleBoxTexture" load_steps=2 format=3]

[ext_resource type="Texture2D" path="%(texture)s" id="1"]

[resource]
texture = ExtResource("1")
texture_margin_left = %(left)d.0
texture_margin_top = %(top)d.0
texture_margin_right = %(right)d.0
texture_margin_bottom = %(bottom)d.0
axis_stretch_vertical = %(vertical)d
"""


#: A panel as a canvas shader (§PW316): the same parts, drawn at whatever size the
#: Control is, with the accent mark a nine-patch would stretch. Sizes are in the
#: panel's pixels, and `pixel_scale` is how many screen pixels one of them takes.
_PANEL_SHADER = """shader_type canvas_item;

uniform vec4 fill : source_color;
uniform float cut = 0.0;
uniform float radius = 0.0;
uniform float edge_width = 0.0;
uniform vec4 edge_colour : source_color;
uniform float piping_width = 0.0;
uniform vec4 piping_colour : source_color;
uniform float piping_raise = 0.0;
uniform float bracket_length = 0.0;
uniform float bracket_width = 0.0;
uniform vec4 bracket_colour : source_color;
uniform float scan_pitch = 0.0;
uniform vec4 scan_colour : source_color;
uniform float tick_length = 0.0;
uniform float tick_width = 0.0;
uniform vec4 tick_colour : source_color;
uniform float pixel_scale = 1.0;
// The fill's material (§PW473), every number 0 drawing it flat.
uniform vec2 light_at = vec2(0.36, 0.30);
uniform float lift = 0.0;
uniform float shade = 0.0;
uniform float core = 0.0;
uniform float vivid = 0.0;
uniform float gloss = 0.0;
uniform float grain = 0.0;
uniform float grain_size = 2.0;
uniform float weave = 0.0;
uniform float weave_pitch = 6.0;
uniform float seed = 0.0;
// An outline of its own, in shares of the Control's size; none while the count is 0.
uniform float outline_count = 0.0;
uniform vec2 outline_points[128];

// How far p is inside the outline stretched over size, negative outside.
float inside_outline(vec2 p, vec2 size) {
\tint count = int(outline_count);
\tvec2 last = outline_points[count - 1] * size;
\tfloat nearest = 1e20;
\tfloat side = -1.0;
\tfor (int i = 0; i < 128; i++) {
\t\tif (i >= count) {
\t\t\tbreak;
\t\t}
\t\tvec2 a = outline_points[i] * size;
\t\tvec2 e = last - a;
\t\tvec2 w = p - a;
\t\tvec2 b = w - e * clamp(dot(w, e) / max(dot(e, e), 1e-9), 0.0, 1.0);
\t\tnearest = min(nearest, dot(b, b));
\t\tbool up = p.y >= a.y;
\t\tbool down = p.y < last.y;
\t\tbool left = e.x * w.y > e.y * w.x;
\t\tif ((up && down && left) || (!up && !down && !left)) {
\t\t\tside = -side;
\t\t}
\t\tlast = a;
\t}
\treturn side * sqrt(nearest);
}

// A lattice point's value from 0 to 1, the same integer sum panel.build does.
float lattice(vec2 at) {
\tuint h = uint(at.x) * 374761393u + uint(at.y) * 668265263u + uint(seed) * 2246822519u;
\th = (h ^ (h >> 13u)) * 1274126177u;
\th = h ^ (h >> 16u);
\treturn float(h & 16777215u) / 16777216.0;
}

vec3 lit(vec3 base, float amount) {
\tfloat lum = dot(base, vec3(0.2126, 0.7152, 0.0722));
\tvec3 pale = mix(base, vec3(1.0, 0.985, 0.95), amount);
\tvec3 bright = clamp(lum + (base - lum) * (1.0 + amount * 2.5), 0.0, 1.0);
\treturn mix(pale, bright, vivid);
}

// The fill lit as its material, at p in the Control's pixels over size.
vec3 finished(vec3 base, vec2 p, vec2 size) {
\tvec2 uv = p / size;
\tvec3 top = lit(base, lift);
\tvec3 glow = lit(base, min(lift * 1.8, 1.0));
\tvec3 foot = base * (1.0 - 0.66 * shade);
\tvec3 rgb = mix(top, foot, clamp((uv.y + 0.12) / 1.22, 0.0, 1.0));
\tfloat spot = length(uv - light_at);
\trgb = mix(rgb, glow, pow(clamp(1.0 - spot / 0.92, 0.0, 1.0), 1.7) * core);
\tfloat oval = length((uv - light_at) / vec2(0.26, 0.17));
\tfloat shine = 1.0 - clamp((oval - 0.6) / 0.4, 0.0, 1.0);
\tshine = shine * shine * (3.0 - 2.0 * shine);
\trgb = mix(rgb, vec3(1.0, 0.995, 0.97), shine * gloss * 0.55);
\tif (grain > 0.0) {
\t\tvec2 q = p / grain_size;
\t\tvec2 i = floor(q);
\t\tvec2 f = q - i;
\t\tvec2 s = f * f * (3.0 - 2.0 * f);
\t\tfloat upper = mix(lattice(i), lattice(i + vec2(1.0, 0.0)), s.x);
\t\tfloat lower = mix(lattice(i + vec2(0.0, 1.0)), lattice(i + vec2(1.0, 1.0)), s.x);
\t\trgb *= 1.0 + (mix(upper, lower, s.y) * 2.0 - 1.0) * 0.1 * grain;
\t}
\tif (weave > 0.0) {
\t\tfloat warp = sin(p.x / weave_pitch * PI) * sin(p.y / weave_pitch * PI);
\t\trgb *= 1.0 + warp * 0.035 * weave;
\t}
\treturn clamp(rgb, 0.0, 1.0);
}

vec4 over(vec4 below, vec4 above) {
\tfloat a = above.a + below.a * (1.0 - above.a);
\tvec3 c = (above.rgb * above.a + below.rgb * below.a * (1.0 - above.a)) / max(a, 1e-5);
\treturn vec4(c, a);
}

varying vec2 local;

void vertex() {
\tlocal = VERTEX;
}

void fragment() {
\t// In the Control's own pixels: a fragment's UV is never 0, being a pixel's centre.
\tvec2 size = local / max(UV, vec2(1e-4)) / pixel_scale;
\tvec2 p = local / pixel_scale;
\tvec2 d = min(p, size - p);
\tfloat diagonal = (d.x + d.y - cut) * 0.70710678;
\tfloat dist = min(min(d.x, d.y), diagonal);
\t// A rounded corner: within its square, the distance is to the arc. Clamped to half
\t// the smaller side, so a radius past it draws a pill at any size.
\tfloat r = min(radius, min(size.x, size.y) * 0.5);
\tif (r > 0.0 && d.x < r && d.y < r) {
\t\tdist = r - length(vec2(r) - d);
\t}
\tif (outline_count > 0.0) {
\t\tdist = inside_outline(p, size);
\t}
\tfloat corner = cut + r;
\tif (dist < 0.0) {
\t\tCOLOR = vec4(0.0);
\t} else {
\t\tvec4 c = vec4(finished(fill.rgb, p, size), fill.a);
\t\tif (scan_pitch > 0.0 && mod(floor(p.y), scan_pitch) < 1.0) {
\t\t\tc = over(c, scan_colour);
\t\t}
\t\tif (dist < piping_width) {
\t\t\t// Lit along the tube's crown, darkened in its own hue at the flanks.
\t\t\tfloat crown = piping_raise * (2.0 * sin(PI * dist / piping_width) - 1.0);
\t\t\tvec3 tube = crown > 0.0 ? mix(piping_colour.rgb, vec3(1.0), crown)
\t\t\t\t: piping_colour.rgb * (1.0 + crown);
\t\t\tc = over(c, vec4(tube, piping_colour.a));
\t\t}
\t\tif (dist < edge_width) {
\t\t\tc = over(c, edge_colour);
\t\t}
\t\tbool along = d.y < bracket_width && d.x >= corner && d.x < corner + bracket_length;
\t\tbool down = d.x < bracket_width && d.y >= corner && d.y < corner + bracket_length;
\t\tif (bracket_length > 0.0 && (along || down)) {
\t\t\tc = over(c, bracket_colour);
\t\t}
\t\tfloat centred = abs(p.x - size.x * 0.5);
\t\tif (tick_length > 0.0 && p.y < tick_width && centred < tick_length * 0.5) {
\t\t\tc = over(c, tick_colour);
\t\t}
\t\tCOLOR = c;
\t}
}
"""

#: A screen wipe as a canvas shader, covering the screen as `progress` goes 0 to 1.
_WIPE_SHADER = {
    "sweep": """shader_type canvas_item;

uniform vec4 colour : source_color;
uniform float progress : hint_range(0.0, 1.0) = 0.0;
uniform float angle = 0.0;
uniform float bow = 0.0;
uniform float softness = 0.02;

void fragment() {
\tvec2 along = vec2(cos(radians(angle)), sin(radians(angle)));
\tvec2 across = vec2(-along.y, along.x);
\tvec2 q = UV - 0.5;
\tfloat t = dot(q, along) / (abs(along.x) + abs(along.y)) + 0.5;
\tt += bow * (0.25 - dot(q, across) * dot(q, across));
\tfloat front = progress * (1.0 + bow + softness * 2.0) - softness;
\tfloat covered = 1.0 - smoothstep(front - softness, front + softness, t);
\tCOLOR = vec4(colour.rgb, colour.a * covered);
}
""",
    "iris": """shader_type canvas_item;

uniform vec4 colour : source_color;
uniform float progress : hint_range(0.0, 1.0) = 0.0;
uniform vec2 centre = vec2(0.5, 0.5);
uniform float softness = 0.02;

void fragment() {
\tvec2 size = 1.0 / max(fwidth(UV), vec2(1e-6));
\tvec2 q = (UV - centre) * size / max(size.x, size.y);
\tfloat reach = 0.75 * (1.0 - progress);
\tfloat covered = smoothstep(reach - softness, reach + softness, length(q));
\tif (progress >= 1.0) {
\t\tcovered = 1.0;
\t}
\tCOLOR = vec4(colour.rgb, colour.a * covered);
}
""",
}

#: What a wipe's table may hold, by kind; every one takes colour and softness.
WIPES = {"sweep": ("angle", "bow"), "iris": ("centre",)}

_MATERIAL = """[gd_resource type="ShaderMaterial" load_steps=2 format=3]

[ext_resource type="Shader" path="%(shader)s" id="1"]

[resource]
shader = ExtResource("1")
%(parameters)s
"""


def _gd(value: Any) -> str:
    """A value as a .tres writes it: a colour from 0-255 parts, a vector, a number."""
    if isinstance(value, list) and value and isinstance(value[0], tuple):
        flat = (f"{float(part):.6g}" for point in value for part in point)
        return f"PackedVector2Array({', '.join(flat)})"
    if isinstance(value, tuple) and len(value) == 4:
        return f"Color({', '.join(f'{part / 255:.6g}' for part in value)})"
    if isinstance(value, list | tuple):
        return f"Vector2({', '.join(f'{float(part):.6g}' for part in value)})"
    # Always with a point: Godot reads `4` as an int, and a float uniform given an int
    # keeps its default, so a cut of 4 drew as no cut at all.
    said = f"{float(value):.6g}"
    return said if "." in said or "e" in said else f"{said}.0"


def _material(shader: str, parameters: dict) -> str:
    said = "\n".join(f"shader_parameter/{k} = {_gd(v)}" for k, v in parameters.items())
    return _MATERIAL % {"shader": shader, "parameters": said}


def _uniforms(panel: dict) -> dict:
    """One state's look as the panel shader's uniforms."""
    none = (0, 0, 0, 0)
    piping = panel["piping"] or {"width": 0, "colour": none, "raise": 0}
    brackets = panel["brackets"] or {"length": 0, "width": 0, "colour": none}
    scan = panel["scan"] or {"pitch": 0, "colour": none}
    tick = panel["tick"] or {"length": 0, "width": 0, "colour": none}
    shaped = {}
    if panel["outline"]:
        shaped = {"outline_count": len(panel["outline"]),
                  "outline_points": panel["outline"]}
    if panel["material"]:
        shaped.update({k: v for k, v in panel["material"].items() if k != "light"})
        shaped["light_at"] = list(panel["material"]["light"])
    return {
        **shaped,
        "fill": panel["fill"], "cut": panel["cut"],
        # A pill's radius is past any size, so the shader's clamp rounds whole ends.
        "radius": 1e4 if panel["pill"] else panel["radius"],
        "edge_width": panel["edge"]["width"], "edge_colour": panel["edge"]["colour"],
        "piping_width": piping["width"], "piping_colour": piping["colour"],
        "piping_raise": piping["raise"],
        "bracket_length": brackets["length"], "bracket_width": brackets["width"],
        "bracket_colour": brackets["colour"],
        "scan_pitch": scan["pitch"], "scan_colour": scan["colour"],
        "tick_length": tick["length"], "tick_width": tick["width"],
        "tick_colour": tick["colour"],
    }


def wipe(name: str, table: Any) -> dict:
    """One wipe's kind and uniforms, refused unless each key means something."""
    def bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
        return PolyweaveError("compose.bad-panel", f"wipe {name}: {what}", remedy,
                              **extra)

    own = table if isinstance(table, dict) else {}
    kind = own.get("kind")
    if kind not in WIPES:
        raise bad(f"has kind {kind!r}", f"name one of {', '.join(WIPES)}",
                  given=str(kind), allowed=sorted(WIPES))
    allowed = ["kind", "colour", "softness", *WIPES[kind]]
    _keys(name, f"[wipe.{name}]", own, allowed)
    uniforms: dict[str, Any] = {
        "colour": _colour(name, "colour", own.get("colour", "#000000")),
        "softness": float(own.get("softness", 0.02)),
    }
    if not 0.0 <= uniforms["softness"] <= 0.5:
        raise bad(f"softness is {uniforms['softness']}", "write softness from 0 to 0.5")
    if kind == "sweep":
        uniforms["angle"] = float(own.get("angle", 0.0))
        uniforms["bow"] = float(own.get("bow", 0.0))
    else:
        centre = own.get("centre", [0.5, 0.5])
        if not (isinstance(centre, list) and len(centre) == 2):
            raise bad(f"centre is {centre!r}", "write centre = [x, y], each 0 to 1")
        uniforms["centre"] = [float(v) for v in centre]
    return {"kind": kind, "uniforms": uniforms}


def _read(source: str, config) -> tuple[Path, dict, dict]:
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError("compose.bad-panel",
                             f"there is no panel file at {source}",
                             "name a *.panel.toml relative to the project root")
    try:
        tables = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("compose.bad-panel", f"{source} is not TOML",
                             "fix the syntax the detail names",
                             detail=str(exc)) from exc
    panels, wipes = tables.get("panel") or {}, tables.get("wipe") or {}
    stray = sorted(set(tables) - {"panel", "wipe"})
    if stray or not isinstance(panels, dict) or not isinstance(wipes, dict) or not (
        panels or wipes
    ):
        raise PolyweaveError("compose.bad-panel",
                             f"{source} holds no [panel.<name>] or [wipe.<name>]",
                             "write each panel as [panel.<name>] with a size and "
                             "margin, and each wipe as [wipe.<name>] with a kind")
    return where, panels, wipes


@operation("panel.build")
def build(
    source: Annotated[str, Param("the *.panel.toml, relative to the project")],
    panel: Annotated[str, Param("one panel; left out, every one")] = None,
    out: Annotated[
        str, Param("the folder the textures are written to; beside the source if unset")
    ] = None,
    shader: Annotated[
        bool, Param("also write each panel as a canvas shader, with a material a state")
    ] = False,
    root: Annotated[str, Param("the project the panels belong to")] = ".",
) -> dict:
    """Build declared menu panels and screen wipes for the engine, each recorded.

    A panel's states land as <name>.<state>.png nine-patches with their records and
    <name>.<state>.tres styleboxes; one with an `outline` of its own is no nine-patch,
    so it has no stylebox and says `stretch: none`. With `shader`, a panel is also
    <name>.gdshader and a <name>.<state>.material.tres a state, which draws the accent
    tick a nine-patch would stretch. A wipe is always <name>.gdshader and
    <name>.material.tres, its `progress` uniform covering the screen from 0 to 1.
    """
    from . import provenance

    config = load(root)
    where, panels, wipes = _read(source, config)
    if panel is not None and panel not in panels:
        raise PolyweaveError(
            "compose.bad-panel", f"{source} has no panel {panel!r}",
            f"name one of {', '.join(sorted(panels))}",
            given=panel, allowed=sorted(panels),
        )
    chosen = {panel: panels[panel]} if panel else panels
    states = {name: declared(name, table, config.root)
              for name, table in chosen.items()}
    wiped = {} if panel else {name: wipe(name, table) for name, table in wipes.items()}
    folder = config.path("paths.work", out) if out else where.parent
    folder.mkdir(parents=True, exist_ok=True)

    def res(path: Path) -> str:
        return "res://" + provenance.relative(path, config.root)

    def recorded(target: Path, kind: str, params: dict) -> None:
        provenance.write(provenance.build(
            kind, target, engine={"name": "panel.build"},
            inputs=[provenance.source("declaration", where, config.root)],
            params=params, root=config.root,
        ), config.root)

    made: dict[str, dict] = {}
    for name, drawn in states.items():
        made[name] = {}
        program = folder / f"{name}.gdshader"
        if shader:
            program.write_text(_PANEL_SHADER, encoding="utf-8", newline="\n")
            recorded(program, "vfx", {"panel": name})
        for state, own in drawn.items():
            target = folder / f"{name}.{state}.png"
            _drawn(own).save(target)
            left, top, right, bottom = own["margin"]
            recorded(target, "picture",
                     {"panel": name, "state": state, "margin": list(own["margin"])})
            made[name][state] = {
                "file": provenance.relative(target, config.root),
                "size": list(own["size"]),
                "margin": list(own["margin"]),
                "stretch": own["stretch"],
            }
            if own["stretch"] != "none":
                style = target.with_suffix(".tres")
                style.write_text(_STYLEBOX % {
                    "texture": res(target),
                    "left": left, "top": top, "right": right, "bottom": bottom,
                    # Scan lines tile, so their pitch holds whatever height it is.
                    "vertical": 2 if own["scan"] else 0,
                }, encoding="utf-8", newline="\n")
                made[name][state]["stylebox"] = provenance.relative(style, config.root)
            if own["tick"] and not shader:
                # Said, not dropped silently: mid-edge, a nine-patch would stretch it.
                made[name][state]["not_drawn"] = ["tick"]
            if own["seam"] and own["stretch"] != "none":
                # Its stitches run the whole edge, so a grown nine-patch draws longer
                # ones in its middle: true only at the size it was built.
                made[name][state]["stretched"] = ["seam"]
            if own["seam"] and shader:
                made[name][state]["not_in_shader"] = ["seam"]
            if shader:
                material = folder / f"{name}.{state}.material.tres"
                material.write_text(_material(res(program), _uniforms(own)),
                                    encoding="utf-8", newline="\n")
                made[name][state]["shader"] = provenance.relative(program, config.root)
                made[name][state]["material"] = provenance.relative(material,
                                                                    config.root)
    swept: dict[str, dict] = {}
    for name, own in wiped.items():
        program = folder / f"{name}.gdshader"
        program.write_text(_WIPE_SHADER[own["kind"]], encoding="utf-8", newline="\n")
        recorded(program, "vfx", {"wipe": name, "kind": own["kind"]})
        material = folder / f"{name}.material.tres"
        material.write_text(_material(res(program), own["uniforms"]),
                            encoding="utf-8", newline="\n")
        swept[name] = {
            "kind": own["kind"],
            "shader": provenance.relative(program, config.root),
            "material": provenance.relative(material, config.root),
        }
    answer: dict[str, Any] = {"source": provenance.relative(where, config.root),
                              "panels": made}
    if swept:
        answer["wipes"] = swept
    return answer


#: What films one built item: a ColorRect wearing each material in turn, each held for
#: HOLD frames so the frame kept is one drawn after the change.
_FILM = """extends SceneTree

var rect := ColorRect.new()
var looks: Array = []
var shown := -1

func _initialize() -> void:
\tvar backdrop := ColorRect.new()
\tbackdrop.color = Color(%(backdrop)s)
\tbackdrop.size = Vector2(%(width)d, %(height)d)
\troot.add_child.call_deferred(backdrop)
\trect.position = Vector2(%(x)d, %(y)d)
\trect.size = Vector2(%(w)d, %(h)d)
\trect.color = Color(1, 1, 1, 1)
\troot.add_child.call_deferred(rect)
\tfor path in [%(materials)s]:
\t\tlooks.append(load(path))

func _process(_delta: float) -> bool:
\tvar frame := Engine.get_process_frames()
\tvar index := (frame - %(start)d) / %(hold)d
\tif index >= 0 and index < looks.size() and index != shown:
\t\tshown = index
\t\tvar look: ShaderMaterial = looks[index].duplicate()
\t\t%(progress)s
\t\trect.material = look
\tif frame == %(start)d:
\t\tprint("environment: resolution=%%dx%%d" %% [root.size.x, root.size.y])
\t\tprint("movie: from %%d" %% frame)
\tif frame == %(stop)d:
\t\tprint("movie: to %%d" %% frame)
\treturn frame >= %(stop)d + 3
"""

#: Frames each look is held for, and the frame of the hold that is kept.
HOLD = 3

#: The screen a panel or a wipe is filmed on.
SCREEN = (320, 180)


@operation("panel.capture", kind="capture")
def capture(
    source: Annotated[str, Param("the *.panel.toml, relative to the project")],
    *,
    out: Annotated[str, Param("the folder the stills go to, under the project")],
    steps: Annotated[
        int, Param("how many stills of a wipe, from progress 0 to 1", lo=2, hi=32)
    ] = 5,
    scale: Annotated[
        int, Param("screen pixels to one of a panel's", lo=1, hi=8)
    ] = 2,
    root: Annotated[str, Param("the project the panels belong to")] = ".",
) -> dict:
    """Film each panel's shader in each state, and each wipe at each progress step.

    The shaders are built first, as `panel.build(shader=true)` builds them, then drawn
    by the engine itself: one still per state as <name>.<state>.capture.png and one per
    step as <wipe>.<step>.capture.png, each recorded, for a spec to hold and a person to
    judge. Needs a display, as `capture.movie` does.
    """
    import shutil

    from . import capture as filming
    from . import provenance

    config = load(root)
    built = build(source, out=out, shader=True, root=root)
    folder = config.path("paths.work", out)
    work = config.path("paths.work") / "panel-film"
    taken: dict[str, dict] = {}
    films = [
        (name, list(states), [states[s]["material"] for s in states],
         max(states["normal"]["size"][0] * scale, 1),
         max(states["normal"]["size"][1] * scale, 1), None)
        for name, states in built["panels"].items()
    ] + [
        (name, [f"{k:02d}" for k in range(steps)], [own["material"]] * steps,
         SCREEN[0], SCREEN[1], steps)
        for name, own in (built.get("wipes") or {}).items()
    ]
    for name, labels, materials, w, h, wiping in films:
        start, count = 2, len(labels) * HOLD
        script = work / f"{name}.film.gd"
        script.parent.mkdir(parents=True, exist_ok=True)
        progress = (
            f'look.set_shader_parameter("progress", float(index) / {wiping - 1}.0)'
            if wiping else f'look.set_shader_parameter("pixel_scale", {scale}.0)'
        )
        script.write_text(_FILM % {
            "backdrop": "0.5, 0.5, 0.5, 1", "width": SCREEN[0], "height": SCREEN[1],
            "x": (SCREEN[0] - w) // 2 if not wiping else 0,
            "y": (SCREEN[1] - h) // 2 if not wiping else 0, "w": w, "h": h,
            "materials": ", ".join(f'"res://{m}"' for m in materials),
            "start": start, "stop": start + count - 1, "hold": HOLD,
            "progress": progress,
        }, encoding="utf-8", newline="\n")
        shot = filming.movie(
            provenance.relative(script, config.root), out=str(work / name),
            root=str(config.root),
            environment={"resolution": f"{SCREEN[0]}x{SCREEN[1]}"}, record=False,
        )
        if not shot["ok"]:
            raise PolyweaveError(
                "compose.unfilmed",
                f"{name} could not be filmed: {shot.get('why')}",
                "run it where a display is, or through the offscreen route; the log "
                "is named in the detail",
                detail=shot.get("log"),
            )
        taken[name] = {}
        for index, label in enumerate(labels):
            frame = work / name / f"{index * HOLD + HOLD:04d}.png"
            still = folder / f"{name}.{label}.capture.png"
            shutil.copyfile(frame, still)
            params = {"panel" if not wiping else "wipe": name,
                      "state" if not wiping else "progress":
                      label if not wiping else round(index / (wiping - 1), 6)}
            provenance.write(provenance.build(
                "capture", still, engine={"name": "panel.capture"},
                inputs=[provenance.source("declaration", config.path(
                    "paths.work", source), config.root),
                    provenance.source("material", config.root / materials[index],
                                      config.root)],
                params=params, root=config.root,
            ), config.root)
            taken[name][label] = provenance.relative(still, config.root)
        shutil.rmtree(work / name, ignore_errors=True)
    return {"source": built["source"], "stills": taken}
