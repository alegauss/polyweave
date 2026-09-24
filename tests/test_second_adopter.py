"""A second adopter, while the config boundary is cheap to move (§PW117).

`tests/fixtures/website.toml` is a project unlike Cottony: a web page with no engine,
two rungs, a smaller ladder and a scale kept in TypeScript. What it found inside the
plugin is asserted here, so it stays fixed: a project without the sphere rung was
refused any material question, and a typed C-family constant could not be read.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from polyweave import accept, config, render, search, units

FIXTURE = Path(__file__).parent / "fixtures" / "website.toml"


@pytest.fixture
def website(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "src" / "lib").mkdir(parents=True)
    (tmp_path / "src" / "lib" / "scale.ts").write_text(
        "// how many CSS pixels one metre of a model takes on the page\n"
        "export const PIXELS_PER_METRE: number = 48;\n",
        encoding="utf-8",
    )
    return tmp_path


def test_it_loads_with_no_unknown_key_and_says_no_engine(website):
    found = config.load(website)
    assert found.get("project.name") == "website"
    assert found.get("capture.declared") == []


def test_its_scale_is_read_from_typescript(website):
    assert units.engine_scale(website)["pixels_per_unit"] == 48.0


@pytest.mark.parametrize(
    "line",
    [
        "public const int CELL = 112;",
        "static readonly float CELL = 112;",
        "constexpr int CELL = 112;",
        "const CELL: u32 = 112;",
    ],
)
def test_a_typed_constant_in_another_language_is_read(tmp_path, line):
    (tmp_path / "Board.cs").write_text(f"class Board {{ {line} }}\n", encoding="utf-8")
    assert units.read_number("Board.cs:CELL", root=tmp_path) == 112.0


def test_a_material_question_goes_to_the_lowest_rung_it_enables(website):
    """It has no sphere, so the preview answers it rather than a refusal."""
    chosen = render.plan(asking=["saturation_p99"], root=website)
    assert chosen["rung"] == "preview"
    assert "sphere being one this project does not enable" in chosen["why"]
    assert chosen["samples"] == 16


def test_a_question_nothing_enabled_can_carry_is_still_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[render]\nrungs = ["sphere"]\n', encoding="utf-8"
    )
    from polyweave.errors import PolyweaveError

    with pytest.raises(PolyweaveError) as refused:
        render.plan(asking=["silhouette_iou"], root=tmp_path)
    assert refused.value.code == "render.rung-disabled"


def test_a_search_over_a_material_takes_the_preview_too(website):
    spec = accept.parse(
        {
            "asset": "hero",
            "predicate": [
                {"id": "vivid", "measure": "saturation_p99", "min": 0.5},
            ],
            "search": {"exposure": {"min": -1.0, "max": 1.0}},
        }
    )
    asked = []

    def bake(report, **how):
        asked.append(how["rung"])
        raise StopIteration

    evaluate = search.renderer(spec, out="r.png", root=website, bake=bake)
    with pytest.raises(StopIteration):
        evaluate({"exposure": 0.0})
    assert asked == ["preview"]


def test_no_palette_or_path_of_cottony_reaches_it():
    text = FIXTURE.read_text(encoding="utf-8")
    assert re.findall(r"#[0-9A-Fa-f]{3,8}\b", text) == []
    assert "cottony" not in text.lower().replace("unlike cottony", "")
