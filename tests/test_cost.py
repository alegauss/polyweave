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

from polyweave import accept, cost, provenance
from polyweave.errors import PolyweaveError
from polyweave.geometry import voxels as V

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
    }


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
