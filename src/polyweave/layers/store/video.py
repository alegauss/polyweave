"""A teaser cut together from captured runs, scored and encoded (§PW429).

`capture.movie` keeps every frame between two marks a script prints. A store teaser is
several such stretches from different runs, cut together at stated lengths with the
game's music under them, encoded as H.264 in an MP4 at a size the store takes, and
opening on play within seconds. The edit is declared in a `*.cut.toml`:

```toml
[video]
out = "store/teaser.mp4"     # where it is written; the call's `out` wins
size = [1920, 1080]          # each clip fitted inside it, centred on black
fps = 30
music = "audio/theme.ogg"    # the sound beneath, optional
music_from = 0.0             # seconds into it the teaser starts
music_gain = 0.0             # dB
clip_audio = false           # each clip's own audio.wav mixed in under the music
fade_out = 1.0               # seconds the end fades to black and silence

[[clip]]
from = ".polyweave/teaser/fight"   # a folder capture.movie wrote
start = 1.0                        # seconds into that run
length = 4.0                       # seconds held
fade_in = 0.0                      # seconds it crossfades from the clip before; 0 cuts
```

`video.cut` builds it with ffmpeg, records it with each sequence as an input, and
measures the file it wrote: its length, size and rate, and `first_motion`, the seconds
before one frame first differs from the one before it. An acceptance spec bounds those
names as it bounds a picture's, and the teaser is laid in a sitting as a sheet of
stills.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: What a predicate may bound on a video, and what it says.
VIDEOS: dict[str, str] = {
    "video_seconds": "the teaser's length in seconds",
    "video_width": "its width in pixels",
    "video_height": "its height in pixels",
    "video_fps": "its frames a second",
    "first_motion": "seconds before one frame first differs from the one before it",
}

#: A frame differs from the one before it where more than MOTION of its pixels, read in
#: grey at _SIDE across, changed by more than _STEP of full scale: the encoder's own
#: noise on a still title or a held black stays under both, and one small thing moving
#: across the screen does not.
MOTION = 0.002
_STEP = 0.06
_SIDE = 160

_VIDEO_KEYS = {
    "out",
    "size",
    "fps",
    "music",
    "music_from",
    "music_gain",
    "clip_audio",
    "fade_out",
}
_CLIP_KEYS = {"from", "start", "length", "fade_in"}


def _ffmpeg(tool: str = "ffmpeg") -> str:
    found = shutil.which(tool)
    if not found:
        raise PolyweaveError(
            "video.no-ffmpeg",
            f"{tool} is not on PATH, and a video is cut and measured with it",
            "install ffmpeg (it carries ffprobe) and put it on PATH",
        )
    return found


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-cut", message, remedy, **extra)


def _number(
    table: dict, key: str, default: float, at: str, *, least: float = 0.0
) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < least:
        raise _bad(
            f"{at}.{key} is {value!r}, and it is a number of at least {least:g}",
            f"give {key} as a number of at least {least:g}",
            given=key,
            at=at,
        )
    return float(value)


def read(source: Path, here: Path) -> dict:
    """The edit a `*.cut.toml` declares, each clip's sequence found and its stretch
    checked against what the run holds."""
    if not source.is_file():
        raise PolyweaveError(
            "video.no-source",
            f"there is no cut at {source}",
            "name a *.cut.toml under the project",
            given=str(source),
        )
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "video.no-source",
            f"{source.name} is not TOML: {exc}",
            "fix the line the detail names",
            given=str(source),
        ) from exc
    video = declared.get("video", {})
    unknown = sorted(set(declared) - {"video", "clip"}) + sorted(
        set(video) - _VIDEO_KEYS
    )
    if unknown:
        raise _bad(
            f"{source.name} has no {', '.join(unknown)}",
            f"[video] takes {', '.join(sorted(_VIDEO_KEYS))}; each [[clip]] takes "
            f"{', '.join(sorted(_CLIP_KEYS))}",
            given=unknown[0],
        )
    size = video.get("size", [1920, 1080])
    if (
        not isinstance(size, list)
        or len(size) != 2
        or not all(isinstance(v, int) and v > 0 and v % 2 == 0 for v in size)
    ):
        raise _bad(
            f"video.size is {size!r}",
            "give [width, height], two even numbers",
            given="size",
        )
    fps = _number(video, "fps", 30, "video", least=1)
    fade_out = _number(video, "fade_out", 0.0, "video")
    music = video.get("music")
    if music is not None and not (here / music).is_file():
        raise _bad(
            f"there is no music at {music}",
            "name a sound file under the project",
            given="music",
        )
    clips = []
    for index, clip in enumerate(declared.get("clip", [])):
        at = f"clip[{index + 1}]"
        extra = sorted(set(clip) - _CLIP_KEYS)
        if extra:
            raise _bad(
                f"{at} has no {', '.join(extra)}",
                f"a clip takes {', '.join(sorted(_CLIP_KEYS))}",
                given=extra[0],
                at=at,
            )
        if "from" not in clip or "length" not in clip:
            raise _bad(
                f"{at} names no run or no length",
                "give from, the folder capture.movie wrote, and length in seconds",
                at=at,
            )
        folder = here / clip["from"]
        folder = folder.parent if folder.name == "sequence.json" else folder
        manifest = folder / "sequence.json"
        if not manifest.is_file():
            raise PolyweaveError(
                "video.no-sequence",
                f"{at} names {clip['from']}, which holds no sequence.json",
                "capture the run with capture.movie and name the folder it wrote",
                given=str(clip["from"]),
                at=at,
            )
        sequence = json.loads(manifest.read_text(encoding="utf-8"))
        rate = float(sequence.get("fps") or 0)
        frames = [one["file"] for one in sequence.get("frames", [])]
        start = _number(clip, "start", 0.0, at)
        length = _number(clip, "length", 0.0, at, least=1 / fps)
        fade_in = _number(clip, "fade_in", 0.0, at)
        held = len(frames) / rate if rate else 0.0
        if rate <= 0 or start + length > held + 1e-6:
            raise PolyweaveError(
                "video.short-sequence",
                f"{at} asks {start:g}s to {start + length:g}s of {folder.name}, which "
                f"holds {held:.2f}s",
                "shorten the clip, start it earlier, or capture a longer run",
                at=at,
                given=str(clip["from"]),
            )
        if index == 0 and fade_in:
            raise _bad(
                f"{at} fades in from nothing",
                "give the first clip no fade_in",
                at=at,
                given="fade_in",
            )
        if fade_in >= length or (clips and fade_in >= clips[-1]["length"]):
            raise _bad(
                f"{at}'s fade_in of {fade_in:g}s is as long as a clip it joins",
                "fade over less than either clip's length",
                at=at,
                given="fade_in",
            )
        clips.append(
            {
                "folder": folder,
                "manifest": manifest,
                "rate": rate,
                "frames": frames,
                "start": start,
                "length": length,
                "fade_in": fade_in,
                "audio": bool(sequence.get("audio")),
            }
        )
    if not clips:
        raise _bad(
            f"{source.name} declares no [[clip]]",
            "add one [[clip]] per stretch of a captured run",
        )
    total = sum(c["length"] for c in clips) - sum(c["fade_in"] for c in clips)
    if fade_out >= total:
        raise _bad(
            f"video.fade_out of {fade_out:g}s is the whole teaser",
            "fade over less than its length",
            given="fade_out",
        )
    return {
        "out": video.get("out"),
        "size": size,
        "fps": fps,
        "music": music,
        "music_from": _number(video, "music_from", 0.0, "video"),
        "music_gain": float(video.get("music_gain", 0.0)),
        "clip_audio": bool(video.get("clip_audio", False)),
        "fade_out": fade_out,
        "clips": clips,
        "seconds": total,
    }


def _command(cut: dict, target: Path, here: Path) -> list[str]:
    """The one ffmpeg call that cuts, joins, scores and encodes the edit."""
    width, height = cut["size"]
    fps = cut["fps"]
    inputs: list[str] = []
    graph: list[str] = []
    for i, clip in enumerate(cut["clips"]):
        first = int(clip["start"] * clip["rate"])
        inputs += [
            "-framerate",
            f"{clip['rate']:g}",
            "-start_number",
            str(first + 1),
            "-i",
            str(clip["folder"] / "%04d.png"),
        ]
        graph.append(
            f"[{i}:v]trim=duration={clip['length']:.6f},setpts=PTS-STARTPTS,"
            f"fps={fps:g},scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"
        )
    joined, at = "v0", cut["clips"][0]["length"]
    for i, clip in enumerate(cut["clips"][1:], start=1):
        if clip["fade_in"]:
            graph.append(
                f"[{joined}][v{i}]xfade=transition=fade:duration="
                f"{clip['fade_in']:.6f}:offset={at - clip['fade_in']:.6f}[j{i}]"
            )
        else:
            graph.append(f"[{joined}][v{i}]concat=n=2:v=1:a=0[j{i}]")
        joined, at = f"j{i}", at + clip["length"] - clip["fade_in"]
    total = cut["seconds"]
    ending = (
        f",fade=t=out:st={total - cut['fade_out']:.6f}:d={cut['fade_out']:.6f}"
        if cut["fade_out"]
        else ""
    )
    graph.append(f"[{joined}]trim=duration={total:.6f}{ending}[vout]")
    sounds: list[str] = []
    count = len(cut["clips"])
    if cut["music"]:
        inputs += ["-ss", f"{cut['music_from']:g}", "-i", str(here / cut["music"])]
        graph.append(
            f"[{count}:a]atrim=duration={total:.6f},asetpts=PTS-STARTPTS,"
            f"volume={cut['music_gain']:g}dB[m]"
        )
        sounds.append("[m]")
        count += 1
    if cut["clip_audio"]:
        offset = 0.0
        for i, clip in enumerate(cut["clips"]):
            offset -= clip["fade_in"]
            if clip["audio"]:
                inputs += ["-i", str(clip["folder"] / "audio.wav")]
                delay = int(round(offset * 1000))
                graph.append(
                    f"[{count}:a]atrim=start={clip['start']:.6f}:duration="
                    f"{clip['length']:.6f},asetpts=PTS-STARTPTS,"
                    f"adelay={delay}|{delay}[c{i}]"
                )
                sounds.append(f"[c{i}]")
                count += 1
            offset += clip["length"]
    mapped = ["-map", "[vout]"]
    if sounds:
        mixed = (
            f"{''.join(sounds)}amix=inputs={len(sounds)}:normalize=0:duration=longest"
            if len(sounds) > 1
            else f"{sounds[0]}anull"
        )
        fading = (
            f",afade=t=out:st={total - cut['fade_out']:.6f}:d={cut['fade_out']:.6f}"
            if cut["fade_out"]
            else ""
        )
        graph.append(
            f"{mixed},atrim=duration={total:.6f}{fading},"
            f"aformat=sample_rates=48000:channel_layouts=stereo[aout]"
        )
        mapped += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    return [
        _ffmpeg(),
        "-v",
        "error",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(graph),
        *mapped,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        f"{fps:g}",
        "-movflags",
        "+faststart",
        str(target),
    ]


def measured(path: Path) -> dict:
    """What a video is: its length, size and rate, whether it carries sound, and the
    seconds before its picture first moves."""
    if not path.is_file():
        raise PolyweaveError(
            "video.unreadable",
            f"there is no video at {path}",
            "name the MP4 video.cut wrote",
            given=str(path),
        )
    probe = subprocess.run(
        [
            _ffmpeg("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,avg_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        read_back = json.loads(probe.stdout)
        streams = read_back["streams"]
        picture = next(s for s in streams if s["codec_type"] == "video")
    except (ValueError, KeyError, StopIteration) as exc:
        raise PolyweaveError(
            "video.unreadable",
            f"{path.name} is not a video ffprobe reads",
            "cut it again with video.cut",
            detail=probe.stderr.strip()[:400],
        ) from exc
    top, _, bottom = picture["avg_frame_rate"].partition("/")
    fps = float(top) / float(bottom or 1) if float(bottom or 1) else 0.0
    width, height = int(picture["width"]), int(picture["height"])
    small = (_SIDE, max(2, round(_SIDE * height / width / 2) * 2))
    raw = subprocess.run(
        [
            _ffmpeg(),
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={small[0]}:{small[1]},format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=False,
    ).stdout
    frames = np.frombuffer(raw, dtype=np.uint8)
    frames = frames[: frames.size - frames.size % (small[0] * small[1])]
    frames = frames.reshape(-1, small[1], small[0]).astype(np.float32) / 255.0
    change = (np.abs(np.diff(frames, axis=0)) > _STEP).mean(axis=(1, 2))
    moved = np.flatnonzero(change > MOTION)
    seconds = float(
        read_back.get("format", {}).get("duration") or len(frames) / (fps or 1)
    )
    return {
        "video_seconds": round(seconds, 3),
        "video_width": width,
        "video_height": height,
        "video_fps": round(fps, 3),
        "first_motion": round((moved[0] + 1) / fps, 3)
        if moved.size and fps
        else seconds,
        "audio": any(s["codec_type"] == "audio" for s in streams),
    }


def _sheet(path: Path, target: Path, seconds: float, stills: int = 8) -> Path:
    """`stills` frames evenly over the teaser, side by side four to a row."""
    from PIL import Image, ImageDraw

    shots = []
    for k in range(stills):
        at = seconds * (k + 0.5) / stills
        png = subprocess.run(
            [
                _ffmpeg(),
                "-v",
                "error",
                "-ss",
                f"{at:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=480:-2",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ],
            capture_output=True,
            check=False,
        ).stdout
        if png:
            import io

            shots.append((at, Image.open(io.BytesIO(png)).convert("RGB")))
    if not shots:
        raise PolyweaveError(
            "video.unreadable",
            f"no still could be read from {path.name}",
            "cut it again with video.cut",
        )
    width, height = shots[0][1].size
    columns = min(4, len(shots))
    rows = -(-len(shots) // columns)
    sheet = Image.new("RGB", (columns * width, rows * (height + 24)), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    for k, (at, shot) in enumerate(shots):
        x, y = (k % columns) * width, (k // columns) * (height + 24)
        sheet.paste(shot, (x, y))
        draw.text((x + 6, y + height + 4), f"{at:.1f}s", fill=(220, 220, 224))
    sheet.save(target)
    return target


@operation("video.cut", kind="capture")
def cut(
    source: Annotated[str, Param("the *.cut.toml, as a path under the project")],
    *,
    out: Annotated[
        str, Param("where the MP4 is written; the cut's own out otherwise")
    ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Cut captured runs together, score and encode them as one MP4, and measure it.

    Each clip is a stretch of a folder capture.movie wrote, fitted inside the size on
    black at the cut's rate, joined by a cut or a crossfade; the music lies beneath and
    the end fades. The answer gives the file, what it measures and a sheet of stills,
    and the record names every sequence and the music as inputs.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    path = Path(source) if Path(source).is_absolute() else here / source
    declared = read(path, here)
    where = (
        out
        or declared["out"]
        or path.with_name(path.name.removesuffix(".cut.toml") + ".mp4").as_posix()
    )
    target = Path(where) if Path(where).is_absolute() else here / where
    if target.suffix.lower() != ".mp4":
        raise _bad(
            f"the teaser is written as {target.name}",
            "write it as an .mp4",
            given="out",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    made = subprocess.run(
        _command(declared, target, here), capture_output=True, text=True, check=False
    )
    if made.returncode != 0 or not target.is_file():
        raise PolyweaveError(
            "video.encode-failed",
            f"ffmpeg did not write {target.name}",
            "read the detail, which is what ffmpeg said",
            detail=made.stderr.strip()[-800:],
        )
    found = measured(target)
    sheet = _sheet(target, target.with_suffix(".sheet.png"), found["video_seconds"])
    inputs = [
        provenance.source("capture", c["manifest"], root=here)
        for c in declared["clips"]
    ]
    if declared["music"]:
        inputs.append(provenance.source("music", here / declared["music"], root=here))
    record = provenance.write(
        provenance.build(
            "capture",
            target,
            engine={"name": "video.cut", "encoder": "ffmpeg libx264"},
            inputs=inputs,
            params={
                "cut": provenance.relative(path, here),
                "size": declared["size"],
                "fps": declared["fps"],
                "clips": len(declared["clips"]),
            },
            measurements={k: v for k, v in found.items() if k in VIDEOS},
            root=here,
        ),
        root=here,
    )
    return {
        "file": provenance.relative(target, here),
        "sheet": provenance.relative(sheet, here),
        "record": provenance.relative(Path(record), here),
        "clips": len(declared["clips"]),
        **found,
        "says": f"{found['video_seconds']:g}s at {found['video_width']}x"
        f"{found['video_height']}, moving from {found['first_motion']:g}s; watch "
        f"{provenance.relative(target, here)}, or lay the sheet in a sitting",
    }


def predicate(p: Any, subject: Any, root: str | Path, seen: dict) -> dict:
    """A video predicate for accept.check, read off the teaser it names or the subject
    (§PW429, §PW503)."""
    where = Path(p.of) if p.of else Path(subject)
    where = where if where.is_absolute() else Path(root) / where
    key = f"video:{where}"
    if key not in seen:
        seen[key] = measured(where)
    return {"value": float(seen[key][p.measure]), "of": str(where)}
