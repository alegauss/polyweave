"""A bound's room measured from the noise, never chosen by eye (§PW107)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import accept, calibrate, provenance, render, search
from polyweave import config as C
from polyweave.errors import PolyweaveError


def star(tmp_path, name, *, body=100, tail=200):
    """Nine tenths of the frame at `body` and the last tenth at `tail`.

    So the median reads the body and the 99th percentile reads the tail, and a variant
    can move one without the other: the whole of why one margin rule cannot fit both.
    """
    pixels = np.full((20, 20, 4), 255, np.uint8)
    pixels[..., :3] = body
    pixels[18:, :, :3] = tail
    where = tmp_path / name
    Image.fromarray(pixels, "RGBA").save(where)
    return where


def spec(**bounds):
    body = bounds.pop("body", 0.5)
    tail = bounds.pop("tail", 0.9)
    return accept.parse(
        {
            "asset": "star",
            "predicate": [
                {"id": "body", "measure": "luma_p50", "region": "frame", "max": body},
                {"id": "tail", "measure": "luma_p99", "region": "frame", "max": tail},
            ],
        }
    )


def test_a_tail_gets_more_room_than_a_median_under_the_same_changes(tmp_path):
    accepted = star(tmp_path, "a.png")
    variants = {
        "seed 1": star(tmp_path, "b.png", tail=190),
        "seed 2": star(tmp_path, "c.png", tail=210),
    }
    found = calibrate.propose(spec(), accepted, variants, root=tmp_path)
    body, tail = found["predicates"]
    assert body["spread"] == 0.0
    assert tail["spread"] > 0.0
    assert body["bounds"][0]["new"] == pytest.approx(body["accepted"], abs=1e-4)
    room = tail["bounds"][0]["new"] - tail["accepted"]
    assert room == pytest.approx(3.0 * tail["spread"], abs=1e-4)
    assert found["multiple"] == 3.0
    assert found["apply"]["tail"]["max"]["origin"] == "measured"
    assert found["apply"]["tail"]["max"]["spread"] == tail["spread"]


def test_a_min_is_placed_below_the_accepted_value(tmp_path):
    parsed = accept.parse(
        {
            "asset": "star",
            "predicate": [
                {"id": "tail", "measure": "luma_p99", "region": "frame", "min": 0.1}
            ],
        }
    )
    found = calibrate.propose(
        parsed,
        star(tmp_path, "a.png"),
        {"seed 1": star(tmp_path, "b.png", tail=190)},
        root=tmp_path,
    )
    (one,) = found["predicates"]
    assert one["bounds"][0]["new"] < one["accepted"]


def test_a_persons_bound_is_left_alone(tmp_path):
    agreed = spec(tail={"value": 0.9, "origin": "person", "date": "2026-09-24"})
    found = calibrate.propose(
        agreed,
        star(tmp_path, "a.png"),
        {"seed 1": star(tmp_path, "b.png", tail=190)},
        root=tmp_path,
    )
    tail = found["predicates"][1]["bounds"][0]
    assert "new" not in tail
    assert "outranks a statistic" in tail["kept"]
    assert "tail" not in found["apply"]


def test_one_picture_is_not_a_measure_of_noise(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        calibrate.propose(spec(), star(tmp_path, "a.png"), {}, root=tmp_path)
    assert refused.value.code == "spec.no-variants"


# -- the request, read back and varied -------------------------------------------------


def recorded(tmp_path, **fields):
    picture = star(tmp_path, "accepted.png")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "star.glb").write_bytes(b"glb")
    record = provenance.build(
        "render",
        picture,
        inputs=[provenance.source("mesh", "assets/star.glb", root=tmp_path)],
        params={"azimuth": 0.0, "exposure": 0.5, "lights": "per radius²", **fields},
        rung="preview",
        seed=11,
        samples=64,
        root=tmp_path,
    )
    provenance.write(record, root=tmp_path)
    return picture


def test_a_record_reads_back_as_the_bake_that_made_it(tmp_path):
    picture = recorded(tmp_path, material={"base_color": "#FFC43F"})
    request = calibrate.request_of(provenance.read(picture, root=tmp_path))
    assert request == {
        "azimuth": 0.0,
        "exposure": 0.5,
        "material": {"base_color": "#FFC43F"},
        "model": "assets/star.glb",
        "rung": "preview",
        "seed": 11,
        "samples": 64,
    }


def test_the_harmless_changes_are_seed_samples_and_size(tmp_path):
    changes = calibrate.variations(
        {"rung": "preview", "seed": 11, "samples": 64}, 256, root=tmp_path
    )
    assert [c["change"] for c in changes] == [
        {"seed": 12},
        {"seed": 13},
        {"samples": 32},
        {"size": 224},
        {"size": 288},
    ]


def test_the_sphere_has_no_rung_below_it(tmp_path):
    changes = calibrate.variations({"rung": "sphere", "seed": 0}, 64, root=tmp_path)
    assert not any("samples" in c["change"] for c in changes)


def test_a_rectangle_steps_its_scale_not_its_size(tmp_path):
    changes = calibrate.variations(
        {"rung": "final", "covers": [2, 1], "pixels_per_unit": 64.0}, 128, root=tmp_path
    )
    assert {"pixels_per_unit": 56.0} in [c["change"] for c in changes]
    assert not any("size" in c["change"] for c in changes)


def test_calibrating_renders_each_change_and_proposes(tmp_path):
    picture = recorded(tmp_path)
    asked = []

    def draw(request, where):
        asked.append(request)
        star(where.parent, where.name, tail=200 + 5 * len(asked))

    found = calibrate.calibrate(spec(), picture, root=tmp_path, draw=draw)
    assert len(asked) == len(found["changes"]) == 5
    assert all(r["model"] == "assets/star.glb" for r in asked)
    assert asked[0]["seed"] == 12 and asked[2]["samples"] == 32
    assert found["accepted"] == "accepted.png"
    assert found["predicates"][1]["spread"] > 0.0
    work = C.load(tmp_path).path("paths.work") / "calibrate" / "star"
    assert len(list(work.glob("accepted-*.png"))) == 5


# -- applying: a separate call, and never silent ---------------------------------------

WRITTEN = """asset = "star"

