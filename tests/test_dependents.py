"""From a changed file to the artefacts that show it (§PW119)."""

from __future__ import annotations

from polyweave import provenance as P


def made(root, artefact, inputs, *, kind="capture", script=None):
    (root / artefact).parent.mkdir(parents=True, exist_ok=True)
    (root / artefact).write_bytes(artefact.encode())
    record = P.build(
        kind,
        root / artefact,
        inputs=[P.source(role, root / path, root=root) for role, path in inputs],
        extra={"script": script} if script else None,
        root=root,
    )
    P.write(record, root=root)


def project(tmp_path):
    (tmp_path / "art").mkdir()
    for name in ("star", "cloud", "title.gd", "board.gd"):
        (tmp_path / "art" / name).write_bytes(name.encode())
    made(
        tmp_path,
        "shots/title.png",
        [("script", "art/title.gd"), ("loaded", "art/star")],
        script="art/title.gd",
    )
    made(
        tmp_path,
        "shots/board.png",
        [("script", "art/board.gd"), ("loaded", "art/cloud")],
        script="art/board.gd",
    )
    made(tmp_path, "renders/star.png", [("mesh", "art/star")], kind="render")
    return tmp_path


def test_a_file_names_every_artefact_made_from_it(tmp_path):
    root = project(tmp_path)
    found = P.dependents("art/star", root=root)
    assert found["input"] == "art/star"
    assert sorted(a["artefact"] for a in found["artefacts"]) == [
        "renders/star.png",
        "shots/title.png",
    ]
    title = next(a for a in found["artefacts"] if a["kind"] == "capture")
    assert title["made_by"] == "capture by art/title.gd"
    assert title["role"] == "loaded"


def test_a_file_nothing_was_made_from_names_nothing(tmp_path):
    root = project(tmp_path)
    assert P.dependents("art/title.gd", root=root)["artefacts"][0]["artefact"] == (
        "shots/title.png"
    )
    assert P.dependents("art/nothing", root=root)["artefacts"] == []


def test_nothing_changed_is_sound(tmp_path):
    assert P.outdated(project(tmp_path))["sound"] is True


def test_a_changed_sprite_leaves_exactly_the_artefacts_that_show_it_outdated(tmp_path):
    root = project(tmp_path)
    (root / "art" / "star").write_bytes(b"a brighter star")
    found = P.outdated(root)
    assert found["sound"] is False
    assert sorted(o["artefact"] for o in found["outdated"]) == [
        "renders/star.png",
        "shots/title.png",
    ]
    assert all(o["moved"] == ["art/star"] for o in found["outdated"])
