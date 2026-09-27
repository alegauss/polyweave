"""The environment a picture of the running game is taken in.

The evidence is §PW25: the same capture script on two machines gives two different
pictures, because the game picks its language from the machine's locale and nothing in
the script says which language the picture is being taken in. Cottony found that the
expensive way and now checks, with a regular expression, that every capture script
both names a locale constant **and** passes it to the translation server — because
naming it and not setting it passes a naive check and still produces the wrong image.

Locale is one of a family. Resolution, display scale, theme, time of day, random seed
and whatever else the running game reads from outside itself are each a way for a
committed screenshot to depend on whose desk it was taken at. What makes this
affordable is that **the list of settings that matter is per project and short** —
`[capture] declared`.

The regular expression is not the shape here, because a pattern that proves a constant
is passed somewhere is a pattern about one project's code. Instead:

1. the **run passes** the settings, after `--`, as `name=value`;
2. the **script applies them and prints back what it applied**, as one
   `environment: name=value ...` line;
3. the **run compares** the two, and refuses where anything declared is missing from the
   line or came back different.

So the script takes the values from the run rather than holding its own, and the check
is against what it says it did rather than against how it is written. A setting the
project declares and nothing gives a value to is `capture.undeclared` before anything
runs, since leaving it to chance is the whole symptom.

The environment is recorded beside the picture, so a screenshot that differs later can
be compared against what it was taken under rather than against a memory of it.

That record is also what the next run is measured against (§PW71). Three of Cottony's
four captures come out byte-identical every time and the fourth does not, and until a
run had the last one's record to read, all four wrote `OK` and nothing said which was
which.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

from . import engine, offscreen, provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a script prints back to say what it actually applied.
REPORTED = re.compile(r"^environment:[ \t]*(?P<pairs>.*)$", re.MULTILINE)

#: How one setting is written, both ways along.
PAIR = re.compile(r"(?P<name>[A-Za-z_][\w.-]*)=(?P<value>\S*)")

#: Where a script says an asset stands in its picture, in pixels: one line per asset,
#: `region: star_dim=412,96,508,192` (§PW112). The script knows where it drew each
#: thing, so it says so, and a spec can be held to that rectangle of the screen.
REGION = re.compile(
    r"^region:[ \t]*(?P<name>[A-Za-z_][\w.-]*)=(?P<box>-?\d+,-?\d+,-?\d+,-?\d+)[ \t]*$",
    re.MULTILINE,
)


#: A resource the game opened, as Godot's `--verbose` log spells it or as a script says
#: it with one `loaded: res://...` line of its own (§PW118).
LOADED = re.compile(
    r"^[ \t]*(?:loaded:|Loading resource:)[ \t]*(?P<path>res://\S+?)[ \t]*$",
    re.MULTILINE,
)


def loaded(output: str) -> list[str]:
    """Every project resource the run says it opened, once each, in order of path."""
    return sorted({found.group("path") for found in LOADED.finditer(output or "")})


def inputs(script: str | Path, opened: list[str], root: str | Path) -> dict:
    """The script and every loaded resource, hashed, as a record's inputs.

    A resource outside the project, or one the log names that is not on disk, is said
    under `unread` rather than dropped silently, since an input the record cannot hash
    is one a later difference cannot be pinned on.
    """
    where = load(root).root
    found = [provenance.source("script", script, root=where)]
    unread = []
    for name in opened:
        path = where / name.removeprefix("res://")
        if path.is_file():
            found.append(provenance.source("loaded", path, root=where))
        else:
            unread.append(name)
    return {"inputs": found, "unread": unread}


def regions(output: str) -> dict[str, list[int]]:
    """Every named rectangle a script printed, as `[x0, y0, x1, y1]`."""
    return {
        found.group("name"): [int(v) for v in found.group("box").split(",")]
        for found in REGION.finditer(output or "")
    }


@operation("capture.declared")
def declared(
    root: Annotated[str, Param("the project whose [capture] declared is read")] = ".",
) -> list[str]:
    """The settings this project says a picture depends on."""
    return [str(name) for name in load(root).get("capture.declared") or ()]


def as_text(value: Any) -> str:
    """One setting's value, as both sides write it.

    A list becomes `1920x1080` rather than `[1920, 1080]`, because the script has to
    print it back and a line of JSON inside a log is a line nobody reads.
    """
    if isinstance(value, list | tuple):
        return "x".join(as_text(part) for part in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def wanted(root: str | Path = ".", **given: Any) -> dict:
    """Every declared setting and the value it will be taken at.

    The explicit argument first, then `[capture]`. A declared setting with no value
    anywhere is refused here rather than left to the machine.
    """
    settings = load(root)
    out: dict[str, str] = {}
    for name in declared(root):
        value = given.get(name)
        if value is None:
            try:
                value = settings.get(f"capture.{name}")
            except PolyweaveError:
                value = None
        text = as_text(value) if value is not None else ""
        if not text.strip():
            raise PolyweaveError(
                "capture.undeclared",
                f"[capture] declared names {name!r}, and nothing gives it a value",
                f"set capture.{name} in the project, or pass {name} to this capture; a "
                f"setting left to the machine is how one desk's picture differs from "
                f"another's",
            )
        out[name] = text
    for name, value in given.items():
        if name not in out and value is not None:
            out[name] = as_text(value)
    return out


def as_args(environment: dict) -> tuple[str, ...]:
    """The user arguments a run carries, for the script to read and apply."""
    return tuple(f"{name}={value}" for name, value in sorted(environment.items()))


def applied(output: str) -> dict:
    """What the script said it actually applied, off its own line."""
    found = REPORTED.search(output or "")
    if found is None:
        return {}
    return {
        pair.group("name"): pair.group("value")
        for pair in PAIR.finditer(found.group("pairs"))
    }


def compare(asked: dict, got: dict) -> dict:
    """Asked against applied, for the settings the project declared."""
    missing = sorted(name for name in asked if name not in got)
    differing = sorted(
        {name: (asked[name], got[name]) for name in asked if name in got}.items()
    )
    differing = [(n, a, b) for n, (a, b) in differing if a != b]
    holds = not missing and not differing
    return {
        "holds": holds,
        "asked": dict(asked),
        "applied": dict(got),
        "missing": missing,
        "differing": [
            {"setting": n, "asked": a, "applied": b} for n, a, b in differing
        ],
        "why": ""
        if holds
        else "; ".join(
            [f"{name} was never applied" for name in missing]
            + [f"{n} was asked at {a} and applied at {b}" for n, a, b in differing]
        ),
    }


def run(
    script: str | Path,
    *,
    expect: str | re.Pattern,
    root: str | Path = ".",
    environment: dict | None = None,
    record: bool = True,
    take: Any = None,
    **how: Any,
) -> dict:
    """Take a picture in a stated environment, and check it was the stated one.

    Everything about which route draws is `offscreen`'s problem; everything about
    whether the run worked is `engine`'s. What this adds is the environment: passed in,
    reported back, compared, and written down beside the picture.
    """
    asked = environment if environment is not None else wanted(root)
    # One `--` only (§PW238): a caller whose args already hold the engine's and then the
    # script's own has written it, and a second would reach the script as an argument.
    given = _sized(tuple(how.pop("args", ())), asked)
    args = given + (() if "--" in given else ("--",)) + as_args(asked)
    until = str(how.pop("until_visible", "") or "")
    tries = max(1, int(how.pop("tries", 3)))
    # Taken again until the script says its subject was on screen (§PW242): a moment in
    # play spawns differently each run, and a fixed frame count cannot wait on that.
    attempt = 0
    while True:
        attempt += 1
        found = (take or offscreen.capture)(
            script, expect=expect, root=root, args=args, **how
        )
        log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
        if not until or not found["ok"] or saw(log, until, expect) or attempt >= tries:
            break
    if until:
        found = {**found, "tries": attempt, "until_visible": until}
        if found["ok"] and not saw(log, until, expect):
            found = {
                **found,
                "ok": False,
                "verdict": "not-visible",
                "why": f"in {attempt} tr{'y' if attempt == 1 else 'ies'} the script "
                f"never said {until} was on screen before the picture: no "
                f"`visible: {until}` line ahead of the one naming it",
            }

    # The pictures the run named, where the caller did not say which group holds them
    # (§PW246): the MCP answer came back with no artefacts for five written pictures.
    if not found.get("artefacts"):
        found = {**found, "artefacts": pictures(log, expect, root)}
    # The picture is the authority on its size, not the script's line (§PW245): a script
    # that set root.size and printed it said 1920x1080 over a 1280x720 picture.
    against = compare(asked, {**applied(log), **_measured(asked, found["artefacts"])})
    answer = {
        **found,
        "environment": against,
        "regions": regions(log),
        "loaded": loaded(log),
    }
    if found["ok"] and not against["holds"]:
        # The run worked and the environment did not hold, and that is said at the top,
        # where a caller reads first, not only inside `environment` (§PW246).
        return {
            **answer,
            "ok": False,
            "verdict": "environment-" + _environment_cause(against),
            "why": "the pictures were taken, but not in the environment asked: "
            + (against["why"] or "the script printed no `environment:` line"),
        }
    if not found["ok"]:
        return {**answer, "ok": False}
    if record:
        read = inputs(found["script"], answer["loaded"], root)
        answer["unread"] = read["unread"]
        made = [
            _record(
                one,
                asked,
                {**found, "regions": answer["regions"], "inputs": read["inputs"]},
                root,
            )
            for one in found["artefacts"]
        ]
        answer["records"] = [str(path) for path, _ in made]
        answer["reproduced"] = again([verdict for _, verdict in made])
    return answer


#: A picture a script names on a line, as a project path or its own.
_PICTURE = re.compile(r"(?:res://|user://)?[^\s'\"]+\.(?:png|jpe?g|webp)\b", re.I)


def pictures(log: str, expect: str | re.Pattern, root: str | Path) -> list[str]:
    """Every picture the lines matching `expect` name, as paths that exist."""
    named = re.compile(expect, re.MULTILINE) if isinstance(expect, str) else expect
    here = load(root).root
    found: list[str] = []
    for match in named.finditer(log or ""):
        line_end = log.find("\n", match.start())
        line = log[match.start() : line_end if line_end >= 0 else len(log)]
        for spelled in _PICTURE.findall(line):
            if spelled.startswith("user://"):
                continue  # the engine's own folder: not a path this side can read
            where = Path(spelled.removeprefix("res://"))
            where = where if where.is_absolute() else here / where
            if where.is_file() and str(where) not in found:
                found.append(str(where))
    return found


def _environment_cause(against: dict) -> str:
    """Which way the environment failed, as require names it."""
    if not against["applied"]:
        return "not-reported"
    if against["missing"]:
        return "not-applied"
    return "differs"


def _size_of(value: Any) -> str:
    """A declared resolution as the engine's flag spells it, or "" where it is none."""
    text = as_text(value) if not isinstance(value, str) else value
    found = re.fullmatch(r"\s*(\d+)\s*x\s*(\d+)\s*", str(text))
    return f"{found[1]}x{found[2]}" if found else ""


