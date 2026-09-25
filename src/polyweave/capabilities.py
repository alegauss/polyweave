"""What this installation can actually do, on this machine, right now.

`docs/specs/tool-surface.md` §4: a caller plans against this rather than discovering a
missing binary three calls later. So the answer is measured — a binary is run and asked
its version — and never inferred from a path existing.

What is not established yet is reported as such, with the line that establishes it,
which is the difference between "no budget" and "nobody has said".
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .census import pending_modules
from .codes import AREAS
from .config import load
from .describe import describe
from .errors import codes
from .jobs.stages import KINDS, TERMINAL
from .measure import COMPUTES, SUFFIXES
from .post import CHEAP, OPTIONAL

#: Long enough for a cold start off a slow disk, short enough not to hold the turn.
PROBE_TIMEOUT_S = 20.0

#: What is not established yet, keyed by topic, each value naming the open roadmap
#: line that establishes it. Empty today: the two it held (PW14, PW23) have shipped.
PENDING: dict[str, str] = {}


def _probe(binary: str, where: str | Path, args: tuple[str, ...]) -> dict:
    """Find a binary and ask it its version, reporting what actually happened.

    `where` is either a bare name to look up on PATH — which is the default, since a
    compiled-in path is the defect §PW5 is about — or the path a project declared.
    """
    named = str(where)
    found = shutil.which(named)
    if not found:
        bare = Path(named).name == named
        return {
            "found": False,
            "path": named,
            "version": None,
            "why": f"{binary} is not on PATH"
            if bare
            else f"nothing runnable at {named}",
        }
    try:
        done = subprocess.run(
            [found, *args],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"found": True, "path": found, "version": None, "why": str(exc)}
    output = (done.stdout or done.stderr or "").strip().splitlines()
    return {
        "found": True,
        "path": found,
        "version": output[0].strip() if output else None,
        "why": None if output else "it printed no version",
    }


def _blender_module() -> dict:
    from .render import blender

    return blender.available()


def _colour(work: Path, probe: bool) -> dict:
    """Whether a colour measured off a render here is the colour that was authored.

    §PW43: a request for the view transform that puts back what was put in can be
    accepted and not take effect, and then every `delta_e` in every acceptance spec is
    measuring the tone curve as much as the material — silently, and with a result that
    looks plausible. One small render settles it for every measurement built on top,
    which is why it sits here rather than being discovered by a search that tuned the
    lighting to compensate for a transform.
    """
    if not probe:
        return {"checked": False, "why": "not probed"}
    from .render import blender

    if not blender.available().get("found"):
        return {"checked": False, "why": "bpy is not importable, so nothing can render"}
    try:
        work.mkdir(parents=True, exist_ok=True)
        return blender.colour_probe(work / "colour-probe.png")
    except Exception as exc:  # noqa: BLE001 - a probe that fails is an answer, not a stop
        return {
            "checked": False,
            "why": f"the probe render failed: {type(exc).__name__}: {exc}",
        }


def _describe_binary(binary: str, where: Path, probe: bool) -> dict:
    """Ask the binary, or say only where it would be looked for."""
    if probe:
        return _probe(binary, where, ("--version",))
    return {"found": None, "path": str(where), "version": None, "why": "not probed"}


def _key(key_env: str | None) -> dict:
    """Whether a service's key is set here, by the variable's name alone."""
    return {
        "key_env": key_env,
        "key_present": bool(os.environ.get(key_env)) if key_env else None,
    }


def capabilities(
    root: str | Path = ".",
    *,
    blender: str | Path | None = None,
    godot: str | Path | None = None,
    service_key_env: str | None = None,
    probe: bool = True,
) -> dict:
    """What this machine can do, and what nothing has established yet.

    Each argument overrides what `polyweave.toml` declares, which overrides the plugin's
    default — the resolution order, on this call rather than at startup.
    `service_key_env` is the **name** of the variable holding a key, never the key.
    """
    config = load(root)
    blender = config.path("paths.blender", blender)
    godot = config.path("paths.godot", godot)
    declared = config.services()
    only = next(iter(declared)) if len(declared) == 1 else None
    if only:
        service_key_env = service_key_env or declared[only]["key_env"] or None
    renderer = _describe_binary("blender", blender, probe)
    engine = _describe_binary("godot", godot, probe)
    reader = _describe_binary("tesseract", config.path("paths.tesseract"), probe)
    # Blender also ships as an importable module, and a worker that has it needs no
    # binary at all. Reporting only the binary would call a machine that can render one
    # that cannot.
    module = _blender_module() if probe else {"found": None, "why": "not probed"}

    # The name is reported and the value never is: a capability read that echoes a
    # secret is a capability read nobody can paste into a bug report. Each service by
    # its own name, since two keys are two questions (§PW162).
    services = {
        name: _key(service_key_env if name == only else about["key_env"] or None)
        for name, about in declared.items()
    }
    service = services[only] if only else None

    return {
        "polyweave": __version__,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "renderer": {
            "blender": renderer,
            "bpy": module,
            "usable": bool(module.get("found") or renderer.get("found")),
            # Usable and trustworthy are different questions: a renderer that runs can
            # still hand back a colour that is not the one authored (§PW43).
            "colour": _colour(config.path("paths.work"), probe),
        },
        "engine": {"godot": engine},
        # Reads the letters back off a picture; absent means lettering goes unchecked.
        "ocr": {"tesseract": reader},
        # The one service where there is one, and none where a caller has to choose.
        "service": service,
        "services": services,
        "operations": describe(),
        # Surface that exists and is not yet an operation (§PW124): named, so a caller
        # knows to look for it, until each module is registered and leaves this list.
        "unregistered": pending_modules(),
        "measures": {
            "names": sorted(COMPUTES),
            "suffixes": list(SUFFIXES),
        },
        "jobs": {
            "kinds": {kind: list(stages) for kind, stages in KINDS.items()},
            "terminal": list(TERMINAL),
        },
        "assertions": {
            "always": sorted(CHEAP),
            "optional": sorted(OPTIONAL),
        },
        "errors": {
            # Listed rather than counted: a caller that knows the codes can plan for a
            # failure instead of meeting it, and `explain` says what each one means.
            "areas": dict(AREAS),
            "codes": codes(),
        },
        "budget": config.budget() if only else None,
        "budgets": {name: config.budget(service=name) for name in declared},
        "project": {
            "name": config.get("project.name"),
            "root": str(config.root),
            "config": str(config.source) if config.source else None,
            "work": str(config.path("paths.work")),
        },
        # What is not established yet, each naming the open line that will establish it.
        # An entry leaves once its line ships (§PW137): a test reads the changelog.
        "pending": dict(PENDING),
    }