# the star as a person saw it
[[predicate]]
id      = "body"
measure = "luma_p50"
region  = "frame"
max     = 0.5   # put by eye

[[predicate]]
id      = "tail"
measure = "luma_p99"
region  = "frame"
max     = { value = 0.9, origin = "person", date = "2026-09-24" }
"""


def proposal(old=0.5):
    return {
        "apply": {
            "body": {
                "max": {
                    "value": 0.1344,
                    "origin": "measured",
                    "measured": 0.1329,
                    "spread": 0.0005,
                    "old": old,
                }
            },
            "tail": {
                "max": {
                    "value": 0.99,
                    "origin": "measured",
                    "measured": 0.5,
                    "spread": 0.1,
                    "old": 0.9,
                }
            },
        }
    }


def test_applying_rewrites_the_bound_and_keeps_the_rest(tmp_path):
    where = tmp_path / "star.accept.toml"
    where.write_text(WRITTEN, encoding="utf-8")
    done = calibrate.apply(where, proposal())
    assert done["written"] == ["body:max"]
    assert done["kept"] == ["tail:max"]
    after = where.read_text(encoding="utf-8")
    assert "# the star as a person saw it" in after
    assert 'max     = { value = 0.1344, origin = "measured"' in after
    body, tail = accept.read(where).predicates
    assert body.maximum == 0.1344
    assert body.origins["max"] == {
        "origin": "measured",
        "measured": 0.1329,
        "spread": 0.0005,
    }
    assert tail.origins["max"]["origin"] == "person"


def test_a_bound_that_moved_since_the_proposal_is_refused(tmp_path):
    where = tmp_path / "star.accept.toml"
    where.write_text(WRITTEN, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        calibrate.apply(where, proposal(old=0.45))
    assert refused.value.code == "spec.stale-proposal"
    assert where.read_text(encoding="utf-8") == WRITTEN


def test_a_bound_over_several_lines_is_refused_rather_than_mangled(tmp_path):
    where = tmp_path / "star.accept.toml"
    where.write_text(
        WRITTEN.replace(
            "max     = 0.5   # put by eye",
            '[predicate.max]\nvalue = 0.5\norigin = "margin"',
        ),
        encoding="utf-8",
    )
    before = where.read_text(encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        calibrate.apply(where, {"apply": {"body": proposal()["apply"]["body"]}})
    assert refused.value.code == "spec.unwritable-bound"
    assert where.read_text(encoding="utf-8") == before


def test_a_measured_miss_says_how_noisy_the_measure_was(tmp_path):
    measured = spec(body={"value": 0.01, "origin": "measured", "spread": 0.002})
    found = accept.check(measured, star(tmp_path, "a.png"), root=tmp_path)
    assert "with 0.002 of noise" in found["predicates"][0]["why"]


# -- what a search may not turn --------------------------------------------------------


@pytest.mark.parametrize("axis", ["seed", "samples", "size"])
def test_a_search_may_not_turn_the_noise(axis):
    def draw(**kwargs):
        return {}

    with pytest.raises(PolyweaveError) as refused:
        search.turnable(draw, {axis: {"min": 0, "max": 4}})
    assert refused.value.code == "search.noise-axis"


def test_a_size_beside_a_rectangle_is_refused(tmp_path):
    class Quiet:
        def stage(self, stage, *, progress=None, note=None):
            return None

    with pytest.raises(PolyweaveError) as refused:
        render.bake(
            Quiet(),
            out="x.png",
            rung="sphere",
            covers=[2, 2],
            size=64,
            root=str(tmp_path),
        )
    assert refused.value.code == "render.size-with-covers"


def test_a_real_calibration_on_the_sphere_rung(tmp_path):
    """Against Blender: the variants really are rendered, at the size and seed asked."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 48\n"
        "samples = { sphere = 4, preview = 4, final = 8 }\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, stage, *, progress=None, note=None):
            return None

    render.bake(Quiet(), out="accepted.png", rung="sphere", inline=False, root=tmp_path)
    parsed = accept.parse(
        {
            "asset": "ball",
            "predicate": [
                {"id": "body", "measure": "luma_p50", "region": "subject", "max": 1.0},
                {"id": "tail", "measure": "luma_p99", "region": "subject", "max": 1.0},
            ],
        }
    )
    found = calibrate.calibrate(parsed, "accepted.png", root=tmp_path)
    assert found["varied"] == [
        "one step larger",
        "one step smaller",
        "seed 1",
        "seed 2",
    ]
    for one in found["predicates"]:
        assert one["spread"] >= 0.0
        assert one["bounds"][0]["new"] >= one["accepted"]
    work = C.load(tmp_path).path("paths.work") / "calibrate" / "ball"
    with Image.open(work / "accepted-3.png") as larger:
        assert larger.size == (54, 54)
