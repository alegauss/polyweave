"""A shape stated as data, rather than as a program that produces one.

§PW30's case: Cottony's tray, star, ball and props are four modules of imperative
geometry code, and the shape each describes is not readable without running it.

The document under test is the tray from `docs/specs/geometry.md`, because a format
whose own spec's example does not parse is a format nobody can write against.
"""

from __future__ import annotations

import pytest

from polyweave import geometry as G
from polyweave.errors import PolyweaveError

TRAY = """
name    = "board_tray"
version = 1
output  = "tray"

[params]
cell       = 112
board      = 8
pad        = 16
face_depth = 6.0
seat_depth = 4.0
bevel      = 2.0

[materials.cushion]
colour    = "#F2E4D0"
roughness = 0.62

[[nodes]]
id       = "face"
op       = "plate"
material = "cushion"
rect     = ["0", "0", "board * cell + pad * 2", "board * cell + pad * 2"]
depth    = "face_depth"
corner   = 28

[[nodes]]
id      = "seat"
op      = "prism"
outline = { shape = "rounded_square", size = "cell * 0.82", corner = 18 }
depth   = "seat_depth"
at      = ["pad + col * cell + cell / 2", "pad + row * cell + cell / 2", "0"]
repeat  = [
  { var = "row", from = 0, to = "board - 1" },
  { var = "col", from = 0, to = "board - 1" },
]

[[nodes]]
id     = "tray"
op     = "carve"
into   = "face"
cutter = "seat"
bevel  = "bevel"
"""


def tray(tmp_path, body=TRAY, name="tray.toml"):
    (tmp_path / name).write_text(body, encoding="utf-8")
    return G.read(name, root=tmp_path)


# -- the expressions, which are one of the three things ------------------------------


@pytest.mark.parametrize(
    ("source", "wanted"),
    [
        ("2 + 3", 5.0),
        ("cell * 0.82", 91.84),
        ("board - 1", 7.0),
        ("(pad + cell) / 2", 64.0),
        ("cell % 100", 12.0),
        ("-pad", -16.0),
        ("max(pad, cell)", 112.0),
        ("round(cell * 0.82)", 92.0),
        ("floor(cell / 10)", 11.0),
        ("sqrt(board * 2)", 4.0),
        ("28", 28.0),
    ],
)
def test_the_grammar_evaluates_what_it_says_it_does(source, wanted):
    assert G.evaluate(source, {"cell": 112, "board": 8, "pad": 16}) == pytest.approx(
        wanted
    )


def test_a_number_passes_straight_through():
    """A document writing `corner = 28` means 28, and quoting it would be ceremony."""
    assert G.evaluate(28, {}) == 28.0
    assert G.evaluate(6.0, {}) == 6.0


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('echo')",
        "open('secret')",
        "cell.__class__",
        "[cell for cell in range(3)]",
        "lambda: 1",
        "cell if pad else board",
        "cell > pad",
        "'a string'",
        "cell[0]",
    ],
)
def test_nothing_evaluates_arbitrary_code(source):
    """A determinism requirement before a security one: a value that can depend on
    anything but its parameters breaks the cache key."""
    with pytest.raises(PolyweaveError) as caught:
        G.evaluate(source, {"cell": 112, "pad": 16, "board": 8})
    assert caught.value.code == "geom.bad-expression"


def test_a_name_nothing_declared_says_what_is_in_scope():
    with pytest.raises(PolyweaveError) as caught:
        G.evaluate("cel * 2", {"cell": 112})
    assert caught.value.code == "geom.unknown-name"
    assert "cell" in caught.value.remedy


def test_dividing_by_a_parameter_that_came_out_zero_is_named():
    with pytest.raises(PolyweaveError) as caught:
        G.evaluate("cell / gap", {"cell": 112, "gap": 0})
    assert caught.value.code == "geom.bad-expression"
    assert "divides by zero" in caught.value.message


def test_where_it_went_wrong_is_in_the_message():
    with pytest.raises(PolyweaveError) as caught:
        G.evaluate("nope", {}, where="seat.depth")
    assert "seat.depth" in caught.value.message


def test_an_array_of_expressions_comes_back_as_numbers():
    found = G.numbers(["0", "pad * 2", "cell"], {"pad": 16, "cell": 112})
    assert found == [0.0, 32.0, 112.0]


def test_which_names_an_expression_reads_is_read_off_the_tree():
    """By the tree and not by matching text, so `pad` is not found inside `padding`."""
    assert G.mentions("padding * 2") == {"padding"}
    assert G.mentions("pad + cell") == {"pad", "cell"}
    assert G.mentions("round(cell)") == {"cell"}, "a function name is not a parameter"


# -- the document ----------------------------------------------------------------------


def test_the_spec_s_own_tray_parses(tmp_path):
    """A format whose own example does not parse is one nobody writes against."""
    found = tray(tmp_path)
    assert found["name"] == "board_tray"
    assert [node["id"] for node in found["nodes"]] == ["face", "seat", "tray"]
    assert found["output"] == "tray"
    assert found["materials"]["cushion"]["roughness"] == 0.62


