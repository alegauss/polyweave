"""The state machines a game wrote, held to reach every state and leave it (§PW368).

Menus, characters and a game's flow are each a state machine written by hand, and the
failure is structural: a state no transition reaches, or one with no way out that was
not meant to be final, found only by a person who walks into it. Starship writes them
the one way GDScript invites, and `engine.states` reads that shape as it stands, with no
declaration and no skeleton:

    enum State { HOVER, LOCK, DIVE }
    var state := State.HOVER                  # the initial state
    ...
    match state:
        State.HOVER:
            if close: state = State.LOCK      # a way out of HOVER
    ...
    func dive() -> void:
        state = State.DIVE                    # a way in from any state

A state that is not the initial one and that nothing assigns is unreachable, an error. A
state with no way out but itself is a warning, unless its line in the enum is marked
`# final`. The check reads code, so it needs no run.
"""

from __future__ import annotations

import re
from typing import Annotated

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

_ENUM = re.compile(r"^enum\s+(?P<name>\w+)\s*\{(?P<body>[^}]*)\}", re.MULTILINE)
_SKIP = {".godot", ".git", ".polyweave", "addons", "node_modules"}


def _members(body: str) -> tuple[list[str], set[str]]:
    """An enum's members in order, and those whose line is marked `# final`."""
    names, final = [], set()
    for line in body.splitlines():
        marked = "# final" in line
        for one in re.findall(r"\b([A-Z_][A-Z0-9_]*)\b", line.split("#", 1)[0]):
            names.append(one)
            if marked:
                final.add(one)
    return names, final


def machines(text: str) -> list[dict]:
    """Each state machine a script holds: its enum, variable, start and moves."""
    found = []
    lines = text.splitlines()
    for enum in _ENUM.finditer(text):
        name = enum["name"]
        members, final = _members(enum["body"])
        declared = re.search(
            rf"^var\s+(?P<var>\w+)\s*(?::\s*{name}\s*)?:?=\s*{name}\.(?P<first>\w+)"
            rf"|^var\s+(?P<bare>\w+)\s*:\s*{name}\s*$",
            text, re.MULTILINE)
        if not declared or not members:
            continue
        var = declared["var"] or declared["bare"]
        first = declared["first"] or members[0]
        assign = re.compile(rf"\b(?:self\.)?{var}\s*=\s*{name}\.(\w+)")
        moves = []
        branch, match_indent = None, None
        for number, line in enumerate(lines, 1):
            body = line.split("#", 1)[0]
            if not body.strip():
                continue
            indent = len(line) - len(line.lstrip("\t "))
            if match_indent is not None and indent <= match_indent:
                branch, match_indent = None, None
            if re.match(rf"\s*match\s+(?:self\.)?{var}\s*:", body):
                match_indent, branch = indent, None
                continue
            if match_indent is not None:
                arm = re.match(rf"\s*((?:{name}\.\w+\s*,?\s*)+):", body)
                if arm and indent == _arm_indent(lines, number, match_indent):
                    branch = re.findall(rf"{name}\.(\w+)", arm[1])
                    rest = body.split(":", 1)[1]
                    for target in assign.findall(rest):
                        moves.append({"from": list(branch), "to": target,
                                      "line": number})
                    continue
            for target in assign.findall(body):
                moves.append({"from": list(branch) if branch else None, "to": target,
                              "line": number})
        found.append({"enum": name, "var": var, "first": first, "states": members,
                      "final": sorted(final), "moves": moves})
    return found


def _arm_indent(lines: list[str], number: int, match_indent: int) -> int:
    """The indent of the arms of the match above, read off its first arm."""
    for line in lines[number - 1:]:
        if line.strip() and not line.strip().startswith("#"):
            indent = len(line) - len(line.lstrip("\t "))
            if indent > match_indent:
                return indent
    return match_indent + 1


def held(machine: dict, script: str) -> list[dict]:
    """Every state nothing reaches, and every one with no way out that is not final."""
    found = []
    reached = {machine["first"]} | {move["to"] for move in machine["moves"]}
    anywhere = {move["to"] for move in machine["moves"] if move["from"] is None}
    line = min((move["line"] for move in machine["moves"]), default=1)
    for state in machine["states"]:
        if state not in reached:
            found.append({"script": script, "enum": machine["enum"], "state": state,
                          "code": "engine.unreachable-state", "severity": "error",
                          "line": line,
                          "said": f"{machine['enum']}.{state} is never assigned to "
                          f"{machine['var']} and is not where it starts"})
            continue
        leaving = {move["to"] for move in machine["moves"]
                   if move["from"] and state in move["from"]} | anywhere
        if not (leaving - {state}) and state not in machine["final"]:
            found.append({"script": script, "enum": machine["enum"], "state": state,
                          "code": "engine.stuck-state", "severity": "warning",
                          "line": line,
                          "said": f"nothing leaves {machine['enum']}.{state}; mark its "
                          "line in the enum # final where that is meant"})
    return found


@operation("engine.states")
def states(
    root: Annotated[str, Param("the Godot project whose scripts are read")] = ".",
) -> dict:
    """Every state machine the game's scripts write, held to reach and leave each state.

    Reads each script outside addons/ for an `enum`, a variable of it and its
    assignments: one inside a `match` arm on the variable leaves that arm's states, one
    outside leaves any. A state nothing assigns that is not the initial one is an error;
    one nothing leaves is a warning unless its enum line is marked `# final` (§PW368).
    """
    here = load(root).root
    if not (here / "project.godot").is_file():
        raise PolyweaveError(
            "engine.no-project",
            f"there is no project.godot at {here}, so no game scripts to read",
            "read the Godot project's own folder",
        )
    found, read = [], []
    for path in sorted(here.rglob("*.gd")):
        parts = path.relative_to(here).parts
        if any(p in _SKIP for p in parts):
            continue
        script = "res://" + path.relative_to(here).as_posix()
        for machine in machines(path.read_text(encoding="utf-8", errors="replace")):
            read.append({"script": script, "enum": machine["enum"],
                         "states": machine["states"], "first": machine["first"],
                         "moves": len(machine["moves"])})
            found += held(machine, script)
    errors = sum(1 for one in found if one["severity"] == "error")
    return {
        "clean": errors == 0,
        "machines": read,
        "findings": found,
        "says": f"{len(read)} state machine(s), {errors} unreachable state(s), "
        f"{len(found) - errors} with no way out",
    }
