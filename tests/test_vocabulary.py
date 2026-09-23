"""The geometry vocabulary, read off the scripts that exist.

§PW31's case: a format covering only cubes and spheres would leave every real asset in
code, so the list comes from what Cottony's models are actually made of — and the one
that matters most is an outline traced from a drawing and extruded, because that is how
a star's silhouette becomes a mesh that *is* the drawn sprite.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave.errors import PolyweaveError
from polyweave.geometry import outline as O
from polyweave.geometry import solid as S
from polyweave.post.mesh import check_mesh


def drawn(where, mask):
    canvas = np.zeros((*mask.shape, 4), dtype=np.uint8)
    canvas[mask] = (200, 90, 60, 255)
    PILImage.fromarray(canvas, "RGBA").save(where)
    return where


# -- the generators, against their own arithmetic ------------------------------------


def test_a_circle_encloses_pi_r_squared():
    assert O.area(O.circle(2.0, steps=512)) == pytest.approx(math.pi * 4, rel=1e-4)


def test_a_square_encloses_its_own_sides():
    assert O.area(O.rounded_square(10.0)) == pytest.approx(100.0)
    assert O.area(O.rounded_square((10.0, 4.0))) == pytest.approx(40.0)


def test_rounding_a_corner_takes_area_off_it():
    assert O.area(O.rounded_square(10.0, 3.0)) < 100.0
    assert O.area(O.rounded_square(10.0, 3.0)) > 80.0


def test_a_corner_bigger_than_the_shape_becomes_a_circle():
    ring = O.rounded_square(10.0, 99.0)
    assert O.area(ring) == pytest.approx(math.pi * 25, rel=0.02)


def test_a_star_has_two_points_per_arm():
    assert len(O.star(5, 10, 4)) == 10


def test_a_star_is_concave_and_a_circle_is_not():
    """The whole reason the solid has to know: a concave cap needs triangles."""
    assert O.convex(O.star(5, 10, 4)) is False
    assert O.convex(O.circle(3.0)) is True
    assert O.convex(O.rounded_square(4.0, 1.0)) is True


def test_a_star_of_one_point_is_not_a_star():
    with pytest.raises(PolyweaveError) as caught:
        O.star(1, 10, 4)
    assert caught.value.code == "geom.bad-outline"


def test_a_lobed_shape_waves_between_two_radii():
    ring = O.lobed(6, 10.0, 2.0, steps=240)
    radii = np.linalg.norm(ring, axis=1)
    assert radii.max() == pytest.approx(12.0, abs=0.01)
    assert radii.min() == pytest.approx(8.0, abs=0.01)


def test_a_radial_array_states_one_petal_and_gets_six(tmp_path):
    petal = [[3, -1], [6, 0], [3, 1]]
    assert len(O.radial(petal, steps=6)) == 18


def test_growing_an_outline_moves_its_corners_by_the_miter():
    """A unit step along the bisector would grow a ten-unit square to 11.4, not 12."""
    assert O.area(O.offset(O.rounded_square(10.0), 1.0)) == pytest.approx(144.0)
    assert O.area(O.offset(O.rounded_square(10.0), -1.0)) == pytest.approx(64.0)


def test_growing_a_circle_grows_its_radius():
    grown = O.offset(O.circle(2.0, steps=256), 1.0)
    assert O.area(grown) == pytest.approx(math.pi * 9, rel=1e-3)


def test_a_generator_nothing_has_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        O.generate("hexagram", radius=2)
    assert caught.value.code == "geom.unknown-shape"
    assert "circle" in caught.value.remedy


# -- the one traced from a drawing ----------------------------------------------------


def test_a_drawn_rectangle_traces_back_to_a_rectangle(tmp_path):
    mask = np.zeros((32, 32), dtype=bool)
    mask[8:24, 6:26] = True
    ring = O.simplify(O.trace(mask), 1.0)
    assert len(ring) == 4, "four corners, not four hundred pixels"
    low_x, low_y, high_x, high_y = O.bounds(ring)
    assert high_x - low_x == pytest.approx(19.0)
    assert high_y - low_y == pytest.approx(15.0)


def test_tracing_keeps_a_concave_shape_concave(tmp_path):
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:30, 10:30] = True
    mask[10:20, 20:30] = False  # a bite out of one corner
    ring = O.simplify(O.trace(mask), 1.0)
    assert O.convex(ring) is False


def test_a_drawing_becomes_an_outline_at_a_stated_size(tmp_path):
    mask = np.zeros((32, 32), dtype=bool)
    mask[8:24, 8:24] = True
    ring = O.image(drawn(tmp_path / "s.png", mask), size=4.0)
    assert float(np.ptp(ring, axis=0).max()) == pytest.approx(4.0)


def test_the_traced_outline_is_not_mirrored(tmp_path):
    """An image counts rows downward and §6 counts y upward."""
    mask = np.zeros((32, 32), dtype=bool)
    mask[4:12, 4:28] = True  # a bar near the top of the picture
    ring = O.image(drawn(tmp_path / "top.png", mask))
    assert ring[:, 1].mean() == pytest.approx(0.0, abs=1.0)
    # The bar is wide and short, and stays that way.
    assert np.ptp(ring[:, 0]) > np.ptp(ring[:, 1])


def test_a_drawing_with_nothing_in_it_traces_nothing(tmp_path):
    mask = np.zeros((16, 16), dtype=bool)
    with pytest.raises(PolyweaveError) as caught:
        O.image(drawn(tmp_path / "empty.png", mask))
    assert caught.value.code == "geom.nothing-to-trace"


def test_simplifying_drops_the_points_that_sit_on_a_line():
    ring = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [3, 3], [0, 3]], dtype=float)
    assert len(O.simplify(ring, 0.01)) == 4


# -- what the declaration asked for ----------------------------------------------------


def test_a_shape_by_name_resolves(tmp_path):
    ring = O.resolve({"shape": "rounded_square", "size": 10, "corner": 2})
    assert O.area(ring) == pytest.approx(O.area(O.rounded_square(10, 2)))


def test_an_image_resolves(tmp_path):
    mask = np.zeros((32, 32), dtype=bool)
    mask[8:24, 8:24] = True
    where = drawn(tmp_path / "s.png", mask)
    ring = O.resolve({"image": str(where), "size": 2.0}, root=tmp_path)
    assert float(np.ptp(ring, axis=0).max()) == pytest.approx(2.0)


def test_points_resolve_as_themselves():
    assert len(O.resolve([[0, 0], [1, 0], [1, 1]])) == 3


def test_an_offset_wraps_whatever_it_was_given():
    ring = O.resolve({"shape": "rounded_square", "size": 10, "offset": 1.0})
    assert O.area(ring) == pytest.approx(144.0)


def test_a_radial_wraps_whatever_it_was_given():
    ring = O.resolve({"points": [[3, -1], [6, 0], [3, 1]], "radial": 4})
    assert len(ring) == 12


def test_a_mapping_naming_no_outline_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        O.resolve({"depth": 2})
    assert caught.value.code == "geom.bad-outline"


# -- the solids ------------------------------------------------------------------------


def test_a_prism_is_an_outline_swept_back():
    found = check_mesh(S.prism(O.rounded_square(10.0, 2.0), 3.0))
    low, high = found["bounds"]
    assert high[0] - low[0] == pytest.approx(10.0)
    assert high[2] - low[2] == pytest.approx(3.0), "the depth runs along z"


def test_a_convex_cap_stays_one_face():
    found = check_mesh(S.prism(O.rounded_square(10.0), 2.0))
    assert found["faces"] == 4 + 2, "four walls and two caps"


def test_a_concave_cap_is_triangulated(tmp_path):
    """Cottony's first star came back with black triangles laid across its arms."""
    star = S.prism(O.star(5, 10.0, 4.0), 2.0)
    found = check_mesh(star)
    assert found["faces"] > 10 + 2, "the caps were cut into triangles"
    assert all(len(face) == 3 for face in star["faces"][10:])


