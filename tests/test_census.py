"""What of the package a caller can find without reading it (§PW124)."""

from __future__ import annotations

from polyweave import census, describe, errors, measure
from polyweave.capabilities import capabilities

#: How much surface is still unregistered. Registering a module lowers it, and this
#: number is lowered with it: it may only fall, never rise.
PENDING = 200


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
