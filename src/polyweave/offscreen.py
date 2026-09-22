"""Getting real pixels out of the engine with nobody watching.

The evidence is §PW23: Godot's headless mode runs on a **dummy renderer that draws
nothing**, so any capture needing real pixels needs a real one, which pushes every
visual check onto a developer's desk and out of every gate. That is the single reason
Block B's comparisons cannot be enforced.

The engine states the problem itself. `--help` on 4.7.1 lists the display drivers as
`"windows" ("vulkan", "d3d12", "opengl3", "opengl3_angle", "dummy")` and
`"headless" ("dummy")`: **the headless display driver offers the dummy rendering driver
and nothing else.** Asking for `--display-driver headless --rendering-driver vulkan`
does not change that; the read back comes out of `dummy/storage/texture_storage.h` and
there is no image.

What does work, measured on this machine, is the third route the section names: a **real
display driver**, and the picture taken from a **viewport texture read back inside
the engine** rather than grabbed off a window. Nothing about the window's contents,
focus or visibility is involved, so the window can be minimised or moved off the desktop
and the capture is identical. All four of the platform's rendering drivers produce the
same pixels.

What that still needs is a **display server**: an interactive session on Windows, an
X or Wayland server elsewhere. That is what `xvfb-run` supplies on a machine with no
screen at all, and why it is a route here rather than a footnote.

**A route is available only where it has been proved available.** `routes` writes a
throwaway project of its own, renders one known colour through each candidate, and reads
the pixel back off disk. A route that draws is one whose picture was looked at. The
answer is kept, because probing is a second or two and it only changes when the machine
does.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import engine
from .config import load
from .errors import PolyweaveError
from .files import write_atomic

#: The colour the probe draws, picked so no default background could be mistaken for it.
PROVES = (0.2, 0.7, 0.35)

#: How close a read-back pixel has to be to count as the colour that was asked for.
NEAR = 8

#: What a route asks a capture script to do with its window, passed after `--`. A script
#: that ignores it still captures; its window is simply visible while it does.
WINDOWS = ("offscreen", "minimized")


@dataclass(frozen=True)
class Route:
    """One way of getting the engine to draw where nobody is looking."""

    name: str
    about: str
    args: tuple[str, ...]
    #: Passed after `--`, for a capture script that honours it.
    window: str = ""
    #: A command that has to exist for this route to be possible at all.
    needs: str = ""
    #: What the engine is launched through, with the engine's own command appended.
    through: tuple[str, ...] = ()


ROUTES: tuple[Route, ...] = (
    Route(
        name="window-offscreen",
        about="a real display driver, with the window moved off the desktop",
        args=(),
        window="offscreen",
    ),
    Route(
        name="window-minimised",
        about="a real display driver, with the window minimised",
        args=(),
        window="minimized",
    ),
    Route(
        name="virtual-display",
        about="a real display driver on a display server started for the run",
        args=(),
        window="offscreen",
        needs="xvfb-run",
        through=("xvfb-run", "-a"),
    ),
    Route(
        name="headless",
        about="the engine's own headless mode, which draws nothing and is here to be "
        "shown not to",
        args=("--headless",),
    ),
)

#: A Godot project of its own, so what is probed is the machine and not a project.
PROJECT = """config_version=5

[application]
config/name="polyweave-offscreen-probe"
run/main_scene=""
"""

#: Renders one known colour into a viewport and reads it back, which is the whole claim.
PROBE = """extends SceneTree

var frames := 0
var view: SubViewport

func _initialize() -> void:
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg == "offscreen":
\t\t\tDisplayServer.window_set_position(Vector2i(-32000, -32000))
\t\telif arg == "minimized":
\t\t\tDisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
\tview = SubViewport.new()
\tview.size = Vector2i(64, 48)
\tview.render_target_update_mode = SubViewport.UPDATE_ALWAYS
\tvar patch := ColorRect.new()
\tpatch.color = Color(%COLOUR%)
\tpatch.size = Vector2(64, 48)
\tview.add_child(patch)
\troot.add_child(view)

