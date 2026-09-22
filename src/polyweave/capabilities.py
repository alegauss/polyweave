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
from .describe import describe
from .jobs.stages import KINDS, TERMINAL
from .post import CHEAP, OPTIONAL

#: Long enough for a cold start off a slow disk, short enough not to hold the turn.
PROBE_TIMEOUT_S = 20.0


def _probe(binary: str, where: str | Path | None, args: tuple[str, ...]) -> dict:
    """Find a binary and ask it its version, reporting what actually happened."""
    found = str(where) if where else shutil.which(binary)
    if not found or not Path(found).exists():
        return {
            "found": False,
            "path": str(where) if where else None,
            "version": None,
            "why": f"{binary} is not on PATH" if not where else f"nothing at {where}",
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


def capabilities(
    *,
    blender: str | Path | None = None,
    godot: str | Path | None = None,
    service_key_env: str | None = None,
    probe: bool = True,
) -> dict:
    """What this machine can do, and what nothing has established yet.

    `blender` and `godot` are where to look; PW5 passes what `polyweave.toml` declares,
    and without them this falls back to PATH. `service_key_env` is the **name** of the
    variable holding a key, never the key.
    """
    renderer = (
        _probe("blender", blender, ("--version",))
        if probe
        else {"found": None, "path": str(blender) if blender else None}
    )
    engine = (
        _probe("godot", godot, ("--version",))
        if probe
        else {"found": None, "path": str(godot) if godot else None}
    )

    service = {"key_env": service_key_env, "key_present": None}
    if service_key_env:
        # The name is reported and the value never is: a capability read that echoes a
        # secret is a capability read nobody can paste into a bug report.
        service["key_present"] = bool(os.environ.get(service_key_env))

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
        "renderer": {"blender": renderer},
        "engine": {"godot": engine},
        "service": service,
        "operations": describe(),
        "jobs": {
            "kinds": {kind: list(stages) for kind, stages in KINDS.items()},
            "terminal": list(TERMINAL),
        },
        "assertions": {
            "always": sorted(CHEAP),
            "optional": sorted(OPTIONAL),
        },
        "pending": {
            "budget": "PW18 spends against it, and PW5 reads it from polyweave.toml",
            "offscreen": "PW23 establishes which offscreen route works on this machine",
            "cache": "PW14 reports what the cache holds and what it cost",
        },
    }
