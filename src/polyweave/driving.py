"""A game held open between an agent's calls, and the tools that act in it (§PW213).

The driver (`addons/polyweave_driver`, docs/specs/driving.md) holds a running game still
and answers on a loopback socket. These are the doors to it on the tool surface: open a
game, query, input, step, wait, call, shot, close.

**A session outlives the call that opened it.** An agent reaches polyweave through the
MCP server, one long process, and through the command line, where every call is a
process of its own. So a session is a file under `.polyweave/driving/` naming the
game's process, port and token, and each call connects, sends one command and reads one
answer. The
driver keeps the game held between connections and quits on `close`, or after
`[driving] idle` seconds with no call, so no Godot process outlives the conversation.

**Every answer says what the engine printed since the last one.** The game's output goes
to a log beside the session, and each call reads what is new and names any error in it
with the runner's own pattern, so a script error mid-flow is reported by the call that
caused it rather than found later in a log.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Any

from . import engine, offscreen
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

__all__ = ["opened", "send"]

#: Where the driver sits inside a project that installed it.
DRIVER = "res://addons/polyweave_driver/driver.gd"

#: The line the driver prints once it listens.
LISTENING = re.compile(r"polyweave_driver: port=(?P<port>\d+) token=(?P<token>\w+)")

#: What the driver refuses with, raised here under its own code (docs/specs/driving.md).
DRIVER_CODES = (
    "driver.bad-token",
    "driver.bad-command",
    "driver.no-node",
    "driver.no-method",
    "driver.no-picture",
    "driver.off-screen",
)

#: How long a game may take to load before it says where it listens.
OPENING_S = 120.0

_SESSION = Param("the session game.open answered")
_ROOT = Param("the project the game belongs to")


def _folder(root: str | Path) -> Path:
    return load(root).root / ".polyweave" / "driving"


def _session(session: str, root: str | Path) -> dict:
    where = _folder(root) / f"{session}.json"
    if not where.is_file():
        raise PolyweaveError(
            "game.no-session",
            f"there is no open session called {session!r} in this project",
            "open the game again with game.open and use the session it answers",
            given=session,
        )
    return json.loads(where.read_text(encoding="utf-8"))


def _alive(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            found = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in found.stdout
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@operation("game.open")
def opened(
    root: Annotated[str, _ROOT] = ".",
    *,
    scene: Annotated[
        str, Param("a scene to load instead of the main one, res://")
    ] = "",
    seed: Annotated[
        int, Param("seed for the global random functions; 0 leaves it")
    ] = 0,
    display: Annotated[
        bool, Param("draw real pixels, through the offscreen route, so game.shot works")
    ] = False,
) -> dict:
    """Launch the game held at its first frame, and answer the session to drive it with.

    The project needs the driver installed (`godot.install` with addon
    polyweave_driver). The game runs until game.close, or `[driving] idle` seconds with
    no call.
    """
    settings = load(root)
    here = settings.root
    if not (here / DRIVER.removeprefix("res://")).is_file():
        raise PolyweaveError(
            "game.no-driver",
            f"{here} has no polyweave_driver addon, so nothing can drive it",
            "install it with godot.install and addon polyweave_driver, then open again",
        )
    args = ["--path", str(here), "--fixed-fps", str(settings.get("engine.fixed_fps"))]
    through: tuple[str, ...] = ()
    after = [f"--idle={int(settings.get('driving.idle'))}"]
    if display:
        route = offscreen.route_for(here)
        args = [*route.args, *args]
        through = route.through
        if route.window:
            after.append(route.window)
    else:
        args = ["--headless", *args]
    if seed:
        after.append(f"--seed={int(seed)}")
    if scene:
        after.append(f"--scene={scene}")
    folder = _folder(here)
    folder.mkdir(parents=True, exist_ok=True)
    session = "g" + secrets.token_hex(4)
    log = folder / f"{session}.log"
    command = [*through, engine.find(here), *args, "--script", DRIVER, "--", *after]
    with log.open("w", encoding="utf-8") as out:
        # Its own process group, so it outlives a command line that opened it.
        extra: dict[str, Any] = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if sys.platform == "win32"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            command, cwd=here, stdout=out, stderr=subprocess.STDOUT, **extra
        )
    started = time.monotonic()
    found = None
    while time.monotonic() - started < OPENING_S:
        text = log.read_text(encoding="utf-8", errors="replace")
        found = LISTENING.search(text)
        if found or process.poll() is not None:
            break
        time.sleep(0.1)
    if not found:
        process.kill()
        raise PolyweaveError(
            "game.not-listening",
            "the game never said where its driver listens"
            + (f"; it ended with code {process.returncode}" if process.poll() else ""),
            f"read {log}, which holds everything it printed",
            detail=log.read_text(encoding="utf-8", errors="replace")[-2000:] or None,
        )
    record = {
        "session": session,
        "pid": process.pid,
        "port": int(found["port"]),
        "token": found["token"],
        "log": str(log),
        "read": found.end(),
        "display": bool(display),
    }
    (folder / f"{session}.json").write_text(json.dumps(record), encoding="utf-8")
    first = send(session, "query", root=here, path="/root", properties=["name"])
    return {
        "session": session,
        "frame": first["frame"],
        "pid": process.pid,
        "log": str(log),
    }


def send(session: str, cmd: str, *, root: str | Path = ".", **fields: Any) -> dict:
    """One command to a held game, and its answer with what the engine printed since."""
    record = _session(session, root)
    request = {"token": record["token"], "id": 1, "cmd": cmd, **fields}
    try:
        with socket.create_connection(
            ("127.0.0.1", record["port"]), timeout=600
        ) as link:
            link.sendall((json.dumps(request) + "\n").encode("utf-8"))
            reply = link.makefile("r", encoding="utf-8").readline()
    except OSError as failed:
        _forget(record, root)
        raise PolyweaveError(
            "game.gone",
            f"session {session} no longer answers: {failed}",
            "open the game again with game.open; read the log for why it ended",
            detail=_printed(record, root)["text"] or None,
        ) from None
    if not reply:
        _forget(record, root)
        raise PolyweaveError(
            "game.gone",
            f"session {session} closed without answering {cmd}",
            f"read {record['log']}, which holds everything the game printed",
        )
    answer = json.loads(reply)
    printed = _printed(record, root)
    if not answer.get("ok"):
        code = answer.get("error")
        raise PolyweaveError(
            code if code in DRIVER_CODES else "game.refused",
            answer.get("message", f"the driver refused {cmd}"),
            "correct the command, as the message says; the game is still held",
            detail=printed["text"] or None,
        )
    return {
        "frame": answer.get("frame"),
        "result": answer.get("result"),
        "errors": printed["errors"],
    }


def _printed(record: dict, root: str | Path) -> dict:
    """What the game printed since the last call, and the errors in it."""
    where = Path(record["log"])
    text = (
        where.read_text(encoding="utf-8", errors="replace") if where.is_file() else ""
    )
    new = text[record.get("read", 0) :]
    record["read"] = len(text)
    folder = _folder(root) / f"{record['session']}.json"
    if folder.is_file():
        folder.write_text(json.dumps(record), encoding="utf-8")
    errors = [line.strip() for line in new.splitlines() if engine.ERRORS.search(line)]
    return {"text": new.strip(), "errors": errors}


def _forget(record: dict, root: str | Path) -> None:
    where = _folder(root) / f"{record['session']}.json"
    if where.is_file():
        where.unlink()


def _node(path: str, group: str, named: str) -> dict:
    """The one way of finding nodes a call gave, refused where it gave none or two."""
    given = {k: v for k, v in (("path", path), ("group", group), ("class", named)) if v}
    if len(given) != 1:
        raise PolyweaveError(
            "game.bad-target",
            "name the node one way: a path, a group or a class",
            "give exactly one of path, group and of_class",
        )
    return given


@operation("game.query")
def queried(
    session: Annotated[str, _SESSION],
    *,
    path: Annotated[
        str, Param("a node's path, from /root or from the main scene")
    ] = "",
    group: Annotated[str, Param("a group, every node in it")] = "",
    of_class: Annotated[str, Param("a class, engine or script, every node of it")] = "",
    properties: Annotated[
        list, Param("the properties to read; a default set if unset")
    ] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """The nodes a path, group or class finds, with their properties, the game held."""
    fields = _node(path, group, of_class)
    if properties:
        fields["properties"] = list(properties)
    return send(session, "query", root=root, **fields)


@operation("game.input")
def inputted(
    session: Annotated[str, _SESSION],
    *,
    action: Annotated[str, Param("an input action, pressed and released")] = "",
    key: Annotated[str, Param("a key by name, e.g. Space")] = "",
    click: Annotated[str, Param("a node's path to click at the centre of")] = "",
    at: Annotated[list, Param("a point in the viewport to click, [x, y]")] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Press an action or a key, or click a node or a point; it lands next frame."""
    if action:
        return send(session, "input", root=root, action=action)
    if key:
        return send(session, "input", root=root, key=key)
    if click:
        return send(session, "input", root=root, click={"path": click})
    if at:
        return send(session, "input", root=root, click={"at": list(at)})
    raise PolyweaveError(
        "game.bad-target",
        "an input needs an action, a key, a node to click or a point",
        "give one of action, key, click and at",
    )


