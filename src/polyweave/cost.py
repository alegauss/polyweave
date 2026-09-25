"""What an asset costs the game to draw, read off the file and not the render (§PW143).

An acceptance spec bounded how an asset looks and never what it costs: a search that
passed every look predicate could triple the triangles and nothing would refuse the rig
that did it. These are the numbers a game pays at run time, and a spec bounds them like
any other measure, `triangles <= 1200`.

Read off the artefact itself, never off pixels, so a cost takes no rung:

- a `.glb`: `triangles`, `materials`, `draw_calls` (one per primitive, as an engine
  submits them) and `texture_bytes` (every embedded image as uncompressed RGBA8, no
  mipmaps);
- a `.voxels.json`: `cells`, `cells_drawn` (the skin, the cells with a face on the
  outside, which is what the Godot addon's `skin()` draws), `triangles` (twelve per
  drawn cube), `materials` and `draw_calls` (one MultiMesh);
- a `.png` texture: `texture_bytes`.
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path
from typing import Annotated, Any

from .describe import Param, operation
from .errors import PolyweaveError

#: Every cost a predicate may bound, and what it counts.
COSTS: dict[str, str] = {
    "triangles": "triangles the game draws",
    "materials": "distinct materials, each a state change",
    "draw_calls": "submissions the engine makes: one per primitive, one per MultiMesh",
    "texture_bytes": "texture memory, uncompressed RGBA8 without mipmaps",
    "cells": "a voxel model's filled cells",
    "cells_drawn": "a voxel model's cells with a face on the outside",
}

#: What each kind of file can answer.
ANSWERS = {
    ".glb": ("triangles", "materials", "draw_calls", "texture_bytes"),
    ".json": ("cells", "cells_drawn", "triangles", "materials", "draw_calls"),
    ".png": ("texture_bytes",),
}

_GLB_MAGIC = 0x46546C67
_JSON_CHUNK = 0x4E4F534A
_BIN_CHUNK = 0x004E4942
_TRIANGLES = 4


def is_cost(name: str) -> bool:
    return name in COSTS


def read(path: str | Path) -> dict:
    """Every cost the file can answer, by name."""
    where = Path(path)
    if not where.is_file():
        raise PolyweaveError(
            "spec.no-cost-source",
            f"there is nothing at {where} to read a cost off",
            "name the mesh, voxel model or texture the game draws with `of`",
        )
    suffix = where.suffix.lower()
    if suffix == ".glb":
        return _glb(where)
    if suffix == ".json":
        return _voxels(where)
    if suffix == ".png":
        from PIL import Image

        with Image.open(where) as picture:
            return {"texture_bytes": picture.width * picture.height * 4}
    raise PolyweaveError(
        "spec.no-cost-source",
        f"{where.name} is not a file a cost is read off",
        "name a .glb, a .voxels.json or a .png",
        given=suffix,
        allowed=tuple(ANSWERS),
    )


def take(name: str, path: str | Path) -> int:
    """One cost off one file, refused where that kind of file cannot answer it."""
    found = read(path)
    if name not in found:
        kind = Path(path).suffix.lower()
        raise PolyweaveError(
            "spec.no-cost-source",
            f"a {kind} file does not say how many {name} it costs",
            f"bound one of {', '.join(sorted(found))} on it, or name another file",
            given=name,
            allowed=tuple(sorted(found)),
        )
    return found[name]


def _glb(where: Path) -> dict:
    data = where.read_bytes()
    magic, _, length = struct.unpack_from("<III", data, 0)
    if magic != _GLB_MAGIC or length > len(data):
        raise PolyweaveError(
            "spec.no-cost-source",
            f"{where.name} is not a binary glTF",
            "export the mesh as .glb, which is what the build writes",
        )
    gltf: dict = {}
    binary = b""
    at = 12
    while at + 8 <= length:
        size, kind = struct.unpack_from("<II", data, at)
        chunk = data[at + 8 : at + 8 + size]
        if kind == _JSON_CHUNK:
            gltf = json.loads(chunk.decode("utf-8"))
        elif kind == _BIN_CHUNK:
            binary = chunk
        at += 8 + size
    accessors = gltf.get("accessors", [])
    triangles = calls = 0
    used: set = set()
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            calls += 1
            if "material" in primitive:
                used.add(primitive["material"])
            if primitive.get("mode", _TRIANGLES) != _TRIANGLES:
                continue
            counted = primitive.get("indices", primitive["attributes"].get("POSITION"))
            if counted is not None:
                triangles += accessors[counted]["count"] // 3
    return {
        "triangles": triangles,
        "materials": len(used) or len(gltf.get("materials", [])),
        "draw_calls": calls,
        "texture_bytes": sum(
            _image_bytes(one, gltf, binary) for one in gltf.get("images", [])
        ),
    }


def _image_bytes(image: dict, gltf: dict, binary: bytes) -> int:
    """One image's size as uncompressed RGBA8, read off its embedded bytes."""
    from PIL import Image

    if "bufferView" not in image:
        return 0
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    with Image.open(io.BytesIO(binary[start : start + view["byteLength"]])) as picture:
        return picture.width * picture.height * 4


def _voxels(where: Path) -> dict:
    stated = json.loads(where.read_text(encoding="utf-8"))
    cells = stated.get("cells")
    if not isinstance(cells, dict) or not {"x", "y", "z"} <= set(cells):
        raise PolyweaveError(
            "spec.no-cost-source",
            f"{where.name} is not a voxel model",
            "name the <name>.voxels.json a voxel build wrote",
        )
    at = set(zip(cells["x"], cells["y"], cells["z"], strict=True))
    faces = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    drawn = sum(
        1 for x, y, z in at if any((x + a, y + b, z + c) not in at for a, b, c in faces)
    )
    return {
        "cells": len(at),
        "cells_drawn": drawn,
        "triangles": drawn * 12,
        "materials": len(set(cells.get("palette", []))) or 1,
        "draw_calls": 1,
    }


@operation("cost.read")
def costs(
    of: Annotated[str, Param("the mesh, voxel model or texture, under the project")],
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """What a file costs the game to draw: the numbers a cost predicate bounds."""
    where = Path(of) if Path(of).is_absolute() else Path(root) / of
    return {"of": of, **read(where)}


def source(subject: Any, of: str | None, root: str | Path) -> Path:
    """The file a cost predicate reads: `of` where the spec names one, else the mesh the
    picture's own record says it was rendered from."""
    here = Path(root)
    if of:
        return Path(of) if Path(of).is_absolute() else here / of
    if isinstance(subject, str | Path):
        from . import provenance

        try:
            record = provenance.read(subject, root=here)
        except PolyweaveError:
            record = {}
        for one in record.get("inputs", []):
            if one.get("role") == "mesh":
                return here / one["path"]
    raise PolyweaveError(
        "spec.no-cost-source",
        "a cost predicate names no file, and the picture records no mesh it came from",
        'add of = "<the .glb or .voxels.json the game draws>" to the predicate',
        example='of = "art/star.glb"',
    )
