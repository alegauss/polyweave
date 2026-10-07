"""Everything a project governs, in one read (§PW299)."""

from __future__ import annotations

import pytest

from polyweave import config as C
from polyweave import project, provenance
from polyweave.errors import PolyweaveError

SHAPE = """name = "{name}"
output = "{name}"

[[nodes]]
id = "{name}"
op = "primitive"
kind = "cube"
size = 1
"""


def record(root, kind, artefact, *, inputs=(), engine=None, params=None, body=b"x"):
    """An artefact on disk and the record a producer would have written beside it."""
    (root / artefact).parent.mkdir(parents=True, exist_ok=True)
    (root / artefact).write_bytes(body)
    provenance.write(
        provenance.build(
            kind,
            root / artefact,
            root=root,
            inputs=[provenance.source(role, path, root) for role, path in inputs],
            engine=engine or {},
            params=params or {},
        ),
        root=root,
    )


@pytest.fixture
def tree(tmp_path):
    (tmp_path / C.FILENAME).write_text(
        '[words]\ntable = "text/strings.csv"\ncanon = "text/canon.json"\n',
        encoding="utf-8",
    )
    (tmp_path / "shapes").mkdir()
    for name in ("barrel", "crate"):
        (tmp_path / "shapes" / f"{name}.toml").write_text(
            SHAPE.format(name=name), encoding="utf-8"
        )
    built = [("declaration", "shapes/barrel.toml")]
    record(tmp_path, "mesh", "assets/barrel.glb", inputs=built)
    drawn = [("mesh", "assets/barrel.glb")]
    record(tmp_path, "render", "docs/renders/barrel.png", inputs=drawn)
    (tmp_path / "music").mkdir()
    (tmp_path / "music" / "theme.toml").write_text("tempo = 120\n", encoding="utf-8")
    record(
        tmp_path,
        "sound",
        "audio/theme.ogg",
        inputs=[("score", "music/theme.toml")],
        engine={"name": "music.render"},
    )
    record(tmp_path, "sound", "audio/hit.wav", engine={"name": "sound.synth"})
    record(tmp_path, "mesh", "anim/walk.glb", params={"clip": "walk"})
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "strings.csv").write_text(
        "keys,en\nTITLE,Starship\nSTART,Press start\n", encoding="utf-8"
    )
    return tmp_path


def by_id(answer):
    return {row["id"]: row for row in answer["items"]}


def test_one_read_lists_every_item_by_kind(tree):
    found = project.inventory(str(tree))
    rows = by_id(found)
    assert rows["assets/barrel.glb"]["kind"] == "mesh"
    assert rows["assets/barrel.glb"]["declaration"] == "shapes/barrel.toml"
    assert rows["assets/barrel.glb"]["record"] == "sound"
    assert len(rows["assets/barrel.glb"]["digest"]) == 16
    assert rows["docs/renders/barrel.png"]["kind"] == "picture"
    assert rows["audio/theme.ogg"]["kind"] == "music"
    assert rows["audio/theme.ogg"]["declaration"] == "music/theme.toml"
    assert rows["audio/hit.wav"]["kind"] == "sound"
    assert rows["anim/walk.glb"]["kind"] == "clip"
    # A declaration not built yet is an item too, and the built one is not listed twice.
    assert rows["shapes/crate.toml"]["record"] == "unbuilt"
    assert "shapes/barrel.toml" not in rows
    # Each line of the table, waiting on a person while the canon holds no verdict.
    assert rows["line:TITLE"]["kind"] == "line"
    assert rows["line:TITLE"]["declaration"] == "text/strings.csv"
    assert rows["line:TITLE"]["pending"] is True
    assert found["kinds"] == {
        "mesh": 2,
        "picture": 1,
        "sound": 1,
        "music": 1,
        "clip": 1,
        "line": 2,
    }
    kinds = [row["kind"] for row in found["items"]]
    assert kinds == sorted(kinds, key=project.KINDS.index)
    # The cache's own records are not the project's items.
    assert not any(r["id"].startswith(".") for r in found["items"])


def test_a_record_says_whether_its_artefact_still_holds(tree):
    (tree / "assets" / "barrel.glb").write_bytes(b"moved")
    (tree / "audio" / "hit.wav").unlink()
    rows = by_id(project.inventory(str(tree)))
    assert rows["assets/barrel.glb"]["record"] == "changed"
    assert rows["audio/hit.wav"]["record"] == "missing"
    # The render's mesh moved under it, so it is outdated rather than sound.
    assert rows["docs/renders/barrel.png"]["record"] == "outdated"


def test_a_produced_file_with_no_record_is_listed_unrecorded(tree):
    (tree / "assets" / "3d").mkdir(parents=True)
    (tree / "assets" / "3d" / "ship.glb").write_bytes(b"bought")
    row = by_id(project.inventory(str(tree)))["assets/3d/ship.glb"]
    assert row["kind"] == "mesh"
    assert row["record"] == "unrecorded"
    assert row["digest"]


def test_it_filters_by_kind_and_pages(tree):
    lines = project.inventory(str(tree), kind="line", limit=1)
    assert [r["id"] for r in lines["items"]] == ["line:START"]
    assert lines["total"] == 2
    assert lines["next"] == 1
    rest = project.inventory(str(tree), kind="line", offset=1, limit=1)
    assert [r["id"] for r in rest["items"]] == ["line:TITLE"]
    assert rest["next"] is None
    # The counts are the whole project's, whatever the filter.
    assert lines["kinds"]["mesh"] == 2


