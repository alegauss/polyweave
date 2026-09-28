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

import contextlib
import json
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

    A picture the OS shrank to the desktop's work area is taken once more with the
    window borderless, which the OS leaves at the size asked (§PW280), and the size is
    kept so the next run at it goes borderless from the start.
    """
    asked = environment if environment is not None else wanted(root)
    size = _size_of(asked.get("resolution", ""))
    known = bool(size) and size in _beyond(root)
    once = {"expect": expect, "root": root, "environment": asked, "record": record,
            "take": take}
    answer = _once(script, borderless=known, **once, **dict(how))
    if not size or known or not answer.get("shrunk"):
        return answer
    try:
        again = _once(script, borderless=True, **once, **dict(how))
    except PolyweaveError as held:
        if held.code != "capture.override-held":
            raise
        return {**answer, "why": f"{answer['why']}; {held.message}: {held.remedy}"}
    if not again.get("shrunk"):
        _remember(root, size)
    return {**again, "borderless": True, "shrunk_first": answer["shrunk"]}


def _once(
    script: str | Path,
    *,
    expect: str | re.Pattern,
    root: str | Path,
    environment: dict,
    record: bool,
    take: Any,
    borderless: bool,
    **how: Any,
) -> dict:
    """One take of `run`, with the window borderless where it has to be."""
    asked = environment
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
        with _borderless(load(root).root, borderless):
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
    claimed, measured = applied(log), _measured(asked, found["artefacts"])
    against = compare(asked, {**claimed, **measured})
    shrunk = _shrunk(asked, claimed, measured, borderless)
    if shrunk:
        against = {**against, "why": "; ".join(filter(None, (against["why"], shrunk)))}
    answer = {
        **found,
        "environment": against,
        "regions": regions(log),
        "loaded": loaded(log),
        **({"shrunk": shrunk} if shrunk else {}),
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
        if not made:
            # Said, not left as an empty list (§PW260): an empty `records` read as a
            # capture recorded, and the review picture it named had no provenance.
            answer["why_unrecorded"] = (
                "no line matching expect named a picture that exists under the "
                "project, so nothing was recorded; print the picture's path on the "
                "expect line, as `captured: res://<path>.png <w> x <h>`"
            )
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
    if len(sizes) > 1:
        # Pictures of several sizes cannot all hold one: said, never left to the
        # script's own line (§PW267).
        return {"resolution": " and ".join(sorted(sizes))}
    return {"resolution": sizes.pop()} if sizes else {}


def _shrunk(
    asked: dict, claimed: dict, measured: dict, borderless: bool = False
) -> str:
    """Why a picture's size differs from what the script said it applied (§PW267).

    The script reports the size it asked the window for; the OS may still shrink a
    window larger than the desktop's work area, and only the picture shows it.
    """
    wanted, said, got = (one.get("resolution") for one in (asked, claimed, measured))
    if not wanted or not got or got == _size_of(wanted) or said is None:
        return ""
    if borderless:
        return (
            f"the picture is {got}, asked {_size_of(wanted)}, even with the window "
            f"borderless: on a virtual display, give it a screen at least that size"
        )
    return (
        f"the picture is {got}, asked {_size_of(wanted)}, though the script said it "
        f"applied {said}: the OS shrank a window larger than the desktop's work area"
    )


#: Where the sizes this machine's desktop shrinks are kept, under the work folder.
BEYOND = "capture/beyond.json"


def _beyond(root: str | Path) -> list[str]:
    """The sizes a window was shrunk from here before, so they start borderless."""
    try:
        kept = json.loads((load(root).path("paths.work") / BEYOND).read_text("utf-8"))
    except (OSError, ValueError):
        return []
    return [str(one) for one in kept.get("sizes", [])] if isinstance(kept, dict) else []


def _remember(root: str | Path, size: str) -> None:
    from .files import write_atomic

    sizes = sorted({*_beyond(root), size})
    write_atomic(load(root).path("paths.work") / BEYOND,
                 json.dumps({"sizes": sizes}, indent=2) + "\n")


@contextlib.contextmanager
def _borderless(here: Path, wanted: bool):
    """The window borderless for one run, which the OS does not shrink (§PW280).

    A decorated window larger than the desktop's work area comes back at the work
    area's size, 3840x2119 asked 3840x2160; a borderless one is left at the size
    asked, even past the screen, and draws the same pixels through the same stretch.
    Godot has no flag for it, so it is `override.cfg` for the run, as a movie's size
    is, and a project with one of its own is refused rather than having it replaced.
    """
    if not wanted:
        yield
        return
    target = here / OVERRIDE
    if target.exists():
        raise PolyweaveError(
            "capture.override-held",
            f"the project has an {OVERRIDE} of its own, and a picture larger than the "
            "desktop is taken borderless by writing one",
            "set display window/size/borderless=true in it for the run",
        )
    target.write_text("[display]\n\nwindow/size/borderless=true\n",
                      encoding="utf-8", newline="\n")
    try:
        yield
    finally:
        target.unlink(missing_ok=True)


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


#: The marks a movie script prints around the frames it wants kept (§PW249).
MARKS = re.compile(r"^movie: (?P<mark>from|to) (?P<frame>\d+)\b", re.MULTILINE)


#: The file Godot reads over project.godot, in the project's own folder.
OVERRIDE = "override.cfg"


@contextlib.contextmanager
def _movie_sized(here: Path, asked: dict):
    """The window overrides a movie is recorded at, for the length of one run (§PW273).

    Movie Maker takes its size from the project's settings before any script runs, so
    `--resolution` and a script setting root.size reach it too late: a run asked at
    320x240 of a 1152x648 project recorded 1152x648. Godot reads `override.cfg` beside
    project.godot over it, and its window overrides keep the game's own design size, so
    the layout is the game's and only its scale is asked. The file is written for the
    run and removed after it, and a project with an `override.cfg` of its own is refused
    before anything runs rather than having it replaced.
    """
    size = _size_of(asked.get("resolution", ""))
    if not size:
        yield
        return
    target = here / OVERRIDE
    if target.exists():
        raise PolyweaveError(
            "capture.override-held",
            f"the project has an {OVERRIDE} of its own, and a movie is sized by "
            "writing one",
            f"set window/size/window_width_override and window_height_override to "
            f"{size.replace('x', ' and ')} in it for the run, or ask no resolution",
        )
    width, height = size.split("x")
    target.write_text(
        "[display]\n\n"
        f"window/size/window_width_override={width}\n"
        f"window/size/window_height_override={height}\n",
        encoding="utf-8", newline="\n",
    )
    try:
        yield
    finally:
        target.unlink(missing_ok=True)


@operation("capture.movie", kind="capture")
def movie(
    script: Annotated[str, Param("the scene script that flies the shot")],
    *,
    out: Annotated[str, Param("the folder the frames go to, under the project")],
    root: Annotated[str, Param("the project the engine runs")] = ".",
    environment: Annotated[
        dict, Param("the settings to take it in; [capture] where unset")
    ] = None,
    args: Annotated[list, Param("the script's own arguments")] = (),
    record: Annotated[bool, Param("write the sequence's record")] = True,
) -> dict:
    """Every frame between two marks the script prints, at the engine's fixed rate.

    The script flies the shot and prints `movie: from <frame>` and `movie: to <frame>`
    with `Engine.get_process_frames()`; Godot's Movie Maker (`--write-movie`) writes
    every frame of the run, and the frames between the marks, both kept, are numbered
    from 0001 into `out` with the audio beside them. One record, `sequence.json`, says
    the environment, rate, count and each frame's tick and hash, and names any frame
    missing between the marks. Needs a display: a headless run draws nothing (§PW249).
    """
    import shutil
    import tempfile

    here = load(root).root
    asked = environment if environment is not None else wanted(here)
    target = Path(out)
    target = target if target.is_absolute() else here / target
    raw = Path(tempfile.mkdtemp(prefix="polyweave-movie-"))
    try:
        user = ("--", *(str(one) for one in args or ())) + as_args(asked)
        engine_args = _sized(("--write-movie", str(raw / "frame.png")), asked)
        with _movie_sized(here, asked):
            found = offscreen.capture(
                script,
                expect=re.compile(r"^movie: to \d+", re.MULTILINE),
                root=here,
                args=(*engine_args, *user),
            )
        log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
        marks = {m["mark"]: int(m["frame"]) for m in MARKS.finditer(log)}
        answer = {
            "ok": False,
            "script": found.get("script"),
            "route": found.get("route"),
            "log": found["log"],
            "marks": marks,
        }
        unmarked = "from" not in marks or "to" not in marks
        if unmarked and found.get("verdict") in ("ok", "no-signal"):
            return {
                **answer,
                "verdict": "no-marks",
                "why": "the script printed no `movie: from <frame>` and `movie: to "
                "<frame>`, so there is no shot to keep",
            }
        if not found["ok"] or unmarked:
            return {**answer, "verdict": found.get("verdict"), "why": found.get("why")}
        if marks["to"] < marks["from"]:
            return {
                **answer,
                "verdict": "bad-marks",
                "why": f"the shot ends at frame {marks['to']}, before it starts at "
                f"{marks['from']}",
            }
        written = {
            int(one.stem.removeprefix("frame")): one
            for one in raw.glob("frame*.png")
            if one.stem.removeprefix("frame").isdigit()
        }
        wanted_frames = range(marks["from"], marks["to"] + 1)
        dropped = [tick for tick in wanted_frames if tick not in written]
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        frames = []
        for number, tick in enumerate(t for t in wanted_frames if t in written):
            kept = target / f"{number + 1:04d}.png"
            shutil.move(str(written[tick]), kept)
            digest, _ = provenance.sha256_of(kept)
            frames.append({"file": kept.name, "tick": tick, "sha256": digest})
        audio = raw / "frame.wav"
        if audio.is_file():
            shutil.move(str(audio), target / "audio.wav")
        against = compare(
            asked,
            {
                **applied(log),
                **_measured(asked, [str(target / f["file"]) for f in frames[:1]]),
            },
        )
        sequence = {
            "format": 1,
            "script": answer["script"],
            "fps": int(load(here).get("engine.fixed_fps")),
            "marks": marks,
            "count": len(frames),
            "dropped": dropped,
            "audio": (target / "audio.wav").is_file(),
            "environment": against,
            "frames": frames,
        }
        manifest = target / "sequence.json"
        with manifest.open("w", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(sequence, indent=2) + "\n")
        holds = against["holds"] and not dropped
        answer.update(
            ok=holds,
            verdict="ok"
            if holds
            else (
                "dropped" if dropped else "environment-" + _environment_cause(against)
            ),
            why=""
            if holds
            else (
                f"{len(dropped)} frames between the marks were not written: "
                f"{dropped[:8]}"
                if dropped
                else "the frames were taken, but not in the environment asked: "
                + (against["why"] or "the script printed no `environment:` line")
            ),
            out=str(target),
            count=len(frames),
            dropped=dropped,
            environment=against,
            sequence=str(manifest),
        )
        if record and holds:
            read = inputs(answer["script"], loaded(log), here)
            answer["record"] = str(
                provenance.write(
                    provenance.build(
                        "capture",
                        manifest,
                        engine={"route": found.get("route", "")},
                        inputs=read["inputs"],
                        params=dict(asked),
                        extra={"script": answer["script"], "frames": len(frames)},
                        root=here,
                    ),
                    root=here,
                )
            )
        return answer
    finally:
        shutil.rmtree(raw, ignore_errors=True)


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
    frames: Annotated[
        int,
        Param("the frame budget; [engine] frames if unset", lo=1, hi=10_000_000),
    ] = None,
    timeout: Annotated[
        float, Param("the wall clock; [engine] timeout if unset", lo=1, unit="s")
    ] = None,
) -> dict:
    """Take a picture in a stated environment, and check it was the stated one.

    `args` are the script's (§PW238): a capture of a moment in play names it, and
    without them the only route was a one-off Python call to the library. They reach
    `OS.get_cmdline_user_args()` ahead of the environment's `name=value` pairs.
    `until_visible` retries a run whose subject was off screen (§PW242). `frames` and
    `timeout` size a run that flies to a late moment, which the project's budget would
    end before it printed its line (§PW251).
    """
    how = {
        "expect": expect,
        "root": root,
        "environment": environment,
        "record": record,
        "args": ("--", *(str(one) for one in args or ())),
        "until_visible": until_visible,
        "tries": tries,
        **({"frames": int(frames)} if frames else {}),
        **({"timeout": float(timeout)} if timeout else {}),
    }
    return require(script, **how) if strict else run(script, **how)
