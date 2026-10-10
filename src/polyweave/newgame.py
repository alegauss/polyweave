"""A game born adopted, from one call (§PW369).

project.init adopts a tree that already exists, which is the right door for Starship and
Cottony and the wrong one for the next game: created bare and adopted afterwards, it has
its first weeks of hand-rolled code to undo. `project.new` creates the game already on
polyweave instead:

- a Godot project with a main scene, keeping the renderer's fallback on;
- the repository's `.gitignore` and `.gitattributes`, binaries in Git LFS, and a git
  repository where git is on this machine;
- polyweave.toml through project.init, with the agent wired (server and AGENTS.md);
- the base kits, each installed by kit.install with its proof: rebinding, menus, the
  options screen, saves, and the tests kit with a first test;
- a gate, `tools/gate.py`, running project.check, engine.check and game.test.

The answer is project.check's verdict on the new tree and every kit provenance.read
says it carries, so a game never has a version of these parts of its own to migrate
away from.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

from .describe import Param, operation
from .errors import PolyweaveError

#: The kits a new game starts with: input, menus, settings, saves and its tests.
BASE = ["remap", "menus", "options", "saves", "tests"]

#: What Git LFS carries: every binary a game keeps.
LFS = ("png", "jpg", "jpeg", "webp", "exr", "hdr", "wav", "ogg", "mp3", "flac", "glb",
       "gltf", "blend", "fbx", "ttf", "otf", "psd", "zip")

IGNORE = """# Godot's own cache, rebuilt by an import
.godot/
# polyweave's work folder: jobs, logs, captures and this machine's baselines
.polyweave/
# exports
build/
*.tmp
"""

GATE = '''"""This game's gate: polyweave's checks and its tests, one exit code."""

import subprocess
import sys

STEPS = [
    ["project.check"],
    ["engine.check"],
    ["game.test"],
]


def main() -> int:
    failed = 0
    for step in STEPS:
        done = subprocess.run([sys.executable, "-m", "polyweave", *step, "--root", "."],
                              check=False)
        print(f"{'ok  ' if done.returncode == 0 else 'FAIL'} {' '.join(step)}")
        failed += done.returncode != 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

FIRST_TEST = '''extends "res://addons/polyweave/tests/test.gd"
## The game's first test: its main scene loads and stands up.


func test_the_main_scene_loads() -> void:
\tvar main := str(ProjectSettings.get_setting("application/run/main_scene", ""))
\tvar packed := load(main) as PackedScene
\tif check(packed != null, "the main scene %s loads" % main):
\t\tvar made := packed.instantiate()
\t\troot.add_child(made)
\t\tcheck(made.is_inside_tree(), "the main scene stands up in the tree")
\t\tmade.queue_free()
'''


@operation("project.new")
def new(
    root: Annotated[str, Param("the folder the game is made in, empty or not there")],
    *,
    name: Annotated[str, Param("the game's name, as Godot shows it")],
    kits: Annotated[
        list, Param("the kits it starts with; input, menus, options, saves and tests")
    ] = None,
    git: Annotated[bool, Param("start a git repository, where git is here")] = True,
) -> dict:
    """A new game, created already adopted: Godot project, repository files, config,
    agent, base kits each proved, a first test and a gate, in one call (§PW369).

    Refuses a folder that already holds files; project.init is the door for those.
    Answers project.check's verdict on the new tree and the kits provenance.read says
    it carries, with their versions.
    """
    from . import kits as kit_module
    from . import project, provenance

    here = Path(root).expanduser().resolve()
    if here.exists() and any(here.iterdir()):
        raise PolyweaveError(
            "adopt.not-empty",
            f"{here} already holds files, and project.new only starts a game",
            "adopt a game that exists with project.init --write --agent",
            given=str(here),
        )
    here.mkdir(parents=True, exist_ok=True)
    (here / "project.godot").write_text(
        "config_version=5\n\n[application]\n\n"
        f'config/name="{name}"\nrun/main_scene="res://main.tscn"\n\n'
        "[rendering]\n\nrendering_device/fallback_to_opengl3=true\n",
        encoding="utf-8", newline="\n")
    (here / "main.tscn").write_text(
        '[gd_scene format=3]\n\n[node name="Main" type="Node"]\n',
        encoding="utf-8", newline="\n")
    (here / ".gitignore").write_text(IGNORE, encoding="utf-8", newline="\n")
    (here / ".gitattributes").write_text(
        "# every binary in Git LFS, every text file with LF endings\n"
        "* text=auto eol=lf\n"
        + "".join(f"*.{ext} filter=lfs diff=lfs merge=lfs -text\n" for ext in LFS),
        encoding="utf-8", newline="\n")
    repository = False
    if git and shutil.which("git"):
        repository = subprocess.run(["git", "init", "-q", str(here)], check=False,
                                    capture_output=True).returncode == 0
    adopted = project.init(str(here), write=True, agent=True)
    landed = []
    for one in (BASE if kits is None else list(kits)):
        installed = kit_module.install(one, root=str(here))
        landed.append({"kit": one, "proved": installed["proved"],
                       "order": installed["order"]})
    if (here / "addons" / "polyweave" / "tests").is_dir():
        (here / "tests").mkdir(exist_ok=True)
        (here / "tests" / "main_test.gd").write_text(FIRST_TEST, encoding="utf-8",
                                                     newline="\n")
    (here / "tools").mkdir(exist_ok=True)
    (here / "tools" / "gate.py").write_text(GATE, encoding="utf-8", newline="\n")
    checked = project.check(str(here))
    # what provenance.read says of each kit the game carries, as an agent would ask it
    carried = []
    for manifest in sorted((here / "addons" / "polyweave").glob("*/kit.json")):
        record = provenance.read(manifest.relative_to(here).as_posix(), root=str(here))
        kit = record.get("kit") or {}
        carried.append((kit.get("name"), kit.get("version")))
    broke = [one for one in landed if one["proved"] and not one["proved"]["passed"]]
    return {
        "root": str(here),
        "repository": repository,
        "config": adopted.get("wrote", False),
        "kits": landed,
        "carries": [{"kit": k, "version": v} for k, v in carried],
        "check": checked,
        "ok": checked["clean"] and not broke,
        "gate": "python tools/gate.py",
        "says": f"{name} made at {here} with {len(carried)} kit(s); project.check "
        + ("clean" if checked["clean"] else f"found {checked['errors']} error(s)")
        + ("" if not broke else f"; {broke[0]['kit']}'s proof failed"),
    }