def test_the_triangulated_cap_covers_the_whole_outline():
    """Every vertex of the star is in some cap triangle, or an arm has no face on it."""
    ring = O.star(6, 10.0, 3.0)
    star = S.prism(ring, 1.0)
    caps = [face for face in star["faces"] if len(face) == 3]
    covered = {index for face in caps for index in face if index < len(ring)}
    assert covered == set(range(len(ring)))


def test_a_plate_is_stated_where_it_sits():
    found = check_mesh(S.plate([4.0, 2.0, 10.0, 6.0], 1.0, 1.0))
    low, high = found["bounds"]
    assert low[0] == pytest.approx(4.0)
    assert low[1] == pytest.approx(2.0)
    assert high[0] == pytest.approx(14.0)


def test_a_crowned_plate_is_taller_than_a_flat_one():
    flat = check_mesh(S.prism(O.circle(5.0, steps=24), 2.0))["bounds"]
    domed = check_mesh(S.crowned(O.circle(5.0, steps=24), 2.0, 3.0))["bounds"]
    assert domed[1][2] - domed[0][2] == pytest.approx(5.0)
    assert flat[1][2] - flat[0][2] == pytest.approx(2.0)


def test_the_dome_leaves_the_silhouette_alone():
    """Only the face swells; the outline of the plate is untouched."""
    flat = check_mesh(S.prism(O.circle(5.0, steps=24), 2.0))["bounds"]
    domed = check_mesh(S.crowned(O.circle(5.0, steps=24), 2.0, 3.0))["bounds"]
    assert domed[0][0] == pytest.approx(flat[0][0])
    assert domed[1][0] == pytest.approx(flat[1][0])


