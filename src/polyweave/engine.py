"""Running a scene script and coming back with a verdict rather than a log.

The evidence is §PW22: **Godot's exit code cannot be trusted.** It exits zero after a
script error and non-zero after a clean quit, so the only honest verdict is

- the line the script printed,
- the absence of an error in the output,
- and the existence of the file it claims to have written.

Cottony's capture driver encodes exactly that — a pattern for the success line,
another for the spellings of a script error, a frame budget and a wall-clock timeout —
and so does its test runner, and so does every other project that drives the engine. It
belongs here once.

**The bounds are part of the contract.** A capture settles in a few dozen frames, so a
script still running after several thousand is hung, and the run says so instead of
sitting there until the wall clock. Both bounds are set, because they catch different
failures: the frame budget ends a script the engine would otherwise loop in forever, and
the wall clock ends a run that never reaches a frame at all.

The success line is the caller's, which is what makes one runner serve a capture, a test
and a measurement run — they are the same problem with a different line printed at the
end. Nothing about any one project's spelling is compiled in here; the only pattern that
is, is the engine's own vocabulary for an error.

`run` reports. `require` is the same thing as a gate, and raises. Which one an operation
wants depends on whether a failed run is an outcome or a stop.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic
from .jobs import children

#: Every spelling the engine has for "the script is broken". This is the engine's own
#: vocabulary and not a project's convention, which is why it is the one pattern here.
#: A formatting error prints without the word SCRIPT and still aborts its own block.
ERRORS = re.compile(r"SCRIPT ERROR|Parse Error|Compile Error|String formatting error")

#: Where in the script an error came from, as the engine prints it. The output line it
#: was on says where to look in the log; this says where to look in the code.
AT = re.compile(r"\((res://[^\s:]+:\d+)\)")

#: How a script reports how far it got. Read only where the script prints it: inferring
#: a frame count from how the process ended is a guess, and a guess in a verdict is the
#: whole thing this replaces.
FRAMES = re.compile(r"\bframes: *(\d+)\b")


@operation("engine.find")
def find(
    root: Annotated[str, Param("the project whose [paths] godot is read")] = ".",
) -> str:
    """The engine binary: what the project names, then $GODOT, then PATH."""
    settings = load(root)
    named = str(settings.get("paths.godot") or "").strip()
    if settings.declared("paths.godot"):
        # A binary is the one setting allowed outside the tree, so `path` hands it back
        # unresolved. One written relative still means relative to the project.
        stated = settings.path("paths.godot")
        if not stated.is_absolute():
            stated = settings.root / stated
        if not stated.is_file():
            raise PolyweaveError(
                "engine.not-found",
                f"[paths] godot is {stated}, and there is no binary there",
                "point it at the console build, or remove it to use $GODOT or PATH",
            )
        return str(stated)
    found = os.environ.get("GODOT") or shutil.which(named or "godot")
    if not found:
        raise PolyweaveError(
            "engine.not-found",
            "no engine binary was found to run the script with",
            "set [paths] godot to the console build, set $GODOT, or put godot on PATH",
        )
    return found


def _as_res(path: Path, root: Path) -> str:
    return "res://" + path.relative_to(root).as_posix()


def _under(named: str, root: Path) -> Path:
    """A path the script printed, back as a path on this machine."""
    cleaned = named.removeprefix("res://")
    where = Path(cleaned)
    return where if where.is_absolute() else root / where


def _errors(output: str, pattern: re.Pattern) -> list[dict]:
    """Every error line, with where in the output and where in the script it began."""
    out = []
    for number, line in enumerate(output.splitlines(), start=1):
        if pattern.search(line):
            found = AT.search(line)
            out.append(
                {
                    "text": line.strip(),
                    "at": found.group(1) if found else "",
                    "output_line": number,
                }
            )
    return out


def _launch(command: list[str], *, cwd: Path, timeout: float) -> tuple[str, int]:
    """Start the engine and wait for it, leaving a trail first.

    `Popen` rather than `subprocess.run` for one reason: the pid has to be written down
    **before** anything waits on it (§PW37). A worker killed while waiting here takes
    its handle to this process with it, and on Windows nothing then connects the two —
    so the pid in the job's trail is all a later sweep has to go on.
    """
    with subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as running:
        children.watch(running.pid)
        try:
            output, _ = running.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            running.kill()
            # `communicate` raises with nothing attached, and what the engine printed
            # before it hung is the most useful part of a timeout. Read it after the
            # kill and put it back on the exception the caller already handles.
            expired.stdout, _ = running.communicate()
            raise
    return output or "", int(running.returncode)


def run(
    script: str | Path,
    *,
    expect: str | re.Pattern,
    root: str | Path = ".",
    produces: tuple[str, ...] = (),
    errors: str | re.Pattern = ERRORS,
    frames: int | None = None,
    timeout: float | None = None,
    fixed_fps: int | None = None,
    headless: bool = False,
    args: tuple[str, ...] = (),
    through: tuple[str, ...] = (),
    binary: str = "",
    launch: Any = None,
) -> dict:
    """Run one scene script and say what happened, in one structure.

    `expect` is the line that means the script did what it was for, as a pattern. Its
    named groups come back in `found`, and every name in `produces` is read as a path
    that has to exist — a script that printed its line before finishing the write is a
    failure, and the exit code will not say so.

    `through` is a command the engine is launched inside, for a run that needs
    something standing up around it — a display server, most of all. `binary` names the
    engine where the caller has already resolved it, or where the project being run is
    not the project whose settings named it.

    Nothing here raises on a failed run. The verdict is the answer.
    """
    settings = load(root)
    where = settings.root
    # `expect` is a line, so `^` and `$` are a line's ends: searched over the whole log
    # without this, `^SHOT` only ever matched a log whose first line was the shot, and
    # Starship's first capture through polyweave printed it and still failed (§PW210).
    wanted = re.compile(expect, re.MULTILINE) if isinstance(expect, str) else expect
    bad = re.compile(errors) if isinstance(errors, str) else errors
    budget = int(settings.get("engine.frames", frames))
    clock = float(settings.get("engine.timeout", timeout))
    fps = int(settings.get("engine.fixed_fps", fixed_fps))

    path = Path(script)
    if not path.is_absolute():
        path = where / path
    if not path.is_file():
        raise PolyweaveError(
            "engine.no-script",
            f"there is no scene script at {path}",
            "write the path relative to the project root",
        )

    command = [*through, binary or find(root)]
    if headless:
        command.append("--headless")
    command += ["--path", str(where), "--fixed-fps", str(fps)]
    command += ["--quit-after", str(budget), "--script", _as_res(path, where)]
    command += list(args)

    started = time.monotonic()
    timed_out = False
    try:
        output, code = (launch or _launch)(command, cwd=where, timeout=clock)
    except subprocess.TimeoutExpired as exc:
        output = _text(exc.stdout) + _text(exc.stderr)
        code, timed_out = None, True
    seconds = round(time.monotonic() - started, 3)

    log = settings.path("paths.work") / "engine" / f"{path.stem}.log"
    write_atomic(log, output)

    return _verdict(
        output=output,
        code=code,
        timed_out=timed_out,
        seconds=seconds,
        wanted=wanted,
        bad=bad,
        produces=produces,
        where=where,
        budget=budget,
        clock=clock,
        command=command,
        log=log,
        script=path,
    )


def _text(raw: Any) -> str:
    if raw is None:
        return ""
    return raw if isinstance(raw, str) else raw.decode("utf-8", "replace")


def _verdict(**about: Any) -> dict:
    """Read the run's output into the four answers the exit code cannot give."""
    output = about["output"]
    found = about["wanted"].search(output)
    reported = FRAMES.search(output)
    elapsed = int(reported.group(1)) if reported else None
    failures = _errors(output, about["bad"])

    fields = found.groupdict() if found else {}
    artefacts, missing = [], []
    for name in about["produces"]:
        named = fields.get(name) or ""
        if not named:
            continue
        artefact = _under(named, about["where"])
        (artefacts if artefact.is_file() else missing).append(str(artefact))

    result = {
        "ok": False,
        "verdict": "",
        "why": "",
        "script": str(about["script"]),
        "found": fields,
        "artefacts": artefacts,
        "missing": missing,
        "errors": failures,
        "frames": elapsed,
        "frame_budget": about["budget"],
        # True only where it can be told: the wall clock fired, or the script itself
        # said how far it got and it got all the way to the budget.
        "bounded": bool(
            about["timed_out"] or (elapsed is not None and elapsed >= about["budget"])
        ),
        "exit_code": about["code"],
        "seconds": about["seconds"],
        "command": list(about["command"]),
        "log": str(about["log"]),
    }
    if about["timed_out"]:
        return {
            **result,
            "verdict": "timed-out",
            "why": f"the run was still going after {about['clock']:g} s",
        }
    if failures:
        first = failures[0]
        return {
            **result,
            "verdict": "script-error",
            "why": f"{len(failures)} error(s) in the output, the first at "
            f"{first['at'] or 'no line the engine named'}: {first['text']}",
        }
    if found is None:
        return {
            **result,
            "verdict": "no-signal",
            "why": "the script never printed the line that says it worked",
        }
    if missing:
        return {
            **result,
            "verdict": "missing-artefact",
            "why": f"it said it wrote {', '.join(missing)}, which is not there",
        }
    return {**result, "ok": True, "verdict": "ok"}


