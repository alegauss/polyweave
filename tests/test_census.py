"""What of the package a caller can find without reading it (§PW124)."""

from __future__ import annotations

from polyweave import census, describe, errors, measure
from polyweave.capabilities import capabilities

#: How much surface is still unregistered. Registering a module lowers it, and this
#: number is lowered with it: it may only fall, never rise.
PENDING = 243


def test_every_public_function_is_classified():
    found = census.census()
    assert found["unclassified"] == [], (
        "register these with @operation, or add their module to census.MODULES with "
        "the reason it is internal or pending"
    )


def test_no_entry_or_module_is_listed_that_no_longer_needs_to_be():
    names = census.public()
    stale_entries = sorted(set(census.ENTRY) - set(names))
    live_modules = set(names.values())
    stale_modules = sorted(set(census.MODULES) - live_modules)
    registered = {op.target for op in describe._REGISTRY.values()}
    wholly_registered = sorted(
        module
        for module in census.MODULES
        if module in live_modules
        and all(
            target in registered or target in census.ENTRY
            for target, owner in names.items()
            if owner == module
        )
    )
    assert stale_entries == []
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
    assert "polyweave.search" in found["unregistered"]


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
