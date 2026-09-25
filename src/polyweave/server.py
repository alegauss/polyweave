"""A served surface that is a shape over the registry (§PW126).

An agent reading a skill or a docstring composes a call and learns the range of
`elevation` from `op.out-of-range`: a range declared on a parameter reached the caller
only as a refusal. A tool schema carries it before the call is made. So the registry
that yields the command line yields one MCP tool per operation, and nothing about an
operation is written a second time:

- `description` is the operation's summary;
- each parameter is a property with its sentence, `minimum` and `maximum` from its
  range, `enum` from its choices, and `required` where it has no default;
- `additionalProperties` is false, so a misspelt argument is refused by the client.

A call runs the operation in process and answers with the fields `--json` prints.

    python -m polyweave serve          # stdio, newline-delimited JSON-RPC

The protocol is the handful of MCP methods a client uses (`initialize`, `tools/list`,
`tools/call`, `ping`), written here rather than depended on: the package's only
dependencies are numpy and Pillow, and a server is not a reason to add a third.

**Two budgets from the first day**, because both projects before this paid to add them
late: `TOOL_BUDGET` characters for any one tool and `LIST_BUDGET` for the whole list,
held by `tests/test_server.py`. A tool whose work needs Blender is listed only where
Blender is reachable, and still answers elsewhere, with the refusal that says so.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import shutil
import sys
from typing import Any

from .errors import PolyweaveError

PROTOCOL = "2025-06-18"

#: The most any one tool may cost the list, in characters of its JSON. The widest
#: is `render.bake` at 3,961, the rig's thirty parameters each with a sentence; this is
#: that plus room for a few more, and a tool needing more is a signal to split it.
TOOL_BUDGET = 4500

#: The most the whole list may cost, which is what every session pays to learn the
#: surface: 74 tools measured 41,683 characters when this was set, and this is a tenth
#: above. A raise is argued here, beside the number, never made silently in the test.
#: Raised to 47,000 at 46,491 for picture.buy (§PW163), the first operation that sends
#: a paid request itself, and `service` on six purchase and schema tools (§PW162).
#: Raised to 48,300 at 47,679 for purchase.reconcile (§PW164) and picture.describe
#: (§PW165), a quote held against the bill and an approved picture's own prompt.
#: Raised to 49,400 at 48,759 for style.read (§PW166) and style.drift (§PW167), and
#: to 50,600 at 50,015 for picture.gate (§PW168) and picture.letters (§PW169), and to
#: 52,400 at 51,765 for picture.vary and picture.against_parent (§PW170), and to
#: 53,300 at 52,889 for picture.fit (§PW171) and verdict.answers (§PW173), and to
#: 54,200 at 53,692 for shape.turntable (§PW176), and to 54,800 at 54,240 for
#: picture.collect (§PW179) and picture.vary's reframe (§PW181), and to 55,800 at
#: 55,151 for mesh.buy (§PW183), and to 56,600 at 56,059 for world.read and
#: world.validate (§PW196), and to 57,400 at 56,827 for words.check and
#: words.unlisted (§PW197), and to 58,400 at 57,832 for words.sheet and entity= on
#: the two purchases (§PW198, §PW199).
LIST_BUDGET = 58400

#: JSON Schema's name for each type an operation declares.
TYPES = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}

#: Operations that render or read a Blender file, beyond those whose kind says so.
BLENDER = frozenset({"clip.compiled", "skeleton.joints_in", "skeleton.plays"})


def tool_name(operation: str) -> str:
    """An operation's name as a tool's: clients take letters, digits, `_` and `-`."""
    return operation.replace(".", "_")


def schema_of(found: dict) -> dict:
    """One operation's declaration as a tool's input schema."""
    properties: dict[str, dict] = {}
    required: list[str] = []
    for p in found["parameters"]:
        one: dict[str, Any] = {}
        kind = TYPES.get(p["type"])
        if kind:
            one["type"] = kind
        about = p["about"] + (f" ({p['unit']})" if p.get("unit") else "")
        one["description"] = about
        low, high = (p.get("range") or (None, None))[:2]
        if low is not None:
            one["minimum"] = low
        if high is not None:
            one["maximum"] = high
        if p.get("choices"):
            one["enum"] = list(p["choices"])
        if not p["required"] and _plain(p["default"]):
            one["default"] = p["default"]
        properties[p["name"]] = one
        if p["required"]:
            required.append(p["name"])
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _plain(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return value is not None


def needs_blender(found: dict) -> bool:
    return found["kind"] in ("bake", "search") or found["operation"] in BLENDER


def blender_here() -> bool:
    """Whether a render could run here, found cheaply: bpy importable, or a binary."""
    return importlib.util.find_spec("bpy") is not None or bool(shutil.which("blender"))


def tools(*, blender: bool | None = None) -> list[dict]:
    """Every operation as a tool, leaving out the ones that need an absent Blender."""
    from . import describe as D

    reachable = blender_here() if blender is None else blender
    return [
        {
            "name": tool_name(found["operation"]),
            "description": found["summary"],
            "inputSchema": schema_of(found),
        }
        for found in D.describe()
        if reachable or not needs_blender(found)
    ]


def call(name: str, arguments: dict | None) -> dict:
    """One tool call as MCP content; a refusal is an error result, not a raise."""
    from . import describe as D
    from .commands import Quiet, as_data

    by_tool = {tool_name(op): op for op in D.operations()}
    try:
        if name not in by_tool:
            raise PolyweaveError(
                "op.unknown",
                f"there is no tool named {name!r}",
                "tools/list names every one",
                given=name,
                allowed=by_tool,
            )
        registered = D._REGISTRY[by_tool[name]]
        args = D.validate(registered.name, dict(arguments or {}))
        injected = {one: Quiet() for one in registered.injects}
        # stdout is the protocol, so whatever the work prints goes to stderr instead.
        with contextlib.redirect_stdout(sys.stderr):
            answer = as_data(registered.fn(**injected, **args))
    except PolyweaveError as refused:
        return _content({"refused": refused.as_dict()}, error=True)
    return _content(answer, error=False)


def _content(data: Any, *, error: bool) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(data, indent=1)}],
        "structuredContent": data if isinstance(data, dict) else {"result": data},
        "isError": error,
    }


def handle(message: dict) -> dict | None:
    """One JSON-RPC message in, its reply out; a notification gets none."""
    from . import __version__

    method = message.get("method")
    if "id" not in message:
        return None
    reply: dict[str, Any] = {"jsonrpc": "2.0", "id": message["id"]}
    params = message.get("params") or {}
    if method == "initialize":
        reply["result"] = {
            "protocolVersion": params.get("protocolVersion", PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "polyweave", "version": __version__},
        }
    elif method == "tools/list":
        reply["result"] = {"tools": tools()}
    elif method == "tools/call":
        reply["result"] = call(params.get("name", ""), params.get("arguments"))
    elif method == "ping":
        reply["result"] = {}
    else:
        reply["error"] = {"code": -32601, "message": f"no method {method!r}"}
    return reply


def serve(stdin: Any = None, stdout: Any = None) -> None:
    """Read one message per line and write one reply per line, until the input ends."""
    reading = stdin or sys.stdin
    writing = stdout or sys.stdout
    for line in reading:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            reply = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        else:
            reply = handle(message)
        if reply is not None:
            writing.write(json.dumps(reply) + "\n")
            writing.flush()
