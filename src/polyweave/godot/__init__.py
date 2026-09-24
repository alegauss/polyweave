"""What polyweave puts into a Godot project (§PW102).

The addons live beside this file and are copied in whole, so a Godot consumer reads a
voxel model with the loader written once here rather than a parser of its own.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..errors import PolyweaveError

__all__ = ["ADDONS", "install"]

#: The addons this package carries, by the folder name they take under `addons/`.
ADDONS = {"polyweave_voxels": Path(__file__).parent / "addons" / "polyweave_voxels"}


def install(project: str | Path, addon: str = "polyweave_voxels") -> dict:
    """Copy an addon into a Godot project's `addons/`, replacing an older copy.

    Refused where the folder is not a Godot project, since an addon copied beside no
    `project.godot` is one nothing will ever load.
    """
    root = Path(project).resolve()
    if not (root / "project.godot").is_file():
        raise PolyweaveError(
            "engine.not-a-project",
            f"{root} has no project.godot, so there is nowhere to install {addon}",
            "point it at the folder holding the Godot project",
        )
    source = ADDONS.get(addon)
    if source is None:
        raise PolyweaveError(
            "engine.unknown-addon",
            f"there is no addon called {addon!r}",
            f"name one of {', '.join(sorted(ADDONS))}",
        )
    target = root / "addons" / addon
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("*.uid", "*.import"))
    return {
        "addon": addon,
        "installed": str(target),
        "files": sorted(
            str(one.relative_to(root)).replace("\\", "/")
            for one in target.rglob("*.gd")
        ),
    }
