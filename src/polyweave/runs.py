"""A game's engine runs declared, not scripted (§PW467).

Cottony kept three Python drivers whose only project knowledge was a table: which
script, the line it prints when it worked, which named group of that line is a file it
wrote, and whether it is a screen taken in the declared environment. Everything else
in them was a call to `engine.run` or `capture.run` and an OK or a FAIL. A second game
would have written the same three files, so the table moves into `polyweave.toml`:

    [run.board3d_beside]
    script   = "tools/perf/board3d_beside.gd"
    expect   = 'captured: res://(?P<wrote>\\S+) (?P<width>\\d+) x (?P<height>\\d+)'
    produces = ["wrote"]
    capture  = true                     # taken in [capture] declared, and recorded
    settings = { locale = "en" }        # what this one run takes differently

and `engine.run_declared` runs one, several or every declared run, each answered with
the verdict `engine.run` gives. `args`, `frames` and `timeout` are the run's own where
it needs them. A verdict on a number a run printed stays the project's, since that is a
judgement about the number and not about the run.
"""

from __future__ import annotations

from typing import Annotated

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a declared run may say, and what each is.
KEYS = {
    "script": "the scene script, as a path under the project",
    "expect": "the line that means it worked, as a pattern",
    "produces": "the named groups of expect that are files it must have written",
    "capture": "whether it is a picture taken in [capture] declared, and recorded",
    "settings": "the declared capture settings this run takes differently",
    "args": "the script's own arguments",
    "frames": "the frame budget, where [engine] frames is too short",
    "timeout": "the wall clock, where [engine] timeout is too short",
}


def declared(root=".") -> dict[str, dict]:
    """Every `[run.<name>]` the project declares, each checked."""
    config = load(root)
    found = {}
    for name, run in config.table("run").items():
        if not isinstance(run, dict):
            raise PolyweaveError(
                "engine.bad-run", f"[run.{name}] is not a table",
                "declare it as [run.<name>] with a script and an expect")
        unknown = sorted(set(run) - set(KEYS))
        if unknown:
            raise PolyweaveError(
                "engine.bad-run",
                f"[run.{name}] has {', '.join(unknown)}, which a run does not take",
                "a run takes " + ", ".join(KEYS), given=unknown[0], allowed=list(KEYS))
        missing = [key for key in ("script", "expect") if not run.get(key)]
        if missing:
            raise PolyweaveError(
                "engine.bad-run", f"[run.{name}] has no {' and no '.join(missing)}",
                "give it the script and the line that means it worked")
        found[str(name)] = run
    return found


@operation("engine.run_declared")
def run_declared(
    runs: Annotated[
        list, Param("the [run.<name>] names to run; every one if empty")
    ] = (),
    root: Annotated[str, Param("the project whose polyweave.toml declares them")] = ".",
) -> dict:
    """Run a game's declared engine runs, each judged by the line it prints (§PW467).

    A run is `[run.<name>]` in polyweave.toml: `script`, `expect`, and optionally
    `produces`, `capture` with `settings`, `args`, `frames` and `timeout`. Each is
    started through `engine.run`, or `capture.run` where it is a capture, so it is
    bounded, its exit code distrusted and its line read. `passed` is false while any
    failed, and the command exits non-zero then.
    """
    from . import capture, engine

    here = load(root).root
    every = declared(here)
    asked = list(runs) or sorted(every)
    unknown = [name for name in asked if name not in every]
    if unknown:
        raise PolyweaveError(
            "engine.unknown-run",
            f"{', '.join(unknown)} is not a run this project declares",
            "declare it as [run.<name>] in polyweave.toml, or name one of: "
            + (", ".join(sorted(every)) or "none is declared"),
            given=unknown[0], allowed=sorted(every))
    answers = {}
    for name in asked:
        run = every[name]
        how = {
            "expect": str(run["expect"]),
            "root": here,
            "produces": tuple(run.get("produces") or ()),
            **({"frames": int(run["frames"])} if run.get("frames") else {}),
            **({"timeout": float(run["timeout"])} if run.get("timeout") else {}),
        }
        args = tuple(str(one) for one in run.get("args") or ())
        if run.get("capture"):
            found = capture.run(
                str(run["script"]),
                environment=capture.wanted(here, **(run.get("settings") or {})),
                **({"args": ("--", *args)} if args else {}), **how)
        else:
            found = engine.run(str(run["script"]), args=args, **how)
        answers[name] = {
            "ok": bool(found["ok"]),
            **({"why": (found.get("environment") or {}).get("why") or found.get("why")}
               if not found["ok"] else {}),
            "found": found.get("found") or {},
            # A capture whose settings held and whose bytes did not, said as capture.run
            # says it, which is the half of capture_screens.py a table could not carry.
            **({"reproduced": found["reproduced"]} if found.get("reproduced") else {}),
            "seconds": found.get("seconds"),
            "log": found.get("log"),
        }
    failed = sorted(name for name, one in answers.items() if not one["ok"])
    return {
        "passed": not failed,
        "runs": answers,
        "says": f"{len(answers) - len(failed)} of {len(answers)} declared run(s) did "
        "what they print they did"
        + (f"; {', '.join(failed)} did not" if failed else ""),
    }
