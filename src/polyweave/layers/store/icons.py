"""A set of small 2D icons, declared, built and held to legibility (§PW331).

Starship's prompts named their buttons in words, and the owner wanted each button drawn
as the player sees it on the pad: the face buttons in their own colours, shoulders and
triggers as their shapes, keycaps for the keyboard, with a lit rim, shading, the symbol
in its colour and a dark outline that reads over a bright scene. The project may not
draw them by hand, so a set is a declaration, `*.icons.toml`:

    name  = "xbox"
    sizes = [32, 64]           # each icon at each size, or one atlas per size
    atlas = false

    [style]                    # the set's look; an icon may override any of it
    outline = "#101014"        # the dark edge that reads over a bright scene
    outline_width = 0.07       # as a share of the icon's size
    rim = 0.35                 # how much lighter the lit rim is than the fill
    shade = 0.3                # how much darker the fill's foot is than its top

    [icon.a]
    shape  = "circle"          # circle, rounded, pill, trigger, keycap, dpad, stick
    fill   = "#3BA935"
    symbol = "A"               # text, or a glyph: cross, ring, square, triangle,
    symbol_colour = "#FFFFFF"  # up, down, left, right, menu (three bars), view, plus,
                               # minus, or north, south, east, west (four dots, that
                               # one filled); text is fitted by its ink as a glyph is
    symbol_scale = 1.0         # how much of the symbol's box it fills, 0.2 to 2

    [icon.dpad_up]
    shape = "dpad"
    direction = "up"           # its arm is lit and holds the arrow

Each icon is drawn four times over and brought down, so its edges are smooth at 32
pixels. `[accept]` holds every icon at the smallest size to the set's bounds: the
symbol's contrast against its face, the icon's edge against a light and a dark
background, and the symbol's share of the face. A sitting puts the set in front of a
person, since whether it reads as the pad is theirs to say.

An icon may instead be a picture of a model the project built (§PW610), a palette tile
or a bestiary entry, rendered rather than cropped by hand:

    [icon.slime]
    model = "build/actors/slime.glb"   # a mesh under the project
    view = "three_quarter"             # or front or side; azimuth and elevation win
    margin = 1.1                       # room around the subject, as render.bake's
    background = "#20242C"             # or "transparent", the default
    rung = "final"                     # the render rung, final unless named
    light = { key = 600, ambient = 0.4 }   # any of render.bake's lights

It is rendered once at twice the largest size and brought down to each. Its record
names the mesh and its hash beside the declaration, so `provenance.outdated` lists
every picture a model edit left behind and `icons.build` again makes them anew. At the
smallest size it is held to `coverage` (the share of the square it fills),
`silhouette_kept` (how much of its outline survives the shrinking, as an overlap) and
`background_contrast` against its background, or the worse of white and black where it
has none.
"""

from __future__ import annotations

import json
import math
import re
import tomllib
from pathlib import Path
from typing import Annotated

import numpy as np

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: What an icon may be shaped as, and what a glyph symbol may be.
SHAPES = ("circle", "rounded", "pill", "trigger", "keycap", "dpad", "stick", "hexagon")
GLYPHS = ("cross", "ring", "square", "triangle", "up", "down", "left", "right", "menu",
          "view", "north", "south", "east", "west", "plus", "minus", "star", "figure",
          "shield")

#: Text a glyph already draws, drawn as that glyph: a font's "+" is a hairline beside
#: the set's strokes, at any size it is fitted to (§PW642).
_AS_GLYPH = {"+": "plus", "-": "minus", "−": "minus"}

#: A symbol whose share of its face is under this share of the set's median is named in
#: what was measured, bound or no bound: a speck is never what was meant (§PW642).
SPECK = 1 / 3

#: The compass glyphs: four buttons in a diamond, the one named filled, as a pad that
#: prints nothing on its face buttons is told which one to press (§PW431).
_COMPASS = {"north": (0.5, 0.18), "south": (0.5, 0.82), "west": (0.18, 0.5),
            "east": (0.82, 0.5)}

#: How many times over an icon is drawn before it is brought down to its size.
_OVER = 4

#: The set's look where it says nothing of its own.
_STYLE = {"outline": "#101014", "outline_width": 0.07, "rim": 0.35, "shade": 0.3,
          "fill": "#5A5F6A", "symbol_colour": "#FFFFFF", "symbol_scale": 1.0}

