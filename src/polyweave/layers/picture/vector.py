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

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

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


#: What a reference by attribute has to land on, or the drawing silently loses it.
_POINTS_AT = {"filter": "filter", "mask": "mask", "clip-path": "clipPath"}

_URL = re.compile(r"url\(\s*#([^)\s]+)")


def _described(element: ET.Element) -> str:
    return f"<{_tag(element)} id=\"{element.get('id')}\">"


def _ids_checked(root: ET.Element, svg: Path, named: set[str]) -> list[dict]:
    """Every id a selector or a reference leans on, held to one element of the right
    kind (§PW478); the duplicate ids nothing leans on, returned to be said."""
    by_id: dict[str, list[ET.Element]] = {}
    for element in root.iter():
        if element.get("id"):
            by_id.setdefault(element.get("id"), []).append(element)
    leaned = set(named)
    for element in root.iter():
        for attribute, value in element.attrib.items():
            local = attribute.rsplit("}", 1)[-1]
            found = _URL.findall(value)
            if local == "href" and value.startswith("#"):
                found.append(value[1:])
            leaned.update(found)
            wanted = _POINTS_AT.get(local)
            for target in found if wanted else ():
                landed = by_id.get(target, [])
                if len(landed) == 1 and _tag(landed[0]) != wanted:
                    raise PolyweaveError(
                        "compose.ambiguous-id",
                        f"{svg.name}: {_described(element)} takes its {local} from "
                        f"#{target}, which is {_described(landed[0])}, not a {wanted}, "
                        f"so the {local} is drawn as nothing",
                        f"give the {wanted} its own id and point {local} at it",
                        given=target,
                    )
    twice = {name: found for name, found in by_id.items() if len(found) > 1}
    for name in sorted(set(twice) & leaned):
        raise PolyweaveError(
            "compose.ambiguous-id",
            f"{svg.name} gives id {name!r} to {len(twice[name])} elements "
            f"({', '.join(_described(e) for e in twice[name])}), so #{name} means "
            "whichever the rasteriser meets first",
            "give each element its own id",
            given=name,
        )
    return [{"id": name, "elements": [_described(e) for e in found]}
            for name, found in sorted(twice.items())]