def test_an_annulus_is_a_ring_between_two_radii():
    found = check_mesh(S.annulus(5.0, 3.0, 2.0, steps=24))
    low, high = found["bounds"]
    assert high[0] - low[0] == pytest.approx(10.0, rel=0.02)
    assert found["faces"] == 24 * 4, "two walls and two caps, all the way round"


def test_an_annulus_with_no_ring_in_it_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        S.annulus(3.0, 5.0, 1.0)
    assert caught.value.code == "geom.bad-solid"


@pytest.mark.parametrize("kind", ["cube", "plane", "cylinder", "sphere"])
def test_every_primitive_builds_a_mesh(kind):
    found = check_mesh(S.primitive(kind, 2.0))
    assert found["faces"] >= 1
    assert found["vertices"] >= 3


def test_a_primitive_is_the_size_it_was_asked_for():
    low, high = check_mesh(S.primitive("sphere", 3.0))["bounds"]
    assert high[1] - low[1] == pytest.approx(3.0)


def test_a_primitive_nothing_has_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        S.primitive("torus")
    assert caught.value.code == "geom.unknown-shape"


# -- putting them together -------------------------------------------------------------


def test_a_transform_scales_then_rotates_then_places():
    found = check_mesh(S.transform(S.primitive("cube", 2.0), scale=2.0, at=(10, 0, 0)))
    low, high = found["bounds"]
    assert high[0] - low[0] == pytest.approx(4.0)
    assert (low[0] + high[0]) / 2 == pytest.approx(10.0)


def test_a_rotation_turns_the_mesh():
    tall = S.transform(S.primitive("cube", 1.0), scale=(1, 4, 1))
    laid = S.transform(tall, rotate=(0, 0, 90))
    low, high = check_mesh(laid)["bounds"]
    assert high[0] - low[0] == pytest.approx(4.0)
    assert high[1] - low[1] == pytest.approx(1.0)


