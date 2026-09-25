"""A clip baked by name, from files (§PW160).

Every step between a clip and what a game plays took a mesh and a fitted rig in memory,
so a GDScript project needed a Python script for motion. `motion.bake` takes the clip,
the mesh and the plan by name. It needs Blender and skips without it, as the render
tests do.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_skeleton import figure

from polyweave import clip as C
from polyweave.commands import Quiet
from polyweave.errors import PolyweaveError
from polyweave.motion import bake

SQUASH = {
    "root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1.06, 0.93, 1.06]), (0.4, [1, 1, 1])]}
}


def files(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        "[render]\npreview_size = 48\n"
        "samples = { sphere = 2, preview = 2, final = 2 }\n\n"
        "[sprites]\nfps = 5\n",
        encoding="utf-8",
    )
    C.write(C.clip("settle", 0.4, channels=SQUASH), "settle.clip.toml", root=tmp_path)
    return tmp_path


def test_a_clip_is_baked_by_name_to_both_shapes(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave.normalise import write_mesh

    root = files(tmp_path)
    write_mesh(figure(), root / "body.glb")
    found = bake(
        Quiet(),
        clip="settle.clip.toml",
        mesh="body.glb",
        out="baked/settle",
        plan="plush",
        root=str(root),
    )
    assert found["clip"] == "settle"
    assert found["plan"] == "plush"
    assert found["matched"] is True
    for key in ("animation", "sheet", "atlas"):
        assert Path(found[key]).is_file(), key


def test_a_mesh_that_is_not_there_is_refused_before_anything_is_fitted(tmp_path):
    root = files(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        bake(
            Quiet(),
            clip="settle.clip.toml",
            mesh="missing.glb",
            out="baked/settle",
            root=str(root),
        )
    assert refused.value.code == "rig.no-mesh"
