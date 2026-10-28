"""A kit of built pieces taken to a sitting in one call (§PW568)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import kit as K


class Report:
    def stage(self, stage, *, progress=None, note=None):
        return None

    def progress(self, value, *, note=None):
        return None

    def note(self, text):
        return None


def piece(folder, name: str, kind: str) -> None:
    (folder / f"{name}.toml").write_text(
        f'name = "{name}"\nversion = 1\noutput = "{name}"\n\n'
        f'[[nodes]]\nid = "{name}"\nop = "primitive"\nkind = "{kind}"\n'
        "size = [1, 1, 2]\n",
        encoding="utf-8")


def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    pieces = tmp_path / "pieces"
    pieces.mkdir()
    piece(pieces, "post", "capsule")
    piece(pieces, "block", "cube")
    return pieces


def test_a_kit_is_built_rendered_specced_checked_and_sat_in_one_call(tmp_path):
    pytest.importorskip("bpy")
    project(tmp_path)
    found = K.kit(Report(), "pieces", out="built", root=str(tmp_path),
                  bounds={"sharp_edge_share": {"max": 0.02}})
    assert set(found["pieces"]) == {"post", "block"}
    # the box is all creases, the capsule none, and the spec says which
    assert found["pieces"]["post"]["passed"] is True
    assert found["pieces"]["block"]["passed"] is False
    assert found["passed"] is False
    assert sorted(found["specs_written"]) == ["docs/accept/block.accept.toml",
                                              "docs/accept/post.accept.toml"]
    written = (tmp_path / "docs/accept/post.accept.toml").read_text(encoding="utf-8")
    assert 'measure = "triangles"' in written and "sharp_edge_share" in written
    assert (tmp_path / "docs/renders/post.png").is_file()
    sat = json.loads((tmp_path / found["sitting"]).read_text(encoding="utf-8"))
    assert sat, "the kit is laid out as one sitting"
    assert found["page"].startswith("/?sitting=")
    assert "block" in found["says"]


def test_a_spec_already_written_is_the_projects_and_is_left_alone(tmp_path):
    pytest.importorskip("bpy")
    project(tmp_path)
    mine = tmp_path / "docs/accept/block.accept.toml"
    mine.parent.mkdir(parents=True)
    text = ('asset = "block"\n\n[[predicate]]\nid = "budget"\nmeasure = "triangles"\n'
            'of = "built/block.glb"\nmax = 100\n')
    mine.write_text(text, encoding="utf-8")
    found = K.kit(Report(), "pieces", out="built", root=str(tmp_path),
                  bounds={"sharp_edge_share": 0.02})
    assert found["specs_written"] == ["docs/accept/post.accept.toml"]
    assert mine.read_text(encoding="utf-8") == text
    assert found["pieces"]["block"]["passed"] is True


def test_a_first_spec_allows_its_headroom_over_the_triangles():
    text = K._first_spec("post", "built/post.glb", "docs/renders/post.png", 100, 0.25,
                         {"sharp_edge_share": {"max": 0.02}})
    assert 'max     = { value = 125, origin = "margin", measured = 100 }' in text
    assert "max     = 0.02" in text


@pytest.mark.parametrize("bounds", [{"sharp_edge_share": "low"},
                                    {"sharp_edge_share": {"under": 1}}])
def test_a_bound_that_is_not_a_min_or_a_max_is_refused(bounds):
    with pytest.raises(PolyweaveError) as refused:
        K._bounds(bounds)
    assert refused.value.code == "geom.bad-kit"


def test_a_folder_with_no_declarations_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    (tmp_path / "empty").mkdir()
    with pytest.raises(PolyweaveError) as refused:
        K.kit(Report(), "empty", root=str(tmp_path))
    assert refused.value.code == "geom.bad-kit"
