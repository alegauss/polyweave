"""Which shipped files a paid generator made, directly or by their inputs (§PW248)."""

from __future__ import annotations

from polyweave import provenance as P


def made(root, path, kind, inputs=(), extra=None, text="x"):
    where = root / path
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(text, encoding="utf-8")
    P.write(
        P.build(
            kind,
            where,
            inputs=[P.source("from", root / one, root=root) for one in inputs],
            extra=extra,
            root=root,
        ),
        root=root,
    )
    return path


def plain(root, path, text="authored"):
    where = root / path
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(text, encoding="utf-8")
    return path


def game(root):
    """Starship's two drones: one voxel model from a declaration, one Meshy mesh."""
    plain(root, "art/voxels/drone.toml")
    made(root, "assets/voxels/drone.voxels.json", "mesh", ["art/voxels/drone.toml"])
    made(
        root,
        "tools/art/meshy/drone.glb",
        "fetch",
        extra={"service": "meshy", "bought": "mesh", "task_id": "t1", "credits": 20},
    )
    made(
        root,
        "tools/art/meshy/drone.stripped.glb",
        "mesh",
        ["tools/art/meshy/drone.glb"],
    )
    made(
        root, "assets/models/drone.glb", "mesh", ["tools/art/meshy/drone.stripped.glb"]
    )
    plain(root, "assets/ui/logo.png", "no record")


def test_a_mesh_descended_from_a_purchase_is_named_with_its_chain(tmp_path):
    game(tmp_path)
    found = P.generated(["assets"], root=tmp_path)
    assert found["generated"] == [
        {
            "path": "assets/models/drone.glb",
            "chain": [
                "assets/models/drone.glb",
                "tools/art/meshy/drone.stripped.glb",
                "tools/art/meshy/drone.glb",
            ],
            "service": "meshy",
            "bought": "mesh",
            "direct": False,
        }
    ]
    assert found["authored"] == ["assets/voxels/drone.voxels.json"]
    assert found["unrecorded"] == ["assets/ui/logo.png"]


def test_a_file_bought_as_it_is_is_direct(tmp_path):
    game(tmp_path)
    found = P.generated(["tools/art/meshy/drone.glb"], root=tmp_path)
    assert found["generated"][0]["direct"] is True


def test_without_paths_every_recorded_artefact_is_read(tmp_path):
    game(tmp_path)
    found = P.generated(root=tmp_path)
    assert {one["path"] for one in found["generated"]} == {
        "assets/models/drone.glb",
        "tools/art/meshy/drone.glb",
        "tools/art/meshy/drone.stripped.glb",
    }
    assert found["unrecorded"] == []


def test_a_cycle_in_the_records_ends_the_walk(tmp_path):
    made(tmp_path, "a.txt", "mesh")
    made(tmp_path, "b.txt", "mesh", ["a.txt"])
    record = P.read("a.txt", tmp_path)
    record["inputs"] = [P.source("from", tmp_path / "b.txt", root=tmp_path)]
    P.write(record, root=tmp_path)
    assert P.generated(["a.txt"], root=tmp_path)["authored"] == ["a.txt"]
