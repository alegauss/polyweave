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
import re
import tomllib
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a panel's table may hold, and what each part's own table may hold.
PARTS = {
    "size": None,
    "margin": None,
    "fill": None,
    "cut": None,
    "edge": ("width", "colour"),
    "brackets": ("length", "width", "colour"),
    "scan": ("pitch", "colour"),
    "states": None,
}

#: The states a panel may declare besides `normal`, as Godot's controls name them.
STATES = ("normal", "hover", "focus", "pressed", "disabled")

#: How many times larger a panel is drawn before it is brought down, for clean edges.
SUPER = 4

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


def declared(name: str, table: Any) -> dict[str, dict]:
    """Every state of one panel, each checked whole, refused unless it can be drawn."""
    table = _keys(name, f"[panel.{name}]", table, list(PARTS))
    for part, keys in PARTS.items():
        if keys and part in table:
            _keys(name, part, table[part], list(keys))
    states = _keys(name, "states", table.get("states") or {}, list(STATES))
    base = {k: v for k, v in table.items() if k != "states"}
    out = {"normal": _checked(name, "normal", base)}
    for state, over in states.items():
        if state == "normal":
            continue
        _keys(name, f"states.{state}", over, [p for p in PARTS if p != "states"])
        out[state] = _checked(name, state, _merged(base, over))
    return out


def _checked(name: str, state: str, panel: dict) -> dict:
    size = panel.get("size")
    if not (isinstance(size, list) and len(size) == 2):
        raise _bad(name, "has no size", "write size = [width, height] in pixels")
    width, height = (_whole(name, "size", v, 8) for v in size)
    margin = panel.get("margin", 0)
    margins = [margin] * 4 if not isinstance(margin, list) else margin
    if len(margins) != 4:
        raise _bad(name, f"margin is {margin!r}",
                   "write margin as one number, or [left, top, right, bottom]")
    left, top, right, bottom = (_whole(name, "margin", v, 1) for v in margins)
    if left + right >= width or top + bottom >= height:
        raise _bad(name, f"margins {margins} leave no middle in {width}x{height}",
                   "make the panel larger, or the margins smaller")
    cut = _whole(name, "cut", panel.get("cut", 0))
    edge = panel.get("edge") or {}
    brackets = panel.get("brackets") or {}
    scan = panel.get("scan") or {}
    out = {
        "size": (width, height),
        "margin": (left, top, right, bottom),
        "fill": _colour(name, "fill", panel.get("fill", "#00000000")),
        "cut": cut,
        "edge": {"width": _whole(name, "edge.width", edge.get("width", 0)),
                 "colour": _colour(name, "edge.colour",
                                   edge.get("colour", "#00000000"))},
        "brackets": None,
        "scan": None,
    }
    reach = cut + out["edge"]["width"]
    if brackets:
        out["brackets"] = {
            "length": _whole(name, "brackets.length", brackets.get("length", 0), 1),
            "width": _whole(name, "brackets.width", brackets.get("width", 1), 1),
            "colour": _colour(name, "brackets.colour", brackets.get("colour")),
        }
        reach = max(reach, cut + out["brackets"]["length"], out["brackets"]["width"])
    if scan:
        out["scan"] = {
            "pitch": _whole(name, "scan.pitch", scan.get("pitch", 0), 2),
            "colour": _colour(name, "scan.colour", scan.get("colour")),
        }
    # A corner's parts are only drawn true where the nine-patch never stretches them.
    if reach > min(left, top, right, bottom):
        raise _bad(
            name,
            f"in state {state}, its corner reaches {reach} px and the smallest margin "
            f"is {min(left, top, right, bottom)} px, so stretching would bend it",
            "make the margin at least as wide as the cut plus the bracket, or shorten "
            "the bracket",
        )
    return out


