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
late: `TOOL_BUDGET` characters for any one tool, and for the list a figure per layer
with `SESSION_BUDGET` over a whole session (§PW510), held by `tests/test_server.py`.
A tool whose work needs Blender is listed only where Blender is reachable, and still
answers elsewhere, with the refusal that says so.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from polyweave.kernel import errors
from polyweave.kernel.errors import PolyweaveError

PROTOCOL = "2025-06-18"

#: The most any one tool may cost the list, in characters of its JSON. The widest
#: is `render.bake` at 3,961, the rig's thirty parameters each with a sentence; this is
#: that plus room for a few more, and a tool needing more is a signal to split it.
TOOL_BUDGET = 4500

#: What the kernel's and the loop's own tools may cost the list, every project's.
#: Each layer's figure is its own, in its `layer.py`, beside the code that grows it
#: (§PW510): measured at 37,550 here when the figure moved.
CORE_TOOLS = 39_000

#: What the heaviest session a real consumer opens may cost, every layer on: Spinhold's,
#: which declares no [layers]. 129,979 when this was set. It is not raised by a line
#: that adds one operation: that line raises its layer's own figure, and this one moves
#: only when the layers' figures together no longer fit, argued here.
#: 132,521 with clip.timeline (§PW554), whose motion layer's figure rose by 600 for it
#: on top of verdict.place and the args of game.open and clip.shots in the same run.
#: 133,265 with sound.stems (§PW558), whose sound layer's figure rose by 400 for it.
#: 134,226 with music.from_midi (§PW559), whose sound layer's figure rose by 1,000.
#: 135,350 with music.from_audio (§PW559), whose sound layer's figure rose by 1,100.
#: 136,539 with geometry.kit (§PW568), whose geometry layer's figure rose by 1,200.
#: 137,117 with picture.copies (§PW585), inside the picture layer's own figure.
#: 137,507 with clip.shots's clip, anchors and place (§PW591), whose motion layer's
#: figure rose by 600 for them.
#: 137,832 with clip.shots's keep and hide (§PW597) and a sitting member's motion
#: (§PW600), each inside its layer's own figure.
#: 138,123 with clip.shots's loop and panel.capture's (§PW600), whose motion layer's
#: figure rose by 300 for them.
#: 139,516 with game.input's drag, wheel, text, button, double and mods (§PW607),
#: inside the engine layer's own figure.
#: 140,106 with music.track (§PW611), whose sound layer's figure rose by 600 for it.
SESSION_BUDGET = 140_400

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


#: The one tool that is not an operation (§PW430): `describe(name)` as the command line
#: answers it, so a caller over MCP reads what a declaration may hold, which the tools
#: list leaves out to stay inside its budget, without a shell or a source read.
DESCRIBE = {
    "name": "describe",
    "description": "One operation in full: its parameters, and where it builds from a "
    "file (vfx.build's *.vfx.toml), every key that file may hold.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "the operation, dotted (vfx.build) or as its tool "
                "(vfx_build)",
            },
        },
        "required": ["operation"],
        "additionalProperties": False,
    },
}


def _on(root: str | Path = ".") -> frozenset[str] | None:
    """The layers this project uses, or None for every one where the file cannot say:
    a `[layers]` the project got wrong is answered on the call, not by an empty list."""
    from polyweave.kernel.layer import on

    try:
        return on(root)
    except PolyweaveError:
        return None


def tools(*, blender: bool | None = None, root: str | Path = ".") -> list[dict]:
    """Every operation of a layer the project uses as a tool, leaving out the ones that
    need an absent Blender, and `describe` beside them (§PW509)."""
    from polyweave.kernel import describe as D

    reachable = blender_here() if blender is None else blender
    using = _on(root)
    return [
        {
            "name": tool_name(found["operation"]),
            "description": found["summary"],
            "inputSchema": schema_of(found),
        }
        for found in D.describe()
        if (reachable or not needs_blender(found))
        and (using is None or found.get("layer") in (None, *using))
    ] + [
        {
            "name": tool_name(found["operation"]),
            "description": found["summary"],
            "inputSchema": schema_of(found),
        }
        for found in _project(root).values()
    ] + [DESCRIBE]


def _project(root: str | Path = ".") -> dict[str, dict]:
    """The project's own operations, described (§PW518), by name. A declaration it got
    wrong serves none of them, and `project.check` says why."""
    from polyweave.loop import extend

    try:
        return {name: one.described() for name, one in extend.operations(root).items()}
    except PolyweaveError:
        return {}


