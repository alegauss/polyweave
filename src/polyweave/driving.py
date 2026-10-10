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
    "driver.shot-not-written",
    "driver.off-screen",
    "driver.no-state",
)

#: How long a game may take to load before it says where it listens.
OPENING_S = 120.0

_SESSION = Param("the session game.open answered")
_ROOT = Param("the project the game belongs to")


def _driver_for(here: Path) -> tuple[str, Path]:
    """The driver a game is launched with, as the engine is told it, and its file.

    The project's own copy where it installed one, so a pinned version is the one that
    runs; otherwise the one polyweave carries, run from outside the project, so
    driving a game needs nothing written into its tree (§PW216).
    """
    installed = here / DRIVER.removeprefix("res://")
    if installed.is_file():
        return DRIVER, installed
    from .godot import ADDONS

    carried = ADDONS["polyweave_driver"] / installed.name
    return carried.resolve().as_posix(), carried


def _own_user(where: Path) -> dict:
    """An environment giving a driven game a fresh `user://` of its own (§PW217).

    Godot puts user:// under the platform's per-user data folder, APPDATA on Windows and
    XDG_DATA_HOME on Linux, so a session or a replay pointed at an empty folder starts
    from a fresh save and never reads or writes the person's own. A flow then replays
    the same whatever the person has played since.
    """
    import shutil

    if where.exists():
        shutil.rmtree(where)
    where.mkdir(parents=True)
    return {"APPDATA": str(where), "XDG_DATA_HOME": str(where)}


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
    return json.loads(where.read_text(encoding="utf-8-sig"))


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
    resolution: Annotated[
        list, Param("[width, height] of the window; [capture]'s where unset")
    ] = None,
    locale: Annotated[str, Param("the game's language; [capture]'s if unset")] = None,
) -> dict:
    """Launch the game held at its first frame, and answer the session to drive it with.

    The project need install nothing: where it has no polyweave_driver addon, the
    driver polyweave carries is run from outside it (§PW216). The game runs until
    game.close, or `[driving] idle` seconds with no call. It runs in the environment
    `[capture]` declares, its resolution and locale, as capture.run's pictures are,
    unless the call names its own (§PW339).
    """
    from .capture import _size_of

    settings = load(root)
    here = settings.root
    script, _ = _driver_for(here)
    wanted = list(resolution) if resolution else settings.get("capture.resolution")
    size = _size_of("x".join(str(int(v)) for v in wanted or ()))
    language = settings.get("capture.locale") if locale is None else locale
    args = ["--path", str(here), "--fixed-fps", str(settings.get("engine.fixed_fps"))]
    if size:
        # On the engine's command line, which beats the project's window override.
        args += ["--resolution", size]
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
    if language:
        after.append(f"--locale={language}")
    folder = _folder(here)
    folder.mkdir(parents=True, exist_ok=True)
    session = "g" + secrets.token_hex(4)
    log = folder / f"{session}.log"
    command = [*through, engine.find(here), *args, "--script", script, "--", *after]
    with log.open("w", encoding="utf-8") as out:
        # Its own process group, so it outlives a command line that opened it.
        extra: dict[str, Any] = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if sys.platform == "win32"
            else {"start_new_session": True}
        )
        own = _own_user(folder / f"{session}.user")
        process = subprocess.Popen(
            command,
            cwd=here,
            stdout=out,
            stderr=subprocess.STDOUT,
            env={**os.environ, **own},
            **extra,
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
        "environment": {"resolution": size or None, "locale": language or None},
        "seed": int(seed or 0),
        "scene": scene,
        # Every command that answered, in order, for game.keep (§PW214).
        "journal": [],
    }
    (folder / f"{session}.json").write_text(json.dumps(record), encoding="utf-8")
    first = send(
        session, "query", root=here, journal=False, path="/root", properties=["name"]
    )
    return {
        "session": session,
        "frame": first["frame"],
        "pid": process.pid,
        "log": str(log),
        "environment": record["environment"],
    }


def send(
    session: str,
    cmd: str,
    *,
    root: str | Path = ".",
    journal: bool = True,
    **fields: Any,
) -> dict:
    """One command to a held game, and its answer with what the engine printed since.

    An answered command is journalled, and the answer's `step` is its place in the
    journal, which is how game.keep is told what to drop and what to hold a flow to.
    """
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
    step = None
    if journal and cmd != "close":
        kept = {"cmd": cmd, **fields}
        if cmd in ("query", "wait"):
            kept["answered"] = answer.get("result")
        # Asked now, while the nodes are there: no frame has passed since the command.
        selectors = _selectors(session, root, cmd, fields, answer.get("result"))
        if selectors:
            kept["selectors"] = selectors
        record = _session(session, root)  # the selector reads moved its log offset
        record.setdefault("journal", []).append(kept)
        step = len(record["journal"]) - 1
        (_folder(root) / f"{session}.json").write_text(
            json.dumps(record), encoding="utf-8"
        )
    return {
        "frame": answer.get("frame"),
        "result": answer.get("result"),
        "errors": printed["errors"],
        "step": step,
    }


