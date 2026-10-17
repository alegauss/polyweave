"""A bought mesh's own colours, carried onto the cells it fills (§PW100).

A hull fetched from the service arrives painted: its colour is a texture, and a voxel
model that throws that away and wears one flat material has kept the shape and lost what
was paid for. So each cell takes the colour of the surface nearest it.

**Sampled, then quantised once.** The surface is sampled at every triangle's middle and
corners, each sample taking the texel under its texture coordinate. Those colours are
quantised to the few a game can use — `colours` on the node — before any cell asks, so a
node asked twice, under a mirror say, answers from one palette and not two.

**Nearest by brute force, bounded.** A voxel model is coarse, so the nearest sample of a
few tens of thousands is as good as the nearest point of the surface, and numpy answers
it in chunks without a spatial index.
"""

from __future__ import annotations

import numpy as np

__all__ = ["painted", "quantise", "samples"]

#: The most surface samples a cell is matched against; more are thinned evenly.
LIMIT = 20_000

#: How many cells are matched at once, which bounds the memory a match takes: a chunk
#: against every sample is CHUNK by LIMIT distances, about 20 MB.
CHUNK = 128


def texel(image: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """The colour under each texture coordinate, 0..255, wrapping as a texture does."""
    tall, wide = image.shape[:2]
    u = np.mod(uv[:, 0], 1.0)
    v = np.mod(uv[:, 1], 1.0)
    x = np.clip((u * wide).astype(int), 0, wide - 1)
    y = np.clip(((1.0 - v) * tall).astype(int), 0, tall - 1)
    return np.round(image[y, x, :3] * 255.0)


def samples(mesh: dict) -> tuple[np.ndarray, np.ndarray]:
    """Points on the surface, with the colour the texture gives each one."""
    vertices = np.asarray(mesh["vertices"], dtype=float)
    corners = np.asarray(mesh["corners"], dtype=float).reshape(-1, 2)
    # Each face as a fan, as indices: into the vertices, and into the corners, which run
    # face after face in the order the faces list their vertices.
    at, fans, loops = 0, [], []
    for face in mesh["faces"]:
        for second in range(1, len(face) - 1):
            fans.append((face[0], face[second], face[second + 1]))
            loops.append((at, at + second, at + second + 1))
        at += len(face)
    if not fans:
        return np.zeros((0, 3)), np.zeros((0, 3))
    where = vertices[np.asarray(fans)]  # (triangles, 3, xyz)
    coords = corners[np.asarray(loops)]  # (triangles, 3, uv)
    points = np.concatenate([where.mean(axis=1), where.reshape(-1, 3)])
    uvs = np.concatenate([coords.mean(axis=1), coords.reshape(-1, 2)])
    return points, texel(mesh["image"], uvs)


def quantise(colours: np.ndarray, count: int, rounds: int = 12) -> tuple:
    """A palette of at most `count` colours, and each colour's slot in it.

    k-means seeded along the colours' brightness, so the same colours always give the
    same palette; a slot that empties is dropped, not kept as a colour nobody wears.
    """
    unique = np.unique(colours, axis=0)
    if len(unique) <= count:
        slots = np.array(
            [np.flatnonzero((unique == c).all(axis=1))[0] for c in colours]
        )
        return unique, slots
    order = unique[np.argsort(unique @ np.array([0.299, 0.587, 0.114]), kind="stable")]
    centres = order[np.linspace(0, len(order) - 1, count).round().astype(int)].astype(
        float
    )
    for _ in range(rounds):
        slots = np.argmin(
            ((colours[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1
        )
        for slot in range(len(centres)):
            mine = colours[slots == slot]
            if len(mine):
                centres[slot] = mine.mean(axis=0)
    slots = np.argmin(((colours[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
    kept = np.unique(slots)
    renumber = {old: new for new, old in enumerate(kept)}
    return np.round(centres[kept]), np.array([renumber[s] for s in slots])


def painted(mesh: dict, count: int) -> dict | None:
    """A textured mesh's surface as samples, each labelled with its palette slot."""
    if (
        mesh.get("image") is None
        or mesh.get("corners") is None
        or not len(mesh["corners"])
    ):
        return None
    points, colours = samples(mesh)
    if not len(points):
        return None
    if len(points) > LIMIT:
        keep = np.linspace(0, len(points) - 1, LIMIT).round().astype(int)
        points, colours = points[keep], colours[keep]
    palette, slots = quantise(colours, max(1, int(count)))
    return {"points": points, "slots": slots, "palette": palette}


def nearest(found: dict, queries: np.ndarray) -> np.ndarray:
    """The palette slot of the surface sample nearest each query point."""
    out = np.zeros(len(queries), dtype=int)
    points = found["points"]
    lengths = (points**2).sum(axis=1)
    for start in range(0, len(queries), CHUNK):
        chunk = queries[start : start + CHUNK]
        # |a - b|² less |a|², which is the same for every sample and so ranks the same.
        distance = lengths[None, :] - 2.0 * (chunk @ points.T)
        out[start : start + CHUNK] = found["slots"][np.argmin(distance, axis=1)]
    return out


def hexed(colour: np.ndarray) -> str:
    return "#" + "".join(f"{int(v):02X}" for v in colour)
