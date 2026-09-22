"""§4 of the tool surface: the surface describes itself.

The measure §PW3 sets is whether a caller can get a call right without opening the file
that implements it, so every test here asks only what `describe` returned.
"""

from __future__ import annotations

from typing import Annotated

import pytest

from polyweave import describe as D
from polyweave.errors import PolyweaveError


@pytest.fixture(autouse=True)
def clean_registry():
    """Each test registers into an empty surface and leaves one behind."""
    saved = dict(D._REGISTRY)
    D._REGISTRY.clear()
    yield
    D._REGISTRY.clear()
    D._REGISTRY.update(saved)


def a_rig():
    @D.operation("render.bake", produces="render", kind="bake", injects=("report",))
    def bake(
        report,
        model: Annotated[str, D.Param("which model to render")],
        size: Annotated[
            int, D.Param("square edge of the image", lo=16, hi=4096, unit="px")
        ] = 512,
        rung: Annotated[
            str, D.Param("which preview level", choices=("sphere", "preview", "final"))
        ] = "preview",
    ) -> str:
        """Render one model on the project's rig.

        A second paragraph, which is not the summary.
        """
        return f"{model}@{size}"

    return bake


# -- what describe returns -----------------------------------------------------


def test_describe_answers_the_whole_parameter_set():
    a_rig()
    found = D.describe("render.bake")
    assert found["summary"] == "Render one model on the project's rig."
    assert found["produces"] == "render"
    assert found["asynchronous"] is True
    names = [p["name"] for p in found["parameters"]]
    assert names == ["model", "size", "rung"]


def test_every_parameter_carries_type_default_range_and_a_sentence():
    a_rig()
    size = next(
        p for p in D.describe("render.bake")["parameters"] if p["name"] == "size"
    )
    assert size["type"] == "int"
    assert size["required"] is False
    assert size["default"] == 512
    assert size["range"] == [16, 4096]
    assert size["unit"] == "px"
    assert size["about"] == "square edge of the image"


def test_a_required_parameter_says_so():
    a_rig()
    model = next(
        p for p in D.describe("render.bake")["parameters"] if p["name"] == "model"
    )
    assert model["required"] is True
    assert model["default"] is None


def test_choices_are_listed_rather_than_described():
    a_rig()
    rung = next(
        p for p in D.describe("render.bake")["parameters"] if p["name"] == "rung"
    )
    assert rung["choices"] == ["sphere", "preview", "final"]


def test_what_the_harness_supplies_is_not_described():
    """`report` is the job's, not the caller's, so a caller never sees it."""
    a_rig()
    assert "report" not in [p["name"] for p in D.describe("render.bake")["parameters"]]


def test_describe_with_no_argument_lists_the_surface():
    a_rig()
    assert D.operations() == ["render.bake"]
    assert [o["operation"] for o in D.describe()] == ["render.bake"]


def test_an_unknown_operation_says_how_to_find_the_real_ones():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.describe("render.bkae")
    assert caught.value.code == "op.unknown"
    assert "describe()" in caught.value.remedy


# -- the description cannot drift ----------------------------------------------


def test_a_parameter_with_no_sentence_is_refused_at_registration():
    with pytest.raises(PolyweaveError) as caught:

        @D.operation("render.bare")
        def bare(size: int = 512) -> None:
            """Render something."""

    assert caught.value.code == "op.unannotated"
    assert "size" in caught.value.message


def test_an_undocumented_operation_is_refused():
    with pytest.raises(PolyweaveError) as caught:

        @D.operation("render.mute")
        def mute() -> None:
            pass

    assert caught.value.code == "op.undocumented"


def test_an_open_signature_cannot_be_described():
    with pytest.raises(PolyweaveError) as caught:

        @D.operation("render.loose")
        def loose(**kw) -> None:
            """Take anything at all."""

    assert caught.value.code == "op.open-signature"


def test_two_operations_cannot_share_a_name():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:

        @D.operation("render.bake")
        def other() -> None:
            """Also bake."""

    assert caught.value.code == "op.duplicate"


def test_the_description_follows_the_signature_it_was_read_from():
    """Rename the parameter and the description renames with it; nothing to update."""

    @D.operation("render.one")
    def one(
        samples: Annotated[int, D.Param("path-tracer samples", lo=1)] = 64,
    ) -> None:
        """Render once."""

    assert D.describe("render.one")["parameters"][0]["name"] == "samples"

    D._REGISTRY.clear()

    @D.operation("render.one")
    def one_renamed(
        spp: Annotated[int, D.Param("path-tracer samples", lo=1)] = 64,
    ) -> None:
        """Render once."""

    assert D.describe("render.one")["parameters"][0]["name"] == "spp"


# -- a declared range is enforced ----------------------------------------------


def test_validate_fills_the_defaults_it_described():
    a_rig()
    assert D.validate("render.bake", {"model": "mascot"}) == {
        "model": "mascot",
        "size": 512,
        "rung": "preview",
    }


def test_a_value_outside_the_declared_range_is_refused():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.bake", {"model": "m", "size": 8192})
    assert caught.value.code == "op.out-of-range"
    assert "16 to 4096" in caught.value.message


def test_a_value_outside_the_declared_choices_is_refused():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.bake", {"model": "m", "rung": "draft"})
    assert caught.value.code == "op.bad-choice"
    assert "sphere" in caught.value.remedy


def test_an_unknown_argument_is_refused_and_the_real_ones_named():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.bake", {"model": "m", "sixe": 512})
    assert caught.value.code == "op.unknown-argument"
    assert "size" in caught.value.remedy


def test_a_missing_required_argument_names_itself():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.bake", {})
    assert caught.value.code == "op.missing-argument"
    assert "model=…" in caught.value.remedy


def test_a_range_refuses_a_value_that_is_not_a_number():
    a_rig()
    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.bake", {"model": "m", "size": "512"})
    assert caught.value.code == "op.bad-type"


def test_a_one_sided_range_says_which_side():
    @D.operation("render.open")
    def at_least(
        samples: Annotated[int, D.Param("samples per pixel", lo=1)] = 64,
    ) -> None:
        """Render with at least one sample."""

    with pytest.raises(PolyweaveError) as caught:
        D.validate("render.open", {"samples": 0})
    assert "at least 1" in caught.value.message
