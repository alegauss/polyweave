"""Live text in an SVG, outlined before the engine draws it (§PW453).

Godot draws SVG through ThorVG, which as Godot builds it draws no `<text>`: a
banner's letters vanished from the PNG and the call answered as if nothing was lost. So
each text run is replaced by its glyphs' outlines before the drawing, in the font its
`font-family`, `font-weight` and `font-style` resolve to: one of `[words] fonts`, else
the system's. The fonts used are returned so the picture's record names them. A run that
cannot be outlined (text along a path, a font nowhere to be found, a character the font
lacks) is refused by name, never drawn blank.

Kerning and shaping are not applied: glyphs are set by their advances, which is what a
Latin title needs and what a script that joins its letters does not get.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

from .errors import PolyweaveError

SVG = "http://www.w3.org/2000/svg"

#: The properties a text run inherits from the elements around it.
_FONT = ("font-family", "font-size", "font-weight", "font-style", "text-anchor",
         "letter-spacing")

#: How a span is painted apart from the run it sits in, kept on its outline.
_PAINT = ("fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "opacity")

#: What a generic family stands for, tried in order.
_GENERIC = {
    "sans-serif": ("Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"),
    "system-ui": ("Segoe UI", "Arial", "Helvetica", "DejaVu Sans"),
    "serif": ("Times New Roman", "Times", "DejaVu Serif", "Liberation Serif"),
    "monospace": ("Consolas", "Courier New", "DejaVu Sans Mono", "Liberation Mono"),
}

_WEIGHTS = {"normal": 400, "bold": 700, "lighter": 300, "bolder": 700}

_FONT_FILES = (".ttf", ".otf", ".ttc")


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def texts(root: ET.Element) -> list[ET.Element]:
    """Every `<text>` in the drawing, wherever it sits."""
    return [one for one in root.iter() if _tag(one) == "text"]


def _style(element: ET.Element) -> dict[str, str]:
    """An element's own presentation properties, its style attribute winning."""
    said = {k: v for k, v in element.attrib.items() if not k.startswith("{")}
    for pair in (element.get("style") or "").split(";"):
        name, _, value = pair.partition(":")
        if value.strip():
            said[name.strip()] = value.strip()
    return said


def _length(value: str | None, size: float = 16.0) -> float:
    """A length as user units: px or bare, pt, em."""
    if not value:
        return 0.0
    number = re.match(r"\s*(-?[0-9.]+)\s*(px|pt|em)?", value)
    if not number:
        return 0.0
    amount = float(number.group(1))
    unit = number.group(2) or ""
    return {"pt": amount * 4 / 3, "em": amount * size}.get(unit, amount)


def _first(value: str | None) -> float | None:
    found = re.findall(r"-?[0-9.]+(?:e-?[0-9]+)?", value or "")
    return float(found[0]) if found else None


@cache
def _faces(path: str, stamp: float) -> tuple:
    """One font file's family names, weight and italic, read off its tables."""
    from fontTools.ttLib import TTFont

    try:
        font = TTFont(path, lazy=True, fontNumber=0)
        names = {str(r).strip().lower() for r in font["name"].names
                 if r.nameID in (1, 16, 4) and r.toUnicode()}
        os2 = font.get("OS/2")
        weight = os2.usWeightClass if os2 else 400
        italic = bool(os2.fsSelection & 1) if os2 else False
    except Exception:  # a file that is not a font is not a candidate
        return ()
    return (frozenset(names), weight, italic)


def _system_dirs() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        return [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
                Path(os.environ.get("LOCALAPPDATA", home)) / "Microsoft/Windows/Fonts"]
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"),
                home / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".fonts",
            home / ".local/share/fonts"]


def _candidates(declared: list[Path], system: bool) -> list[Path]:
    found = [one for one in declared if one.is_file()]
    if system:
        for folder in _system_dirs():
            if folder.is_dir():
                found += sorted(p for p in folder.rglob("*")
                                if p.suffix.lower() in _FONT_FILES)
    return found


def _pick(families: list[str], weight: int, italic: bool, declared: list[Path]) -> Path:
    """The font a run's family list resolves to: declared fonts first, then the
    system's, the nearest weight and the asked slant among a family's faces."""
    wanted = []
    for family in families:
        wanted += [family, *_GENERIC.get(family.lower(), ())]
    for system in (False, True):
        pool = [(p, _faces(str(p), p.stat().st_mtime))
                for p in _candidates(declared, system)]
        for family in wanted:
            faces = [(p, f) for p, f in pool if f and family.lower() in f[0]]
            if faces:
                return min(faces, key=lambda pf: (pf[1][2] != italic,
                                                  abs(pf[1][1] - weight)))[0]
    raise PolyweaveError(
        "compose.text-unoutlined",
        f"no font for {', '.join(families) or 'a run with no font-family'} is declared "
        "or installed, so its letters cannot be drawn",
        "add the font file to [words] fonts in polyweave.toml, or install it",
        given=", ".join(families),
    )


@cache
def _font(path: str):
    from fontTools.ttLib import TTFont

    font = TTFont(path, fontNumber=0)
    return font, font.getBestCmap(), font.getGlyphSet(), font["head"].unitsPerEm