def _swept(sweep: Any, root: ET.Element, svg: Path) -> dict | None:
    """A sweep checked whole, its elements found by id anywhere in the drawing."""
    if not sweep:
        return None

    def bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
        return PolyweaveError("compose.bad-sweep", f"sweep: {what}", remedy, **extra)

    if not isinstance(sweep, dict):
        raise bad(f"{sweep!r} is not a table",
                  "write sweep = {element, attribute, from, to, frames}")
    allowed = ("element", "attribute", "from", "to", "frames")
    stray = sorted(set(sweep) - set(allowed))
    missing = [key for key in allowed if key not in sweep]
    if stray or missing:
        raise bad(f"has {', '.join(stray) or 'no ' + ', '.join(missing)}",
                  f"write exactly {', '.join(allowed)}", allowed=list(allowed))
    said = sweep["element"]
    said = said if isinstance(said, list) else [said]
    ids = {e.get("id"): e for e in root.iter() if e.get("id")}
    elements = []
    for one in said:
        name = str(one).lstrip("#")
        if name not in ids:
            raise bad(f"{svg.name} has no element #{name}",
                      "name an element by its id, anywhere in the drawing",
                      given=str(one), allowed=sorted(f"#{i}" for i in ids))
        elements.append(ids[name])
    numbers = [sweep["from"], sweep["to"]]
    if not all(isinstance(n, int | float) and not isinstance(n, bool) for n in numbers):
        raise bad(f"from {numbers[0]!r} to {numbers[1]!r}", "write both as numbers")
    frames = sweep["frames"]
    counted = isinstance(frames, int) and not isinstance(frames, bool)
    if not counted or not 2 <= frames <= 256:
        raise bad(f"frames is {frames!r}", "write frames as a whole number, 2 to 256")
    if not str(sweep["attribute"]).strip():
        raise bad("names no attribute", "name the attribute that moves")
    return {"element": [f"#{e.get('id')}" for e in elements],
            "attribute": str(sweep["attribute"]), "from": float(numbers[0]),
            "to": float(numbers[1]), "frames": frames, "_elements": elements}


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
    sweep: Annotated[
        dict,
        Param("one attribute moved over frames: element (#id, or a list), attribute, "
              "from, to (left out, so the loop closes), frames")
    ] = None,
    strip: Annotated[
        bool, Param("with a sweep, also pack each layer's frames into one strip")
    ] = False,
    whole: Annotated[
        bool, Param("write the whole picture too; false writes the layers alone")
    ] = True,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Draw a vector to a PNG at a width, filters and masks included, with its record.

    Each layer is written beside `out` as `<out>.<layer>.png`, on the whole picture's
    canvas and origin, so the layers stack back into it. Live text is outlined first in
    the font its family names, from `[words] fonts` or the system's, and that font is
    recorded; a run that cannot be is refused, never drawn blank (§PW453). With a
    `sweep`, each is drawn once a frame as `<out>[.<layer>].<frame>.png`, every record
    naming the one source, the sweep and its frame (§PW476).
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

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
    if not whole and not picked:
        raise PolyweaveError("compose.no-layer",
                             "whole is false and no layer is named, so nothing would "
                             "be drawn", "name a layer, or draw whole")
    moved = _swept(sweep, tree.getroot(), svg)
    selected = {str(s).lstrip("#") for s in (layers or {}).values()
                if str(s).startswith("#")}
    if moved:
        selected.update(e.lstrip("#") for e in moved["element"])
    doubled = _ids_checked(tree.getroot(), svg, selected)
    target = here / out if not Path(out).is_absolute() else Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    fonts: list[Path] = []
    names = ([""] if whole else []) + [*picked]
    pictures, values = _frames(tree, svg, names, picked, moved,
                               lambda alone: _drawn_svg(
                                   alone, {"alone": scale}, here, fonts)["alone"])
    empty = _emptiness(pictures, layers or {})
    # The fonts live text was outlined in are inputs like the SVG (§PW453).
    inputs = [provenance.source("vector", svg, here),
              *(provenance.source("font", one, here) for one in fonts)]
    said = {k: v for k, v in moved.items() if not k.startswith("_")} if moved else None

    def record(where: Path, params: dict) -> None:
        provenance.write(provenance.build(
            "picture", where,
            engine={"name": "picture.vector", "rasteriser": "godot thorvg"},
            inputs=inputs, params=params, root=here,
        ), root=here)

    written: dict[str, dict] = {}
    for name, drawn_frames in pictures.items():
        stem = target.stem if not name else f"{target.stem}.{name}"
        base = {"made_by": "picture.vector", "width": int(width)}
        if name:
            base.update(layer=name, selector=str(layers[name]))
        files = []
        for frame, picture in enumerate(drawn_frames):
            named = f"{stem}.{frame:02d}.png" if moved else f"{stem}.png"
            where = target.with_name(named)
            picture.save(where)
            record(where, {**base, **({"sweep": said, "frame": frame,
                                       "value": values[frame]} if moved else {})})
            files.append(provenance.relative(where, here))
        one = {"size": list(drawn_frames[0].size)}
        if moved:
            one["frames"] = files
            if strip:
                band = _strip(drawn_frames)
                where = target.with_name(f"{stem}.strip.png")
                band.save(where)
                record(where, {**base, "sweep": said, "frames": files})
                one["strip"] = provenance.relative(where, here)
        else:
            one["file"] = files[0]
        written[name or "whole"] = one
    answer = {
        "source": provenance.relative(svg, here),
        **({"whole": written.pop("whole")} if whole else {}),
        "layers": written,
        "choices": _choices(drawn),
    }
    if moved:
        answer["sweep"] = {**said, "values": values}
    if empty:
        answer["empty_frames"] = empty
    if doubled:
        # Said, not refused: nothing leans on these, so nothing is drawn wrong yet.
        answer["duplicate_ids"] = doubled
    return answer


def _emptiness(pictures: dict[str, list], layers: dict) -> dict[str, list[int]]:
    """A layer that drew no pixel in any frame is refused, naming what chose it
    (§PW478); a sweep's frames that drew nothing, where others did, are returned."""
    empty: dict[str, list[int]] = {}
    for name, frames in pictures.items():
        blank = [k for k, p in enumerate(frames)
                 if p.convert("RGBA").getextrema()[3][1] == 0]
        if len(blank) == len(frames):
            chose = f"layer {name} ({layers[name]})" if name else "the whole picture"
            raise PolyweaveError(
                "compose.empty-layer",
                f"{chose} drew no pixel: every one of its pixels is transparent",
                "check the element it names is drawn and visible on its own, and that "
                "what it points at (a filter, a mask, a clip) is the element meant",
                given=str(layers.get(name, "whole")),
            )
        if blank:
            empty[name or "whole"] = blank
    return empty


