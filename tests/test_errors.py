"""§3 of the tool surface: errors are typed, and name the door.

The measure §PW4 sets is whether a failure can be answered without opening any
implementation file. The registry test below is what keeps that true as code is added:
a code raised anywhere in the package must be declared, and a declaration nothing raises
is a promise the plugin does not keep.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from polyweave import codes as C
from polyweave import config
from polyweave.errors import PolyweaveError, codes, explain, guard

SRC = Path(__file__).resolve().parent.parent / "src" / "polyweave"

#: A code-shaped string. The scan looks for these rather than for arguments of a
#: particular call, because a code reaches `PolyweaveError` through a helper as often as
#: it is written at the raise itself.
SHAPED = re.compile(rf"^({'|'.join(C.AREAS)})\.[a-z0-9]+(-[a-z0-9]+)*$")


#: `area.name` is the shape of three different vocabularies here: an error code, a
#: config address (`render.samples`) and an operation name (`render.bake`). Only the
#: codes have to be declared, so the other two are enumerated and subtracted first.
def _not_codes() -> set[str]:
    import polyweave.render  # noqa: F401 - imported for the side effect of registering
    from polyweave.describe import operations

    settings = {f"{t}.{k}" for t, keys in config.DEFAULTS.items() for k in keys}
    return settings | set(operations())


SETTINGS = _not_codes()


def used_codes() -> dict[str, list[str]]:
    """Every code-shaped literal in the package, other than the declarations."""
    found: dict[str, list[str]] = {}
    for path in SRC.rglob("*.py"):
        if path.name == "codes.py":
            continue  # the declaration itself, which would make the check circular
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and SHAPED.match(node.value)
                and node.value not in SETTINGS
            ):
                found.setdefault(node.value, []).append(f"{path.name}:{node.lineno}")
    return found


# -- the registry cannot drift from the code ----------------------------------


def test_every_code_used_in_the_package_is_declared():
    undeclared = {c: w for c, w in used_codes().items() if c not in C.CODES}
    assert not undeclared, f"declare these in codes.py: {undeclared}"


def test_every_declared_code_is_used_somewhere():
    """A declaration nothing raises describes a failure that cannot happen."""
    unused = sorted(set(C.CODES) - set(used_codes()))
    assert not unused, f"declared but never raised: {unused}"


def test_no_code_is_assembled_at_runtime():
    """A code built from a variable is one nothing can enumerate."""
    dynamic = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            name = getattr(node.func, "id", None)
            if name == "PolyweaveError" and isinstance(node.args[0], ast.JoinedStr):
                dynamic.append(f"{path.name}:{node.lineno}")
    assert not dynamic, f"codes assembled from an f-string: {dynamic}"


def test_an_undeclared_code_cannot_be_raised():
    with pytest.raises(ValueError, match="not declared"):
        PolyweaveError("job.invented", "…", "…")


def test_a_code_outside_the_grammar_is_refused():
    with pytest.raises(ValueError, match="not a code"):
        PolyweaveError("Job.Worker_Gone", "…", "…")


def test_an_error_without_a_remedy_is_refused():
    with pytest.raises(ValueError, match="no remedy"):
        PolyweaveError("job.unknown", "…", "")


# -- explain ------------------------------------------------------------------


def test_explain_says_what_it_means_what_produces_it_and_the_doors():
    found = explain("job.worker-gone")
    assert found["area"] == "job"
    assert "no longer running" in found["means"]
    assert "heartbeat" in found["when"]
    assert found["doors"]


def test_explain_suggests_the_code_that_was_meant():
    with pytest.raises(PolyweaveError) as caught:
        explain("job.worker-goen")
    assert caught.value.code == "spec.unknown-code"
    assert "job.worker-gone" in caught.value.remedy


def test_explain_places_a_code_it_cannot_match():
    with pytest.raises(PolyweaveError) as caught:
        explain("render.something-entirely-unlike")
    assert "producing a picture" in caught.value.remedy


def test_codes_lists_the_whole_set_and_one_area():
    everything = codes()
    assert len(everything) == len(C.CODES)
    assert codes("op") == sorted(c for c in everything if c.startswith("op."))


def test_an_unknown_area_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        codes("renderer")
    assert caught.value.code == "spec.unknown-area"


def test_every_declaration_says_what_it_means_and_what_produces_it():
    for code, declared in C.CODES.items():
        assert declared.means, code
        assert declared.when, code
        assert declared.doors, code
        assert not declared.means.endswith("."), f"{code}: means is a clause"


# -- the boundary that types what it did not write ----------------------------


def test_guard_types_an_untyped_failure_and_keeps_the_traceback():
    with (
        pytest.raises(PolyweaveError) as caught,
        guard("job.target-failed", remedy="read the log"),
    ):
        raise ValueError("the boolean left no faces")
    error = caught.value
    assert error.code == "job.target-failed"
    assert "the boolean left no faces" in error.message
    assert "Traceback" not in error.message
    assert "Traceback" in error.detail
    assert error.remedy == "read the log"


def test_guard_lets_a_typed_failure_through_untouched():
    """It already names its own door, so wrapping it would bury the better answer."""
    original = PolyweaveError("post.mesh-empty", "no faces", "check the inputs")
    with (
        pytest.raises(PolyweaveError) as caught,
        guard("job.target-failed", remedy="read the log"),
    ):
        raise original
    assert caught.value is original


def test_guard_does_nothing_when_nothing_fails():
    with guard("job.target-failed", remedy="read the log"):
        value = 2 + 2
    assert value == 4


# -- the wire form ------------------------------------------------------------


def test_an_error_round_trips_through_its_wire_form():
    original = PolyweaveError("post.mesh-nan", "3 vertices", "check it", detail="…")
    assert PolyweaveError.from_dict(original.as_dict()).as_dict() == original.as_dict()


def test_detail_is_absent_rather_than_null_when_there_is_none():
    assert "detail" not in PolyweaveError("job.unknown", "m", "r").as_dict()