def test_a_union_keeps_every_part(tmp_path):
    one = check_mesh(S.primitive("cube", 1.0))
    both = check_mesh(S.union(S.primitive("cube", 1.0), S.primitive("cube", 1.0)))
    assert both["faces"] == one["faces"] * 2
    assert both["vertices"] == one["vertices"] * 2


def test_a_union_moves_each_part_s_faces_onto_its_own_vertices():
    both = S.union(
        S.primitive("cube", 1.0), S.transform(S.primitive("cube", 1.0), at=(5, 0, 0))
    )
    assert max(max(face) for face in both["faces"]) == len(both["vertices"]) - 1


def test_a_union_of_nothing_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        S.union()
    assert caught.value.code == "geom.bad-solid"


# -- the headline case: a drawn sprite, extruded ---------------------------------------


def test_a_drawn_star_becomes_the_drawn_star_extruded(tmp_path):
    """Not merely similar to the sprite. The sprite, with a depth."""
    mask = np.zeros((64, 64), dtype=bool)
    ring = O.star(5, 28.0, 11.0, rotation=90) + 32
    for y in range(64):
        for x in range(64):
            mask[y, x] = _inside(ring, (x, y))

    traced = O.image(drawn(tmp_path / "star.png", mask), size=10.0)
    built = S.prism(traced, 2.0)
    found = check_mesh(built)

    assert O.convex(traced) is False, "a star traced off a drawing is still a star"
    assert float(np.ptp(traced, axis=0).max()) == pytest.approx(10.0)
    assert found["faces"] > len(traced), "walls and a triangulated cap"
    low, high = found["bounds"]
    assert high[2] - low[2] == pytest.approx(2.0)


def _inside(ring, point) -> bool:
    x, y = point
    crossings = 0
    for index in range(len(ring)):
        one, two = ring[index], ring[(index + 1) % len(ring)]
        if (one[1] > y) != (two[1] > y):
            at = one[0] + (y - one[1]) / (two[1] - one[1]) * (two[0] - one[0])
            crossings += at > x
    return crossings % 2 == 1


# -- a drawing given volume ------------------------------------------------------------


def test_inflating_a_panel_keeps_its_silhouette_to_the_point(tmp_path):
    """A cushion made from a traced drawing still has the drawn outline."""
    ring = O.rounded_square(10.0, 2.0)
    found = check_mesh(S.inflate(ring, 4.0, resolution=16))
    low, high = found["bounds"]
    assert high[0] - low[0] == pytest.approx(10.0)
    assert high[1] - low[1] == pytest.approx(10.0)


def test_and_gives_it_the_thickness_it_was_asked_for():
    found = check_mesh(S.inflate(O.circle(5.0, steps=24), 4.0, resolution=16))
    low, high = found["bounds"]
    assert high[2] - low[2] == pytest.approx(4.0)


def test_a_cushion_swells_in_the_middle_and_not_at_the_edge():
    """Which is what makes it look stuffed rather than extruded."""
    ring = O.circle(5.0, steps=24)
    points = np.asarray(S.inflate(ring, 4.0, resolution=16)["vertices"])
    # The outline's own vertices come first, and every one of them is on the silhouette.
    assert np.abs(points[: len(ring), 2]).max() < 1e-9, (
        "the outline stays at zero depth"
    )
    assert np.allclose(points[: len(ring), :2], ring), "and exactly where it was"
    middle = points[np.linalg.norm(points[:, :2], axis=1) < 1.0]
    assert np.abs(middle[:, 2]).max() > 1.5


def test_a_star_inflates_into_a_star_shaped_cushion():
    built = S.inflate(O.star(5, 10.0, 4.0), 3.0, resolution=16)
    found = check_mesh(built)
    low, high = found["bounds"]
    assert high[2] - low[2] == pytest.approx(3.0)
    assert found["faces"] > 20