def test_a_node_names_the_nodes_it_takes(tmp_path):
    found = tray(tmp_path)
    carve = next(n for n in found["nodes"] if n["id"] == "tray")
    assert sorted(G.refers_to(carve)) == ["face", "seat"]


def test_the_output_defaults_to_the_last_node(tmp_path):
    found = tray(tmp_path, TRAY.replace('output  = "tray"\n', ""))
    assert found["output"] == "tray"


def test_a_file_that_is_toml_and_is_not_a_shape_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, 'name = "empty"\n')
    assert caught.value.code == "geom.malformed"


def test_a_hand_edit_that_broke_the_syntax_says_where(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, 'name = "broken\n')
    assert caught.value.code == "geom.unreadable"
    assert caught.value.detail


def test_two_nodes_with_one_id_make_every_reference_ambiguous(tmp_path):
    body = TRAY.replace('id       = "face"', 'id       = "seat"')
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, body)
    assert caught.value.code == "geom.duplicate-id"


def test_a_node_pointing_at_nothing_is_refused(tmp_path):
    body = TRAY.replace('into   = "face"', 'into   = "fase"')
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, body)
    assert caught.value.code == "geom.unknown-node"
    assert "face" in caught.value.remedy


def test_an_output_naming_nothing_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, TRAY.replace('output  = "tray"', 'output  = "trey"'))
    assert caught.value.code == "geom.unknown-node"


def test_an_output_written_below_the_nodes_is_named_rather_than_misread(tmp_path):
    """TOML puts a bare key after a table header inside that table, so an output
    written there would quietly become the last node's own field."""
    body = TRAY.replace('output  = "tray"\n', "") + '\noutput = "tray"\n'
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, body)
    assert caught.value.code == "geom.malformed"
    assert "above the first [[nodes]]" in caught.value.remedy


def test_nodes_that_refer_to_each_other_in_a_circle_are_refused(tmp_path):
    body = TRAY.replace('cutter = "seat"', 'cutter = "tray"')
    with pytest.raises(PolyweaveError) as caught:
        tray(tmp_path, body)
    assert caught.value.code == "geom.cycle"
    assert "tray" in caught.value.message


# -- repeat, which is the third of the three things ------------------------------------


def test_a_repeated_node_becomes_one_instance_per_point(tmp_path):
    found = G.expand(tray(tmp_path))
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    assert len(seat["instances"]) == 64, "eight rows by eight columns"


def test_the_repeat_variables_are_in_scope_for_that_node(tmp_path):
    found = G.expand(tray(tmp_path))
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    # pad + col * cell + cell / 2, at col = 0 and col = 7.
    assert seat["instances"][0]["at"][0] == pytest.approx(16 + 0 + 56)
    assert seat["instances"][-1]["at"][0] == pytest.approx(16 + 7 * 112 + 56)


def test_to_is_inclusive_because_board_minus_one_means_the_last_row(tmp_path):
    found = G.expand(tray(tmp_path))
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    assert seat["over"][0]["values"] == [0, 1, 2, 3, 4, 5, 6, 7]


def test_a_repeated_node_s_id_names_the_whole_set(tmp_path):
    """Which is what makes the tray one boolean rather than sixty-four."""
    found = G.expand(tray(tmp_path))
    carve = next(node for node in found["nodes"] if node["id"] == "tray")
    assert carve["refers_to"] == ["face", "seat"]
    assert len(carve["instances"]) == 1


def test_a_node_that_repeats_over_nothing_is_one_instance(tmp_path):
    found = G.expand(tray(tmp_path))
    face = next(node for node in found["nodes"] if node["id"] == "face")
    assert len(face["instances"]) == 1
    assert face["over"] == []


def test_a_step_can_be_asked_for(tmp_path):
    body = TRAY.replace(
        '{ var = "row", from = 0, to = "board - 1" },',
        '{ var = "row", from = 0, to = "board - 1", step = 2 },',
    )
    found = G.expand(tray(tmp_path, body))
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    assert seat["over"][0]["values"] == [0, 2, 4, 6]


def test_a_step_of_zero_is_a_loop_that_never_ends(tmp_path):
    body = TRAY.replace(
        '{ var = "row", from = 0, to = "board - 1" },',
        '{ var = "row", from = 0, to = "board - 1", step = 0 },',
    )
    with pytest.raises(PolyweaveError) as caught:
        G.expand(tray(tmp_path, body))
    assert caught.value.code == "geom.bad-repeat"


def test_a_range_with_no_variable_is_not_a_range(tmp_path):
    body = TRAY.replace('{ var = "row", from = 0, to = "board - 1" },', "{ from = 0 },")
    with pytest.raises(PolyweaveError) as caught:
        G.expand(tray(tmp_path, body))
    assert caught.value.code == "geom.bad-repeat"