#: Which code each verdict closes with, so a gate never invents one.
REFUSALS = {
    "timed-out": "engine.timed-out",
    "script-error": "engine.script-error",
    "no-signal": "engine.no-signal",
    "missing-artefact": "engine.missing-artefact",
}


def require(script: str | Path, **how: Any) -> dict:
    """The same run, as a gate: anything but a clean verdict stops here.

    The refusal carries the log, because "the capture failed" is not actionable and a
    file somebody can open is.
    """
    found = run(script, **how)
    if found["ok"]:
        return found
    raise PolyweaveError(
        REFUSALS[found["verdict"]],
        f"{Path(found['script']).name} did not report a result: {found['why']}",
        f"read {found['log']}, which holds everything the run printed",
        detail="\n".join(error["text"] for error in found["errors"][:5]) or None,
    )


@operation("engine.run")
def ran(
    script: Annotated[str, Param("the scene script, as a path under the project")],
    *,
    expect: Annotated[str, Param("the line that means it worked, as a pattern")],
    root: Annotated[str, Param("the project the engine runs")] = ".",
    produces: Annotated[
        list, Param("the named groups of expect that are paths it must have written")
    ] = (),
    frames: Annotated[int, Param("the frame budget; the project's if unset")] = None,
    timeout: Annotated[
        float, Param("the wall clock; the project's if unset", unit="s")
    ] = None,
    headless: Annotated[bool, Param("run with no window")] = False,
    args: Annotated[list, Param("user arguments passed after the script")] = (),
) -> dict:
    """Run one scene script and say what happened: the verdict, not the log."""
    return run(
        script,
        expect=expect,
        root=root,
        produces=tuple(produces),
        frames=frames,
        timeout=timeout,
        headless=headless,
        args=tuple(args),
    )