#: Every key an icon, the style and `[accept]` may carry.
_ICON_KEYS = {"shape", "symbol", "direction", "tints", *_STYLE}
_ACCEPT_KEYS = {"symbol_contrast_min", "background_contrast_min", "symbol_share_min",
                "coverage_min", "silhouette_kept_min"}

#: What an icon rendered from a model may say, and the views it may name (§PW610). A
#: view is render.bake's camera: the rig's own three-quarter, straight on, or the side.
_MODEL_KEYS = {"model", "view", "azimuth", "elevation", "margin", "focal_mm",
               "background", "rung", "light"}
VIEWS = {"three_quarter": (35.0, 20.0), "front": (0.0, 0.0), "side": (90.0, 0.0)}
#: The lights `light` may set, as render.bake names them.
_LIGHTS = {"key", "fill", "rim", "ambient", "ambient_colour", "exposure",
           "light_distance"}
_MESHES = (".glb", ".gltf", ".fbx")


def _refuse(source: Path, what: str, remedy: str, **more) -> PolyweaveError:
    return PolyweaveError("compose.bad-icons", f"{source.name}: {what}", remedy, **more)


def read(source: Path) -> dict:
    """The declaration, its icons resolved over the set's style, or a refusal."""
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise _refuse(source, "the declaration cannot be read as TOML",
                      "fix the syntax the detail points at", detail=str(exc)) from exc
    sizes = declared.get("sizes") or [64]
    if not all(isinstance(n, int) and 8 <= n <= 1024 for n in sizes):
        raise _refuse(source, f"sizes are {sizes!r}, and a size is 8 to 1024 pixels",
                      "write sizes = [32, 64]")
    style = {**_STYLE, **(declared.get("style") or {})}
    icons = {}
    for name, own in (declared.get("icon") or {}).items():
        if "model" in own:
            icons[name] = _modelled(source, name, own)
            continue
        unknown = sorted(set(own) - _ICON_KEYS - {"states"})
        if unknown:
            raise _refuse(source, f"[icon.{name}] declares {', '.join(unknown)}",
                          f"use some of {', '.join(sorted(_ICON_KEYS | {'states'}))}",
                          given=unknown[0], allowed=sorted(_ICON_KEYS | {"states"}))
        states = own.get("states") or {}
        base = {**style, **{k: v for k, v in own.items() if k != "states"}}
        icons[name] = _checked(source, name, base)
        # A state is the icon with what it changes, built and measured as an icon of
        # its own: a mark earned and one still to earn, from one declaration (§PW644).
        if not isinstance(states, dict):
            raise _refuse(source, f"[icon.{name}] has states {states!r}",
                          f"write [icon.{name}.states.empty] with what it changes")
        for state, changed in states.items():
            unknown = sorted(set(changed) - _ICON_KEYS) if isinstance(
                changed, dict) else ["(not a table)"]
            if unknown:
                raise _refuse(source, f"[icon.{name}.states.{state}] declares "
                              f"{', '.join(unknown)}",
                              f"use some of {', '.join(sorted(_ICON_KEYS))}",
                              given=unknown[0], allowed=sorted(_ICON_KEYS))
            icons[f"{name}_{state}"] = _checked(source, f"{name}.states.{state}",
                                                {**base, **changed})
    if not icons:
        raise _refuse(source, "the set declares no [icon.<name>]",
                      'declare each as [icon.a] with shape = "circle"')
    accept = declared.get("accept") or {}
    unknown = sorted(set(accept) - _ACCEPT_KEYS)
    if unknown:
        raise _refuse(source, f"[accept] declares {', '.join(unknown)}",
                      f"use some of {', '.join(sorted(_ACCEPT_KEYS))}")
    return {"name": str(declared.get("name") or source.name.split(".")[0]),
            "sizes": sizes, "atlas": bool(declared.get("atlas")), "icons": icons,
            "accept": accept}


