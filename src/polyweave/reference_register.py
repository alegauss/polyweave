"""A reference video registered once, and read by name after (§PW407).

Every reference call named its video by path, so a video replaced, re-encoded or cut
between two calls was read silently as the same one, and a reading of one stretch was
laid against frames of another file. `reference.register` records a video once, in the
work area: its path, its SHA-256, its size, and the duration, resolution and frame rate
ffprobe reads from it. Later calls name it, or its path, and a video whose digest moved
since is refused with the call that registers it again. A `[reference.<name>]` declared
at another size than the video's is refused when the video is registered, so regions
are never measured against a video they were not drawn on.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The registry, in the work area beside the references' frames.
REGISTRY = Path("references") / "registered.json"


def _registry(here: Path) -> Path:
    return load(here).path("paths.work") / REGISTRY


def registered(here: Path) -> dict[str, dict]:
    """Every registered reference by name."""
    where = _registry(here)
    return json.loads(where.read_text(encoding="utf-8")) if where.is_file() else {}


def _probe(video: Path) -> dict:
    """The video's duration, width, height and frame rate; nothing without ffprobe."""
    if shutil.which("ffprobe") is None:
        return {}
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=False,
    )
    if done.returncode:
        return {}
    said = json.loads(done.stdout or "{}")
    stream = (said.get("streams") or [{}])[0]
    out: dict = {}
    if stream.get("width"):
        out["width"], out["height"] = int(stream["width"]), int(stream["height"])
    rate = str(stream.get("r_frame_rate", ""))
    if "/" in rate and rate.split("/")[1] not in ("", "0"):
        top, bottom = rate.split("/")
        out["rate"] = round(float(top) / float(bottom), 3)
    duration = (said.get("format") or {}).get("duration")
    if duration:
        out["duration"] = round(float(duration), 3)
    return out


def _unchanged(entry: dict, path: Path) -> bool:
    """Whether the file is the one registered. Its size and time are checked first, and
    its digest only where either moved: a video can be gigabytes, read each call."""
    if not path.is_file():
        return False
    stat = path.stat()
    if stat.st_size == entry["bytes"] and stat.st_mtime_ns == entry["mtime_ns"]:
        return True
    return provenance.sha256_of(path)[0] == entry["sha256"]


def video_of(given: str, here: Path) -> tuple[Path, str | None]:
    """The video a call names, by its registered name or its path, and that name; one
    registered is refused where it is no longer the file that was registered."""
    known = registered(here)
    entry, name = known.get(given), given if given in known else None
    if entry is None:
        path = Path(given) if Path(given).is_absolute() else here / given
        for other, one in known.items():
            if Path(one["path"]) == path.resolve():
                entry, name = one, other
                break
        if entry is None:
            return path, None
    path = Path(entry["path"])
    if not _unchanged(entry, path):
        raise PolyweaveError(
            "fetch.reference-changed",
            f"{name} is not the video registered on {entry['at']}: "
            + ("it is gone" if not path.is_file() else "its digest moved"),
            f"register it again: reference.register --video {path.as_posix()} "
            f"--name {name}",
            given=str(given),
        )
    return path, name


@operation("reference.register")
def register(
    video: Annotated[str, Param("the gameplay video, anywhere; it is never copied in")],
    *,
    name: Annotated[
        str, Param("what later calls name it by; the video's file name if empty")
    ] = "",
    root: Annotated[str, Param("the project the registry is kept in")] = ".",
) -> dict:
    """Register a reference video once, so later calls name it and a changed file is
    refused (§PW407).

    Its path, SHA-256 and size, and the duration, resolution and frame rate ffprobe
    reads, are kept in the work area's references/registered.json. A video declared as
    `[reference.<name>]` at another size than it is, is refused.
    """
    config = load(root)
    here = config.root
    path = Path(video) if Path(video).is_absolute() else here / video
    if not path.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no video at {path}",
            "name the gameplay video's path; it stays where it is",
            given=str(video),
        )
    called = name or path.stem
    probed = _probe(path)
    declared = (config.references() or {}).get(called)
    if declared and probed.get("width") and declared.get("size") and list(
            declared["size"]) != [probed["width"], probed["height"]]:
        raise PolyweaveError(
            "capture.wrong-size",
            f"{path.name} is {probed['width']}x{probed['height']}, and "
            f"[reference.{called}] was declared at "
            f"{declared['size'][0]}x{declared['size'][1]}",
            "register the video the regions were measured on, or declare the "
            "reference at this size",
            given=f"{probed['width']}x{probed['height']}",
        )
    from datetime import UTC, datetime

    stat = path.stat()
    entry = {
        "path": path.resolve().as_posix(),
        "sha256": provenance.sha256_of(path)[0],
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        **probed,
    }
    known = registered(here)
    known[called] = entry
    where = _registry(here)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    size = (f", {probed['width']}x{probed['height']}" if "width" in probed else "")
    return {
        "name": called,
        **entry,
        "registry": provenance.relative(where, here),
        "says": f"{path.name} registered as {called}{size}; name it in reference "
        "calls, and a changed file is refused",
    }
