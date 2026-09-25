"""A remedy's call as data, so the call it names can be checked (§PW127).

A remedy was a sentence: "pass `model`" named an argument from memory, and when the
argument was renamed the sentence kept offering it. Roadkeep lived with that for four
hundred commits before it found one of 118 remedy rows had ever been run. So a remedy
that names a call carries the call:

    raise PolyweaveError(
        "render.no-mesh", "...", "pass the mesh",
        call=door("render.bake", out=Blank("where to write"), model=Blank("the mesh")),
    )

The operation and its arguments are data, a `Blank` stands where only the caller has
the value, and the command line is rendered from it. `tests/test_doors.py` finds every
`door(...)` in the source and in the codes table and parses it against the derived
command line, so a door naming an operation or a flag that does not exist fails.

Nothing here imports the package: `codes` and `errors` both use it, and they are the
bottom of the stack.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Blank:
    """Where a door needs a value only the caller can give."""

    what: str

    def __str__(self) -> str:
        return f"<{self.what}>"


def door(operation: str, **arguments: Any) -> dict:
    """The call a remedy names: an operation and its arguments, blanks included."""
    return {"operation": operation, "arguments": dict(arguments)}


def as_data(call: dict) -> dict:
    """The door as the wire carries it: blanks spelled, and the command line beside."""
    return {
        "operation": call["operation"],
        "arguments": {
            name: str(value) if isinstance(value, Blank) else value
            for name, value in call["arguments"].items()
        },
        "command": command(call),
    }


def argv(call: dict) -> list[str]:
    """The door as the words after `python -m polyweave`."""
    words = [call["operation"]]
    for name, value in call["arguments"].items():
        shown = (
            value
            if isinstance(value, str)
            else str(value)
            if isinstance(value, Blank)
            else json.dumps(value)
        )
        words += [f"--{name}", shown]
    return words


def command(call: dict) -> str:
    """The door as one command line a person or an agent can run."""
    return "python -m polyweave " + " ".join(
        word if " " not in word and word else json.dumps(word) for word in argv(call)
    )
