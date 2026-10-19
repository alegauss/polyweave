"""What an asset costs the game to draw, bounded like a look (§PW143).

A search that passed every look predicate could triple the triangles and nothing in the
spec would refuse it. A cost is read off the file the game draws, never off pixels, so
it takes no rung and a spec bounds it as it bounds anything else.
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import cost
from polyweave.layers.geometry.representations.voxels import model as V
from polyweave.loop import accept

SOLID = {
    "name": "block",
    "version": 1,
    "params": {},
    "materials": {"stone": {"colour": "#808080"}},
    "nodes": [
        {
            "id": "block",
            "op": "plate",
            "rect": [0, 0, 4, 4],
            "depth": 4,
            "material": "stone",
        },
    ],
    "output": "block",
    "voxels": {"cell": 1.0},
}


def glb(where: Path) -> Path:
    """Two primitives of 12 and 2 triangles, two materials, one 4x4 image inside."""
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(png, "PNG")
    image = png.getvalue()
    binary = image + b"\0" * (-len(image) % 4)
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(image)}],
        "images": [{"bufferView": 0, "mimeType": "image/png"}],
        "accessors": [
            {"count": 8, "componentType": 5126, "type": "VEC3"},
            {"count": 36, "componentType": 5123, "type": "SCALAR"},
            {"count": 6, "componentType": 5123, "type": "SCALAR"},
        ],
        "materials": [{"name": "body"}, {"name": "trim"}],
        "meshes": [
            {
                "primitives": [
                    {"attributes": {"POSITION": 0}, "indices": 1, "material": 0},
                    {"attributes": {"POSITION": 0}, "indices": 2, "material": 1},
                ]
            }
        ],
    }
    text = json.dumps(gltf).encode("utf-8")
    text += b" " * (-len(text) % 4)
    body = (
        struct.pack("<II", len(text), 0x4E4F534A)
        + text
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )
    where.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return where


def picture(where: Path) -> Path:
    rgba = np.zeros((16, 16, 4), dtype=np.uint8)
    rgba[4:12, 4:12] = [200, 80, 60, 255]
    Image.fromarray(rgba, "RGBA").save(where)
    return where


def spec(tmp_path: Path, body: str) -> accept.Spec:
    where = tmp_path / "block.accept.toml"
    where.write_text('asset = "block"\n' + body, encoding="utf-8")
    return accept.read(where)


def test_a_mesh_says_what_it_costs(tmp_path):
    found = cost.read(glb(tmp_path / "m.glb"))
    assert found == {
        "triangles": 14,
        "materials": 2,
        "draw_calls": 2,
        "texture_bytes": 64,
        # Its accessors carry no vertex data, so its topology reads as nothing missing.
        "holes": 0,
        "non_manifold": 0,
        "sharp_edge_share": 0.0,
        "edge_radius_min": 0.0,
    }


def solid_glb(where: Path, made: dict) -> Path:
    """A solid's mesh as a .glb of positions and triangle indices, its quads split."""
    points = np.asarray(made["vertices"], dtype="<f4")
    corners = [i for face in made["faces"] for k in range(1, len(face) - 1)
               for i in (face[0], face[k], face[k + 1])]
    index = np.asarray(corners, dtype="<u4").tobytes()
    data = points.tobytes() + index
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(data)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(points.tobytes())},
            {"buffer": 0, "byteOffset": len(points.tobytes()),
             "byteLength": len(index)},
        ],
        "accessors": [
            {"bufferView": 0, "count": len(points), "componentType": 5126,
             "type": "VEC3"},
            {"bufferView": 1, "count": len(corners), "componentType": 5125,
             "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
    }
    text = json.dumps(gltf).encode("utf-8")
    text += b" " * (-len(text) % 4)
    data += b"\0" * (-len(data) % 4)
    body = (struct.pack("<II", len(text), 0x4E4F534A) + text
            + struct.pack("<II", len(data), 0x004E4942) + data)
    where.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return where


def test_a_box_is_all_creases_and_a_rounded_one_none():
    """§PW497: one square edge among moulded pieces reads as another game."""
    from polyweave.layers.geometry import solid as S

    def read(made, name):
        return cost.read(solid_glb(Path(name), made))

    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        box = read(S.primitive("cube", 1.0), f"{folder}/box.glb")
        soft = read(S.primitive("rounded_box", 1.0, radius=0.2), f"{folder}/soft.glb")
        ball = read(S.primitive("sphere", 1.0), f"{folder}/ball.glb")
    # Twelve unit edges turn a quarter; six face diagonals, each root two, turn none.
    assert box["sharp_edge_share"] == pytest.approx(12 / (12 + 6 * 2**0.5), rel=1e-3)
    assert box["edge_radius_min"] == 0.0
    assert soft["sharp_edge_share"] == 0.0
    # A sphere's round read off its facets to within a percent or two.
    assert ball["edge_radius_min"] == pytest.approx(0.5, rel=0.02)
    # A rounded box's corners are meshed in skewed facets, which read tighter than the
    # radius declared, never below half of it; well clear of a crease's 0 either way.
    assert 0.1 <= soft["edge_radius_min"] <= 0.2


@pytest.mark.parametrize("size, steps", [
    ([3.0, 1.0, 3.0], 32),  # Spinhold's pizza, 0.028 when its rings were laid evenly
    ([3.0, 1.0, 3.0], 28),  # its pepperoni, which read 0.135
    ([3.0, 0.5, 1.5], 24),  # flat and oval at once
    ([1.0, 4.0, 1.0], 24),  # stretched, not squashed
])
def test_a_flattened_sphere_is_as_round_as_its_steps_say(size, steps):
    """§PW565: the rings follow the normal, so the rim is no crease."""
    import tempfile

    from polyweave.layers.geometry import solid as S

    made = S.primitive("sphere", size, steps=steps)
    with tempfile.TemporaryDirectory() as folder:
        read = cost.read(solid_glb(Path(folder) / "ball.glb", made))
    assert read["sharp_edge_share"] == 0.0
    # Still on the ellipsoid it declares.
    half = np.asarray(size) / 2.0
    assert np.allclose(np.sum((made["vertices"] / half) ** 2, axis=1), 1.0)


def test_a_spec_refuses_a_hard_edge_and_says_where_it_is(tmp_path):
    from polyweave.layers.geometry import solid as S

    solid_glb(tmp_path / "box.glb", S.transform(S.primitive("cube", 1.0), at=(5, 0, 0)))
    found = accept.check(
        spec(tmp_path, '[[predicate]]\nid = "soft"\nmeasure = "sharp_edge_share"\n'
                       'of = "box.glb"\nmax = 0.02\n'),
        picture(tmp_path / "p.png"), root=tmp_path)
    (one,) = found["predicates"]
    assert found["passed"] is False
    assert len(one["sharp_at"]) == 3
    assert all(4.4 < at[0] < 5.6 for at in one["sharp_at"]), "on the box, at x = 5"


def test_a_crease_the_predicate_states_decides_what_is_sharp(tmp_path):
    from polyweave.layers.geometry import solid as S

    solid_glb(tmp_path / "box.glb", S.primitive("cube", 1.0))
    found = accept.check(
        spec(tmp_path, '[[predicate]]\nid = "soft"\nmeasure = "sharp_edge_share"\n'
                       'of = "box.glb"\nmax = 0.02\ncrease = 95\n'),
        picture(tmp_path / "p.png"), root=tmp_path)
    assert found["passed"] is True, "a quarter turn is under a crease of 95 degrees"


def test_a_voxel_model_costs_its_skin_and_not_its_volume(tmp_path):
    written = V.write(SOLID, "block.glb", root=tmp_path, mesh=False, sheet=False)
    found = cost.read(written["voxels"])
    assert found["cells"] == 64
    assert found["cells_drawn"] == 56
    assert found["triangles"] == 56 * 12
    assert found["draw_calls"] == found["materials"] == 1


def test_a_texture_costs_its_pixels(tmp_path):
    Image.new("RGBA", (8, 4)).save(tmp_path / "t.png")
    assert cost.read(tmp_path / "t.png") == {"texture_bytes": 128}


def test_a_spec_refuses_a_look_bought_with_triangles(tmp_path):
    glb(tmp_path / "m.glb")
    found = accept.check(
        spec(
            tmp_path,
            '[[predicate]]\nid = "budget"\nmeasure = "triangles"\nof = "m.glb"\n'
            "max = 10\n",
        ),
        picture(tmp_path / "p.png"),
        root=tmp_path,
    )
    (one,) = found["predicates"]
    assert found["passed"] is False
    assert one["value"] == 14
    assert one["rung"] is None
    assert found["failed"] == ["budget"]


def test_a_cost_sits_beside_a_look_and_asks_nothing_of_the_ladder(tmp_path):
    glb(tmp_path / "m.glb")
    both = spec(
        tmp_path,
        '[[predicate]]\nid = "budget"\nmeasure = "draw_calls"\nof = "m.glb"\nmax = 4\n'
        '[[predicate]]\nid = "vivid"\nmeasure = "saturation_p50"\nmin = 0.2\n',
    )
    assert both.needs_rung() == "sphere"
    only = spec(
        tmp_path,
        '[[predicate]]\nid = "budget"\nmeasure = "triangles"\nof = "m.glb"\nmax = 20\n',
    )
    assert only.needs_rung() == "sphere"
    assert accept.check(both, picture(tmp_path / "p.png"), root=tmp_path)["passed"]


def test_with_no_file_named_the_cost_is_read_off_the_mesh_the_picture_records(
    tmp_path,
):
    glb(tmp_path / "m.glb")
    shot = picture(tmp_path / "p.png")
    provenance.write(
        provenance.build(
            "render",
            shot,
            inputs=[provenance.source("mesh", "m.glb", tmp_path)],
            root=tmp_path,
        ),
        root=tmp_path,
    )
    found = accept.check(
        spec(tmp_path, '[[predicate]]\nid = "t"\nmeasure = "triangles"\nmax = 20\n'),
        shot,
        root=tmp_path,
    )
    assert found["predicates"][0]["value"] == 14


def test_a_cost_with_nothing_to_read_it_off_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        accept.check(
            spec(
                tmp_path, '[[predicate]]\nid = "t"\nmeasure = "triangles"\nmax = 20\n'
            ),
            picture(tmp_path / "p.png"),
            root=tmp_path,
        )
    assert refused.value.code == "spec.no-cost-source"
    assert "of =" in refused.value.remedy


def test_a_cost_the_file_cannot_answer_is_refused_with_what_it_can(tmp_path):
    written = V.write(SOLID, "block.glb", root=tmp_path, mesh=False, sheet=False)
    with pytest.raises(PolyweaveError) as refused:
        cost.take("texture_bytes", written["voxels"])
    assert refused.value.code == "spec.no-cost-source"
    assert "cells_drawn" in refused.value.allowed


def test_the_operation_reads_a_file_by_path(tmp_path):
    glb(tmp_path / "m.glb")
    assert cost.costs("m.glb", root=str(tmp_path))["triangles"] == 14