def _runs(text: ET.Element, inherited: dict) -> list[tuple[float, float, str, dict]]:
    """A `<text>` as runs of characters, each with where it starts and its own style."""
    if any(_tag(one) == "textPath" for one in text.iter()):
        raise PolyweaveError(
            "compose.text-unoutlined",
            f"a text run ({''.join(text.itertext()).strip()[:40]!r}) follows a path, "
            "which this does not outline",
            "convert that text to outlines in the editor that made the SVG",
            given="textPath",
        )
    runs: list[list] = []
    x = _first(text.get("x")) or 0.0
    y = _first(text.get("y")) or 0.0
    x += _first(text.get("dx")) or 0.0
    y += _first(text.get("dy")) or 0.0
    style = {**inherited, **_style(text)}
    if text.text:
        runs.append([x, y, text.text, style])
    for span in text:
        if _tag(span) != "tspan":
            continue
        own = {**style, **_style(span),
               "__paint": {k: v for k, v in _style(span).items() if k in _PAINT}}
        if span.get("x") is not None or span.get("y") is not None:
            x = _first(span.get("x")) if span.get("x") is not None else x
            y = _first(span.get("y")) if span.get("y") is not None else y
            runs.append([x, y, "", own, True])
        x_shift = _first(span.get("dx")) or 0.0
        y_shift = _first(span.get("dy")) or 0.0
        spoken = "".join(span.itertext())
        runs.append([None, None, spoken, own, False, x_shift, y_shift])
        if span.tail:
            runs.append([None, None, span.tail, style, False, 0.0, 0.0])
    return _placed(runs)


def _placed(runs: list[list]) -> list[tuple[float, float, str, dict]]:
    """Runs whose start is carried on from the one before, each made absolute."""
    out: list[tuple[float, float, str, dict]] = []
    x = y = 0.0
    for one in runs:
        if one[0] is not None:
            x, y = one[0], one[1]
            if one[2]:
                out.append((x, y, one[2], one[3]))
                x += _advance(one[2], one[3])
            continue
        x += one[5]
        y += one[6]
        if one[2]:
            out.append((x, y, one[2], one[3]))
            x += _advance(one[2], one[3])
    return out


def _resolved(style: dict) -> tuple[Path, float, float]:
    families = [f.strip().strip("'\"") for f in style.get("font-family", "").split(",")
                if f.strip()]
    weight = style.get("font-weight", "normal")
    weight = _WEIGHTS.get(weight, int(weight) if str(weight).isdigit() else 400)
    italic = style.get("font-style", "") in ("italic", "oblique")
    size = _length(style.get("font-size")) or 16.0
    spacing = _length(style.get("letter-spacing"), size)
    return _pick(families, weight, italic, style["__declared"]), size, spacing


def _advance(characters: str, style: dict) -> float:
    path, size, spacing = _resolved(style)
    font, cmap, _, upem = _font(str(path))
    metrics = font["hmtx"]
    return sum(metrics[cmap.get(ord(c), ".notdef")][0] * size / upem + spacing
               for c in characters)


def _outline(x: float, y: float, characters: str, style: dict) -> tuple[str, Path]:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    path, size, spacing = _resolved(style)
    font, cmap, glyphs, upem = _font(str(path))
    scale = size / upem
    anchor = style.get("text-anchor", "start")
    if anchor in ("middle", "end"):
        x -= _advance(characters, style) / (2 if anchor == "middle" else 1)
    pen = SVGPathPen(glyphs)
    for character in characters:
        name = cmap.get(ord(character))
        if name is None:
            if character.isspace():
                name = cmap.get(32, ".notdef")
            else:
                raise PolyweaveError(
                    "compose.text-unoutlined",
                    f"{path.name} has no glyph for {character!r}, so the run "
                    f"{characters.strip()[:40]!r} would lose it",
                    "name a font that has it in the SVG's font-family, and add it to "
                    "[words] fonts",
                    given=character,
                )
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, y)))
        x += font["hmtx"][name][0] * scale + spacing
    return pen.getCommands(), path


def outlined(tree: ET.ElementTree, declared: list[Path]) -> list[Path]:
    """Replace each `<text>` in the tree by its outlines, in place, and say which font
    files drew them. A tree with no text is left alone and needs no fontTools."""
    root = tree.getroot()
    found = texts(root)
    if not found:
        return []
    try:
        import fontTools  # noqa: F401
    except ImportError:
        raise PolyweaveError(
            "compose.text-unoutlined",
            f"the SVG has {len(found)} text run(s), which the engine draws blank, and "
            "fontTools, which outlines them first, is not installed",
            "pip install fonttools, or convert the text to outlines in the editor",
        ) from None
    parents = {child: parent for parent in root.iter() for child in parent}
    used: list[Path] = []
    for text in found:
        chain, at = [], text
        while at in parents:
            at = parents[at]
            chain.append(at)
        inherited: dict = {"__declared": declared}
        for one in reversed(chain):
            inherited.update({k: v for k, v in _style(one).items() if k in _FONT})
        group = ET.Element(f"{{{SVG}}}g")
        for key, value in text.attrib.items():
            if key not in ("x", "y", "dx", "dy", "style", *_FONT):
                group.set(key, value)
        kept = ";".join(f"{k}:{v}" for k, v in _style(text).items()
                        if k not in _FONT and k != "style" and k not in text.attrib)
        if kept:
            group.set("style", kept)
        for x, y, characters, style in _runs(text, inherited):
            d, path = _outline(x, y, characters, style)
            if path not in used:
                used.append(path)
            if d:
                ET.SubElement(group, f"{{{SVG}}}path",
                              {"d": d, **style.get("__paint", {})})
        holder = parents[text]
        holder[list(holder).index(text)] = group
    return used