def shares(listed: list[dict] | None = None) -> dict[str, dict]:
    """What each layer's tools cost the list, and its three dearest, by layer; the
    kernel's and the loop's are under `core` (§PW510)."""
    from polyweave.kernel import describe as D

    D.load()
    by_tool = {tool_name(op.name): op.layer or "core" for op in D._REGISTRY.values()}
    # A project's own operations are counted as its own share, never hidden in another.
    by_tool.update({tool_name(name): "project" for name in _project()})
    found: dict[str, dict] = {}
    for tool in tools(blender=True) if listed is None else listed:
        size = len(json.dumps(tool))
        one = found.setdefault(by_tool.get(tool["name"], "core"),
                               {"size": 0, "tools": []})
        one["size"] += size
        one["tools"].append((size, tool["name"]))
    return {
        layer: {"size": one["size"],
                "dearest": [name for _, name in sorted(one["tools"], reverse=True)[:3]]}
        for layer, one in sorted(found.items())
    }


def over(found: dict[str, dict], budgets: dict[str, int]) -> list[str]:
    """Each layer whose tools cost more than its own figure, naming its dearest."""
    return [
        f"{layer} serves {one['size']} characters of tools, past its {budgets[layer]}; "
        f"dearest: {', '.join(one['dearest'])}"
        for layer, one in found.items()
        if one["size"] > budgets.get(layer, 0)
    ]


def budgets() -> dict[str, int]:
    """Each layer's own figure, and the core's."""
    from polyweave.kernel.layer import layers

    return {"core": CORE_TOOLS, **{name: one.tools for name, one in layers().items()}}


def session(root: str | Path = ".") -> dict:
    """What this project's tools/list costs a session, and the three dearest layers."""
    listed = tools(blender=True, root=root)
    found = shares(listed)
    return {
        "size": len(json.dumps(listed)),
        "ceiling": SESSION_BUDGET,
        "dearest": [
            {"layer": layer, "size": one["size"]}
            for layer, one in sorted(found.items(), key=lambda kv: -kv[1]["size"])[:3]
        ],
    }


def _described(arguments: dict) -> Any:
    """`describe(name)`, a tool's name taken for its operation's."""
    from polyweave.kernel import describe as D

    unknown = sorted(set(arguments) - {"operation"})
    if unknown or not isinstance(arguments.get("operation"), str):
        raise PolyweaveError(
            "op.unknown-argument" if unknown else "op.missing-argument",
            "describe takes one argument, operation, the name of one",
            'pass {"operation": "vfx.build"}',
            given=unknown[0] if unknown else "operation",
        )
    asked = arguments["operation"]
    own = _project()
    project = {**own, **{tool_name(name): one for name, one in own.items()}}
    if asked in project:
        return project[asked]
    by_tool = {tool_name(op): op for op in D.operations()}
    said = D.describe(by_tool.get(asked, asked))
    using = _on()
    if using is not None and said.get("layer") not in (None, *using):
        # Still described, so an agent finds what exists, and said off (§PW509).
        said = {**said, "off": True}
    return said


def call(name: str, arguments: dict | None) -> dict:
    """One tool call as MCP content; a refusal is an error result, not a raise."""
    from polyweave.kernel import describe as D
    from polyweave.kernel.layer import off, on

    from .commands import Quiet, as_data

    by_tool = {tool_name(op): op for op in D.operations()}
    try:
        if name == DESCRIBE["name"]:
            return _content(_described(dict(arguments or {})), error=False)
        project = {tool_name(one): one for one in _project()}
        if name in project:
            from polyweave.loop import extend

            # Held to its declaration, then run apart or started as a job (§PW518).
            with contextlib.redirect_stdout(sys.stderr):
                answer = as_data(extend.called(project[name], dict(arguments or {})))
            return _content(answer, error=False)
        if name not in by_tool:
            raise PolyweaveError(
                "op.unknown",
                f"there is no tool named {name!r}",
                "tools/list names every one",
                given=name,
                allowed=by_tool,
            )
        registered = D._REGISTRY[by_tool[name]]
        if registered.layer and registered.layer not in on():
            raise off(registered.layer, registered.name)
        args = D.validate(registered.name, dict(arguments or {}))
        if registered.guard is not None:
            registered.guard(args)
        injected = {one: Quiet() for one in registered.injects}
        # stdout is the protocol, so whatever the work prints goes to stderr instead.
        with contextlib.redirect_stdout(sys.stderr):
            answer = as_data(registered.fn(**injected, **args))
    except PolyweaveError as refused:
        return _content({"refused": refused.as_dict()}, error=True)
    except Exception as crashed:  # noqa: BLE001 - one bad call must not end the server
        # A raise here used to close the connection, and every other tool with it for
        # the rest of the caller's turn (§PW261). It is a defect, and said as one.
        return _content({"refused": errors.crashed(
            name,
            crashed,
            "this is a defect in polyweave, not in the call; the other tools still "
            "answer, and the detail says where it raised",
        ).as_dict()}, error=True)
    return _content(answer, error=False)


def _content(data: Any, *, error: bool) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(data, indent=1)}],
        "structuredContent": data if isinstance(data, dict) else {"result": data},
        "isError": error,
    }


def handle(message: dict) -> dict | None:
    """One JSON-RPC message in, its reply out; a notification gets none."""
    from polyweave import __version__

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
