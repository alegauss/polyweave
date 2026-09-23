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


# -- a ring between two edges rather than two radii (§PW65) ----------------------------


def test_a_ring_between_two_radii_is_what_it_always_was():
    """The narrower form still means what it meant, and is still a circle."""
    ring = S.annulus(10.0, 4.0, 2.0)
    check_mesh(ring)
    points = np.asarray(ring["vertices"], dtype=float)
    assert np.ptp(points[:, 0]) == pytest.approx(20.0, rel=1e-3)


def test_a_rim_between_two_rounded_rectangles_is_a_ring_too():
    """Cottony's tray rim: a rounded rectangle with the same one offset inside it."""
    outer = O.rounded_square(100.0, 20.0)
    rim = S.annulus(outer, O.offset(outer, -18.0), 60.0)
    check_mesh(rim)
    points = np.asarray(rim["vertices"], dtype=float)
    # A ring and not a slab: it keeps the outline's silhouette exactly, and the hole in
    # the middle is why it is not a cream lid over the whole tray.
    assert points[:, 0].min() == pytest.approx(-50.0)
    assert points[:, 0].max() == pytest.approx(50.0)
    assert not np.any(np.all(np.abs(points[:, :2]) < 20.0, axis=1)), "it has a hole"


def test_two_edges_that_do_not_correspond_are_refused_rather_than_twisted():
    """An inner edge is an `offset` of the outer, which keeps its count and order."""
    with pytest.raises(PolyweaveError) as caught:
        S.annulus(O.circle(10.0, steps=32), O.circle(4.0, steps=12), 2.0)
    assert caught.value.code == "geom.bad-solid"
    assert "offset" in caught.value.remedy


def test_an_inner_edge_that_is_not_inside_has_no_ring_between_them():
    outer = O.rounded_square(100.0, 20.0)
    with pytest.raises(PolyweaveError) as caught:
        S.annulus(outer, O.offset(outer, 10.0), 60.0)
    assert caught.value.code == "geom.bad-solid"
    assert "no ring between them" in caught.value.message


def test_a_radius_that_is_not_inside_still_says_so():
    with pytest.raises(PolyweaveError) as caught:
        S.annulus(4.0, 10.0, 2.0)
    assert caught.value.code == "geom.bad-solid"


# -- the dome keeps the silhouette it was given (§PW66) --------------------------------


@pytest.mark.parametrize(
    ("named", "ring"),
    [
        ("a star", O.star(5, 240.64, 120.32)),
        ("a rounded square", O.rounded_square(100.0, 10.0)),
        ("a circle", O.circle(40.0)),
        ("a lobed shape", O.lobed(6, 30.0, 0.35)),
    ],
)
def test_a_crown_never_reaches_outside_the_outline_it_domes(named, ring):
    """The op's own promise: the silhouette is untouched and only the face swells.

    It was kept on a convex outline and broken on a concave one. `offset` moves a corner
    along its miter, which points inward at a convex corner and outward at a reflex one,
    so a star's inner vertices travelled outward while the ring was supposed to shrink.
    """
    made = S.crowned(ring, 51.2, 66.56)
    points = np.asarray(made["vertices"], dtype=float)
    assert points[:, 0].min() == pytest.approx(ring[:, 0].min()), named
    assert points[:, 0].max() == pytest.approx(ring[:, 0].max()), named
    assert points[:, 1].min() == pytest.approx(ring[:, 1].min()), named
    assert points[:, 1].max() == pytest.approx(ring[:, 1].max()), named


def test_a_convex_crown_still_shrinks_along_its_miter():
    """Which is what holds a corner radius constant, and what nothing should move."""
    ring = O.rounded_square(100.0, 10.0)
    made = S.crowned(ring, 10.0, 15.0)
    points = np.asarray(made["vertices"], dtype=float)
    assert np.ptp(points[:, 2]) == pytest.approx(25.0), "depth plus crown"
    assert O.convex(ring) is True