def _sized(given: tuple[str, ...], asked: dict) -> tuple[str, ...]:
    """The engine's own args with the declared size on them (§PW245).

    A project's window override beats a script setting root.size, so Starship's codex
    came back at 1280x720 asked 1920x1080; `--resolution` on the engine's command line
    beats the override, and then the script only has to report what applied. A caller
    that put a size of its own on the engine's args keeps it.
    """
    size = _size_of(asked.get("resolution", ""))
    cut = given.index("--") if "--" in given else len(given)
    engine_args = given[:cut]
    if not size or "--resolution" in engine_args:
        return given
    return (*engine_args, "--resolution", size, *given[cut:])


def _measured(asked: dict, artefacts: list) -> dict:
    """The size the pictures came out at, where a size was asked and they agree."""
    if "resolution" not in asked:
        return {}
    from PIL import Image

    sizes = set()
    for one in artefacts:
        where = Path(one)
        if where.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        try:
            with Image.open(where) as picture:
                sizes.add(f"{picture.width}x{picture.height}")
        except OSError:
            continue
    return {"resolution": sizes.pop()} if len(sizes) == 1 else {}


def saw(log: str, group: str, expect: str | re.Pattern) -> bool:
    """Whether the script said `group` was on screen before it named its picture.

    The script decides what on screen means, a camera test over the group's nodes, and
    prints `visible: <group>`; the run only reads the line, as it reads `environment:`.
    """
    named = re.compile(expect, re.MULTILINE) if isinstance(expect, str) else expect
    picture = named.search(log or "")
    before = (log or "")[: picture.start()] if picture else log or ""
    return any(
        line.strip() == f"visible: {group}" for line in before.splitlines()
    )


