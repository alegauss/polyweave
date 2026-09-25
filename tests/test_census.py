"""What of the package a caller can find without reading it (§PW124)."""

from __future__ import annotations

from polyweave import census, describe, errors, measure
from polyweave.capabilities import capabilities

#: How much surface is still unregistered. Registering a module lowers it, and this
#: number is lowered with it: it may only fall, never rise.
PENDING = 0


def test_every_public_function_is_classified():
    found = census.census()
    assert found["unclassified"] == [], (
        "register these with @operation, or add their module to census.MODULES with "
        "the reason it is internal or pending"
    )


def test_no_entry_or_module_is_listed_that_no_longer_needs_to_be():
    names = census.public()
    registered = {op.target for op in describe._REGISTRY.values()}
    stale_entries = sorted(set(census.ENTRY) - set(names))
    live_modules = set(names.values())
    listed_functions = [key for key in census.MODULES if ":" in key]
    listed_modules = [key for key in census.MODULES if ":" not in key]
    stale_functions = sorted(
        key for key in listed_functions if key not in names or key in registered
    )
    stale_modules = sorted(set(listed_modules) - live_modules)
    wholly_registered = sorted(
        module
        for module in listed_modules
        if module in live_modules
        and all(
            target in registered or target in census.ENTRY or target in census.MODULES
            for target, owner in names.items()
            if owner == module
        )
    )
    assert stale_entries == []
    assert stale_functions == [], "these are gone or registered; take them off"
    assert stale_modules == []
    assert wholly_registered == [], "take these off census.MODULES: nothing is left"


def test_the_pending_surface_only_shrinks():
    pending = len(census.census()["pending"])
    assert pending <= PENDING, "surface was added unregistered; register it instead"
    assert pending == PENDING, f"it shrank to {pending}: lower PENDING to match"


def test_everything_capabilities_names_is_one_read_away():
    """The first read names it, and one more read says what it is."""
    found = capabilities(probe=False)
    for one in found["operations"]:
        assert describe.describe(one["operation"])["summary"]
    for code in found["errors"]["codes"]:
        assert errors.explain(code)["means"]
    for area in found["errors"]["areas"]:
        assert errors.codes(area)
    for name in found["measures"]["names"]:
        assert measure.resolve(name)
    assert set(found["unregistered"]) == set(census.pending_modules())
    assert "polyweave.search" not in found["unregistered"]
    assert all(module.startswith("polyweave") for module in found["unregistered"])


def test_a_spec_is_checked_by_name_with_nothing_but_paths(tmp_path):
    """accept is registered: an agent reaches it from describe, with JSON arguments."""
    from PIL import Image

    (tmp_path / "star.accept.toml").write_text(
        "asset = 'star'\n[[predicate]]\nid = 'tone'\nmeasure = 'luma_p99'\n"
        "region = 'frame'\nmax = 0.37\n",
        encoding="utf-8",
    )
    Image.new("RGBA", (8, 8), (102, 102, 102, 255)).save(tmp_path / "star.png")
    args = describe.validate(
        "accept.check",
        {"spec": "star.accept.toml", "subject": "star.png", "root": str(tmp_path)},
    )
    target = describe._REGISTRY["accept.check"].fn
    assert target(**args)["passed"] is True
    assert {"accept.check", "accept.verify", "accept.check_screen"} <= set(
        describe.operations()
    )


def test_a_search_is_described_as_a_job_with_its_budget_bounded():
    found = describe.describe("search.sweep")
    assert found["asynchronous"] is True
    budget = next(p for p in found["parameters"] if p["name"] == "budget")
    assert budget["range"] == [1, None]
    assert describe._REGISTRY["search.worth_parallel"].fn(11.44) is True


def test_calibrate_apply_by_name_never_overrules_a_persons_bound(tmp_path):
    (tmp_path / "s.accept.toml").write_text(
        "asset = 's'\n[[predicate]]\nid = 'tone'\nmeasure = 'luma_p99'\n"
        "max = { value = 0.4, origin = 'person', date = '2026-09-24' }\n",
        encoding="utf-8",
    )
    names = {p["name"] for p in describe.describe("calibrate.apply")["parameters"]}
    assert "person" not in names
    proposal = {
        "apply": {
            "tone": {
                "max": {
                    "value": 0.3,
                    "origin": "measured",
                    "measured": 0.29,
                    "spread": 0.001,
                    "old": 0.4,
                }
            }
        }
    }
    done = describe._REGISTRY["calibrate.apply"].fn(
        "s.accept.toml", proposal, root=str(tmp_path)
    )
    assert done["kept"] == ["tone:max"]


def test_a_ledger_run_is_driven_by_name_with_the_run_as_json(tmp_path):
    import json

    def call(name, **args):
        fn = describe._REGISTRY[name].fn
        answer = fn(**describe.validate(name, args))
        return json.loads(json.dumps(answer))  # what a caller over a wire gets

    root = str(tmp_path)
    for way, seconds in (("before", 9.0), ("after", 3.0)):
        run = call("loop.start", asset="star", way=way, root=root)
        run = call("loop.spent", run=run, seconds=seconds)
        run = call("loop.judged", run=run, tool_passed=True, person_accepted=True)
        call("loop.finish", run=run, root=root)
    assert "faster" in call("loop.compare", asset="star", root=root)["verdict"]
    assert call("loop.assets", root=root) == ["star"]


