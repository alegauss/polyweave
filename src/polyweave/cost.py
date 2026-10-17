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
    "sharp_edge_share": "the share of edge length whose faces turn more than the "
                        "crease, 30 degrees unless the predicate says crease",
    "edge_radius_min": "the tightest round over the surface, in the model's units; a "
                       "crease is 0",
}

#: The measures of how round a model is (§PW497), which take a predicate's `crease`.
EDGES = ("sharp_edge_share", "edge_radius_min")

#: How far two faces may turn at an edge, in degrees, before the edge is a crease. A
#: round of a quarter turn in three segments turns 30 at each, the coarsest that reads
#: as round; a chamfer turns 45 and a box 90.
CREASE = 30.0

#: What each kind of file can answer.
ANSWERS = {
    ".glb": ("triangles", "materials", "draw_calls", "texture_bytes", "holes",
             "non_manifold", *EDGES),
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


def bounds(path: str | Path) -> tuple[list[float], list[float]]:
    """A .glb's extent off its position accessors' own min and max, the mesh as
    stored with no node transform applied (§PW451)."""
    gltf, _ = _parsed(Path(path))
    low, high = [float("inf")] * 3, [float("-inf")] * 3
    accessors = gltf.get("accessors", [])
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            at = primitive.get("attributes", {}).get("POSITION")
            if at is None or "min" not in accessors[at]:
                continue
            for axis in range(3):
                low[axis] = min(low[axis], float(accessors[at]["min"][axis]))
                high[axis] = max(high[axis], float(accessors[at]["max"][axis]))
    if low[0] == float("inf"):
        raise PolyweaveError(
            "spec.no-cost-source",
            f"{Path(path).name} has no positions with a stated extent",
            "export the mesh again; a glTF exporter writes each position's min and max",
        )
    return low, high


def _parsed(where: Path) -> tuple[dict, bytes]:
    """A binary glTF's JSON and its binary chunk."""
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
    return gltf, binary


def _glb(where: Path) -> dict:
    gltf, binary = _parsed(where)
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
        **{k: v for k, v in _edged(gltf, binary, CREASE).items() if k in EDGES},
    }


def edges(path: str | Path, crease: float = CREASE) -> dict:
    """How round a .glb is at a crease, and where its sharpest edges are (§PW497)."""
    where = Path(path)
    if where.suffix.lower() != ".glb" or not where.is_file():
        raise PolyweaveError(
            "spec.no-cost-source",
            f"{where.name} is not a mesh whose edges can be read",
            "name the .glb the game draws with `of`",
        )
    gltf, binary = _parsed(where)
    return _edged(gltf, binary, float(crease))


def _welded(gltf: dict, binary: bytes):
    """Every triangle primitive's points and faces, vertices at one place welded."""
    import numpy as np

    points, faces, offset = [], [], 0
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", _TRIANGLES) != _TRIANGLES:
                continue
            at = primitive["attributes"].get("POSITION")
            if at is None or "bufferView" not in gltf["accessors"][at]:
                continue
            these = _accessor(gltf, binary, at).astype(np.float64)
            if "indices" in primitive:
                corners = _accessor(gltf, binary, primitive["indices"]).reshape(-1)
            else:
                corners = np.arange(len(these))
            points.append(these)
            faces.append(corners[: len(corners) // 3 * 3].reshape(-1, 3) + offset)
            offset += len(these)
    if not points:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=int)
    every = np.vstack(points)
    _, welded = np.unique(np.round(every, 5), axis=0, return_inverse=True)
    welded = welded.reshape(-1)
    joined = np.zeros((welded.max() + 1, 3))
    joined[welded] = every
    return joined, welded[np.vstack(faces)]


def _edged(gltf: dict, binary: bytes, crease: float) -> dict:
    """Sharp edges' share of length, the tightest round, and the sharpest edges' places.

    Over each edge two faces share: the angle their normals turn is how sharp it is.
    Past the crease it is a crease, with no radius; under it, the round it belongs to is
    as tight as the strip across the edge, half of each face's height over it, divided
    by that angle: an arc's length over its turn. That reads a sphere and a cylinder's
    side to within a percent; where a round's corner is meshed in skewed facets it reads
    the tightest of them, down to about half the radius declared. A flat edge has no
    radius and is left out.
    """
    import numpy as np

    points, faces = _welded(gltf, binary)
    empty = {"sharp_edge_share": 0.0, "edge_radius_min": 0.0, "sharp_at": []}
    if not len(faces):
        return empty
    a, b, c = (points[faces[:, i]] for i in range(3))
    normal = np.cross(b - a, c - a)
    twice = np.linalg.norm(normal, axis=1)
    keep = twice > 1e-12
    faces, normal, area = faces[keep], normal[keep] / twice[keep, None], twice[keep] / 2
    pairs = np.concatenate([np.sort(faces[:, [i, (i + 1) % 3]], axis=1)
                            for i in range(3)])
    owner = np.tile(np.arange(len(faces)), 3)
    unique, inverse, counts = np.unique(pairs, axis=0, return_inverse=True,
                                        return_counts=True)
    grouped = owner[np.argsort(inverse.reshape(-1), kind="stable")]
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    # An edge two faces share, and only two: a third makes it non-manifold, not sharp.
    shared = np.nonzero(counts == 2)[0]
    if not len(shared):
        return empty
    edge = unique[shared]
    one, two = grouped[starts[shared]], grouped[starts[shared] + 1]
    turn = np.degrees(np.arccos(np.clip(np.sum(normal[one] * normal[two], axis=1),
                                        -1.0, 1.0)))
    length = np.linalg.norm(points[edge[:, 0]] - points[edge[:, 1]], axis=1)
    sharp = turn > crease
    share = float(length[sharp].sum() / max(length.sum(), 1e-12))
    bent = (turn > 1e-3) & ~sharp
    # Each face's height over the edge is twice its area over the edge's length, and
    # the strip a bend spans is half of each.
    across = (area[one] + area[two]) / np.maximum(length, 1e-12)
    radius = across[bent] / np.radians(turn[bent])
    # A crease has no round at all, and a body all flat faces has none to measure.
    tightest = 0.0 if sharp.any() or not len(radius) else float(radius.min())
    at = (points[edge[:, 0]] + points[edge[:, 1]]) / 2
    longest = np.argsort(-length * sharp)[: min(3, int(sharp.sum()))]
    return {
        "sharp_edge_share": round(share, 6),
        "edge_radius_min": round(tightest, 6),
        "sharp_at": [[round(float(v), 4) for v in at[i]] for i in longest],
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
