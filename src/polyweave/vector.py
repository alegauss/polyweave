"""A vector picture drawn to the PNG a game loads, whole and in layers (§PW315).

Starship's title shows the logo the owner accepted for its store page. That logo is an
SVG whose groups hold a blurred halo, a dashed ring and the letters, and the store's PNG
came from a rasterisation no record covered, so the game's copy and the store's could
drift. And a ring that turns or a glow that pulses needs its own layer to move.

`picture.vector` draws the SVG at a stated width through the engine's own rasteriser
(Godot's ThorVG, as `store.capsules` draws a vector logo), blur filters and masks
included, and writes a record naming the SVG. Given `layers`, it also draws each named
group alone on the same canvas, at the same origin, so the layers stack back into the
whole. An SVG's groups often carry no ids, so a layer is chosen by `#id` or by its place
among the drawing's top-level elements, counted from 1.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Annotated, Any

from .describe import Param, operation
from .errors import PolyweaveError

SVG = "http://www.w3.org/2000/svg"

#: What sits at the top of an SVG and draws nothing: never a layer, always kept.
_UNDRAWN = {"defs", "metadata", "title", "desc", "style", "script"}


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _read(svg: Path) -> ET.ElementTree:
    for prefix, uri in (("", SVG), ("xlink", "http://www.w3.org/1999/xlink")):
        ET.register_namespace(prefix, uri)
    try:
        return ET.parse(svg)
    except ET.ParseError as exc:
        raise PolyweaveError(
            "compose.no-vector",
            f"{svg.name} is not an SVG this can read",
            "check it opens in a browser; the detail says where it stops parsing",
            detail=str(exc),
        ) from exc


def _drawn(root: ET.Element) -> list[ET.Element]:
    """The top-level elements that draw, in order: what a layer is chosen among."""
    return [child for child in root if _tag(child) not in _UNDRAWN]


def _native_width(root: ET.Element, svg: Path) -> float:
    """The width the drawing declares, in its own units, which scale 1 draws at."""
    stated = re.fullmatch(r"\s*([0-9.]+)\s*(px)?\s*", root.get("width") or "")
    if stated:
        return float(stated.group(1))
    box = (root.get("viewBox") or "").replace(",", " ").split()
    if len(box) == 4:
        return float(box[2])
    raise PolyweaveError(
        "compose.no-vector",
        f"{svg.name} states neither a width in pixels nor a viewBox, so no width can "
        "be drawn to",
        "give the svg element a viewBox",
    )


def _choices(drawn: list[ET.Element]) -> list[str]:
    return [str(n) for n in range(1, len(drawn) + 1)] + [
        f"#{e.get('id')}" for e in drawn if e.get("id")
    ]


def _chosen(selector: Any, drawn: list[ET.Element], svg: Path, name: str) -> int:
    """Where the element a layer's selector names sits; refused where none does."""
    said = str(selector).strip()
    if said.startswith("#"):
        for index, element in enumerate(drawn):
            if element.get("id") == said[1:]:
                return index
    elif said.isdigit() and 1 <= int(said) <= len(drawn):
        return int(said) - 1
    raise PolyweaveError(
        "compose.no-layer",
        f"layer {name} names {said!r}, and {svg.name} has no top-level element by that",
        f"name one by #id, or by its place counted from 1 among the {len(drawn)} it "
        "draws",
        given=said,
        allowed=_choices(drawn),
    )


@operation("picture.vector")
def vector(
    source: Annotated[str, Param("the SVG, as a path under the project")],
    out: Annotated[str, Param("where the whole picture is written, as a PNG")],
    width: Annotated[int, Param("the width to draw at", lo=1, hi=16384, unit="px")],
    *,
    layers: Annotated[
        dict,
        Param(
            "each layer's name to the element it draws alone: #id, or its place among "
            "the top-level elements from 1"
        ),
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Draw a vector to a PNG at a width, filters and masks included, with its record.

    Each layer is written beside `out` as `<out>.<layer>.png`, on the whole picture's
    canvas and origin, so the layers stack back into it.
    """
    import tempfile

    from . import provenance, store
    from .config import load

    here = load(root).root
    svg = here / source if not Path(source).is_absolute() else Path(source)
    if not svg.is_file() or svg.suffix.lower() != ".svg":
        raise PolyweaveError(
            "compose.no-vector",
            f"there is no SVG at {source}",
            "name an .svg file under the project",
        )
    tree = _read(svg)
    drawn = _drawn(tree.getroot())
    scale = width / _native_width(tree.getroot(), svg)
    picked = {
        name: _chosen(selector, drawn, svg, name)
        for name, selector in (layers or {}).items()
    }
    target = here / out if not Path(out).is_absolute() else Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)

    pictures = {"": store._drawn_svg(svg, {"whole": scale}, here)["whole"]}
    with tempfile.TemporaryDirectory(prefix="polyweave-layer-") as held:
        for name, index in picked.items():
            # Every other drawing element hidden, defs kept, so the canvas, the origin
            # and anything a filter or mask points at are the whole picture's.
            for place, element in enumerate(drawn):
                if place == index:
                    element.attrib.pop("display", None)
                else:
                    element.set("display", "none")
            alone = Path(held) / f"{name}.svg"
            tree.write(alone, encoding="utf-8", xml_declaration=True)
            pictures[name] = store._drawn_svg(alone, {"alone": scale}, here)["alone"]

    written: dict[str, dict] = {}
    for name, picture in pictures.items():
        where = target if not name else target.with_name(f"{target.stem}.{name}.png")
        picture.save(where)
        params = {"made_by": "picture.vector", "width": int(width)}
        if name:
            params.update(layer=name, selector=str(layers[name]))
        provenance.write(
            provenance.build(
                "picture",
                where,
                engine={"name": "picture.vector", "rasteriser": "godot thorvg"},
                inputs=[provenance.source("vector", svg, here)],
                params=params,
                root=here,
            ),
            root=here,
        )
        written[name or "whole"] = {
            "file": provenance.relative(where, here),
            "size": list(picture.size),
        }
    return {
        "source": provenance.relative(svg, here),
        "whole": written.pop("whole"),
        "layers": written,
        "choices": _choices(drawn),
    }