def test_a_measure_is_taken_by_name_with_its_arguments_declared(tmp_path):
    from PIL import Image

    Image.new("RGBA", (8, 8), (230, 40, 40, 255)).save(tmp_path / "board.png")
    args = describe.validate(
        "measure.take",
        {
            "subject": "board.png",
            "measures": ["delta_e"],
            "target": "#E62828",
            "root": str(tmp_path),
        },
    )
    (one,) = describe._REGISTRY["measure.take"].fn(**args)
    assert one["measure"] == "delta_e" and one["value"] < 1.0
    names = {p["name"] for p in describe.describe("measure.take")["parameters"]}
    assert {"target", "against", "display", "delta"} <= names


def test_a_declaration_is_described_and_built_by_name(tmp_path):
    (tmp_path / "box.toml").write_text(
        'name = "box"\noutput = "box"\n\n[params]\nsize = 4\n\n[voxels]\ncell = 1\n\n'
        '[[nodes]]\nid = "box"\nop = "primitive"\nkind = "cube"\nsize = "size"\n',
        encoding="utf-8",
    )
    root = str(tmp_path)
    said = describe._REGISTRY["geometry.describe"].fn("box.toml", root=root)
    assert said["reads"]
    built = describe._REGISTRY["geometry.build"].fn(
        "box.toml", root=root, given={"size": 2}
    )
    assert built["status"] == "built"
    assert built["says"].startswith("a voxel model 2 by 2 by 2")
    assert describe._REGISTRY["geometry.variants"].fn("box.toml", root=root) == []


def test_the_budget_is_asked_by_name_with_a_date_as_text(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[budget]\ncredits = 50\nexpires = "2026-12-31"\n', encoding="utf-8"
    )
    import pytest

    from polyweave.errors import PolyweaveError

    fn = describe._REGISTRY["purchase.allow"].fn
    root = str(tmp_path)
    assert fn(20.0, root=root, today="2026-09-24")["left"] == 50
    with pytest.raises(PolyweaveError) as refused:
        fn(20.0, root=root, today="2027-01-02")
    assert refused.value.code == "fetch.budget-closed"


def test_the_engine_side_is_described_without_its_test_hooks():
    for name, hook in (("engine.run", "launch"), ("capture.run", "take")):
        names = {p["name"] for p in describe.describe(name)["parameters"]}
        assert hook not in names
        assert "expect" in names
    assert describe.describe("capture.run")["asynchronous"] is True


def test_a_declared_choice_is_the_modules_own_list():
    """A choice typed out beside the code drifts; these are read off it."""
    from polyweave import compose, normalise

    def choices(op, name):
        found = describe.describe(op)["parameters"]
        return next(p for p in found if p["name"] == name)["choices"]

    assert choices("compose.place", "anchor") == list(compose.ANCHORS)
    assert choices("normalise.ingest", "size_on") == list(normalise.SIZE_ON)
    assert choices("normalise.ingest", "origin") == list(normalise.ORIGINS)


def test_a_sheet_is_laid_out_by_name_and_says_where_it_landed(tmp_path):
    from PIL import Image

    for n in range(3):
        Image.new("RGBA", (8, 8), (40 * n, 90, 90, 255)).save(tmp_path / f"{n}.png")
    made = describe._REGISTRY["compose.sheet"].fn(
        [str(tmp_path / f"{n}.png") for n in range(3)],
        out=str(tmp_path / "sheet.png"),
        cell=16,
    )
    assert (tmp_path / "sheet.png").is_file()
    assert made["size"][0] >= 16


def test_a_clip_is_authored_by_name_and_round_trips_as_json(tmp_path):
    import json

    def call(operation, **args):
        fn = describe._REGISTRY[operation].fn
        return json.loads(json.dumps(fn(**describe.validate(operation, args))))

    root = str(tmp_path)
    made = call(
        "clip.new",
        name="settle",
        duration=0.5,
        channels={"spine": {"scale": [[0.0, [1, 1, 1]], [0.5, [1, 0.93, 1]]]}},
    )
    keyed = call(
        "clip.set_key",
        subject=made,
        joint="spine",
        prop="scale",
        when=0.25,
        value=[1, 0.96, 1],
    )
    slower = call("clip.retime", subject=keyed, duration=1.0)
    where = call("clip.write", subject=slower, path="settle.clip.toml", root=root)
    back = call("clip.read", path=where, root=root)
    assert back["duration"] == 1.0
    assert "spine" in back["channels"]


def test_nothing_is_left_pending():
    found = capabilities(probe=False)
    assert found["unregistered"] == {}


def test_a_fresh_read_of_the_operations_loads_them():
    """capabilities in a new process used to list whatever had been imported."""
    import subprocess
    import sys

    said = subprocess.run(
        [
            sys.executable,
            "-c",
            "from polyweave.describe import operations; print(operations())",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "render.bake" in said.stdout