def test_an_empty_project_answers_with_nothing_and_is_never_refused(tmp_path):
    found = project.inventory(str(tmp_path))
    assert found == {"items": [], "total": 0, "kinds": {}, "next": None}


def test_an_unknown_kind_is_refused_with_the_kinds(tree):
    from polyweave import describe as D

    with pytest.raises(PolyweaveError) as caught:
        D.validate("project.inventory", {"root": str(tree), "kind": "meshes"})
    assert caught.value.code == "op.bad-choice"
    assert "mesh" in caught.value.remedy


def test_a_record_that_does_not_read_is_left_out_not_raised(tree):
    (tree / "assets" / "broken.glb.prov.json").write_text("{", encoding="utf-8")
    try:
        project.inventory(str(tree))
    except PolyweaveError as refused:  # pragma: no cover - the failure being tested
        pytest.fail(f"refused: {refused}")


def test_a_brief_answers_for_any_item_the_inventory_lists(tree):
    # §PW300: a sound, a picture or a line has a one-read state, not only a mesh.
    from polyweave import brief

    hit = brief.brief("audio/hit.wav", root=str(tree))
    assert hit["item"]["kind"] == "sound"
    assert hit["artefact"]["matches_record"] is True
    theme = brief.brief("audio/theme.ogg", root=str(tree))
    assert theme["declaration"]["path"] == "music/theme.toml"
    assert "valid" in theme["declaration"]
    # A change to the mesh reaches the render made from it.
    barrel = brief.brief("assets/barrel.glb", root=str(tree))
    assert barrel["declaration"]["path"] == "shapes/barrel.toml"
    assert barrel["declaration"]["reads"]
    assert [d["artefact"] for d in barrel["dependents"]] == ["docs/renders/barrel.png"]


def test_a_brief_on_a_line_reads_its_text_speaker_and_verdict(tree):
    import json

    from polyweave import brief

    (tree / "text" / "strings.csv").write_text(
        "keys,en,pt_BR,_speaker\nTITLE,Starship,Nave,captain\n", encoding="utf-8"
    )
    line = brief.brief("line:TITLE", root=str(tree))
    assert line["item"]["pending"] is True
    assert line["waiting_on_a_person"] is True
    assert line["declaration"]["text"] == {"en": "Starship", "pt_BR": "Nave"}
    assert line["declaration"]["speaker"] == "captain"
    assert line["declaration"]["verdict"] is None
    assert line["spec"] is None
    (tree / "text" / "canon.json").write_text(
        json.dumps(
            [
                {
                    "key": "TITLE",
                    "sha256": "an older text",
                    "approved": True,
                    "verdict": {"choice": "accept", "why": "fits"},
                }
            ]
        ),
        encoding="utf-8",
    )
    judged = brief.brief("line:TITLE", root=str(tree))["declaration"]["verdict"]
    assert judged["approved"] is True
    assert judged["on_this_text"] is False


def test_an_id_nothing_lists_is_refused_like_an_unknown_name(tree):
    from polyweave import brief

    with pytest.raises(PolyweaveError) as refused:
        brief.brief("audio/nothing.wav", root=str(tree))
    assert "project.inventory" in refused.value.remedy


def test_a_brief_reads_each_kind_back_in_its_own_words(tmp_path):
    # §PW300: an effect as its table, a cue as music.validate, a picture as its family.
    from polyweave import brief, sfx, vfx

    (tmp_path / C.FILENAME).write_text(
        '[style]\npalette = ["#112233", "#ffeedd"]\nfilter = "pixel"\n',
        encoding="utf-8",
    )
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "board.sfx.toml").write_text(
        '[effect.pop]\ngenerator = "pickup"\nseed = 7\n', encoding="utf-8"
    )
    sfx.synth("audio/board.sfx.toml", root=str(tmp_path))
    (tmp_path / "vfx").mkdir()
    (tmp_path / "vfx" / "trails.vfx.toml").write_text(
        "[effect.sparks]\namount = 64\nlifetime = 0.8\nsize = 0.2\n", encoding="utf-8"
    )
    vfx.build("vfx/trails.vfx.toml", root=str(tmp_path))
    (tmp_path / "music").mkdir()
    (tmp_path / "music" / "theme.music.toml").write_text(
        '[music]\ntitle = "Theme"\n', encoding="utf-8"
    )
    record(
        tmp_path,
        "sound",
        "audio/theme.ogg",
        inputs=[("score", "music/theme.music.toml")],
        engine={"name": "music.render"},
    )
    record(tmp_path, "picture", "art/icon.png")

    pop = brief.brief("audio/pop.wav", root=str(tmp_path))["declaration"]
    assert pop["effect"] == "pop"
    assert pop["table"]["generator"] == "pickup"
    sparks = brief.brief("vfx/sparks.tscn", root=str(tmp_path))["declaration"]
    assert sparks["effect"] == "sparks"
    assert sparks["table"]["amount"] == 64
    assert sparks["measures"]
    theme = brief.brief("audio/theme.ogg", root=str(tmp_path))["declaration"]
    assert theme["valid"] is False
    assert theme["problems"]
    icon = brief.brief("art/icon.png", root=str(tmp_path))["declaration"]
    assert icon["family"] == "default"
    assert icon["palette"] == ["#112233", "#ffeedd"]
    assert icon["filter"] == "pixel"
