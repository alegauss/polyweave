"""What a project still does its own way, beside the call that already does it (§PW59).

An adoption asserted per asset can come back without anything failing: a helper written
again under deadline, a floor copied into another check script, one more runner that
starts the engine because the last one did. Each is one commit, each looks reasonable in
review, and the claim that the project uses polyweave stays an opinion.

So the project's own code is read for the surfaces polyweave owns, each by a signature
that is about what the code does and never about how one project names it:

- `engine`: a script that starts Godot itself, through `subprocess` with Godot's own
  flags, where `engine.run`, `capture.run`, `game.test` and `game.export_smoke` bound
  the run and read its line;
- `render`: a script that drives Blender's Python, where `render.bake` and
  `geometry.build` render and build with a record;
- `fetch`: a script that calls a generative service's API itself, where a purchase goes
  through the ledger and its budget;
- `measure`: a gate that opens a picture, takes a percentile, quantile or median of it
  and exits on the answer, where a bar in an acceptance spec is one a search can aim
  at. The exit is what tells a check from a pass that paints with a median colour.

A file the project keeps on purpose is listed under `[adoption] own` with the reason, as
`"tools/art/make_assets.py" = "drawn 2D generation, which polyweave does not do"`. Kept
files are reported with their reason and fail nothing; the rest are what `project.check`
fails on. That is the denominator stated, so the fraction is a count of surfaces and not
a slogan. The comparison of two pictures side by side has no signature that could not
match a test, so it is not read, and the answer says so.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from polyweave.kernel.describe import Param, operation

#: Each surface: what it is, the calls that own it, and what a file's text must hold.
SURFACES: dict[str, dict] = {
    "engine": {
        "does": "starts Godot itself",
        "use": "engine.run, capture.run, game.test or game.export_smoke",
        "all": (
            re.compile(r"\bsubprocess\b"),
            re.compile(r"godot", re.IGNORECASE),
            re.compile(r"""["']--(?:quit-after|script|export-release|export-debug|"""
                       r"""export-pack|headless|editor)["']"""),
        ),
    },
    "render": {
        "does": "drives Blender's Python itself",
        "use": "render.bake or geometry.build",
        "all": (re.compile(r"^\s*(?:import bpy\b|from bpy\b)", re.MULTILINE),),
    },
    "fetch": {
        "does": "calls a generative service's API itself",
        "use": "mesh.buy, picture.buy or sound.buy, through the purchase ledger",
        "all": (
            re.compile(
                r"api\.meshy\.ai|api\.ideogram\.ai|tripo3d\.(?:com|ai)|hyper3d\.ai"
                r"|deemos\.com|api\.cloud\.scenario\.com"
            ),
        ),
    },
    "measure": {
        "does": "holds a picture to a statistic of its own and exits on it",
        "use": "a predicate in an acceptance spec, checked by accept.check or verify",
        "all": (
            re.compile(r"Image\.open\(|imageio\.|cv2\.imread\("),
            re.compile(r"\b(?:percentile|quantile|median)\("),
            re.compile(r"\bSystemExit\b|\bsys\.exit\("),
        ),
    },
}

#: What the scan cannot read, said rather than left out.
UNREAD = {
    "sheet": "a picture laid beside another has no signature a test would not share",
}

#: Folders never read: the work area, dependencies and tool caches.
SKIP = {"node_modules", "__pycache__", "site-packages", "venv", "build", "dist"}


def _files(here: Path, work: Path) -> list[Path]:
    found = []
    for path in sorted(here.rglob("*.py")):
        parts = path.relative_to(here).parts
        if any(p.startswith(".") or p in SKIP for p in parts[:-1]):
            continue
        if path.is_relative_to(work):
            continue
        found.append(path)
    return found


def scan(here: Path, kept: dict, work: Path) -> dict:
    """Each surface's files: the ones doing it here, and the ones kept on purpose."""
    surfaces = {
        name: {"does": one["does"], "use": one["use"], "own": [], "kept": []}
        for name, one in SURFACES.items()
    }
    for path in _files(here, work):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        named = path.relative_to(here).as_posix()
        for name, one in SURFACES.items():
            if not all(pattern.search(text) for pattern in one["all"]):
                continue
            if named in kept:
                surfaces[name]["kept"].append({"file": named, "why": kept[named]})
            else:
                surfaces[name]["own"].append(named)
    return surfaces


@operation("project.adoption")
def adoption(
    root: Annotated[str, Param("the adopted project whose own code is read")] = ".",
) -> dict:
    """What the project's own code still does that a polyweave call already does.

    Per surface, `own` lists the files doing it here and `kept` the ones that
    `[adoption] own` names with a reason. `adopted` counts the surfaces with nothing
    left of either; a file kept on purpose still counts against it, so the number says
    what is left and
    the reasons say why. `clean` is false while any file is in `own`, and the command
    exits non-zero then, so a project can gate on this alone; `project.check` fails on
    the same files and never on `kept`.
    """
    from polyweave.kernel.config import load

    config = load(root)
    here = config.root
    kept = {
        str(k).replace("\\", "/"): str(v) for k, v in config.get("adoption.own").items()
    }
    surfaces = scan(here, kept, config.path("paths.work"))
    clear = [n for n, one in surfaces.items() if not one["own"] and not one["kept"]]
    owning = sum(len(one["own"]) for one in surfaces.values())
    keeping = sum(len(one["kept"]) for one in surfaces.values())
    stale = sorted(k for k in kept if not (here / k).is_file())
    return {
        # What a gate stands on: false while any file does a surface unkept.
        "clean": owning == 0,
        "surfaces": surfaces,
        "adopted": {"surfaces": len(clear), "of": len(surfaces), "clear": clear},
        "unread": UNREAD,
        **({"stale": stale} if stale else {}),
        "says": (
            f"{len(clear)} of {len(surfaces)} surfaces are polyweave's alone; "
            f"{owning} file(s) do one of them here and {keeping} are kept on purpose"
            + (f"; [adoption] own names {len(stale)} file(s) that are gone" if stale
               else "")
        ),
    }
