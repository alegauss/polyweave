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
    symbol_colour = "#FFFFFF"  # up, down, left, right, menu (three bars), view

    [icon.dpad_up]
    shape = "dpad"
    direction = "up"           # its arm is lit and holds the arrow

Each icon is drawn four times over and brought down, so its edges are smooth at 32
pixels. `[accept]` holds every icon at the smallest size to the set's bounds: the
symbol's contrast against its face, the icon's edge against a light and a dark
background, and the symbol's share of the face. A sitting puts the set in front of a
person, since whether it reads as the pad is theirs to say.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Annotated

import numpy as np

from .describe import Param, operation
from .errors import PolyweaveError

#: What an icon may be shaped as, and what a glyph symbol may be.
SHAPES = ("circle", "rounded", "pill", "trigger", "keycap", "dpad", "stick")
GLYPHS = ("cross", "ring", "square", "triangle", "up", "down", "left", "right", "menu",
          "view")

#: How many times over an icon is drawn before it is brought down to its size.
_OVER = 4

#: The set's look where it says nothing of its own.
_STYLE = {"outline": "#101014", "outline_width": 0.07, "rim": 0.35, "shade": 0.3,
          "fill": "#5A5F6A", "symbol_colour": "#FFFFFF"}

#: Every key an icon, the style and `[accept]` may carry.
_ICON_KEYS = {"shape", "symbol", "direction", *_STYLE}
_ACCEPT_KEYS = {"symbol_contrast_min", "background_contrast_min", "symbol_share_min"}


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
        unknown = sorted(set(own) - _ICON_KEYS)
        if unknown:
            raise _refuse(source, f"[icon.{name}] declares {', '.join(unknown)}",
                          f"use some of {', '.join(sorted(_ICON_KEYS))}",
                          given=unknown[0], allowed=sorted(_ICON_KEYS))
        icon = {**style, **own}
        if icon.get("shape") not in SHAPES:
            raise _refuse(source, f"[icon.{name}] is shaped {icon.get('shape')!r}",
                          f"make it one of {', '.join(SHAPES)}",
                          given=str(icon.get("shape")), allowed=SHAPES)
        icons[name] = icon
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
    if said:
        box_side = big * (0.42 if icon["shape"] != "pill" else 0.3)
        box = ((big - box_side) / 2, (big - box_side) / 2,
               (big + box_side) / 2, (big + box_side) / 2)
        if arm is not None:
            box = _arm_box(icon["direction"], big)
        if said in GLYPHS:
            _glyph(pen, said, box, 255, max(1, round(big * 0.07)))
        else:
            text_size = big * (0.5 if len(said) == 1 else 0.36 if len(said) == 2
                               else 0.26)
            font = ImageFont.load_default(size=text_size)
            pen.text((big / 2, big / 2), said, fill=255, font=font, anchor="mm")
    colour = Image.new("RGBA", (big, big), (*_colour(icon["symbol_colour"]), 255))
    image.paste(colour, (0, 0), symbol)
    small = image.resize((size, size), Image.Resampling.LANCZOS)
    face_small = np.asarray(
        Image.fromarray((face * 255).astype(np.uint8)).resize((size, size)), float
    ) / 255.0
    symbol_small = np.asarray(symbol.resize((size, size)), float) / 255.0
    return small, face_small, symbol_small


def _luminance(rgb: np.ndarray) -> np.ndarray:
    from .measure import srgb_to_linear

    return srgb_to_linear(rgb / 255.0) @ np.array([0.2126, 0.7152, 0.0722])


def _wcag(one: float, other: float) -> float:
    return (max(one, other) + 0.05) / (min(one, other) + 0.05)


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
    """
    from . import provenance, verdict
    from .config import load

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
    made = []
    for size in declared["sizes"]:
        drawn = {name: draw(icon, size)[0] for name, icon in declared["icons"].items()}
        if declared["atlas"]:
            made += _atlas(drawn, size, folder, declared["name"])
        else:
            for name, image in drawn.items():
                target = folder / f"{name}_{size}.png"
                image.save(target)
                made.append(target)
    for one in made:
        provenance.write(provenance.build(
            "picture", one, engine={"name": "icons.build"},
            inputs=[provenance.source("icons", where, root=here)],
            params={"set": declared["name"]}, root=here,
        ), here)
    smallest = min(declared["sizes"])
    measured, failed = {}, {}
    for name, icon in declared["icons"].items():
        measured[name] = legibility(icon, smallest)
        broken = _failed(measured[name], declared["accept"])
        if broken:
            failed[name] = broken
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
        laid = verdict.sitting(
            {declared["name"]: shown},
            out=str(config.path("paths.work", f"icons/{declared['name']}")),
            root=str(here),
            about="a set of prompt icons: does each read as the pad's own button?"
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
