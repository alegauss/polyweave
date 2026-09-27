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

    The project need install nothing: where it has no polyweave_driver addon, the
    driver polyweave carries is run from outside it (§PW216). The game runs until
    game.close, or `[driving] idle` seconds with no call.
    """
    settings = load(root)
    here = settings.root
    script, _ = _driver_for(here)
    args =["--path", str(here), "--fixed-fps", str(settings.get("engine.fixed_fps"))]
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
    command = [*through, engine.find(here), *args, "--script", script, "--", *after]
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
        fields = {k: v for k, v in entry.items() if k != "answered"}
        if cmd == "query":
            if index in wanted:
                for node in entry.get("answered") or ():
                    for name, value in node["properties"].items():
                        steps.append(
                            {
                                "cmd": "expect",
                                "path": node["path"],
                                "property": name,
                                "equals": value,
                            }
                        )
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
    return {
        "flow": str(where),
        "steps": len(steps),
        "expectations": sum(1 for one in steps if one["cmd"] == "expect"),
        "proves": proves,
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
    stated = json.loads(where.read_text(encoding="utf-8"))
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
    if presets_file.is_file():
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
