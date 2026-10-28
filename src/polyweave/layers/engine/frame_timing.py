"""Play timed by frames, named where it is written (§PW657).

`game.replay_rates` (§PW640) finds a drift once a run flown at another frame rate parts
from the first, and only in what the state kit names. Spinhold's causes were each a
pattern in a script, which a read of the game's own `.gd` files names at its line before
anything runs:

- a member `_process` writes and `_physics_process` reads: a hit stop counted down per
  frame, read per tick;
- `Engine.time_scale` set inside a physics step, which reaches the next tick only where
  that tick starts a new frame;
- an `await` on an AnimationPlayer's or a Tween's signal where nothing in the script
  puts it on the physics clock.

It is pattern work, not a parse: a finding is a place to look, a warning and never an
error, and a script it cannot read is said rather than counted clean.
"""

from __future__ import annotations

import re
from pathlib import Path

#: A function's head at the top level of a script, and the line it starts on.
_FUNC = re.compile(r"^(?:static\s+)?func\s+(?P<name>\w+)\s*\(", re.MULTILINE)
#: A member declared at the top level.
_MEMBER = re.compile(r"^(?:@\w+(?:\([^)]*\))?\s+)*var\s+(?P<name>\w+)", re.MULTILINE)
#: An assignment, not a comparison.
_WRITE = r"(?<![\w.]){name}\s*(?:[-+*/%]?=)(?!=)"
_SCALE = re.compile(r"Engine\.time_scale\s*=(?!=)")
_AWAIT = re.compile(r"await\s+(?P<what>[\w.()\[\]\"']+)\.(?P<signal>animation_finished|"
                    r"finished|tween_finished)\b")
#: What puts an AnimationPlayer or a Tween on the physics clock.
_PHYSICS = re.compile(r"ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS|TWEEN_PROCESS_PHYSICS|"
                      r"callback_mode_process\s*=\s*1\b")

#: The engine's and the plugins' code, which is not the game's own play.
_SKIP = {"addons"}


def _bodies(text: str) -> dict[str, tuple[int, list[str]]]:
    """Each top-level function's first body line number and its lines."""
    lines = text.splitlines()
    heads = [(text.count("\n", 0, m.start()), m["name"]) for m in _FUNC.finditer(text)]
    out = {}
    for index, (at, name) in enumerate(heads):
        end = heads[index + 1][0] if index + 1 < len(heads) else len(lines)
        out[name] = (at + 2, lines[at + 1:end])
    return out


def hazards(here: Path) -> dict:
    """Every frame-timed pattern in the game's own scripts, as `engine.check` findings,
    and the scripts it could not read."""
    from polyweave.kernel.files import project_files

    found, unread, read = [], [], 0
    for path in project_files(here, "*.gd"):
        parts = path.relative_to(here).parts
        if any(p in _SKIP for p in parts):
            continue
        res = "res://" + path.relative_to(here).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unread.append(res)
            continue
        read += 1
        found += _members(text, res) + _scales(text, res) + _awaits(text, res)
    return {"findings": found, "scripts": read, "unread": unread}


def _members(text: str, res: str) -> list[dict]:
    from .integrity import _finding

    bodies = _bodies(text)
    if "_process" not in bodies or "_physics_process" not in bodies:
        return []
    first, frame = bodies["_process"]
    tick = "\n".join(bodies["_physics_process"][1])
    out = []
    for member in {m["name"] for m in _MEMBER.finditer(text)}:
        if not re.search(rf"(?<![\w.]){member}\b", tick):
            continue
        written = re.compile(_WRITE.format(name=re.escape(member)))
        for offset, line in enumerate(frame):
            if written.search(line):
                out.append(_finding(
                    "engine.frame-timed", res, first + offset,
                    f"_process writes {member}, which _physics_process reads: it moves "
                    "per frame and is read per tick, so play parts at another rate",
                    f"write {member} in _physics_process, or read it in _process"))
                break
    return out


def _scales(text: str, res: str) -> list[dict]:
    from .integrity import _finding

    first, tick = _bodies(text).get("_physics_process", (0, []))
    return [_finding(
        "engine.frame-timed", res, first + offset,
        "Engine.time_scale is set inside a physics step, and reaches the next tick "
        "only where that tick starts a new frame",
        "set time_scale outside _physics_process, between frames")
        for offset, line in enumerate(tick) if _SCALE.search(line)]


def _awaits(text: str, res: str) -> list[dict]:
    from .integrity import _finding

    if _PHYSICS.search(text):
        return []
    return [_finding(
        "engine.frame-timed", res, text.count("\n", 0, m.start()) + 1,
        f"play waits on {m['what']}.{m['signal']}, which steps on the idle clock, so "
        "the wait ends on a frame, not a tick",
        "put the player or tween on the physics clock: callback_mode_process = "
        "ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS, or set_process_mode(Tween."
        "TWEEN_PROCESS_PHYSICS)")
        for m in _AWAIT.finditer(text)]
