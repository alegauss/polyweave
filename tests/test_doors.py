"""A door is a call, and every door is run (§PW127)."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pytest

from polyweave import codes, commands, describe, doors, loop
from polyweave.errors import PolyweaveError, explain

SOURCE = Path(__file__).parents[1] / "src" / "polyweave"


def written() -> list[tuple[str, int, str, set[str]]]:
    """Every `door(...)` in the source: where, which operation, which arguments."""
    found = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "door"
            ):
                first = node.args[0]
                assert isinstance(first, ast.Constant), f"{path}:{node.lineno}"
                keywords = {k.arg for k in node.keywords}
                found.append((path.name, node.lineno, first.value, keywords))
    return found


def parameters(operation: str) -> dict[str, dict]:
    return {p["name"]: p for p in describe.describe(operation)["parameters"]}


def test_there_are_doors_to_check():
    assert len(written()) >= 6


@pytest.mark.parametrize(
    ("where", "line", "operation", "given"),
    written(),
    ids=lambda v: str(v) if not isinstance(v, set) else "",
)
def test_every_door_in_the_source_names_a_real_call(where, line, operation, given):
    assert operation in describe.operations(), f"{where}:{line}"
    declared = parameters(operation)
    unknown = given - set(declared)
    assert not unknown, f"{where}:{line} passes {unknown}, which {operation} lacks"
    missing = {n for n, p in declared.items() if p["required"]} - given
    assert not missing, f"{where}:{line} leaves out {missing}"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(prog="python -m polyweave")
    commands.add_operations(made.add_subparsers(dest="command"))
    return made


@pytest.mark.parametrize(
    "code", sorted(name for name, one in codes.CODES.items() if one.calls)
)
def test_every_door_the_codes_table_teaches_parses(code):
    """SH1074's lesson: where a refusal teaches a form, the form is accepted."""
    for call in codes.CODES[code].calls:
        stated = parser().parse_args(doors.argv(call))
        assert stated.command == call["operation"]


def test_a_refusal_carries_its_door_as_data_and_as_a_command(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star", "before", root=tmp_path, change="hue")
    call = refused.value.as_dict()["call"]
    assert call["operation"] == "loop.start"
    assert call["arguments"]["asset"] == "star"
    assert call["command"].startswith("python -m polyweave loop.start --asset star")
    assert parser().parse_args(doors.argv(refused.value.call)).way == "before"


def test_a_blank_is_spelled_where_only_the_caller_has_the_value():
    why = doors.Blank("x")
    call = doors.door("verdict.judge", members=[], choice="accept", why=why)
    assert doors.as_data(call)["arguments"]["why"] == "<x>"
    assert "--why <x>" in doors.command(call)


def test_explain_carries_the_codes_calls():
    assert explain("loop.not-ported")["calls"][0]["operation"] == "loop.start"


def test_a_door_survives_the_wire():
    raised = PolyweaveError(
        "loop.not-ported",
        "m",
        "r",
        call=doors.door("loop.start", asset="a", way="before"),
    )
    back = PolyweaveError.from_dict(raised.as_dict())
    assert back.call["operation"] == "loop.start"
