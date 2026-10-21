"""A picture's derived copies, cut from a declared table and recorded (§PW585).

A promo site ships its own copies of a game's art: GitHub Pages serves the site's folder
alone, and the originals are too heavy for a page. Cottony cut 28 of them with a script
whose `--check` re-cut each in memory and called it stale past a mean and a 99th
percentile tuned by hand, after twelve copies went stale for weeks because nothing
recorded what each was made from.

That is provenance's job. A `*.copies.toml` declares every copy, and `picture.copies`
cuts and encodes each one and writes its record, naming the source and the table as
inputs. `provenance.outdated` then says a copy is stale the moment its source moves, by
the source's digest, so a newer Pillow re-encoding a level differently changes nothing.

    into = "site/assets"     # where each row's `out` is written; the project if unset
    quality = 88             # for WebP and JPEG, unless a row says otherwise

    [[copy]]
    source = "docs/design/promo3.jpg"
    out = "hero.webp"        # the extension picks the format: .webp, .jpg, .png
    side = 820               # the largest side in px; the size kept if unset
    box = [30, 402, 850, 1024]   # a crop, left top right bottom, before the resize
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: What a copy is encoded as, by the extension of its `out`.
FORMATS = {".webp": "WEBP", ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}

#: The quality a WebP or JPEG is written at where neither the row nor the table says.
QUALITY = 90

_TABLE_KEYS = ("into", "quality", "copy")
_ROW_KEYS = ("source", "out", "side", "box", "quality")


def _bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("copies.bad-table", what, remedy, **extra)


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _rows(table: Path, here: Path) -> list[dict]:
    """Every row of the table, checked whole before anything is cut."""
    try:
        said = tomllib.loads(table.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise _bad(f"{table.name} is not a table this can read",
                   "check the TOML; the detail says where it stops", detail=str(exc)
                   ) from exc
    stray = sorted(set(said) - set(_TABLE_KEYS))
    if stray:
        raise _bad(f"{table.name} has {', '.join(stray)}, which a copies table does "
                   "not take", f"write only {', '.join(_TABLE_KEYS)}",
                   given=stray[0], allowed=list(_TABLE_KEYS))
    into = here / str(said.get("into") or ".")
    quality = said.get("quality", QUALITY)
    rows = said.get("copy")
    if not isinstance(rows, list) or not rows:
        raise _bad(f"{table.name} declares no copy",
                   "add a [[copy]] row with a source and an out")
    checked = []
    for place, row in enumerate(rows, 1):
        name = f"{table.name} copy {place}"
        stray = sorted(set(row) - set(_ROW_KEYS))
        if stray:
            raise _bad(f"{name} has {', '.join(stray)}",
                       f"write only {', '.join(_ROW_KEYS)}", given=stray[0],
                       allowed=list(_ROW_KEYS))
        absent = [key for key in ("source", "out") if not row.get(key)]
        if absent:
            raise _bad(f"{name} names no {absent[0]}",
                       "give every row a source and an out")
        out = into / str(row["out"])
        if out.suffix.lower() not in FORMATS:
            raise _bad(f"{name} writes {row['out']}, an extension no format is picked "
                       "by", f"end out in one of {', '.join(FORMATS)}",
                       given=out.suffix, allowed=list(FORMATS))
        side, box = row.get("side"), row.get("box")
        if side is not None and not (_whole(side) and side > 0):
            raise _bad(f"{name} has side {side!r}",
                       "write side as a whole number of px")
        if box is not None and not (isinstance(box, list) and len(box) == 4
                                    and all(_whole(n) for n in box)
                                    and box[0] < box[2] and box[1] < box[3]):
            raise _bad(f"{name} has box {box!r}",
                       "write box as [left, top, right, bottom] in px, right of left "
                       "and below top")
        kept = row.get("quality", quality)
        if not (_whole(kept) and 1 <= kept <= 100):
            raise _bad(f"{name} has quality {kept!r}", "write quality from 1 to 100")
        checked.append({"source": here / str(row["source"]), "out": out, "side": side,
                        "box": box, "quality": kept})
    return checked


def _cut(row: dict) -> Any:
    """The source cropped and resized as the row says, in the mode its format takes."""
    from PIL import Image

    with Image.open(row["source"]) as opened:
        image = opened.convert(
            "RGBA" if opened.mode in ("RGBA", "LA", "P") else "RGB"
        )
    if row["box"]:
        image = image.crop(tuple(row["box"]))
    if row["side"]:
        image.thumbnail((row["side"], row["side"]), Image.LANCZOS)
    if FORMATS[row["out"].suffix.lower()] == "JPEG" and image.mode == "RGBA":
        if image.getextrema()[3][0] < 255:
            raise PolyweaveError(
                "copies.no-alpha",
                f"{row['out'].name} is a JPEG, and {row['source'].name} has "
                "transparent pixels a JPEG would fill",
                "write it as .webp or .png, or crop to where the source is opaque",
            )
        image = image.convert("RGB")
    return image


def _save(image: Any, row: dict) -> None:
    kind = FORMATS[row["out"].suffix.lower()]
    row["out"].parent.mkdir(parents=True, exist_ok=True)
    if kind == "WEBP":
        image.save(row["out"], kind, quality=row["quality"], method=6)
    elif kind == "JPEG":
        image.save(row["out"], kind, quality=row["quality"])
    else:
        image.save(row["out"], kind)


@operation("picture.copies")
def copies(
    source: Annotated[str, Param("the *.copies.toml, as a path under the project")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Cut every copy a table declares, each recorded with its source and the table.

    Each row is cropped by `box`, resized to `side` and encoded by its `out`'s
    extension. A source that is not there is refused before anything is written,
    naming every one missing. A copy is stale once its source moves, which
    `provenance.outdated` says, so no statistic is needed to tell.
    """
    import PIL

    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    table = here / source if not Path(source).is_absolute() else Path(source)
    if not table.is_file():
        raise _bad(f"there is no copies table at {source}",
                   "name a *.copies.toml under the project")
    rows = _rows(table, here)
    missing = sorted({provenance.relative(r["source"], here) for r in rows
                      if not r["source"].is_file()})
    if missing:
        raise PolyweaveError(
            "copies.missing-source",
            f"{len(missing)} source(s) the table names are not there, the first "
            f"{missing[0]}; nothing was written",
            "restore them, or point the rows at where they moved",
            detail=", ".join(missing),
        )
    written = []
    for row in rows:
        image = _cut(row)
        _save(image, row)
        provenance.write(provenance.build(
            "picture", row["out"],
            engine={"name": "picture.copies", "pillow": PIL.__version__},
            inputs=[provenance.source("picture", row["source"], here),
                    provenance.source("table", table, here)],
            params={"made_by": "picture.copies", "side": row["side"],
                    "box": row["box"], "quality": row["quality"]},
            root=here,
        ), root=here)
        written.append({
            "out": provenance.relative(row["out"], here),
            "source": provenance.relative(row["source"], here),
            "size": list(image.size),
            "bytes": row["out"].stat().st_size,
        })
    return {"table": provenance.relative(table, here), "written": written}