def test_a_repeat_variable_is_not_in_scope_on_another_node(tmp_path):
    """It resolves as text rather than as arithmetic, and the review says so.

    A value is arithmetic only where **every** name in it is in scope, because
    `art/star.png` parses as a division and evaluating an image path would break a
    working document. That leaves a typo looking like a name, so it is a warning.
    """
    from polyweave.geometry import review

    body = TRAY.replace('depth    = "face_depth"', 'depth    = "face_depth + row"')
    document = tray(tmp_path, body)
    assert G.expand(document)["nodes"][0]["instances"][0]["depth"] == "face_depth + row"
    assert any("over row" in one for one in review.warn(document))


# -- resolving -------------------------------------------------------------------------


def test_every_expression_is_a_number_once_expanded(tmp_path):
    found = G.expand(tray(tmp_path))
    face = next(node for node in found["nodes"] if node["id"] == "face")["instances"][0]
    assert face["rect"] == [0.0, 0.0, 928.0, 928.0]
    assert face["depth"] == 6.0
    assert face["corner"] == 28.0


def test_a_word_stays_a_word_and_is_not_arithmetic(tmp_path):
    """`shape = "rounded_square"` is a name; the vocabulary reads it, not this."""
    found = G.expand(tray(tmp_path))
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    assert seat["instances"][0]["outline"]["shape"] == "rounded_square"
    assert seat["instances"][0]["outline"]["size"] == pytest.approx(91.84)


def test_a_parameter_can_be_overridden_at_the_call(tmp_path):
    found = G.expand(tray(tmp_path), board=2)
    seat = next(node for node in found["nodes"] if node["id"] == "seat")
    assert len(seat["instances"]) == 4
    assert found["params"]["board"] == 2


def test_the_material_stays_on_the_node(tmp_path):
    found = G.expand(tray(tmp_path))
    face = next(node for node in found["nodes"] if node["id"] == "face")
    assert face["material"] == "cushion"


# -- what a change costs ---------------------------------------------------------------


def test_a_parameter_change_rebuilds_what_reads_it_and_what_is_downstream(tmp_path):
    """The search needs this: rebuilding geometry costs more than re-rendering it."""
    found = tray(tmp_path)
    assert G.rebuilds(found, "seat_depth") == ["seat", "tray"]


def test_a_parameter_only_one_node_reads_still_rebuilds_the_output(tmp_path):
    found = tray(tmp_path)
    assert G.rebuilds(found, "face_depth") == ["face", "tray"]


def test_a_parameter_everything_reads_rebuilds_everything(tmp_path):
    found = tray(tmp_path)
    assert G.rebuilds(found, "cell") == ["face", "seat", "tray"]


def test_a_parameter_nothing_reads_rebuilds_nothing(tmp_path):
    found = tray(tmp_path)
    assert G.rebuilds(found, "unused") == []


def test_a_parameter_read_only_in_a_repeat_range_still_counts(tmp_path):
    found = tray(tmp_path)
    assert "seat" in G.rebuilds(found, "board")


def test_the_build_order_puts_every_input_before_what_needs_it(tmp_path):
    found = tray(tmp_path)
    order = G.order(found)
    assert order.index("face") < order.index("tray")
    assert order.index("seat") < order.index("tray")


# -- a surface declared over the same parameters a shape is (§PW50) --------------------


def fuzzy(tmp_path, depth='"fluff_depth"', coarseness='"fluff_coarseness"'):
    body = TRAY.replace(
        "[materials.cushion]",
        f"[materials.cushion]\nfuzz      = "
        f"{{ depth = {depth}, coarseness = {coarseness} }}",
    ).replace("bevel      = 2.0", "bevel      = 2.0\nfluff_depth = 3.0\n"
              "fluff_coarseness = 0.62")
    return tray(tmp_path, body)


def test_a_material_s_own_values_resolve_like_a_node_s(tmp_path):
    """Otherwise a surface declared over the parameters is not searchable at all."""
    found = G.expand(fuzzy(tmp_path))
    assert found["materials"]["cushion"]["fuzz"] == {"depth": 3.0, "coarseness": 0.62}


def test_a_material_s_colour_is_a_name_and_not_arithmetic(tmp_path):
    """The all-or-nothing rule reaches the materials table too."""
    found = G.expand(fuzzy(tmp_path))
    assert found["materials"]["cushion"]["colour"] == "#F2E4D0"


def test_turning_a_surface_s_parameter_rebuilds_whatever_wears_it(tmp_path):
    """A search told that nothing rebuilds would sample the shape it already had."""
    found = fuzzy(tmp_path)
    assert G.rebuilds(found, "fluff_coarseness") == ["face", "tray"]


def test_a_node_in_no_material_is_not_rebuilt_by_one(tmp_path):
    found = fuzzy(tmp_path)
    assert "seat" not in G.rebuilds(found, "fluff_depth")


def test_which_parameters_each_material_reads_is_answerable(tmp_path):
    assert G.coats(fuzzy(tmp_path)) == {
        "cushion": {"fluff_depth", "fluff_coarseness"}
    }
