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
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import engine, offscreen, provenance
from .config import load
from .errors import PolyweaveError

#: What a script prints back to say what it actually applied.
REPORTED = re.compile(r"^environment:[ \t]*(?P<pairs>.*)$", re.MULTILINE)

#: How one setting is written, both ways along.
PAIR = re.compile(r"(?P<name>[A-Za-z_][\w.-]*)=(?P<value>\S*)")


def declared(root: str | Path = ".") -> list[str]:
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
    args = tuple(how.pop("args", ())) + ("--", *as_args(asked))
    found = (take or offscreen.capture)(
        script, expect=expect, root=root, args=args, **how
    )

    log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
    against = compare(asked, applied(log))
    answer = {**found, "environment": against}
    if not found["ok"] or not against["holds"]:
        return {**answer, "ok": False}
    if record:
        answer["records"] = [
            str(_record(one, asked, found, root)) for one in found["artefacts"]
        ]
    return answer


def _record(artefact: str, asked: dict, found: dict, root: str | Path) -> Path:
    """The environment, beside the picture it was taken in."""
    written = provenance.build(
        "capture",
        artefact,
        engine={"route": found.get("route", ""), "about": found.get("about", "")},
        params=dict(asked),
        elapsed_s=found.get("seconds"),
        extra={"script": found["script"], "frames": found.get("frames")},
        root=root,
    )
    return provenance.write(written, root=root)


def require(script: str | Path, **how: Any) -> dict:
    """The same capture as a gate: an environment left to chance stops here."""
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
    if not found["ok"]:
        raise PolyweaveError(
            engine.REFUSALS[found["verdict"]],
            f"{Path(found['script']).name} did not report a result: {found['why']}",
            f"read {found['log']}, which holds everything the run printed",
        )
    return found