def _drawn(panel: dict):
    """One state drawn large and brought down, so its diagonals are smooth."""
    from PIL import Image, ImageDraw

    width, height = panel["size"]
    big = (width * SUPER, height * SUPER)
    cut = panel["cut"] * SUPER

    def outline(inset: float) -> list[tuple[float, float]]:
        x0, y0, x1, y1 = inset, inset, big[0] - inset, big[1] - inset
        c = max(0.0, cut - inset * 0.414)
        return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
                (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]

    edge = panel["edge"]["width"] * SUPER
    shape = Image.new("L", big, 0)
    ImageDraw.Draw(shape).polygon(outline(0), fill=255)
    picture = Image.new("RGBA", big, (0, 0, 0, 0))
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
    if edge:
        rim = Image.new("RGBA", big, (0, 0, 0, 0))
        points = outline(edge / 2)
        ImageDraw.Draw(rim).line([*points, points[0]], fill=panel["edge"]["colour"],
                                 width=edge, joint="curve")
        picture = Image.alpha_composite(picture, rim)
    if panel["brackets"]:
        marks = Image.new("RGBA", big, (0, 0, 0, 0))
        pen = ImageDraw.Draw(marks)
        thick = panel["brackets"]["width"] * SUPER
        reach = cut + panel["brackets"]["length"] * SUPER
        colour = panel["brackets"]["colour"]
        for x, y, dx, dy in ((0, 0, 1, 1), (big[0], 0, -1, 1),
                             (0, big[1], 1, -1), (big[0], big[1], -1, -1)):
            # Along the top or bottom edge and down or up the side, past the cut.
            pen.rectangle(_box(x + dx * cut, y, x + dx * reach, y + dy * thick),
                          fill=colour)
            pen.rectangle(_box(x, y + dy * cut, x + dx * thick, y + dy * reach),
                          fill=colour)
        picture = Image.alpha_composite(picture, marks)
    return picture.resize(panel["size"], Image.Resampling.BOX)


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


@operation("panel.build")
def build(
    source: Annotated[str, Param("the *.panel.toml, relative to the project")],
    panel: Annotated[str, Param("one panel; left out, every one")] = None,
    out: Annotated[
        str, Param("the folder the textures are written to; beside the source if unset")
    ] = None,
    root: Annotated[str, Param("the project the panels belong to")] = ".",
) -> dict:
    """Build declared menu panels into nine-patch PNGs and Godot styleboxes, by state.

    Each state lands as <name>.<state>.png with its record, and <name>.<state>.tres, a
    StyleBoxTexture with the declared margins that a Control's theme takes as it is.
    """
    from PIL import Image  # noqa: F401 - the drawing needs it; refused early if absent

    from . import provenance

    config = load(root)
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError("compose.bad-panel",
                             f"there is no panel file at {source}",
                             "name a *.panel.toml relative to the project root")
    try:
        tables = tomllib.loads(where.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("compose.bad-panel", f"{source} is not TOML",
                             "fix the syntax the detail names",
                             detail=str(exc)) from exc
    panels = tables.get("panel")
    if set(tables) - {"panel"} or not isinstance(panels, dict) or not panels:
        raise PolyweaveError("compose.bad-panel",
                             f"{source} holds no [panel.<name>]",
                             "write each panel as [panel.<name>] with a size and "
                             "margin")
    if panel is not None and panel not in panels:
        raise PolyweaveError(
            "compose.bad-panel", f"{source} has no panel {panel!r}",
            f"name one of {', '.join(sorted(panels))}",
            given=panel, allowed=sorted(panels),
        )
    chosen = {panel: panels[panel]} if panel else panels
    states = {name: declared(name, table) for name, table in chosen.items()}
    folder = config.path("paths.work", out) if out else where.parent
    folder.mkdir(parents=True, exist_ok=True)
    made: dict[str, dict] = {}
    for name, drawn in states.items():
        made[name] = {}
        for state, own in drawn.items():
            target = folder / f"{name}.{state}.png"
            _drawn(own).save(target)
            left, top, right, bottom = own["margin"]
            provenance.write(provenance.build(
                "picture", target, engine={"name": "panel.build"},
                inputs=[provenance.source("declaration", where, config.root)],
                params={"panel": name, "state": state, "margin": list(own["margin"])},
                root=config.root,
            ), config.root)
            style = target.with_suffix(".tres")
            style.write_text(_STYLEBOX % {
                "texture": "res://" + provenance.relative(target, config.root),
                "left": left, "top": top, "right": right, "bottom": bottom,
                # Scan lines tile, so their pitch holds whatever height the panel is.
                "vertical": 2 if own["scan"] else 0,
            }, encoding="utf-8", newline="\n")
            made[name][state] = {
                "file": provenance.relative(target, config.root),
                "stylebox": provenance.relative(style, config.root),
                "size": list(own["size"]),
                "margin": list(own["margin"]),
            }
    return {"source": provenance.relative(where, config.root), "panels": made}
