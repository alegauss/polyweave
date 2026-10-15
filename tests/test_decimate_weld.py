"""A preview rung's decimation welds a mesh's seams before it collapses (§PW78).

A glTF splits a vertex at every seam of its texture coordinates, and a collapse shrinks
each piece on its own. Cottony's booster tray, a cushion inflated from its drawing, came
back from the preview rung in stripes of holes, and the search measured those as a
different colour on every render it paid for.
"""

from __future__ import annotations

import pytest

bpy = pytest.importorskip("bpy", reason="Blender decimates the mesh")


def unwelded_grid(cells: int):
    """A flat grid whose every quad has its own four corners, as a seamed glTF comes."""
    from polyweave.render import blender

    blender.reset()
    vertices, faces = [], []
    for row in range(cells):
        for col in range(cells):
            at = len(vertices)
            vertices += [(col, row, 0.0), (col + 1, row, 0.0), (col + 1, row + 1, 0.0),
                         (col, row + 1, 0.0)]
            faces.append((at, at + 1, at + 2, at + 3))
    mesh = bpy.data.meshes.new("grid")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("grid", mesh)
    bpy.context.scene.collection.objects.link(obj)
    # a little relief, so the collapse has something to keep and planar dissolve cannot
    # merge the whole sheet into one face
    for vertex in mesh.vertices:
        vertex.co.z = ((vertex.co.x * 7 + vertex.co.y * 13) % 5) * 0.01
    return obj


def open_edges(obj) -> int:
    import bmesh

    held = bmesh.new()
    held.from_mesh(obj.data)
    count = sum(1 for edge in held.edges if edge.is_boundary)
    held.free()
    return count


def test_a_seamed_mesh_is_whole_after_the_preview_decimation(tmp_path):
    from polyweave.render import blender

    cells = 170  # 57,800 triangles, over the floor
    obj = unwelded_grid(cells)
    assert blender.triangles(obj) > blender.DECIMATE_FLOOR
    blender.decimate(obj, 0.25)
    # only the sheet's own border is open: no seam came apart
    assert open_edges(obj) <= 4 * cells