def test_every_ring_of_a_concave_dome_is_inside_the_one_below_it():
    """Which is what scaling toward the centroid gives and offsetting does not."""
    ring = O.star(5, 240.64, 120.32)
    made = S.crowned(ring, 51.2, 66.56)
    points = np.asarray(made["vertices"], dtype=float)
    rings = points.reshape(-1, len(ring), 3)
    reach = [
        float(np.linalg.norm(one[:, :2] - one[:, :2].mean(axis=0), axis=1).max())
        for one in rings
    ]
    assert reach == sorted(reach, reverse=True), "each ring is no wider than the last"
    assert reach[-1] < reach[0], "and the dome actually closes"


# -- where a picture goes on a shape (§PW68) -------------------------------------------


def test_a_stuffed_panel_says_where_its_drawing_lies():
    """The drawing that gave the panel its outline is the picture on its face."""
    ring = O.rounded_square(20.0, 4.0)
    panel = S.inflate(ring, 6.0)
    assert len(panel["uv"]) == len(panel["vertices"]), "one pair per vertex"
    # Over the ring's own bounds, so the outline touches 0 and 1 on each axis.
    assert panel["uv"].min() == pytest.approx(0.0)
    assert panel["uv"].max() == pytest.approx(1.0)
    check_mesh(panel)


def test_most_meshes_carry_no_coordinates_at_all():
    """Absent rather than zeroed: a mesh with zeros claims a corner for every face."""
    assert "uv" not in S.primitive("cube", 2.0)
    assert "uv" not in S.prism(O.circle(3.0), 2.0)
    assert "uv" not in S.annulus(10.0, 4.0, 2.0)


def test_moving_a_panel_leaves_its_picture_where_it_was():
    """A transform reorders nothing, so the coordinates come through untouched."""
    panel = S.inflate(O.rounded_square(20.0, 4.0), 6.0)
    moved = S.transform(panel, at=[100, 0, 0], rotate=[0, 40, 0])
    assert np.allclose(moved["uv"], panel["uv"])


def test_joining_two_panels_keeps_both_pictures():
    panel = S.inflate(O.rounded_square(20.0, 4.0), 6.0)
    joined = S.union(panel, S.transform(panel, at=[50, 0, 0]))
    assert len(joined["uv"]) == len(joined["vertices"])


def test_joining_a_panel_to_something_with_none_keeps_none():
    """All of them or none: filling the other part with zeros would place it wrongly."""
    panel = S.inflate(O.rounded_square(20.0, 4.0), 6.0)
    assert "uv" not in S.union(panel, S.primitive("cube", 2.0))


def test_a_projection_can_be_told_the_frame_the_drawing_came_in():
    """A shape smaller than the canvas it was drawn on sits where it was drawn."""
    made = S.prism(O.rounded_square(10.0), 1.0)
    # Ten wide, centred, in a frame forty across: it occupies the middle quarter.
    uv = S.planar_uv(made["vertices"], [-20.0, -20.0, 40.0, 40.0])
    assert uv.min() == pytest.approx(0.375)
    assert uv.max() == pytest.approx(0.625)


def test_coordinates_that_do_not_line_up_are_refused():
    """An array one short puts the picture on the wrong part of the shape after that."""
    panel = S.inflate(O.rounded_square(20.0, 4.0), 6.0)
    with pytest.raises(PolyweaveError) as caught:
        check_mesh({**panel, "uv": panel["uv"][:-1]})
    assert caught.value.code == "post.uv-mismatched"
    assert "one pair per vertex" in caught.value.remedy


def test_coordinates_that_are_not_numbers_are_refused():
    panel = S.inflate(O.rounded_square(20.0, 4.0), 6.0)
    broken = panel["uv"].copy()
    broken[0, 0] = np.nan
    with pytest.raises(PolyweaveError) as caught:
        check_mesh({**panel, "uv": broken})
    assert caught.value.code == "post.uv-mismatched"


# -- the second profile, read off the alpha rather than the outline (§PW68) ------------