@operation("game.step")
def stepped(
    session: Annotated[str, _SESSION],
    *,
    frames: Annotated[int, Param("how many frames pass", lo=1)] = 1,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Let a number of frames pass, then hold the game again."""
    return send(session, "step", root=root, frames=int(frames))


@operation("game.wait")
def waited(
    session: Annotated[str, _SESSION],
    *,
    frames: Annotated[int, Param("the most frames the wait may spend", lo=1)] = 60,
    path: Annotated[str, Param("the node the signal or property is on")] = "",
    signal: Annotated[str, Param("a signal of that node to wait for")] = "",
    node: Annotated[str, Param("a path or group that must come to exist")] = "",
    prop: Annotated[str, Param("a property of that node to wait on")] = "",
    equals: Annotated[str, Param("the value the property must reach, as JSON")] = "",
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Let frames pass until a signal fires, a node exists or a value is reached.

    An unmet wait is an answer, met false, and not an error: the budget ran out.
    """
    fields: dict[str, Any] = {"frames": int(frames)}
    if signal:
        fields.update(path=path, signal=signal)
    elif node:
        fields.update(node=node)
    elif prop:
        try:
            wanted = json.loads(equals) if equals != "" else None
        except json.JSONDecodeError:
            wanted = equals  # a bare word is the string it spells
        fields.update(path=path, property=prop, equals=wanted)
    else:
        raise PolyweaveError(
            "game.bad-target",
            "a wait needs a signal, a node, or a property and its value",
            "give signal with path, or node, or prop with path and equals",
        )
    return send(session, "wait", root=root, **fields)


@operation("game.call")
def called(
    session: Annotated[str, _SESSION],
    *,
    path: Annotated[str, Param("the node the method is on")],
    method: Annotated[str, Param("a method the game exposes for setup")],
    args: Annotated[list, Param("its arguments")] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Call a method the game exposes for setup, and answer what it returned."""
    return send(session, "call", root=root, path=path, method=method, args=list(args))


@operation("game.shot")
def shot(
    session: Annotated[str, _SESSION],
    *,
    out: Annotated[str, Param("where the PNG goes, under the project")],
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Save the screen as it is now, answering the path and size, not the picture.

    A picture costs many tokens and a query few, so the agent chooses to read it.
    Whether it looks right stays a person's verdict. Needs a session opened with
    display, since a headless run draws nothing.
    """
    where = Path(out)
    if not where.is_absolute():
        where = load(root).root / where
    where.parent.mkdir(parents=True, exist_ok=True)
    return send(session, "shot", root=root, out=str(where))


@operation("game.close")
def closed(
    session: Annotated[str, _SESSION],
    *,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """End the game, and say whether it ended when asked."""
    record = _session(session, root)
    try:
        answer = send(session, "close", root=root)
    except PolyweaveError as ended:
        return {"session": session, "closed": True, "why": ended.message}
    deadline = time.monotonic() + 30
    while _alive(record["pid"]) and time.monotonic() < deadline:
        time.sleep(0.2)
    _forget(record, root)
    return {
        "session": session,
        "closed": not _alive(record["pid"]),
        "frame": answer["frame"],
        "errors": answer["errors"],
    }