def _generated(path: Any) -> bool:
    """Whether a node path holds a name Godot generated, which reordering renumbers."""
    return isinstance(path, str) and "@" in path


def _selectors(session: str, root, cmd: str, fields: dict, result: Any) -> dict:
    """A selector for each generated path a command used or answered (§PW270)."""
    paths = [fields.get("path"), (fields.get("click") or {}).get("path")
             if isinstance(fields.get("click"), dict) else None]
    if cmd == "query" and isinstance(result, list):
        paths += [one.get("path") for one in result if isinstance(one, dict)]
    found = {}
    for path in dict.fromkeys(p for p in paths if _generated(p)):
        try:
            said = send(session, "selector", root=root, journal=False, path=path)
        except PolyweaveError:
            continue
        chosen = (said.get("result") or {}).get("select")
        if chosen:
            found[path] = chosen
    return found


def _selected(fields: dict, selectors: dict) -> dict:
    """A kept step with each generated path it used put as the selector found for it."""
    out = dict(fields)
    if out.get("path") in selectors:
        out["select"] = selectors[out.pop("path")]
    click = out.get("click")
    if isinstance(click, dict) and click.get("path") in selectors:
        out["click"] = {"select": selectors[click["path"]]}
    return out


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
    state: Annotated[
        list, Param("names the state kit declares, or ['*'] for every one")
    ] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """The nodes a path, group or class finds, with their properties, the game held.

    `state` reads names the project declared with the state kit instead, each with its
    value and type, so `state=["health"]` needs no node path (§PW359).
    """
    if state:
        if path or group or of_class:
            raise PolyweaveError(
                "game.bad-target",
                "a query reads declared state or finds nodes, not both",
                "give state alone, or one of path, group and of_class",
            )
        return send(session, "state", root=root, names=list(state))
    fields = _node(path, group, of_class)
    if properties:
        fields["properties"] = list(properties)
    return send(session, "query", root=root, **fields)