def again(verdicts: list[dict]) -> dict:
    """Whether this run drew what the last one drew, in `compare`'s own shape (§PW71).

    `holds` is false only where the same declared settings produced a different file. A
    first capture holds, because there is nothing it disagrees with, and so does one
    whose key moved, because the record already explains that difference.

    It is a report and not a gate. A capture that waits for an effect rather than
    counting frames lands on whichever frame the effect arrived on, which is a
    deliberate choice in the script and not a fault this can rule on — but it is the
    difference between a screenshot worth reviewing and one that is only noise, so it is
    said out loud.
    """
    differing = [one for one in verdicts if one["verdict"] == "differs"]
    return {
        "holds": not differing,
        "artefacts": list(verdicts),
        "differing": differing,
        "why": "; ".join(one["why"] for one in differing),
    }


def _record(
    artefact: str, asked: dict, found: dict, root: str | Path
) -> tuple[Path, dict]:
    """The environment, beside the picture it was taken in.

    The comparison against the last record happens here rather than in `run`, because
    writing this one is what overwrites the evidence it is compared against.
    """
    written = provenance.build(
        "capture",
        artefact,
        engine={"route": found.get("route", ""), "about": found.get("about", "")},
        inputs=found.get("inputs") or (),
        params=dict(asked),
        elapsed_s=found.get("seconds"),
        extra={
            "script": found["script"],
            "frames": found.get("frames"),
            **({"regions": found["regions"]} if found.get("regions") else {}),
            **({"tries": found["tries"]} if found.get("tries") else {}),
        },
        root=root,
    )
    verdict = provenance.reproduced(written, root=root)
    return provenance.write(written, root=root), verdict