def _frames(tree: ET.ElementTree, svg: Path, names: list[str], picked: dict,
            moved: dict | None, draw) -> tuple[dict[str, list], list[float]]:
    """Each name's picture at each frame of the sweep, or once with none; "" is the
    whole, drawn as the source shows it."""
    import tempfile

    drawn = _drawn(tree.getroot())
    shown = [element.get("display") for element in drawn]
    frames = moved["frames"] if moved else 1
    pictures: dict[str, list] = {name: [] for name in names}
    values: list[float] = []
    with tempfile.TemporaryDirectory(prefix="polyweave-layer-") as held:
        for frame in range(frames):
            if moved:
                # The end is left out, so the last frame steps back into the first.
                value = moved["from"] + (moved["to"] - moved["from"]) * frame / frames
                values.append(round(value, 6))
                for element in moved["_elements"]:
                    element.set(moved["attribute"], f"{value:.6g}")
            for name in names:
                # Every other drawing element hidden, defs kept, so the canvas, the
                # origin and anything a filter or mask points at are the whole's.
                for place, element in enumerate(drawn):
                    keep = shown[place]
                    if name:
                        keep = None if place == picked[name] else "none"
                    element.attrib.pop("display", None)
                    if keep is not None:
                        element.set("display", keep)
                alone = svg
                if name or moved:
                    alone = Path(held) / f"{name or 'whole'}.{frame}.svg"
                    tree.write(alone, encoding="utf-8", xml_declaration=True)
                pictures[name].append(draw(alone))
    return pictures, values


def _strip(frames: list) -> Any:
    """Frames side by side, left to right in order, on one transparent canvas."""
    from PIL import Image

    w, h = frames[0].size
    band = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for index, picture in enumerate(frames):
        band.paste(picture.convert("RGBA"), (index * w, 0))
    return band


_SVG = """extends SceneTree

func _initialize() -> void:
\tvar text := FileAccess.get_file_as_string("%(svg)s")
\tif OS.get_cmdline_user_args().is_empty():
\t\tprint("svg: nothing asked")
\t\tquit(1)
\t\treturn
\tfor pair in OS.get_cmdline_user_args():
\t\tvar image := Image.new()
\t\tvar failed := image.load_svg_from_string(text, float(pair.get_slice("=", 0)))
\t\tif failed != OK:
\t\t\tprint("svg: failed %%d" %% failed)
\t\t\tquit(1)
\t\t\treturn
\t\timage.save_png(pair.get_slice("=", 1))
\tprint("svg: drawn")
\tquit()
"""


def _declared_fonts(root: Path) -> list[Path]:
    """The font files `[words] fonts` names, which a text run is outlined in first."""
    from polyweave.kernel.config import load

    try:
        config = load(root)
    except PolyweaveError:
        return []
    return [config.root / one["path"] for one in config.get("words.fonts") or ()
            if isinstance(one, dict) and one.get("path")]


def _drawn_svg(svg: Path, scales: dict[str, float], root: Path,
               used: list | None = None) -> dict:
    """A vector logo drawn at each scale asked, by the engine's own SVG rasteriser.

    Godot draws SVG through ThorVG, which a headless run does in milliseconds, so a
    vector logo is drawn at the size each capsule shows it and its strokes measured
    there, where a raster scaled down from one export measures the export (§PW275).
    ThorVG draws no text, so live text is outlined first (§PW453), and the font files
    that drew it are added to `used` for the picture's record.
    """
    import tempfile

    from PIL import Image

    from polyweave.layers.engine import engine
    from polyweave.layers.words import svgtext

    try:
        binary = engine.find(root)
    except PolyweaveError as missing:
        raise PolyweaveError(
            "store.no-rasteriser",
            f"{svg.name} is a vector, and drawing one needs the engine, which is not "
            "found",
            "set $GODOT or [paths] godot, or give the logo as a PNG with alpha",
            detail=missing.message,
        ) from missing
    with tempfile.TemporaryDirectory(prefix="polyweave-svg-") as held:
        work = Path(held)
        tree = _read(svg)
        if svgtext.texts(tree.getroot()):
            fonts = svgtext.outlined(tree, _declared_fonts(root))
            svg = work / "outlined.svg"
            tree.write(svg, encoding="utf-8", xml_declaration=True)
            if used is not None:
                used += [one for one in fonts if one not in used]
        (work / "polyweave.toml").write_text("", encoding="utf-8")
        (work / "project.godot").write_text(
            'config_version=5\n\n[application]\nconfig/name="svg"\n', encoding="utf-8"
        )
        (work / "draw.gd").write_text(
            _SVG % {"svg": svg.resolve().as_posix()}, encoding="utf-8"
        )
        outs = {name: work / f"{index}.png" for index, name in enumerate(scales)}
        ran = engine.run(
            work / "draw.gd", expect=r"^svg: drawn", root=work, headless=True,
            binary=binary,
            args=("--", *(f"{scales[n]:.6f}={outs[n].as_posix()}" for n in scales)),
        )
        if not ran["ok"]:
            raise PolyweaveError(
                "store.no-rasteriser",
                f"the engine could not draw {svg.name}: {ran.get('why')}",
                "check the SVG opens in a browser, or give the logo as a PNG",
                detail=ran.get("log"),
            )
        drawn = {}
        for name, out in outs.items():
            with Image.open(out) as picture:
                drawn[name] = picture.convert("RGBA")
        return drawn