@operation("game.text_fit")
def text_fit(
    session: Annotated[str, _SESSION],
    *,
    locale: Annotated[
        str, Param("a locale to switch the game to first, such as pt_BR")
    ] = "",
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Every visible Label and Button, and whether its text fits on screen (§PW336).

    Per node: its key and the text shown, its box, the lines it took against those it
    shows, and `findings`: text wider than its box, lines it cannot show, a box out of
    its container, and text it lies over. `locale` switches the game's language first,
    so a project sweeps each screen in each language and a finding names the key.
    """
    if locale:
        send(session, "locale", root=root, locale=locale)
    nodes = send(session, "text_fit", root=root)["result"]
    unfit = [one for one in nodes if one.get("findings")]
    return {
        "locale": locale or None,
        "nodes": nodes,
        "unfit": [{"path": one["path"], "key": one["key"], "findings": one["findings"]}
                  for one in unfit],
        "passed": not unfit,
        "says": f"{len(nodes)} text node(s), {len(unfit)} that do not fit",
    }


@operation("game.input")
def inputted(
    session: Annotated[str, _SESSION],
    *,
    action: Annotated[str, Param("an input action, pressed and released")] = "",
    key: Annotated[str, Param("a key by name, e.g. Space")] = "",
    click: Annotated[str, Param("a node's path to click at the centre of")] = "",
    at: Annotated[list, Param("a point in the viewport to click, [x, y]")] = (),
    hold: Annotated[bool, Param("press the action or key and keep it held")] = False,
    release: Annotated[bool, Param("release an action or key held before")] = False,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Press an action or a key, or click a node or a point; it lands next frame."""
    halves = {k: True for k, v in (("hold", hold), ("release", release)) if v}
    if action:
        return send(session, "input", root=root, action=action, **halves)
    if key:
        return send(session, "input", root=root, key=key, **halves)
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


@operation("game.set")
def set_value(
    session: Annotated[str, _SESSION],
    *,
    path: Annotated[str, Param("the node the property is on")],
    prop: Annotated[str, Param("the property; a nested one as rng:seed")],
    value: Annotated[str, Param("the value to set, as JSON")],
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Set a property for setup, such as the seed of a generator the game made itself.

    The driver's seed covers the global random functions only; a game drawing from its
    own RandomNumberGenerator repeats only once a flow seeds that too (§PW217).
    """
    try:
        wanted = json.loads(value)
    except json.JSONDecodeError:
        wanted = value  # a bare word is the string it spells
    return send(session, "set", root=root, path=path, property=prop, value=wanted)


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
    display, since a headless run draws nothing. The answer says the environment it
    was taken in, the size and locale, beside the one the session asked, and
    `differs` names any that are not (§PW339).
    """
    answer = send(session, "shot", root=root, out=_shot_to(out, root))
    took = answer.get("result") or {}
    asked = _session(session, root).get("environment") or {}
    size = took.get("size")
    environment = {
        "resolution": f"{size[0]}x{size[1]}" if size else None,
        "locale": took.get("locale"),
    }
    differs = [
        f"{key} is {environment[key]}, and the session asked {asked[key]}"
        for key in ("resolution", "locale")
        if asked.get(key) and environment[key] and not (
            environment[key] == asked[key]
            or (key == "locale" and str(environment[key]).startswith(str(asked[key])))
        )
    ]
    return {**answer, "environment": environment, "asked": asked, "differs": differs}


def _shot_to(out: Any, root: str | Path) -> str:
    """Where a shot goes, absolute under the project, its folder made (§PW373).

    game.shot and a batch's shot both come through here, so neither hands the game a
    folder that is not there; a folder that cannot be made is refused before the game
    is asked, and the driver refuses a save that wrote nothing.
    """
    where = Path(str(out or ""))
    if not str(out or "").strip():
        raise PolyweaveError(
            "game.bad-target", "a shot names no file to write",
            "pass out, a .png path under the project",
        )
    if not where.is_absolute():
        where = load(root).root / where
    try:
        where.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PolyweaveError(
            "driver.shot-not-written",
            f"the shot cannot be written to {where}: its folder cannot be made",
            "name a folder under the project the game can write to",
            detail=str(exc),
        ) from exc
    return str(where)


#: The commands a batch may send: the session's own, each journalled as its tool's is.
BATCHED = ("query", "input", "step", "wait", "call", "set", "expect", "shot")


@operation("game.batch")
def batched(
    session: Annotated[str, _SESSION],
    commands: Annotated[
        list,
        Param("the commands in order, each as the driver takes it: "
              '{"cmd": "input", "click": {"path": "UI/Play"}}'),
    ],
    *,
    keep_going: Annotated[bool, Param("carry on past a refused command")] = False,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Send several commands to a held game in one call, answering each (§PW271).

    A loop of query, input and wait from the command line paid a process per call, and a
    level of thirty moves cost hundreds. Each command is journalled with its `step`, as
    its own tool's would be, so game.keep keeps a batch like any other calls. The first
    refusal stops the batch and is answered in its place, unless `keep_going`.
    """
    if not isinstance(commands, list | tuple) or not commands:
        raise PolyweaveError(
            "game.bad-target",
            "a batch needs a list of commands",
            f'pass commands, each {{"cmd": <one of {", ".join(BATCHED)}>, ...}}',
        )
    answers, stopped = [], None
    for index, one in enumerate(commands):
        cmd = one.get("cmd") if isinstance(one, dict) else None
        if cmd not in BATCHED:
            raise PolyweaveError(
                "game.bad-target",
                f"command {index} is {one!r}, not one a batch sends",
                f"make each a table with cmd, one of {', '.join(BATCHED)}",
                given=str(cmd),
                allowed=list(BATCHED),
            )
        fields = {k: v for k, v in one.items() if k != "cmd"}
        try:
            if cmd == "shot":
                fields["out"] = _shot_to(fields.get("out"), root)
            answers.append({"index": index, **send(session, cmd, root=root, **fields)})
        except PolyweaveError as refused:
            answers.append({"index": index, "refused": refused.as_dict()})
            if not keep_going:
                stopped = index
                break
    return {
        "answers": answers,
        "sent": len(answers),
        "stopped": stopped,
        "frame": next(
            (a.get("frame") for a in reversed(answers) if "frame" in a), None
        ),
    }


#: What a flow file is written as, and the one version of it the driver reads.
FLOW_FORMAT = 1

#: The line a replayed flow ends on.
FLOWED = re.compile(
    r"polyweave_flow: (?P<verdict>passed|failed) (?:steps=(?P<steps>\d+) )?"
    r"(?:step=(?P<step>\d+) )?frame=(?P<frame>\d+)(?: why=(?P<why>.*))?"
)


def _engine_version(log: str) -> str:
    found = re.search(r"Godot Engine v(\S+)", log)
    return found[1] if found else ""


def _driver_hash(root: Path) -> str:
    import hashlib

    _, where = _driver_for(root)
    return hashlib.sha256(where.read_bytes()).hexdigest()


@operation("game.keep")
def kept(
    session: Annotated[str, _SESSION],
    *,
    out: Annotated[str, Param("the flow file to write, under the project's tests")],
    proves: Annotated[str, Param("what the flow proves, in a sentence")],
    expect: Annotated[
        list, Param("the steps of queries whose values the flow must see again")
    ] = (),
    drop: Annotated[list, Param("the steps that were wrong turns, left out")] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Write what the session did as a flow that replays without an agent (§PW214).

    Each answer's `step` numbers the journal. Inputs, steps, calls and waits are kept in
    order; a query is kept only where `expect` names it, as the values it answered; a
    shot is left out, since a replay draws nothing. Nothing is kept on its own, because
    a session includes wrong turns.
    """
    record = _session(session, root)
    journal = record.get("journal") or []
    wanted, dropped = {int(i) for i in expect}, {int(i) for i in drop}
    wrong = sorted(
        i for i in wanted if i >= len(journal) or journal[i]["cmd"] != "query"
    )
    if wrong:
        raise PolyweaveError(
            "game.bad-target",
            f"step {wrong[0]} is no query this session answered, so there is "
            "nothing to expect from it",
            "name in expect the step of a game.query, as its answer numbered it",
            given=wrong[0],
        )
    steps: list[dict] = []
    for index, entry in enumerate(journal):
        if index in dropped:
            continue
        cmd = entry["cmd"]
        selectors = entry.get("selectors") or {}
        fields = _selected(
            {k: v for k, v in entry.items() if k not in ("answered", "selectors")},
            selectors,
        )
        if cmd == "query":
            if index in wanted:
                for node in entry.get("answered") or ():
                    for name, value in node["properties"].items():
                        steps.append(_selected(
                            {
                                "cmd": "expect",
                                "path": node["path"],
                                "property": name,
                                "equals": value,
                            },
                            selectors,
                        ))
        elif cmd == "wait":
            answered = entry.get("answered") or {}
            steps.append({**fields, "must": bool(answered.get("met", True))})
        elif cmd != "shot":
            steps.append(fields)
    here = load(root).root
    where = Path(out)
    where = where if where.is_absolute() else here / where
    log = Path(record["log"])
    flow = {
        "format": FLOW_FORMAT,
        "proves": proves,
        "seed": record.get("seed", 0),
        "scene": record.get("scene", ""),
        "engine": _engine_version(
            log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        ),
        "driver": _driver_hash(here),
        "steps": steps,
    }
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("w", encoding="utf-8", newline="\n") as written:
        written.write(json.dumps(flow, indent=2) + "\n")
    # A generated path no selector picked out stays, and is said, since a node added
    # ahead of it breaks the flow (§PW270).
    fragile = sorted({
        one for step in steps
        for one in (step.get("path"), (step.get("click") or {}).get("path")
                    if isinstance(step.get("click"), dict) else None)
        if _generated(one)
    })
    return {
        "flow": str(where),
        "steps": len(steps),
        "expectations": sum(1 for one in steps if one["cmd"] == "expect"),
        "proves": proves,
        "fragile": fragile,
    }


@operation("game.record_flow")
def record_flow(
    record: Annotated[str, Param("a record PolyweaveRecorder saved, as a path")],
    *,
    out: Annotated[str, Param("the flow file to write, under the project's tests")],
    proves: Annotated[str, Param("what the flow proves, in a sentence")],
    expect: Annotated[
        list, Param("{path, property, equals} the run must end on, the bug's place")
    ] = (),
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """A run a player recorded, written as a flow game.replay runs in the gate (§PW360).

    The determinism kit's record holds the run's seed and each action's press and
    release by physics frame; the flow steps to each frame, holds or releases the
    action there, and ends on the expectations given, which is where a bug seen once
    becomes a test that fails until it is fixed. A step is one frame, which is one
    physics frame where the project ticks physics at the engine's fixed rate.
    """
    here = load(root).root
    source = Path(record) if Path(record).is_absolute() else here / record
    try:
        held = json.loads(source.read_text(encoding="utf-8"))
        events = sorted(held["events"], key=lambda e: int(e["frame"]))
    except (OSError, ValueError, KeyError, TypeError) as failed:
        raise PolyweaveError(
            "game.bad-target",
            f"{record} is no record the determinism kit saved: {failed}",
            "save one with PolyweaveRecorder.save() and name the file it printed",
            given=record,
        ) from None
    steps: list[dict] = []
    at = 0
    for event in events:
        frame = int(event["frame"])
        if frame > at:
            steps.append({"cmd": "step", "frames": frame - at})
            at = frame
        half = {"hold": True} if event["pressed"] else {"release": True}
        steps.append({"cmd": "input", "action": str(event["action"]), **half})
    steps.append({"cmd": "step", "frames": 1})
    for one in expect or ():
        steps.append({"cmd": "expect", "path": one["path"], "property": one["property"],
                      "equals": one["equals"]})
    flow = {"format": FLOW_FORMAT, "proves": proves, "seed": int(held.get("seed", 0)),
            "scene": "", "engine": "", "driver": _driver_hash(here), "steps": steps}
    where = Path(out) if Path(out).is_absolute() else here / out
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("w", encoding="utf-8", newline="\n") as written:
        written.write(json.dumps(flow, indent=2) + "\n")
    return {
        "flow": str(where),
        "steps": len(steps),
        "seed": flow["seed"],
        "expectations": len(expect or ()),
        "says": "" if expect else "the flow expects nothing yet: name with expect "
        "the value the bug leaves wrong, so it fails until the bug is fixed",
    }


def _user_dir(root: str | Path = ".") -> Path:
    """Where Godot keeps a project's user:// here, by the name project.godot gives."""
    here = load(root).root
    text = (here / "project.godot").read_text(encoding="utf-8-sig", errors="replace")

    def said(key: str) -> str:
        found = re.search(rf'^{re.escape(key)}=(.*)$', text, re.MULTILINE)
        return found[1].strip().strip('"') if found else ""

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    if said("config/use_custom_user_dir") == "true":
        return base / (said("config/custom_user_dir_name") or said("config/name"))
    return base / ("Godot" if sys.platform != "linux" else "godot") / "app_userdata" / (
        said("config/name") or "[unnamed project]")


@operation("game.crash_read")
def crash_read(
    capture: Annotated[
        str, Param("a capture a person sent; the newest on this machine where unset")
    ] = "",
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """What a crash left: its error, script and line, the state and the log (§PW361).

    The crash kit packs a capture in user://polyweave_log/captures/ on every error, and
    on the launch after a run that never closed its log. This reads one back: a file a
    person sent, or the newest of this machine's, found where Godot keeps the project's
    user:// for its name. The answer is the error with its script and line, the state
    kit's snapshot, the seed where the determinism kit gave one, and the log's last
    lines, so an agent starts from the facts rather than from a retelling.
    """
    if capture:
        where = Path(capture)
        where = where if where.is_absolute() else load(root).root / capture
        others: list[Path] = []
    else:
        folder = _user_dir(root) / "polyweave_log" / "captures"
        others = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not others:
            raise PolyweaveError(
                "game.no-capture",
                f"there is no capture in {folder}",
                "install the crash kit and open its log first thing, or name the "
                "capture a person sent",
            )
        where = others[-1]
    try:
        packed = json.loads(where.read_text(encoding="utf-8"))
    except (OSError, ValueError) as failed:
        raise PolyweaveError(
            "game.no-capture",
            f"{where} is no capture the crash kit packed: {failed}",
            "name the .json file in user://polyweave_log/captures/",
        ) from None
    error = packed.get("error") or {}
    return {
        "capture": str(where),
        "reason": packed.get("reason"),
        "error": error,
        "at": f"{error['script']}:{error['line']}" if error.get("script") else None,
        "state": packed.get("state"),
        "seed": packed.get("seed"),
        "lines": packed.get("lines", [])[-10:],
        "captures": len(others),
        "says": (f"{packed.get('reason')}: {error.get('said', '')}"
                 + (f" at {error['script']}:{error['line']}"
                    if error.get("script") else "")),
    }


def _step_paths(step: dict) -> list[str]:
    """The generated paths one kept step reaches its node by."""
    click = step.get("click")
    found = [step.get("path"), click.get("path") if isinstance(click, dict) else None]
    return [one for one in found if _generated(one)]


@operation("game.rekey")
def rekeyed(
    flow: Annotated[str, Param("the flow file to re-key, as game.keep wrote it")],
    *,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Put a selector in place of each generated path an older flow reaches by (§PW276).

    The flow is sent step by step through a held session at its own seed and scene, as
    a replay would, and before each step the driver is asked what picks out every
    generated path it uses, while the node is there. The flow is written back with
    those selectors; a path none could pick out stays and is named in `fragile`, and
    naming the node in the game or giving its script a class_name is what cures it.
    """
    here = load(root).root
    where = Path(flow)
    where = where if where.is_absolute() else here / where
    if not where.is_file():
        raise PolyweaveError(
            "game.no-flow",
            f"there is no flow at {where}",
            "name a .flow.json game.keep wrote, under the project",
        )
    kept = json.loads(where.read_text(encoding="utf-8-sig"))
    session = opened(root, scene=kept.get("scene", ""), seed=int(kept.get("seed", 0)))
    selectors: dict[str, dict] = {}
    broke = None
    try:
        for index, step in enumerate(kept.get("steps") or []):
            for path in _step_paths(step):
                if path in selectors:
                    continue
                try:
                    said = send(session["session"], "selector", root=root,
                                journal=False, path=path)
                except PolyweaveError:
                    continue
                chosen = (said.get("result") or {}).get("select")
                if chosen:
                    selectors[path] = chosen
            fields = {k: v for k, v in step.items() if k != "cmd"}
            try:
                send(session["session"], step["cmd"], root=root, journal=False,
                     **fields)
            except PolyweaveError as refused:
                broke = {"step": index, "code": refused.code, "why": refused.message}
                break
    finally:
        closed(session["session"], root=root)
    if broke is not None:
        raise PolyweaveError(
            "game.flow-broke",
            f"the flow broke at step {broke['step']} while being re-keyed: "
            f"{broke['why']}",
            "replay it with game.replay and mend it first; nothing was written",
            detail=broke["code"],
        )
    steps = [_selected(step, selectors) for step in kept.get("steps") or []]
    fragile = sorted({one for step in steps for one in _step_paths(step)})
    kept["steps"] = steps
    with where.open("w", encoding="utf-8", newline="\n") as written:
        written.write(json.dumps(kept, indent=2) + "\n")
    return {
        "flow": str(where),
        "rekeyed": len(selectors),
        "selectors": selectors,
        "fragile": fragile,
    }


@operation("game.replay")
def replayed(
    flow: Annotated[str, Param("the flow file game.keep wrote")],
    *,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Run a kept flow in one launch, no agent: every expectation held or the first that
    broke, with the frame it broke on (§PW214)."""
    here = load(root).root
    where = Path(flow)
    where = where if where.is_absolute() else here / where
    if not where.is_file():
        raise PolyweaveError(
            "game.no-flow",
            f"there is no flow at {where}",
            "write one with game.keep, and name it relative to the project",
        )
    stated = json.loads(where.read_text(encoding="utf-8-sig"))
    if stated.get("format") != FLOW_FORMAT:
        raise PolyweaveError(
            "game.no-flow",
            f"{where.name} is flow format {stated.get('format')!r}, and this reads "
            f"{FLOW_FORMAT}",
            "keep the flow again with game.keep",
        )
    budget = sum(
        int(one.get("frames", 1))
        for one in stated["steps"]
        if one["cmd"] in ("step", "wait")
    )
    found = engine.run(
        _driver_for(here)[1],
        expect=FLOWED,
        root=here,
        headless=True,
        frames=max(int(load(here).get("engine.frames")), budget + 600),
        args=("--", f"--flow={where.as_posix()}"),
        env=_own_user(_folder(here) / "replay.user"),
    )
    said = found.get("found") or {}
    passed = found["ok"] and said.get("verdict") == "passed"
    log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
    moved = {}
    if stated.get("engine") and _engine_version(log) not in ("", stated["engine"]):
        moved["engine"] = [stated["engine"], _engine_version(log)]
    if stated.get("driver") and _driver_hash(here) != stated["driver"]:
        moved["driver"] = "the driver changed since this flow was kept"
    return {
        "ok": passed,
        "proves": stated.get("proves", ""),
        "steps": len(stated["steps"]),
        "frame": int(said["frame"]) if said.get("frame") else None,
        "failed_step": int(said["step"]) if said.get("step") else None,
        "why": said.get("why") or ("" if passed else found.get("why", "")),
        "differs": moved,
        "log": found["log"],
    }


#: Where the driver's files sit in a project, as an export filter and a pack spell them.
ADDON = "addons/polyweave_driver/"


def _presets(text: str) -> list[dict]:
    """Each `[preset.N]` table of export_presets.cfg: its keys, and their lines."""
    presets: list[dict] = []
    current: dict | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        header = re.fullmatch(r"\s*\[preset\.(\d+)\]\s*", line)
        if header:
            current = {"index": int(header[1]), "line": number, "keys": {}}
            presets.append(current)
            continue
        if line.strip().startswith("["):
            current = None
            continue
        pair = re.fullmatch(r"\s*([\w/.]+)\s*=\s*(.*?)\s*", line)
        if current is not None and pair:
            current["keys"][pair[1]] = (pair[2].strip('"'), number)
    return presets


def _patterns(value: str) -> list[str]:
    return [one.strip() for one in value.split(",") if one.strip()]


def _matches(patterns: list[str], path: str) -> bool:
    import fnmatch

    return any(
        fnmatch.fnmatch(path, one) or fnmatch.fnmatch("res://" + path, one)
        for one in patterns
    )


def left_out(here: Path, path: Path) -> str:
    """Why a Godot export would leave `path` out of the game, or "" where it ships.

    A folder above it holding a .gdignore is never imported, and a preset exporting
    all resources leaves out what its exclude_filter names (§PW374). One preset that
    leaves it out is enough: that build cannot load what is there.
    """
    relative = Path(path).resolve().relative_to(here.resolve())
    for depth in range(len(relative.parts)):
        if (here.joinpath(*relative.parts[:depth]) / ".gdignore").exists():
            folder = "/".join(relative.parts[:depth]) or "the project"
            return f"{folder} holds a .gdignore"
    presets_file = here / "export_presets.cfg"
    if not presets_file.is_file():
        return ""
    posix = relative.as_posix()
    for preset in _presets(presets_file.read_text(encoding="utf-8")):
        keys = preset["keys"]
        name = keys.get("name", (f"preset.{preset['index']}", 0))[0]
        if keys.get("export_filter", ("all_resources", 0))[0] != "all_resources":
            continue
        if _matches(_patterns(keys.get("exclude_filter", ("", 0))[0]), posix):
            return f"the {name} preset's exclude_filter leaves it out"
    return ""


@operation("game.release_check")
def release_checked(
    root: Annotated[str, _ROOT] = ".",
    *,
    pack: Annotated[
        str, Param("an exported .pck to look inside, if there is one")
    ] = "",
    strict: Annotated[bool, Param("refuse on the first finding, as a gate")] = False,
) -> dict:
    """Whether the driver could ship to a player: presets, autoloads, a pack (§PW215).

    A listener that runs any method it is asked to is a way into a game, so its
    absence from a release is checked rather than assumed. It reads and spends nothing,
    and never edits a preset: each finding names the preset and the line to change.
    """
    here = load(root).root
    driver = DRIVER.removeprefix("res://")
    findings: list[dict] = []
    presets_file = here / "export_presets.cfg"
    # A project that installed no driver has none a preset could ship: the one
    # polyweave carries runs from outside it (§PW216), so only an installed copy needs
    # the exclusion. Cottony's release check found the preset flagged for nothing.
    if presets_file.is_file() and (here / ADDON).is_dir():
        for preset in _presets(presets_file.read_text(encoding="utf-8")):
            keys = preset["keys"]
            name = keys.get("name", (f"preset.{preset['index']}", preset["line"]))[0]
            mode = keys.get("export_filter", ("all_resources", preset["line"]))[0]
            excluded = _matches(
                _patterns(keys.get("exclude_filter", ("", 0))[0]), driver
            )
            included = _matches(
                _patterns(keys.get("include_filter", ("", 0))[0]), driver
            )
            ships = (mode == "all_resources" and not excluded) or (
                mode != "all_resources" and included and not excluded
            )
            if ships:
                line = keys.get("exclude_filter", (None, preset["line"]))[1]
                findings.append(
                    {
                        "code": "game.driver-exported",
                        "preset": name,
                        "at": f"export_presets.cfg:{line}",
                        "why": f"the {name} preset exports {driver}",
                        "fix": f'add "{ADDON}*" to its exclude_filter',
                    }
                )
    project = here / "project.godot"
    if project.is_file():
        section = ""
        for number, line in enumerate(
            project.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.strip().startswith("["):
                section = line.strip()
            elif section == "[autoload]" and "polyweave_driver" in line:
                findings.append(
                    {
                        "code": "game.driver-autoloaded",
                        "preset": "",
                        "at": f"project.godot:{number}",
                        "why": "an autoload loads the driver in every run, a "
                        "release too",
                        "fix": "remove that autoload; the driver is launched with "
                        "--script",
                    }
                )
    read_pack = False
    if pack:
        where = Path(pack)
        where = where if where.is_absolute() else here / where
        if not where.is_file():
            raise PolyweaveError(
                "game.no-pack",
                f"there is no exported pack at {where}",
                "export the release first, or leave pack out to check the presets",
            )
        data = where.read_bytes()
        read_pack = True
        # A pack header is GDPC, then format, major, minor, patch and flags (format 2
        # on), each 32 bits; flag 1 is an encrypted directory, which no search can read.
        encrypted = (
            data[:4] == b"GDPC"
            and len(data) >= 24
            and int.from_bytes(data[4:8], "little") >= 2
            and int.from_bytes(data[20:24], "little") & 1
        )
        if encrypted:
            findings.append(
                {
                    "code": "game.pack-unread",
                    "preset": "",
                    "at": str(where),
                    "why": f"{where.name}'s directory is encrypted, so whether it "
                    "holds "
                    "the driver cannot be read",
                    "fix": "check the preset instead, or export a pack without "
                    "directory encryption to check it",
                }
            )
        elif ADDON.encode("utf-8") in data:
            findings.append(
                {
                    "code": "game.driver-in-pack",
                    "preset": "",
                    "at": str(where),
                    "why": f"{where.name} holds files under {ADDON}",
                    "fix": f'exclude "{ADDON}*" from the preset that made it, and '
                    "export "
                    "again",
                }
            )
    if strict and findings:
        first = findings[0]
        raise PolyweaveError(
            first["code"],
            f"{first['why']} ({first['at']})",
            first["fix"],
            detail="\n".join(f"{one['at']}: {one['why']}" for one in findings[1:])
            or None,
        )
    return {
        "ok": not findings,
        "findings": findings,
        "presets": presets_file.is_file(),
        "pack": read_pack,
    }


#: The preset platform this machine can launch, by Godot's own name for it.
_HOST = {"win32": "Windows Desktop", "linux": "Linux"}

#: What an exported build prints when the export left something out or broke it.
_BROKE = re.compile(
    r"No loader found|Failed loading resource|Resource file not found|Cannot open file"
    r"|Failed to load|SCRIPT ERROR|Parse Error|Compile Error"
)


@operation("game.export_smoke")
def export_smoke(
    flow: Annotated[
        str, Param("a kept flow to run in each export, through to the menu and back")
    ] = "",
    presets: Annotated[
        list, Param("the presets to export; every one for this machine where unset")
    ] = (),
    frames: Annotated[
        int, Param("frames the plain run plays before it quits", lo=1)
    ] = 120,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Each export preset built and launched, as a player would launch it (§PW363).

    Every preset for this machine's platform is exported as a debug build, and its
    binary runs headless for `frames` frames: a resource an export filter left out, a
    script stripped from it or one that does not parse prints there, and the preset is
    answered as broken with that line. With a `flow`, the exported pack also runs on
    this engine with the driver from outside it, never inside, and replays it. The
    answer says which each pass ran against, since a debug build proves less than a
    release; game.release_check is what keeps the driver out of the release itself.
    """
    here = load(root).root
    presets_file = here / "export_presets.cfg"
    if not presets_file.is_file():
        raise PolyweaveError(
            "game.no-preset",
            f"there is no export_presets.cfg in {here}, so nothing to export",
            "add an export preset in the editor's Export dialog, for this platform",
        )
    host = _HOST.get(sys.platform, "")
    godot = engine.find(here)
    work = load(here).path("paths.work") / "exports"
    engine._launch([godot, "--headless", "--import", "--path", str(here)], cwd=here,
                   timeout=600)
    flowed = Path(flow) if flow and Path(flow).is_absolute() else here / flow if flow \
        else None
    if flowed is not None and not flowed.is_file():
        raise PolyweaveError("game.no-flow", f"there is no flow at {flowed}",
                             "keep one with game.keep or game.record_flow")
    answered = []
    for preset in _presets(presets_file.read_text(encoding="utf-8")):
        name = preset["keys"].get("name", (f"preset.{preset['index']}", 0))[0]
        platform = preset["keys"].get("platform", ("", 0))[0]
        if presets and name not in presets:
            continue
        if platform != host:
            answered.append({"preset": name, "held": None, "skipped":
                             f"a {platform} build does not launch on this machine"})
            continue
        answered.append(_smoked(here, godot, work, name, flowed, frames))
    ran = [one for one in answered if one["held"] is not None]
    broke = [one for one in ran if not one["held"]]
    return {
        "ok": bool(ran) and not broke,
        "presets": answered,
        "says": (f"{len(ran)} preset(s) launched, {len(broke)} broken"
                 + (f", the first {broke[0]['preset']}: {broke[0]['why']}" if broke
                    else "")) if ran else "no preset here exports for this machine",
    }


def _smoked(here: Path, godot: str, work: Path, name: str, flow: Path | None,
            frames: int) -> dict:
    """One preset exported, its binary launched, and its pack running the flow."""
    import shutil

    out = work / re.sub(r"[^\w.-]+", "_", name)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    suffix = ".exe" if sys.platform == "win32" else ".x86_64"
    binary = out / f"game{suffix}"
    exported, _ = engine._launch(
        [godot, "--headless", "--path", str(here), "--export-debug", name, str(binary)],
        cwd=here, timeout=900)
    answer: dict = {"preset": name, "binary": str(binary),
                    "ran": "the exported debug binary"}
    if not binary.is_file():
        (out / "export.log").write_text(exported, encoding="utf-8")
        return {**answer, "held": False, "log": str(out / "export.log"),
                "why": "the export wrote no binary: "
                + (exported.strip().splitlines() or ["nothing said"])[-1]}
    console = out / "game.console.exe"
    launched = console if console.is_file() else binary
    try:
        output, _ = engine._launch(
            [str(launched), "--headless", "--quit-after", str(frames)], cwd=out,
            timeout=300, env=_own_user(out / "user"))
    except subprocess.TimeoutExpired:
        output = f"the build was still running after 300 s, past {frames} frames\n"
    (out / "run.log").write_text(output, encoding="utf-8")
    broke = [line.strip() for line in output.splitlines() if _BROKE.search(line)]
    answer.update(log=str(out / "run.log"), held=not broke,
                  why=broke[0] if broke else "")
    if flow is None or broke:
        return answer
    pack = binary.with_suffix(".pck")
    from .godot import ADDONS

    # the one polyweave carries, from outside the pack: a release never holds a driver
    driver = (ADDONS["polyweave_driver"] / Path(DRIVER).name).resolve()
    played, _ = engine._launch(
        [godot, "--headless", "--main-pack", str(pack if pack.is_file() else binary),
         "--fixed-fps", "60", "--script", driver.as_posix(), "--",
         f"--flow={flow.resolve().as_posix()}"],
        cwd=out, timeout=600, env=_own_user(out / "flow.user"))
    (out / "flow.log").write_text(played, encoding="utf-8")
    said = FLOWED.search(played)
    passed = bool(said) and said["verdict"] == "passed"
    answer["ran"] += ", and its pack on this engine with the driver from outside"
    broke_at = said["why"] if said and said["why"] else (
        "the flow did not finish in the exported pack")
    answer.update(held=passed, flow_log=str(out / "flow.log"),
                  why="" if passed else broke_at)
    return answer


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