def keeps(root: str | Path = ".") -> bool:
    """Whether a capture that stops reproducing refuses here (§PW75)."""
    return bool(load(root).get("capture.reproducible"))


def require(script: str | Path, **how: Any) -> dict:
    """The same capture as a gate: an environment left to chance stops here.

    A picture that stopped reproducing stops here too, but only where the project asked
    for it. §PW71 settled that this cannot refuse by default — the plugin cannot make an
    engine deterministic, and a capture that waits for an effect made a choice it cannot
    rule on — and that covers the default rather than a project that has done the work.
    Cottony pinned its seed and reported its frame, and all four of its captures came
    out identical over two passes; what it could not do was say so and have it kept.

    Only `differs` refuses. A `first` has nothing to disagree with, and a
    `different-work` is a key that moved, which the record already explains — refusing
    either would fail the run that legitimately redraws a reference, which is most.
    """
    found = run(script, **how)
    against = found["environment"]
    if not against["holds"]:
        if not against["applied"]:
            code = "capture.not-reported"
        elif against["missing"]:
            code = "capture.not-applied"
        else:
            code = "capture.differs"
        raise PolyweaveError(
            code,
            f"{Path(found['script']).name} did not take the picture in the environment "
            f"it was given: {against['why'] or 'it reported no environment at all'}",
            f"print one `environment: name=value ...` line naming what was applied, "
            f"taking each value from the run's own arguments rather than from a "
            f"constant; the log is at {found['log']}",
        )
    if not found["ok"] and found.get("verdict") == "not-visible":
        raise PolyweaveError(
            "capture.not-visible",
            f"{Path(found['script']).name} did not catch its subject: "
            f"{found['why']}",
            f"print `visible: {found['until_visible']}` once a node of that group is "
            f"in the camera's view, or raise tries; the log is at {found['log']}",
        )
    if not found["ok"]:
        raise PolyweaveError(
            engine.REFUSALS[found["verdict"]],
            f"{Path(found['script']).name} did not report a result: {found['why']}",
            f"read {found['log']}, which holds everything the run printed",
        )
    drew = found.get("reproduced") or {}
    if not drew.get("holds", True) and keeps(how.get("root", ".")):
        raise PolyweaveError(
            "capture.not-reproduced",
            f"{Path(found['script']).name} drew a different picture than it drew last "
            f"time: {drew['why']}",
            "declare whatever moved, so the run passes it and the script applies it — "
            "or commit the new picture, which re-anchors what the next run is compared "
            "against; [capture] reproducible is what asked for this to be a refusal",
        )
    return found


@operation("capture.run", kind="capture")
def taken(
    script: Annotated[str, Param("the scene script, as a path under the project")],
    *,
    expect: Annotated[str, Param("the line naming the picture, as a pattern")],
    root: Annotated[str, Param("the project the engine runs")] = ".",
    environment: Annotated[
        dict, Param("the settings to take it in; [capture] where unset")
    ] = None,
    record: Annotated[bool, Param("write the environment beside the picture")] = True,
    strict: Annotated[
        bool, Param("refuse, as require does, rather than report a failed run")
    ] = False,
    args: Annotated[
        list,
        Param(
            "the script's own arguments, e.g. [\"--boss\", \"--frames=420\"]; they go "
            "after the engine's and after --, beside the environment's"
        ),
    ] = (),
    until_visible: Annotated[
        str,
        Param(
            "a group the script reports with a `visible: <group>` line; the run is "
            "taken again until it does"
        ),
    ] = "",
    tries: Annotated[
        int, Param("how many runs until_visible may take", lo=1, hi=20)
    ] = 3,
) -> dict:
    """Take a picture in a stated environment, and check it was the stated one.

    `args` are the script's (§PW238): a capture of a moment in play names it, and
    without them the only route was a one-off Python call to the library. They reach
    `OS.get_cmdline_user_args()` ahead of the environment's `name=value` pairs.
    `until_visible` retries a run whose subject was off screen (§PW242).
    """
    how = {
        "expect": expect,
        "root": root,
        "environment": environment,
        "record": record,
        "args": ("--", *(str(one) for one in args or ())),
        "until_visible": until_visible,
        "tries": tries,
    }
    return require(script, **how) if strict else run(script, **how)