def _checked(source: Path, name: str, icon: dict) -> dict:
    """One drawn icon's keys, refused where they cannot be drawn."""
    scale = icon["symbol_scale"]
    if isinstance(scale, bool) or not isinstance(scale, int | float) or not (
            0.2 <= scale <= 2):
        raise _refuse(source, f"[icon.{name}] has symbol_scale {scale!r}",
                      "write symbol_scale from 0.2 to 2, 1 filling its box")
    if icon.get("shape") not in SHAPES:
        raise _refuse(source, f"[icon.{name}] is shaped {icon.get('shape')!r}",
                      f"make it one of {', '.join(SHAPES)}",
                      given=str(icon.get("shape")), allowed=SHAPES)
    tints = icon.get("tints") or []
    if not isinstance(tints, list) or not all(
            isinstance(t, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", t) for t in tints):
        raise _refuse(source, f"[icon.{name}] has tints {tints!r}",
                      'write tints = ["#e85d4a", "#4ab0e8"], the colours the game '
                      "tints it with")
    return {**icon, "tints": list(tints)}


def _modelled(source: Path, name: str, own: dict) -> dict:
    """An icon rendered from a model, its camera, lights and background checked."""
    unknown = sorted(set(own) - _MODEL_KEYS)
    if unknown:
        raise _refuse(source, f"[icon.{name}] renders a model and declares "
                      f"{', '.join(unknown)}",
                      "an icon from a model takes some of "
                      f"{', '.join(sorted(_MODEL_KEYS))}; a shape is drawn, not "
                      "rendered",
                      given=unknown[0], allowed=sorted(_MODEL_KEYS))
    if Path(str(own["model"])).suffix.lower() not in _MESHES:
        raise _refuse(source, f"[icon.{name}] names {own['model']!r} as its model",
                      f"name a mesh, one of {', '.join(_MESHES)}, built or ingested")
    view = str(own.get("view", "three_quarter"))
    if view not in VIEWS:
        raise _refuse(source, f"[icon.{name}] views it from {view!r}",
                      f"make view one of {', '.join(VIEWS)}, or give azimuth and "
                      "elevation", given=view, allowed=sorted(VIEWS))
    light = own.get("light") or {}
    if not isinstance(light, dict) or set(light) - _LIGHTS:
        raise _refuse(source, f"[icon.{name}] lights it with {light!r}",
                      f"give light as a table of some of {', '.join(sorted(_LIGHTS))}")
    background = str(own.get("background", "transparent"))
    if background != "transparent":
        try:
            _colour(background)
        except ValueError:
            raise _refuse(source, f"[icon.{name}] has a background of {background!r}",
                          'give it as "#RRGGBB", or "transparent"') from None
    azimuth, elevation = VIEWS[view]
    return {"model": str(own["model"]),
            "azimuth": float(own.get("azimuth", azimuth)),
            "elevation": float(own.get("elevation", elevation)),
            "margin": float(own.get("margin", 1.15)),
            "focal_mm": float(own.get("focal_mm", 50.0)),
            "background": background, "rung": str(own.get("rung", "final")),
            "light": dict(light)}


def _colour(text: str) -> tuple[int, int, int]:
    text = str(text).lstrip("#")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))


def _mix(colour, toward, share):
    pairs = zip(colour, toward, strict=True)
    return tuple(round(c + (t - c) * share) for c, t in pairs)


def _mask(shape: str, size: int, inset: float, direction: str | None):
    """The shape's pixels at `size`, shrunk by `inset` pixels on every side."""
    from PIL import Image, ImageDraw

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    a, b = inset, size - 1 - inset
    span = b - a
    if shape in ("circle", "stick"):
        draw.ellipse((a, a, b, b), fill=255)
    elif shape == "rounded":
        draw.rounded_rectangle((a, a, b, b), radius=span * 0.22, fill=255)
    elif shape == "keycap":
        draw.rounded_rectangle((a, a, b, b), radius=span * 0.14, fill=255)
    elif shape == "pill":
        top, bottom = a + span * 0.22, b - span * 0.22
        draw.rounded_rectangle((a, top, b, bottom), radius=(bottom - top) / 2, fill=255)
    elif shape == "trigger":
        draw.rounded_rectangle((a + span * 0.12, a, b - span * 0.12, b),
                               radius=span * 0.38, fill=255)
        draw.rectangle((a + span * 0.12, a + span * 0.6, b - span * 0.12, b), fill=255)
    elif shape == "dpad":
        third = span / 3
        draw.rectangle((a + third, a, b - third, b), fill=255)
        draw.rectangle((a, a + third, b, b - third), fill=255)
    elif shape == "hexagon":
        # Point up, as a pip on a map card stands (§PW644).
        middle, radius = (a + b) / 2, span / 2
        draw.polygon([(middle + radius * math.cos(math.radians(90 + 60 * k)),
                       middle - radius * math.sin(math.radians(90 + 60 * k)))
                      for k in range(6)], fill=255)
    return np.asarray(mask, dtype=np.float64) / 255.0