def test_an_outline_with_no_width_has_nothing_to_inflate():
    with pytest.raises(PolyweaveError) as caught:
        S.inflate([[0, 0], [0, 0.0000001], [0, 0]], 1.0)
    assert caught.value.code in ("geom.bad-solid", "geom.bad-outline")


# -- the two that need a solver --------------------------------------------------------


def solving():
    from polyweave.geometry import solver

    found = solver.available()
    if not found["ready"]:
        pytest.skip(found["why"])
    return solver


def test_a_carve_cuts_a_pocket_and_says_what_it_cost():
    solver = solving()
    plate = S.plate([0, 0, 20, 20], 4.0, 2.0)
    seat = S.transform(S.prism(O.circle(3.0, steps=16), 10.0), at=(10, 10, -2))
    found = solver.carve(plate, seat)
    assert found["after"] > found["before"], "a pocket adds faces"
    assert found["solver"] == "MANIFOLD"
    check_mesh(found)


def test_a_carve_that_returned_nothing_is_refused_rather_than_returned():
    """An empty boolean raises nothing on its own, which is why §PW2 asked for this."""
    solver = solving()
    plate = S.plate([0, 0, 10, 10], 2.0)
    swallowing = S.plate([-10, -10, 40, 40], 20.0, front=-8.0)
    with pytest.raises(PolyweaveError) as caught:
        solver.carve(plate, swallowing)
    assert caught.value.code == "post.boolean-empty"
    assert "assertion" in caught.value.remedy


def test_a_bevel_softens_every_edge():
    solver = solving()
    before = check_mesh(S.primitive("cube", 4.0))
    after = check_mesh(solver.bevel(S.primitive("cube", 4.0), 0.4))
    assert after["faces"] > before["faces"]
    low, high = after["bounds"]
    assert high[0] - low[0] == pytest.approx(4.0, abs=0.01), "a bevel cuts in, not out"


def test_a_build_carves_before_it_bevels():
    """A cut against an already-bevelled object is the case that went empty."""
    solver = solving()
    plate = S.plate([0, 0, 20, 20], 4.0, 2.0)
    seat = S.transform(S.prism(O.circle(3.0, steps=16), 10.0), at=(10, 10, -2))
    found = check_mesh(solver.build(plate, cutter=seat, bevel_by=0.4))
    assert found["faces"] > 56, "the bevel ran after the cut, on the cut result"


def test_a_build_with_neither_is_the_mesh_it_was_given():
    solver = solving()
    plate = S.plate([0, 0, 20, 20], 4.0, 2.0)
    assert check_mesh(solver.build(plate))["faces"] == check_mesh(plate)["faces"]


# -- one key naming two things (§PW64) -------------------------------------------------


def test_a_generator_is_given_the_points_count_the_document_wrote():
    """`points` names a kind of outline and a generator's own argument.

    Stripped unconditionally, `{ shape = "star", points = 5 }` reached `star()` without
    a count and was refused for missing the argument the declaration plainly supplied.
    """
    ring = O.resolve({"shape": "star", "points": 5, "outer": 240.0, "inner": 120.0})
    assert len(ring) == 10, "two points per arm"
    assert O.convex(ring) is False


def test_a_literal_list_of_points_is_still_a_list_of_points():
    """The other branch, which is the reason the key was reserved in the first place."""
    ring = O.resolve({"points": [[0, 0], [10, 0], [5, 8]]})
    assert len(ring) == 3


def test_a_shape_that_takes_no_points_is_unaffected():
    ring = O.resolve({"shape": "circle", "radius": 3.0, "steps": 12})
    assert len(ring) == 12


def test_a_generator_given_an_argument_it_does_not_take_still_refuses():
    """The refusal that was firing for the wrong reason has to keep firing."""
    with pytest.raises(PolyweaveError) as caught:
        O.resolve({"shape": "circle", "radius": 3.0, "arms": 5})
    assert caught.value.code == "geom.unknown-shape"
