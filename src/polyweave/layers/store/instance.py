"""The clean product instance a web visit films, declared, reset and proved (§PW710).

A product video films WordPress or Shio on a clean instance, and every retake repeated
Docker Compose and seed commands by hand, so a clip could not say which instance it
recorded. The instance is declared in a `*.instance.toml`:

```toml
[instance]
compose = "docker/wordpress.compose.yml"   # the Compose file, under the project
project = "pw-wordpress"                   # the Compose project, the only one touched
ready   = "http://localhost:8080/wp-login.php"
ready_seconds = 120                        # how long up or reset waits for it

[[seed]]                                   # run in a service of that project, in order
service = "cli"
run = ["wp", "core", "install", "--url=localhost:8080", "--title=Demo"]
```

`capture.instance` plans, brings up, resets or takes down that one Compose project, at a
person's or agent's explicit call and never as a side effect of filming: a reset is
`down --volumes` of the declared project, `up`, the readiness wait and the seeds.
Nothing outside the project is named, so a container, volume or network it does not own
is never touched. `capture.web` with `[web] instance` refuses an instance that is not
ready and records which containers and images it filmed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: What `capture.instance` does; `plan` says the commands and runs none.
ACTIONS = ("plan", "up", "reset", "down", "status")

_KEYS = {"compose", "project", "ready", "ready_seconds"}


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("web.bad-instance", message, remedy, **extra)


def read(source: Path, here: Path) -> dict:
    """The instance a *.instance.toml declares, checked before anything runs."""
    if not source.is_file():
        raise _bad(f"there is no instance at {source}",
                   "name a *.instance.toml under the project", given=str(source))
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise _bad(f"{source.name} is not TOML", "fix the line the detail names",
                   detail=str(broken)) from None
    table = declared.get("instance") or {}
    stray = sorted(set(table) - _KEYS) + sorted(set(declared) - {"instance", "seed"})
    if stray:
        raise _bad(f"{source.name} has {stray[0]!r}", f"use [instance] with "
                   f"{', '.join(sorted(_KEYS))}, and [[seed]]", given=stray[0])
    compose = here / str(table.get("compose") or "")
    if not table.get("compose") or not compose.is_file():
        raise _bad(f"{source.name} names no Compose file under the project",
                   "give [instance] compose as the Compose file's path")
    project = str(table.get("project") or "")
    if not project or not all(c.isalnum() or c in "-_" for c in project):
        raise _bad(f"[instance] project is {project!r}",
                   "name the Compose project in letters, digits, - and _")
    ready = str(table.get("ready") or "")
    if not ready.startswith(("http://", "https://")):
        raise _bad(f"[instance] ready is {ready!r}",
                   "give ready as the URL that answers once the product is up")
    seconds = table.get("ready_seconds", 120)
    if isinstance(seconds, bool) or not isinstance(seconds, int | float) or (
            seconds <= 0):
        raise _bad(f"[instance] ready_seconds is {seconds!r}", "give seconds above 0")
    seeds = declared.get("seed") or []
    for n, one in enumerate(seeds):
        if not (isinstance(one, dict) and isinstance(one.get("service"), str)
                and isinstance(one.get("run"), list) and one["run"]
                and all(isinstance(a, str) for a in one["run"])):
            raise _bad(f"seed[{n}] is {one!r}",
                       "give each seed a service and run, a list of strings",
                       at=f"seed[{n}]")
    return {"compose": compose, "project": project, "ready": ready,
            "ready_seconds": float(seconds), "seeds": seeds, "source": source}


def _docker(argv: list[str]) -> str:
    """One docker call; a failure is a code with what docker said."""
    found = shutil.which("docker")
    if not found:
        raise PolyweaveError(
            "web.no-docker",
            "an instance is run with Docker Compose, and docker is not on PATH",
            "install Docker and put it on PATH")
    done = subprocess.run([found, *argv], capture_output=True, text=True,
                          encoding="utf-8", check=False, timeout=900)
    if done.returncode != 0:
        raise PolyweaveError(
            "web.instance-failed", f"docker {' '.join(argv[:6])} failed",
            "read the detail, which is what docker said",
            detail=(done.stderr or done.stdout or "")[-400:])
    return done.stdout


def _answers(url: str) -> bool:
    """Whether the instance's ready URL answers below 500."""
    try:
        with urllib.request.urlopen(url, timeout=5) as answer:  # noqa: S310
            return answer.status < 500
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (urllib.error.URLError, OSError):
        return False


def _compose(fixture: dict) -> list[str]:
    return ["compose", "-p", fixture["project"], "-f", str(fixture["compose"])]


def _commands(fixture: dict, action: str) -> list[list[str]]:
    """The docker calls an action makes, every one scoped to the declared project."""
    base = _compose(fixture)
    up = [*base, "up", "--detach", "--wait"]
    seeds = [[*base, "exec", "-T", one["service"], *one["run"]]
             for one in fixture["seeds"]]
    return {
        "up": [up, *seeds],
        "reset": [[*base, "down", "--volumes", "--remove-orphans"], up, *seeds],
        "down": [[*base, "down", "--remove-orphans"]],
        "status": [],
    }.get(action, [])


def waited(fixture: dict) -> float:
    """Seconds until the ready URL answered, refused past `ready_seconds`."""
    started = time.monotonic()
    while not _answers(fixture["ready"]):
        if time.monotonic() - started > fixture["ready_seconds"]:
            raise PolyweaveError(
                "web.instance-not-ready",
                f"{fixture['ready']} did not answer within "
                f"{fixture['ready_seconds']:g}s",
                "bring the instance up with capture.instance action=up, or reset it")
        time.sleep(1.0)
    return round(time.monotonic() - started, 3)


def identity(fixture: dict) -> list[dict]:
    """Which containers of the project are running, and from which image."""
    said = _docker([*_compose(fixture), "ps", "--format", "json"])
    rows = []
    for line in said.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        for one in parsed if isinstance(parsed, list) else [parsed]:
            rows.append({"service": one.get("Service"), "container": one.get("ID"),
                         "image": one.get("Image"), "state": one.get("State")})
    return rows


@operation("capture.instance")
def instance(
    fixture: Annotated[str, Param("the *.instance.toml, under the project")],
    *,
    action: Annotated[str, Param("what to do with it", choices=ACTIONS)] = "plan",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Plan, bring up, reset, take down or read a declared product instance (§PW710).

    `plan` answers the docker calls the other actions would make and runs none. `up`
    starts the project and runs its seeds; `reset` takes the project down with its own
    volumes first, so the next visit films a clean instance; both wait for the ready
    URL within `ready_seconds`. `down` stops it; `status` reads which containers and
    images run. Every call names the declared Compose project and file, so nothing it
    does not own is touched, and nothing runs unless this is called.
    """
    from polyweave.kernel.config import load

    here = load(root).root
    declared = read(here / fixture, here)
    planned = _commands(declared, action)
    if action == "plan":
        return {"fixture": fixture, "project": declared["project"],
                "plan": {name: [["docker", *one] for one in _commands(declared, name)]
                         for name in ("up", "reset", "down")}}
    for one in planned:
        _docker(one)
    answer: dict = {"fixture": fixture, "project": declared["project"],
                    "action": action, "ran": len(planned)}
    if action in ("up", "reset"):
        answer["ready_after"] = waited(declared)
    if action != "down":
        answer["containers"] = identity(declared)
    return answer