func _process(_delta: float) -> bool:
\tframes += 1
\tif frames < 4:
\t\treturn false
\tvar texture := view.get_texture()
\tif texture == null:
\t\tprint("capture failed: the renderer handed back no texture")
\t\treturn true
\tvar image := texture.get_image()
\tif image == null:
\t\tprint("capture failed: the renderer handed back no image")
\t\treturn true
\timage.save_png("res://probe.png")
\tprint("captured: res://probe.png %d x %d" % [image.get_width(), image.get_height()])
\treturn true
"""

CAPTURED = r"captured: (?P<artefact>\S+) (?P<width>\d+) x (?P<height>\d+)"


def _bench(root: Path) -> Path:
    """The throwaway project the probe runs in, written fresh each time."""
    where = root / "offscreen"
    colour = ", ".join(f"{channel}" for channel in PROVES)
    write_atomic(where / "project.godot", PROJECT)
    write_atomic(where / "probe.gd", PROBE.replace("%COLOUR%", colour))
    (where / "probe.png").unlink(missing_ok=True)
    return where


def _drew(picture: Path) -> tuple[bool, str]:
    """Whether the picture on disk really is the colour the probe was told to draw."""
    from .image import load as load_image

    if not picture.is_file():
        return False, "no picture was written"
    pixels = load_image(picture).rgba
    middle = pixels[pixels.shape[0] // 2, pixels.shape[1] // 2]
    wanted = [round(channel * 255) for channel in PROVES]
    off = max(abs(int(middle[i]) - wanted[i]) for i in range(3))
    if off > NEAR:
        return False, (
            f"the middle pixel is {tuple(int(v) for v in middle[:3])} and the probe "
            f"drew {tuple(wanted)}"
        )
    return True, ""


def _said(found: dict) -> str:
    """What the probe itself reported, in preference to the generic verdict.

    "the script never printed its line" is true of a dummy renderer and says nothing;
    "the renderer handed back no image" is the finding.
    """
    try:
        log = Path(found["log"]).read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - the log is written before this is read
        return found["why"]
    for line in log.splitlines():
        if line.startswith("capture failed:"):
            return line.removeprefix("capture failed:").strip()
    return found["why"]


def probe(route: Route, *, root: str | Path = ".", timeout: float = 90.0) -> dict:
    """Run one known colour through one route, and look at what came out."""
    settings = load(root)
    if route.needs and not shutil.which(route.needs):
        return {
            "route": route.name,
            "about": route.about,
            "works": False,
            "why": f"{route.needs} is not on PATH, so this route is not possible here",
            "seconds": 0.0,
        }
    bench = _bench(settings.path("paths.work"))
    args = tuple(route.args)
    if route.window:
        args += ("--", route.window)

    started = time.monotonic()
    try:
        found = engine.run(
            bench / "probe.gd",
            expect=CAPTURED,
            root=bench,
            produces=("artefact",),
            timeout=timeout,
            args=args,
            through=route.through,
            # The engine the project named, running the probe's own project: what is
            # being probed is the machine, and it has to be the same binary.
            binary=engine.find(root),
        )
    except PolyweaveError as refused:
        return {
            "route": route.name,
            "about": route.about,
            "works": False,
            "why": refused.message,
            "seconds": round(time.monotonic() - started, 3),
        }

    drew = _drew(bench / "probe.png")
    works, why = drew if found["ok"] else (False, _said(found))
    return {
        "route": route.name,
        "about": route.about,
        "works": works,
        "why": "" if works else why,
        "seconds": found["seconds"],
        "log": found["log"],
    }


def _kept(root: str | Path) -> Path:
    return load(root).path("paths.work") / "offscreen" / "routes.json"


def routes(root: str | Path = ".", *, recheck: bool = False) -> dict:
    """Which routes draw on this machine, proved rather than assumed.

    Kept once probed: the answer is a second or two of engine start-up per route and it
    only changes when the machine does. `recheck` pays for it again.
    """
    where = _kept(root)
    if not recheck and where.is_file():
        try:
            return json.loads(where.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    found = [probe(route, root=root) for route in ROUTES]
    answer = {
        "engine": engine.find(root),
        "checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "routes": found,
        "available": [one["route"] for one in found if one["works"]],
    }
    write_atomic(where, json.dumps(answer, indent=2) + "\n")
    return answer


def route_for(root: str | Path = ".", *, named: str = "") -> Route:
    """The route a capture will take, without the caller having to know which."""
    by_name = {one.name: one for one in ROUTES}
    if named:
        if named not in by_name:
            raise PolyweaveError(
                "engine.no-offscreen-route",
                f"{named!r} is not a route",
                f"name one of {', '.join(by_name)}, or leave it out to take the first "
                f"that draws here",
            )
        return by_name[named]
    found = routes(root)
    if found["available"]:
        return by_name[found["available"][0]]
    tried = "; ".join(f"{one['route']}: {one['why']}" for one in found["routes"])
    raise PolyweaveError(
        "engine.no-offscreen-route",
        "no route draws real pixels on this machine",
        "on a machine with no screen, install xvfb-run; otherwise run where there is a "
        "display server, because the engine's headless mode draws nothing at all",
        detail=tried,
    )


def capture(script: str | Path, *, route: str = "", **how: Any) -> dict:
    """Run a capture script by whichever route draws here, and say which one it was.

    The caller names a scene script and the line it prints. Which of the routes gets the
    engine drawing is this function's problem, and the result records the answer so a
    picture can be traced back to how it was taken.
    """
    root = how.get("root", ".")
    taken = route_for(root, named=route)
    args = tuple(how.pop("args", ()))
    if taken.window and taken.window not in args:
        # One `--` only: everything past the first is a user argument, so a second
        # separator arrives at the script as an argument spelled "--".
        args += (taken.window,) if "--" in args else ("--", taken.window)
    found = engine.run(
        script, args=tuple(taken.args) + args, through=taken.through, **how
    )
    return {**found, "route": taken.name, "about": taken.about}