def ring_drawing(size=128, outer=50, inner=18):
    """A blob with a hole in it: the case where the two profiles disagree."""
    yy, xx = np.mgrid[0:size, 0:size]
    far = (xx - size // 2) ** 2 + (yy - size // 2) ** 2
    alpha = np.zeros((size, size), dtype=float)
    alpha[far < outer**2] = 1.0
    alpha[far < inner**2] = 0.0
    return alpha


def test_a_stuffed_drawing_is_shaped_by_what_is_inside_it():
    """Which is the whole difference from inflate, and the reason for a second rule.

    `inflate` knows only where the shape stops, so it swells toward the middle whatever
    is there. This blurs the alpha, so a hole in the drawing is a hole in the surface.
    """
    made = S.stuffed(ring_drawing(), 10.0, size=100.0)
    check_mesh(made)
    points = np.asarray(made["vertices"], dtype=float)
    middle = points[np.argmin(np.hypot(points[:, 0], points[:, 1]))]
    assert middle[2] == pytest.approx(0.0, abs=0.01), "the hole did not fill in"
    assert points[:, 2].max() == pytest.approx(10.0, rel=0.02), "and the ring rose"


def test_a_stuffed_drawing_comes_out_at_the_size_it_was_asked_for():
    made = S.stuffed(ring_drawing(), 10.0, size=100.0)
    points = np.asarray(made["vertices"], dtype=float)
    assert np.ptp(points[:, 0]) == pytest.approx(100.0, rel=0.02)
    assert np.ptp(points[:, 1]) == pytest.approx(100.0, rel=0.02)


def test_a_stuffed_drawing_wears_the_drawing_that_shaped_it():
    made = S.stuffed(ring_drawing(), 10.0, size=100.0)
    assert len(made["uv"]) == len(made["vertices"])
    assert made["uv"].min() == pytest.approx(0.0)
    assert made["uv"].max() == pytest.approx(1.0)


def test_the_faintest_tail_of_a_shadow_is_not_built():
    """Built down to it, the panel showed a pale rectangle the size of the canvas."""
    alpha = ring_drawing()
    alpha[alpha == 0.0] = 0.004  # a shadow far below the floor, over the whole canvas
    made = S.stuffed(alpha, 10.0, size=100.0, floor=0.02)
    whole = S.stuffed(alpha, 10.0, size=100.0, floor=0.0)
    assert len(made["faces"]) < len(whole["faces"])


def _at_full_height(made, thickness=10.0):
    """How much of the mesh sits at the top, which is how flat the face reads."""
    points = np.asarray(made["vertices"], dtype=float)
    return float((points[:, 2] > thickness * 0.9).mean())


def test_a_tight_blur_only_rounds_the_rim():
    """Cottony's reading: at 0.10 and 0.06 the cushion read as the flat card it was.

    Measured on a disc half the canvas across: at 0.06 nearly a third of the mesh is
    within a tenth of full height — a flat top with a narrow fall-off at the edge —
    against a tenth of it at 0.20, where the fall-off is spread across the face.
    """
    size = 128
    yy, xx = np.mgrid[0:size, 0:size]
    disc = ((xx - 64) ** 2 + (yy - 64) ** 2 < 50**2).astype(float)
    tight = S.stuffed(disc, 10.0, size=100.0, soften=0.06)
    domed = S.stuffed(disc, 10.0, size=100.0, soften=0.20)
    assert _at_full_height(tight) > _at_full_height(domed) * 2

    # And a blur wider than the shape flattens it again, because the field it samples is
    # near-uniform inside before it is normalised. Worth knowing rather than hiding: the
    # useful range is bounded at both ends, and `soften` is a share of the shorter side.
    flooded = S.stuffed(disc, 10.0, size=100.0, soften=0.40)
    assert _at_full_height(flooded) > _at_full_height(domed)


def test_a_drawing_with_nothing_solid_in_it_has_no_body_to_stuff():
    with pytest.raises(PolyweaveError) as caught:
        S.stuffed(np.full((64, 64), 0.2), 10.0)
    assert caught.value.code == "geom.bad-solid"
    assert "no body" in caught.value.message


def test_something_that_is_not_a_drawing_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        S.stuffed(np.zeros((8, 8, 4)), 10.0)
    assert caught.value.code == "geom.bad-solid"
