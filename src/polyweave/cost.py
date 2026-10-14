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
    "holes": "edges one triangle uses once the seams are welded: the rims of holes",
    "non_manifold": "edges more than two triangles share, which no clean surface has",
}

#: What each kind of file can answer.
ANSWERS = {
    ".glb": ("triangles", "materials", "draw_calls", "texture_bytes", "holes",
             "non_manifold"),
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
        **_topology(gltf, binary),
    }


#: glTF's component types, as numpy reads them.
_COMPONENTS = {5121: "<u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
_WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor(gltf: dict, binary: bytes, index: int):
    """One accessor's values as an array, rows by element (§PW447)."""
    import numpy as np

    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    kind = np.dtype(_COMPONENTS[accessor["componentType"]])
    width = _WIDTHS[accessor["type"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride") or kind.itemsize * width
    count = accessor["count"]
    if stride == kind.itemsize * width:
        flat = np.frombuffer(binary, dtype=kind, count=count * width, offset=start)
        return flat.reshape(count, width)
    rows = [np.frombuffer(binary, dtype=kind, count=width, offset=start + i * stride)
            for i in range(count)]
    return np.array(rows)


def _topology(gltf: dict, binary: bytes) -> dict:
    """The rims of holes and the edges more than two triangles share, over every
    triangle primitive, with vertices at one place welded first: a glTF splits a vertex
    at each UV seam, and an unwelded seam would read as a hole (§PW447)."""
    import numpy as np

    edges = []
    offset = 0
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", _TRIANGLES) != _TRIANGLES:
                continue
            at = primitive["attributes"].get("POSITION")
            if at is None or "bufferView" not in gltf["accessors"][at]:
                continue
            points = _accessor(gltf, binary, at).astype(np.float64)
            keys = np.round(points, 5)
            _, welded = np.unique(keys, axis=0, return_inverse=True)
            welded = welded.reshape(-1) + offset
            offset = int(welded.max()) + 1 if len(welded) else offset
            if "indices" in primitive:
                corners = _accessor(gltf, binary, primitive["indices"]).reshape(-1)
            else:
                corners = np.arange(len(points))
            faces = welded[corners[: len(corners) // 3 * 3]].reshape(-1, 3)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges.append(np.sort(faces[:, [a, b]], axis=1))
    if not edges:
        return {"holes": 0, "non_manifold": 0}
    every = np.concatenate(edges)
    every = every[every[:, 0] != every[:, 1]]
    _, uses = np.unique(every, axis=0, return_counts=True)
    return {"holes": int((uses == 1).sum()), "non_manifold": int((uses > 2).sum())}


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
    stated = json.loads(where.read_text(encoding="utf-8-sig"))
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
