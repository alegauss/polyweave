"""The engine layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "engine": {
        # The bounds a scene script runs under. Both of them, because the frame budget
        # is what ends a script the engine would otherwise sit in forever, and the wall
        # clock is what ends a run the engine never reaches a frame of (§PW22).
        "fixed_fps": 60,
        "frames": 6000,
        "timeout": 180,
        # A capture's window starts minimised and unfocused, out of sight (§PW296).
        "quiet": True,
        # The leak at exit game.boot forgives, as [objects, resources] (§PW469): one the
        # engine's headless dummy driver causes and the game cannot, named exactly.
        "leaks": [],
    },
    # Each scene's performance budget, `[perf.<name>]` (§PW365): its scene, the frames
    # measured, and the most each measure may reach; engine.perf reads them.
    "perf": {},
    # Each engine run a game declares, `[run.<name>]` (§PW467): its script, the line it
    # prints when it worked and what it writes; engine.run_declared runs them.
    "run": {},
    "driving": {
        # Seconds a driven game waits for its next call before it quits, so a session an
        # agent forgot never outlives the conversation that opened it (§PW213).
        "idle": 600,
    },
    "capture": {
        "locale": "",
        "resolution": [1920, 1080],
        # The two that differed between two machines in §PW25, and the reason the list
        # exists at all.
        "declared": ["locale", "resolution"],
        # Whether a capture that stops reproducing is a refusal rather than a remark
        # (§PW75). Off, because the plugin cannot make an engine deterministic and a
        # project that has not pinned its captures would fail every run. A project that
        # has pinned them turns it on, and keeps what it earned.
        "reproducible": False,
    },
    "flashes": {
        # The photosensitivity guidance measure.flashes holds a captured run to
        # (§PW354), WCAG 2.3.1's numbers: at most `limit` flashes in any one second, a
        # flash being two opposing changes of relative luminance of `luminance` with the
        # darker state under `dark`, or of a saturated red's (R - G - B) * 320 by more
        # than `red`, over at least `area` of the screen (a quarter of a 10 degree
        # field, 341 by 256 of a 1024 by 768 screen).
        "limit": 3,
        "luminance": 0.1,
        "dark": 0.8,
        "red": 20.0,
        "area": 0.0277,
    },
}

#: Tables a project may add its own keys to.
FREE = ("capture", "perf", "run",)