def _glyph(draw, glyph: str, box, colour, width: int) -> None:
    """A drawn symbol inside `box`: the pad's shapes and the four arrows."""
    left, top, right, bottom = box
    cx, cy = (left + right) / 2, (top + bottom) / 2
    if glyph == "cross":
        draw.line((left, top, right, bottom), fill=colour, width=width)
        draw.line((left, bottom, right, top), fill=colour, width=width)
    elif glyph == "ring":
        draw.ellipse(box, outline=colour, width=width)
    elif glyph == "square":
        draw.rectangle(box, outline=colour, width=width)
    elif glyph == "triangle":
        draw.polygon([(cx, top), (right, bottom), (left, bottom)], outline=colour,
                     width=width)
    elif glyph == "menu":
        for y in (top + (bottom - top) * f for f in (0.2, 0.5, 0.8)):
            draw.line((left, y, right, y), fill=colour, width=width)
    elif glyph == "star":
        side = min(right - left, bottom - top) / 2
        draw.polygon([(cx + (side if k % 2 == 0 else side * 0.42)
                       * math.cos(math.radians(90 + 36 * k)),
                       cy - (side if k % 2 == 0 else side * 0.42)
                       * math.sin(math.radians(90 + 36 * k)) + side * 0.06)
                      for k in range(10)], fill=colour)
    elif glyph == "figure":
        # A head over a pair of shoulders: a person, a crew member, a holder.
        side = right - left
        head = side * 0.2
        draw.ellipse((cx - head, top, cx + head, top + 2 * head), fill=colour)
        draw.chord((left + side * 0.08, top + side * 0.5, right - side * 0.08,
                    bottom + side * 0.42), 180, 360, fill=colour)
    elif glyph == "shield":
        side = right - left
        shoulder, waist = top + side * 0.12, top + side * 0.5
        draw.polygon([(left, shoulder), (cx, top), (right, shoulder), (right, waist),
                      (cx, bottom), (left, waist)], fill=colour)
    elif glyph in ("plus", "minus"):
        # As thick as the glyphs beside it, so a toolbar's add and remove match them.
        draw.line((left, cy, right, cy), fill=colour, width=round(width * 1.4))
        if glyph == "plus":
            draw.line((cx, top, cx, bottom), fill=colour, width=round(width * 1.4))
    elif glyph in _COMPASS:
        side = right - left
        radius = side * 0.16
        for named, (x, y) in _COMPASS.items():
            px, py = left + side * x, top + (bottom - top) * y
            dot = (px - radius, py - radius, px + radius, py + radius)
            if named == glyph:
                draw.ellipse(dot, fill=colour)
            else:
                draw.ellipse(dot, outline=colour, width=max(1, width // 2))
    elif glyph == "view":
        step = (right - left) * 0.3
        draw.rectangle((left, top, right - step, bottom - step), outline=colour,
                       width=width)
        draw.rectangle((left + step, top + step, right, bottom), outline=colour,
                       width=width)
    else:
        points = {
            "up": [(cx, top), (right, bottom), (left, bottom)],
            "down": [(left, top), (right, top), (cx, bottom)],
            "left": [(left, cy), (right, top), (right, bottom)],
            "right": [(left, top), (right, cy), (left, bottom)],
        }[glyph]
        draw.polygon(points, fill=colour)


def _text(pen, said: str, box, fonts) -> None:
    """Text fitted by its ink to `box`, as a glyph fills it (§PW642).

    A font's size is its line, not its ink: at half the icon a "+" inked a twentieth of
    the face and a "-" a speck. So the text is measured at one size and scaled until its
    ink meets the box on its longer side, then centred on that ink.
    """
    left, top, right, bottom = box
    trial = 100.0
    ink = pen.textbbox((0, 0), said, font=fonts.load_default(size=trial), anchor="lt")
    wide, tall = max(ink[2] - ink[0], 1), max(ink[3] - ink[1], 1)
    size = trial * min((right - left) / wide, (bottom - top) / tall)
    font = fonts.load_default(size=size)
    ink = pen.textbbox((0, 0), said, font=font, anchor="lt")
    at = ((left + right) / 2 - (ink[0] + ink[2]) / 2,
          (top + bottom) / 2 - (ink[1] + ink[3]) / 2)
    pen.text(at, said, fill=255, font=font, anchor="lt")


#: Where each D-pad arm sits, as the share of the icon each side of it reaches.
_ARMS = {
    "up": (0.36, 0.06, 0.64, 0.34),
    "down": (0.36, 0.66, 0.64, 0.94),
    "left": (0.06, 0.36, 0.34, 0.64),
    "right": (0.66, 0.36, 0.94, 0.64),
}


def _arm(icon: dict, big: int) -> np.ndarray | None:
    """The pressed arm of a D-pad as a mask, or None where it names no direction."""
    reach = _ARMS.get(str(icon.get("direction")))
    if reach is None:
        return None
    mask = np.zeros((big, big))
    left, top, right, bottom = (round(v * big) for v in reach)
    mask[top:bottom, left:right] = 1.0
    return mask


def _arm_box(direction: str, big: int) -> tuple:
    """The arrow's box inside the pressed arm."""
    left, top, right, bottom = (v * big for v in _ARMS[direction])
    inset = (right - left) * 0.22
    return (left + inset, top + inset, right - inset, bottom - inset)


def draw(icon: dict, size: int):
    """One icon at `size` pixels, with its face, symbol and outline as masks too."""
    from PIL import Image, ImageDraw, ImageFont

    big = size * _OVER
    edge = max(1.0, float(icon["outline_width"]) * big)
    outer = _mask(icon["shape"], big, 0, icon.get("direction"))
    face = _mask(icon["shape"], big, edge, icon.get("direction"))
    lit = _mask(icon["shape"], big, edge * 1.9, icon.get("direction"))
    fill = np.array(_colour(icon["fill"]), dtype=np.float64)
    # Lighter at the top and darker at the foot: a lit, rounded face, not a flat disc.
    down = np.linspace(0.0, 1.0, big)[:, None, None]
    shaded = fill * (1 - float(icon["shade"]) * down)
    rim = np.array(_mix(tuple(fill), (255, 255, 255), float(icon["rim"])), float)
    ring = np.clip(face - lit, 0, 1)[..., None]
    body = shaded * (1 - ring) + rim * ring
    arm = _arm(icon, big) if icon["shape"] == "dpad" else None
    if arm is not None:
        # The direction pressed is the arm lit, as the pad's prompt shows it.
        glow = (arm * face)[..., None]
        pressed = np.array(_mix(tuple(fill), (255, 255, 255), 0.75), float)
        body = body * (1 - glow) + pressed * (1 - 0.4 * down) * glow
    dark = np.array(_colour(icon["outline"]), dtype=np.float64)
    inside = face[..., None]
    rgb = body * inside + dark * (1 - inside)
    rgba = np.dstack([rgb, outer * 255]).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(rgba, "RGBA")
    symbol = Image.new("L", (big, big), 0)
    pen = ImageDraw.Draw(symbol)
    said = str(icon.get("symbol") or icon.get("direction") or "")
    said = _AS_GLYPH.get(said, said)
    if said:
        box_side = big * float(icon["symbol_scale"]) * (
            0.62 if said in _COMPASS else 0.42 if icon["shape"] != "pill" else 0.3)
        box = ((big - box_side) / 2, (big - box_side) / 2,
               (big + box_side) / 2, (big + box_side) / 2)
        if arm is not None:
            box = _arm_box(icon["direction"], big)
        if said in GLYPHS:
            _glyph(pen, said, box, 255, max(1, round(big * 0.07)))
        else:
            _text(pen, said, box, ImageFont)
    colour = Image.new("RGBA", (big, big), (*_colour(icon["symbol_colour"]), 255))
    image.paste(colour, (0, 0), symbol)
    small = image.resize((size, size), Image.Resampling.LANCZOS)
    face_small = np.asarray(
        Image.fromarray((face * 255).astype(np.uint8)).resize((size, size)), float
    ) / 255.0
    symbol_small = np.asarray(symbol.resize((size, size)), float) / 255.0
    return small, face_small, symbol_small


def _tinted_layers(icon: dict, size: int):
    """A tinted icon as the two pictures a game draws (§PW644): its face in white, which
    the game modulates by the colour it is given, its shading kept as light and dark;
    and over it the outline and symbol in their own colours, which no tint touches."""
    from PIL import Image

    whole, face, symbol = draw(icon, size)
    white, _, _ = draw({**icon, "fill": "#FFFFFF", "symbol": "", "direction": None},
                       size)
    base = np.asarray(white, dtype=np.float64).copy()
    base[..., 3] = face * 255
    over = np.asarray(whole, dtype=np.float64).copy()
    outline = np.clip(over[..., 3] / 255 - face, 0, 1)
    over[..., 3] = np.maximum(outline, symbol) * 255
    return (Image.fromarray(base.clip(0, 255).astype(np.uint8), "RGBA"),
            Image.fromarray(over.clip(0, 255).astype(np.uint8), "RGBA"))


def _luminance(rgb: np.ndarray) -> np.ndarray:
    from polyweave.loop.measure import srgb_to_linear

    return srgb_to_linear(rgb / 255.0) @ np.array([0.2126, 0.7152, 0.0722])


def _wcag(one: float, other: float) -> float:
    return (max(one, other) + 0.05) / (min(one, other) + 0.05)


def _held(icon: dict, size: int) -> dict:
    """An icon's legibility, and for one a game tints, the worst over every colour it
    declares it will be tinted with, naming that colour (§PW644)."""
    if not icon.get("tints"):
        return legibility(icon, size)
    each = {tint: legibility({**icon, "fill": tint}, size) for tint in icon["tints"]}
    worst = {key: min(found[key] for found in each.values() if key in found)
             for key in {k for found in each.values() for k in found}}
    if "symbol_contrast" in worst:
        worst["worst_tint"] = min(
            (t for t in each if "symbol_contrast" in each[t]),
            key=lambda t: each[t]["symbol_contrast"])
    return worst


def legibility(icon: dict, size: int) -> dict:
    """What an icon measures at a size: its symbol's contrast, share and edge."""
    image, face, symbol = draw(icon, size)
    rgba = np.asarray(image, dtype=np.float64)
    lum = _luminance(rgba[..., :3])
    alpha = rgba[..., 3] / 255.0
    sym = symbol > 0.5
    plain = (face > 0.5) & ~(symbol > 0.05)
    found = {"symbol_share": round(float(sym.sum()) / max(float((face > 0.5).sum()), 1),
                                   3)}
    if sym.any() and plain.any():
        found["symbol_contrast"] = round(
            _wcag(float(np.median(lum[sym])), float(np.median(lum[plain]))), 2
        )
    # Over a bright scene the dark outline carries the icon, and over a dark one its
    # face does: the worse of the two is what the icon is held to.
    rim = (alpha > 0.5) & ~(face > 0.5)
    if rim.any() and (face > 0.5).any():
        edge = float(np.median(lum[rim]))
        body = float(np.median(lum[face > 0.5]))
        found["background_contrast"] = round(min(_wcag(edge, 1.0), _wcag(body, 0.0)),
                                             2)
    return found


def _rendered(icon: dict, side: int, out: Path, here: Path):
    """A model's icon rendered once, transparent, at `side` pixels (§PW610)."""
    from PIL import Image

    from polyweave.layers.geometry import render as R
    from polyweave.layers.geometry.shape import _Quiet

    mesh = here / icon["model"]
    if not mesh.is_file():
        raise PolyweaveError(
            "compose.bad-icons",
            f"the icon's model is not at {icon['model']}",
            "build or ingest the model first, or name the mesh it was written to",
            given=icon["model"],
        )
    R.bake(
        _Quiet(), out=str(out), model=str(mesh), rung=icon["rung"], root=str(here),
        inline=False, azimuth=icon["azimuth"], elevation=icon["elevation"],
        margin=icon["margin"], focal_mm=icon["focal_mm"], transparent=True,
        size=side, **icon["light"],
    )
    with Image.open(out) as picture:
        return picture.convert("RGBA")


def _shrunk(big, size: int, icon: dict):
    """A rendered model brought down to one size, laid on its background."""
    from PIL import Image

    small = big.resize((size, size), Image.Resampling.LANCZOS)
    if icon["background"] == "transparent":
        return small
    laid = Image.new("RGBA", (size, size), (*_colour(icon["background"]), 255))
    laid.alpha_composite(small)
    return laid


def model_legibility(big, icon: dict, size: int) -> dict:
    """What a model's icon measures at a size: what it fills, keeps and contrasts."""
    from PIL import Image

    alpha_big = np.asarray(big, dtype=np.float64)[..., 3] / 255.0 > 0.5
    small = big.resize((size, size), Image.Resampling.LANCZOS)
    rgba = np.asarray(small, dtype=np.float64)
    inside = rgba[..., 3] / 255.0 > 0.5
    found = {"coverage": round(float(inside.mean()), 3)}
    # The outline at this size, grown back to the render's, laid over the render's own:
    # what a palette tile loses of the shape that tells one actor from another.
    grown = np.asarray(
        Image.fromarray((inside * 255).astype(np.uint8)).resize(big.size), float
    ) / 255.0 > 0.5
    union = float((grown | alpha_big).sum())
    found["silhouette_kept"] = round(float((grown & alpha_big).sum()) / union, 3) if (
        union) else 0.0
    if inside.any():
        body = float(np.median(_luminance(rgba[..., :3])[inside]))
        if icon["background"] == "transparent":
            worse = min(_wcag(body, 1.0), _wcag(body, 0.0))
        else:
            behind = float(_luminance(np.array(_colour(icon["background"]), float)))
            worse = _wcag(body, behind)
        found["background_contrast"] = round(worse, 2)
    return found


def _specks(measured: dict) -> None:
    """Each symbol far under the set's median share of its face, said in what it
    measured whether or not a bound asks (§PW642)."""
    shares = {name: found["symbol_share"] for name, found in measured.items()
              if found.get("symbol_share")}
    if len(shares) < 3:
        return
    middle = float(np.median(list(shares.values())))
    for name, share in shares.items():
        if share < middle * SPECK:
            measured[name]["speck"] = (
                f"its symbol fills {share:g} of its face, under a third of the set's "
                f"median {middle:g}: raise symbol_scale or name a glyph")


def _failed(found: dict, accept: dict) -> list[str]:
    said = []
    for key, bound in accept.items():
        measured = found.get(key.removesuffix("_min"))
        if measured is not None and measured < float(bound):
            said.append(f"{key.removesuffix('_min')} {measured:g} under {bound}")
    return said


@operation("icons.build")
def build(
    source: Annotated[str, Param("the *.icons.toml declaration under the project")],
    *,
    out: Annotated[str, Param("the folder it lands in; the declaration's if unset")] = (
        None
    ),
    sitting: Annotated[
        bool, Param("lay the set out for a person's verdict on the review page")
    ] = True,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Build a declared icon set at each size, held to its legibility bounds (§PW331).

    Each icon lands as `<set>/<icon>_<size>.png`, or each size as one atlas with a
    JSON map of names to boxes, every file recorded with the declaration as input.
    `[accept]` holds every icon at the smallest size; `failed` names each under a
    bound. With `sitting`, the set waits on the review page for a person.

    An icon naming a `model` is that mesh rendered, at a declared view, lights,
    margin and background, and recorded with the mesh as an input, so
    provenance.outdated names it once the model changes (§PW610).
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load
    from polyweave.loop import verdict

    config = load(root)
    here = config.root
    where = Path(source) if Path(source).is_absolute() else here / source
    if not where.is_file():
        raise PolyweaveError(
            "compose.bad-icons",
            f"there is no icon declaration at {source}",
            "name a *.icons.toml under the project",
            given=str(source),
        )
    declared = read(where)
    base = config.path("paths.work", out) if out else where.parent
    folder = base / declared["name"]
    folder.mkdir(parents=True, exist_ok=True)
    made: dict[Path, list[str]] = {}
    modelled = {name: icon for name, icon in declared["icons"].items()
                if "model" in icon}
    renders = config.path("paths.work", f"icons/{declared['name']}/renders")
    if modelled:
        renders.mkdir(parents=True, exist_ok=True)
    big = {name: _rendered(icon, 2 * max(declared["sizes"]), renders / f"{name}.png",
                           here)
           for name, icon in modelled.items()}
    for size in declared["sizes"]:
        drawn = {}
        for name, icon in declared["icons"].items():
            if name in big:
                drawn[name] = _shrunk(big[name], size, icon)
            elif icon.get("tints"):
                # The face to tint, and over it what keeps its own colour (§PW644).
                drawn[name], drawn[f"{name}_over"] = _tinted_layers(icon, size)
            else:
                drawn[name] = draw(icon, size)[0]
        if declared["atlas"]:
            for one in _atlas(drawn, size, folder, declared["name"]):
                made[one] = list(modelled)
        else:
            for name, image in drawn.items():
                target = folder / f"{name}_{size}.png"
                image.save(target)
                made[target] = [name] if name in modelled else []
    for one, models in made.items():
        # Each mesh an icon was rendered from is an input, beside the declaration.
        meshes = [provenance.source("mesh", here / modelled[name]["model"], root=here)
                  for name in models]
        provenance.write(provenance.build(
            "picture", one, engine={"name": "icons.build"},
            inputs=[provenance.source("icons", where, root=here), *meshes],
            params={"set": declared["name"]}, root=here,
        ), here)
    smallest = min(declared["sizes"])
    measured, failed = {}, {}
    for name, icon in declared["icons"].items():
        measured[name] = (model_legibility(big[name], icon, smallest) if name in big
                          else _held(icon, smallest))
        broken = _failed(measured[name], declared["accept"])
        if broken:
            failed[name] = broken
    _specks(measured)
    answer = {
        "set": declared["name"],
        "files": [provenance.relative(one, here) for one in made],
        "measured": measured,
        "failed": failed,
        "passed": not failed,
    }
    if sitting:
        shown = [provenance.relative(one, here) for one in made
                 if one.stem.endswith(f"_{max(declared['sizes'])}")]
        # A tinted icon's own files are a white face and what lies over it, which a
        # person cannot judge, so it is shown once in each colour it declares.
        previews = config.path("paths.work", f"icons/{declared['name']}/previews")
        for name, icon in declared["icons"].items():
            if icon.get("tints") and name not in big:
                previews.mkdir(parents=True, exist_ok=True)
                dropped = {f"{name}_{max(declared['sizes'])}",
                           f"{name}_over_{max(declared['sizes'])}"}
                shown = [one for one in shown if Path(one).stem not in dropped]
                for tint in icon["tints"]:
                    target = previews / f"{name}_{tint.lstrip('#').lower()}.png"
                    draw({**icon, "fill": tint}, max(declared["sizes"]))[0].save(target)
                    shown.append(provenance.relative(target, here))
        laid = verdict.sitting(
            {declared["name"]: shown},
            out=str(config.path("paths.work", f"icons/{declared['name']}")),
            root=str(here),
            about=("a set of icons rendered from models: does each read as its own "
                   "model at a glance?" if modelled else
                   "a set of prompt icons: does each read as the pad's own button?")
            + (f" Failed at {smallest}px: {json.dumps(failed)}" if failed else ""),
        )
        answer["sitting"] = list(laid["sheets"].values())[0].get("sheet")
    return answer


def _atlas(drawn: dict, size: int, folder: Path, name: str) -> list[Path]:
    """Every icon of one size on one sheet, with the map of names to boxes."""
    from PIL import Image

    across = max(1, int(np.ceil(np.sqrt(len(drawn)))))
    down = int(np.ceil(len(drawn) / across))
    sheet = Image.new("RGBA", (across * size, down * size), (0, 0, 0, 0))
    boxes = {}
    for index, (icon, image) in enumerate(drawn.items()):
        x, y = (index % across) * size, (index // across) * size
        sheet.paste(image, (x, y))
        boxes[icon] = [x, y, size, size]
    picture = folder / f"{name}_{size}.png"
    sheet.save(picture)
    mapped = folder / f"{name}_{size}.json"
    mapped.write_text(json.dumps(boxes, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    return [picture]
