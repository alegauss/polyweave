"""A camera move declared as a clip, built into a camera the game plays (§PW372).

Met in Starship (RK190): a cinema opening of five camera shots over the city, each a
place, a target and a slow drift over about a second and a half, cut by a flash, with
the shots kept in the game's own JSON and set by eye. A camera clip is that list
declared in a `*.camera.toml`, one clip to a file:

    name = "opening"
    easing = "sine"               # how a shot drifts, where the shot does not say
    fov = 50                      # degrees, where the shot does not say

    [[shot]]
    anchor = "ship"               # whose frame the places are in; "" is the world's
    from = [0.06, 2.0, 57.0]      # where the camera starts the shot
    to = [0.16, 2.0, 56.5]        # where it ends it; left out, it holds still
    look = [0.42, 3.0, 45.0]      # what it looks at, and look_to what it ends on
    hold = 1.3                    # seconds
    mark = "citadel"              # a word the game is handed at the cut, if any

`clip.camera` writes it as a Godot scene: a Camera3D whose script holds the shots and is
placed from `time` alone, so a moment of the clip is the same every time. A place is
three numbers in its anchor's frame, and what that frame is belongs to the game: by
default the anchor is a Node3D in `anchors` and a place is a point in its local frame,
and a game whose world is not Cartesian (Starship's is a cylinder) sets `place`, a
Callable(anchor, place) -> Vector3, so no project's frame is compiled in here. Every
shot boundary is a cut, and `cut` carries the shot and its mark, so the game flashes,
clicks or blinks what it likes. `still` holds each shot at its start, which is what
reduced motion asks for. What it measures is arithmetic over the declaration; whether a
framing is right stays a person's call.
"""

from __future__ import annotations

import difflib
import math
import shutil
import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: How a shot drifts from its start to its end: as it goes, on a smoothstep, on half a
#: cosine (Starship's), or not at all until the cut.
EASINGS = ("linear", "ease", "sine", "step")

#: Every key a shot may hold, and its default where it has one.
SHOT_KEYS: dict[str, Any] = {
    "anchor": "",
    "from": None,
    "to": None,
    "look": None,
    "look_to": None,
    "fov": None,
    "hold": None,
    "ease": None,
    "mark": "",
}

#: Every key a clip may hold beside its shots.
CLIP_KEYS = ("name", "easing", "fov", "shot")

#: Degrees a camera's field of view may take.
FOV = (1.0, 179.0)

#: What a camera clip measures, and what it says.
MEASURES: dict[str, str] = {
    "duration": "seconds from the first shot's start to the last one's end",
    "shots": "how many shots, so how many cuts the game is handed",
    "shortest_hold": "seconds the briefest shot holds",
    "longest_hold": "seconds the longest shot holds",
}


def _bad(where: str, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("clip.bad-camera", f"{where}: {what}", remedy, **extra)


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _place(where: str, key: str, value: Any) -> list[float]:
    if (not isinstance(value, list) or len(value) != 3
            or not all(_number(v) for v in value)):
        raise _bad(where, f"sets {key} to {value!r}",
                   f"write {key} as three numbers in the anchor's frame, such as "
                   "[0.0, 2.0, 10.0]")
    return [float(v) for v in value]


def _easing(where: str, value: Any) -> str:
    if value not in EASINGS:
        raise _bad(where, f"asks for an easing {value!r}",
                   f"name one of {', '.join(EASINGS)}", given=str(value),
                   allowed=list(EASINGS))
    return value


def _fov(where: str, value: Any) -> float:
    if not _number(value) or not FOV[0] <= value <= FOV[1]:
        raise _bad(where, f"sets fov to {value!r}",
                   f"write fov as degrees from {FOV[0]:g} to {FOV[1]:g}")
    return float(value)


def _shot(index: int, table: Any, easing: str, fov: float) -> dict:
    where = f"shot {index + 1}"
    if not isinstance(table, dict):
        raise _bad(where, "is not a table", "write each shot as [[shot]]")
    for key in table:
        if key not in SHOT_KEYS:
            near = difflib.get_close_matches(key, SHOT_KEYS, n=1)
            raise _bad(where, f"has no key {key!r}",
                       f"did you mean {near[0]!r}?" if near
                       else f"name one of {', '.join(SHOT_KEYS)}",
                       given=key, allowed=list(SHOT_KEYS))
    for key in ("from", "look", "hold"):
        if key not in table:
            raise _bad(where, f"states no {key}",
                       "every shot has a place it starts from, something it looks at "
                       "and a hold in seconds")
    hold = table["hold"]
    if not _number(hold) or hold <= 0:
        raise _bad(where, f"holds for {hold!r}",
                   "write hold as seconds above 0; a shot that holds for nothing is a "
                   "cut nobody sees")
    start = _place(where, "from", table["from"])
    look = _place(where, "look", table["look"])
    own = {
        "anchor": table.get("anchor", ""),
        "from": start,
        "to": _place(where, "to", table["to"]) if "to" in table else start,
        "look": look,
        "look_to": _place(where, "look_to", table["look_to"]) if "look_to" in table
        else look,
        "fov": _fov(where, table["fov"]) if "fov" in table else fov,
        "hold": float(hold),
        "ease": _easing(where, table["ease"]) if "ease" in table else easing,
        "mark": table.get("mark", ""),
    }
    for key in ("anchor", "mark"):
        if not isinstance(own[key], str):
            raise _bad(where, f"sets {key} to {own[key]!r}",
                       f"write {key} as a word, or leave it out")
    for at, (eye, target) in (("start", ("from", "look")), ("end", ("to", "look_to"))):
        if own[eye] == own[target]:
            raise _bad(where, f"looks at the place it stands at its {at}",
                       f"move {target} off {eye}: a camera has no direction to face a "
                       "point it is standing on")
    return own


def checked(table: Any, source: str = "the clip") -> dict:
    """One camera clip with its defaults, every key and value refused unless it means
    something."""
    if not isinstance(table, dict):
        raise _bad(source, "is not a table", "write a name and [[shot]] tables")
    for key in table:
        if key not in CLIP_KEYS:
            near = difflib.get_close_matches(key, CLIP_KEYS, n=1)
            raise _bad(source, f"has no key {key!r}",
                       f"did you mean {near[0]!r}?" if near
                       else f"name one of {', '.join(CLIP_KEYS)}",
                       given=key, allowed=list(CLIP_KEYS))
    name = table.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        raise _bad(source, f"is named {name!r}",
                   "name it as a word of letters, digits and underscores; it is the "
                   "scene's file name and its root node's")
    easing = _easing(source, table.get("easing", "linear"))
    fov = _fov(source, table.get("fov", 50.0))
    shots = table.get("shot")
    if not isinstance(shots, list) or not shots:
        raise _bad(source, "has no shot",
                   "write at least one [[shot]] with its from, look and hold")
    return {"name": name, "easing": easing, "fov": fov,
            "shots": [_shot(i, shot, easing, fov) for i, shot in enumerate(shots)]}


def measured(clip: dict) -> dict:
    holds = [shot["hold"] for shot in clip["shots"]]
    return {
        "duration": round(sum(holds), 6),
        "shots": len(holds),
        "shortest_hold": min(holds),
        "longest_hold": max(holds),
    }


# -- what it shows at a moment, the same arithmetic the scene's script does ------------


def eased(fraction: float, how: str) -> float:
    if how == "step":
        return 0.0
    if how == "ease":
        return fraction * fraction * (3.0 - 2.0 * fraction)
    if how == "sine":
        return 0.5 - 0.5 * math.cos(math.pi * fraction)
    return fraction


def shot_at(clip: dict, when: float) -> int:
    """The shot showing at `when`, or -1 before the clip and after it."""
    if when < 0:
        return -1
    start = 0.0
    for index, shot in enumerate(clip["shots"]):
        if when < start + shot["hold"]:
            return index
        start += shot["hold"]
    return -1


def at(clip: dict, when: float, *, still: bool = False) -> dict | None:
    """The camera at `when`, in its anchor's frame: the shot, where it stands, what it
    looks at and its field of view; None outside the clip."""
    index = shot_at(clip, when)
    if index < 0:
        return None
    shot = clip["shots"][index]
    start = sum(one["hold"] for one in clip["shots"][:index])
    into = min(1.0, (when - start) / shot["hold"])
    mixed = 0.0 if still else eased(into, shot["ease"])

    def lerp(a: list, b: list) -> list[float]:
        return [x + (y - x) * mixed for x, y in zip(a, b, strict=True)]

    return {"shot": index, "anchor": shot["anchor"], "mark": shot["mark"],
            "from": lerp(shot["from"], shot["to"]),
            "look": lerp(shot["look"], shot["look_to"]), "fov": shot["fov"]}


# -- the scene the game plays ----------------------------------------------------------

_PLAYS = """\
extends Camera3D
## A camera clip polyweave built (clip.camera, §PW372). Seek it by time and it frames
## the shot showing then; every shot boundary is a cut, said through `cut`.

signal cut(index: int, mark: String)

## each shot: anchor, from, to, look, look_to, fov, hold, ease and mark
@export var shots: Array = []
## anchor name -> the Node3D whose frame its places are in
var anchors := {}
## Callable(anchor: String, place: Vector3) -> Vector3, for a world whose frame is not a
## node's; left unset, a place is a point in its anchor node's frame, or the world's
var place: Callable
## hold each shot at its start, as reduced motion asks
var still := false
## seconds since the clip began
var time := 0.0
## a moment held whatever the game seeks, so clip.shots can frame each shot in the
## running game (§PW372); below 0, the game's own time is framed
var pinned := -1.0
## the shot shown, or -1 outside the clip
var shown := -1


## the clip's length in seconds
func length() -> float:
\treturn start_of(shots.size())


func start_of(index: int) -> float:
\tvar start := 0.0
\tfor i in mini(index, shots.size()):
\t\tstart += float(shots[i]["hold"])
\treturn start


## the shot showing at `at`, or -1 before the clip and after it
func shot_at(at: float) -> int:
\tif at < 0.0:
\t\treturn -1
\tvar start := 0.0
\tfor i in shots.size():
\t\tstart += float(shots[i]["hold"])
\t\tif at < start:
\t\t\treturn i
\treturn -1


func advance(delta: float) -> void:
\tseek(time + delta)


## frame the moment `at`; a change of shot is a cut
func seek(at: float) -> void:
\tif pinned >= 0.0:
\t\tat = pinned
\ttime = at
\tvar index := shot_at(at)
\tif index != shown:
\t\tshown = index
\t\tif index >= 0:
\t\t\tcut.emit(index, String(shots[index].get("mark", "")))
\tif index < 0:
\t\treturn
\tvar shot: Dictionary = shots[index]
\tvar into := clampf((at - start_of(index)) / float(shot["hold"]), 0.0, 1.0)
\tvar mixed := 0.0 if still else eased(into, String(shot["ease"]))
\tvar anchor := String(shot["anchor"])
\tvar eye := where(anchor, (shot["from"] as Vector3).lerp(shot["to"], mixed))
\tvar target := where(anchor, (shot["look"] as Vector3).lerp(shot["look_to"], mixed))
\tfov = float(shot["fov"])
\tglobal_position = eye
\tif not eye.is_equal_approx(target):
\t\tvar plumb := absf((target - eye).normalized().y) > 0.999
\t\tlook_at(target, Vector3.BACK if plumb else Vector3.UP)


## a place in an anchor's frame, in the world
func where(anchor: String, at: Vector3) -> Vector3:
\tif place.is_valid():
\t\treturn place.call(anchor, at)
\tvar node: Node3D = anchors.get(anchor)
\treturn node.global_transform * at if node else at


static func eased(fraction: float, how: String) -> float:
\tmatch how:
\t\t"step":
\t\t\treturn 0.0
\t\t"ease":
\t\t\treturn fraction * fraction * (3.0 - 2.0 * fraction)
\t\t"sine":
\t\t\treturn 0.5 - 0.5 * cos(PI * fraction)
\treturn fraction
"""


def _vector(values: list[float]) -> str:
    return "Vector3(" + ", ".join(f"{v:.9g}" for v in values) + ")"


def _text(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def scene(clip: dict) -> str:
    """The clip as a Godot 4 scene: a Camera3D holding its shots and the script that
    plays them."""
    source = _PLAYS.replace("\\", "\\\\").replace('"', '\\"')
    shots = ", ".join(
        "{" + ", ".join([
            f'"anchor": {_text(shot["anchor"])}',
            f'"from": {_vector(shot["from"])}', f'"to": {_vector(shot["to"])}',
            f'"look": {_vector(shot["look"])}',
            f'"look_to": {_vector(shot["look_to"])}',
            f'"fov": {shot["fov"]:.9g}', f'"hold": {shot["hold"]:.9g}',
            f'"ease": {_text(shot["ease"])}', f'"mark": {_text(shot["mark"])}',
        ]) + "}"
        for shot in clip["shots"]
    )
    return (
        "[gd_scene load_steps=2 format=3]\n\n"
        '[sub_resource type="GDScript" id="plays"]\n'
        f'script/source = "{source}"\n\n'
        f'[node name="{clip["name"]}" type="Camera3D"]\n'
        f'fov = {clip["shots"][0]["fov"]:.9g}\n'
        'script = SubResource("plays")\n'
        f"shots = [{shots}]\n"
    )


def _source(source: str, config) -> tuple[Path, dict]:
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError(
            "clip.no-camera", f"there is no camera clip at {source}",
            "name a *.camera.toml relative to the project root",
        )
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "clip.no-camera", f"{source} is not TOML",
            "fix the syntax the detail names", detail=str(exc),
        ) from exc
    return where, checked(declared, source)


@operation("clip.camera")
def build(
    source: Annotated[str, Param("the *.camera.toml, relative to the project")],
    out: Annotated[
        str, Param("the folder the scene is written to; beside the source if unset")
    ] = None,
    root: Annotated[str, Param("the project the clip belongs to")] = ".",
) -> dict:
    """Build a declared camera move, its shots cut one to the next, into a Godot scene.

    It lands as <name>.tscn: a Camera3D the game seeks by time, which emits cut(index,
    mark) at each shot. A place is in its anchor's frame: a Node3D the game puts in
    `anchors`, or its own `place` Callable for a frame that is not a node's. The answer
    says the clip's duration, shots and shortest and longest hold.
    """
    from polyweave.layers.vfx.vfx import shipped_folder

    config = load(root)
    where, clip = _source(source, config)
    folder = shipped_folder(config, where, out, None, "clip.unshipped")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{clip['name']}.tscn"
    target.write_text(scene(clip), encoding="utf-8", newline="\n")
    numbers = measured(clip)
    provenance.write(provenance.build(
        "camera", target, engine={"name": "clip.camera"},
        inputs=[provenance.source("camera", where, config.root)],
        params={"clip": clip["name"]}, measurements=numbers, root=config.root,
    ), config.root)
    return {
        "source": provenance.relative(where, config.root),
        "file": provenance.relative(target, config.root),
        "anchors": sorted({shot["anchor"] for shot in clip["shots"]}),
        "marks": [shot["mark"] for shot in clip["shots"]],
        **numbers,
    }


def moments(clip: dict, into: float = 0.5) -> list[float]:
    """The moment each shot is framed at: `into` of the way through its hold."""
    found, start = [], 0.0
    for shot in clip["shots"]:
        found.append(start + shot["hold"] * into)
        start += shot["hold"]
    return found


#: Frames clip.shots waits, in a game it opened itself, for the camera to exist.
OPEN_FRAMES = 600


@operation("clip.shots")
def shots(
    source: Annotated[str, Param("the *.camera.toml the game's camera was built from")],
    *,
    out: Annotated[str, Param("the folder the shots and the sitting are written to")],
    camera: Annotated[
        str, Param("the built camera's node in the running game; or give clip")
    ] = "",
    clip: Annotated[
        str, Param("the built clip's .tscn, stood up when the game is not playing it")
    ] = "",
    anchors: Annotated[
        dict, Param("with clip: anchor to node path, where the node is not so named")
    ] = None,
    place: Annotated[
        str, Param("with clip: Path:method placing a point, for a world not Cartesian")
    ] = "",
    session: Annotated[str, Param("a game.open session, opened with display")] = "",
    args: Annotated[list, Param("the game's own flags")] = None,
    into: Annotated[
        float, Param("how far through each shot's hold it is framed", lo=0.0, hi=1.0)
    ] = 0.5,
    keep: Annotated[
        dict, Param("shot number to a path under the project, each written with its "
                    "record so capture.again frames it again")
    ] = None,
    hide: Annotated[
        list, Param("node paths hidden while framing, as a cutscene hides its HUD")
    ] = None,
    loop: Annotated[
        int, Param("frames a second of a loop of the whole clip played on the page; "
                   "0 for none", lo=0, hi=30)
    ] = 0,
    root: Annotated[str, Param("the project the clip belongs to")] = ".",
) -> dict:
    """Frame every shot of a camera clip in the running game and lay them out to judge.

    Whether a framing is right is a person's call, and it can only be made on what the
    game draws: the anchors are placed at run time. The game is driven to the scene
    that plays the clip first; then each shot is held through the camera's `pinned`,
    whatever the game seeks, a frame is let pass and the screen is saved. The pin is
    let go after. The shots are one family in one sitting, answered on the review page.
    With no `session` the game is opened here with `args`, and closed after (§PW553).
    Given `clip` instead of `camera`, the camera is stood up in the game as it stands,
    each anchor found by name or by `anchors`, so a cutscene reached through menus is
    framed with no driving to it (§PW591). Every frame is recorded with the clip, the
    shot and the game it was framed in, and `keep` writes a chosen shot to a path of
    its own with that record, which capture.again frames again (§PW597). `loop` films
    the whole clip at that rate as a muted MP4 the page plays beside the shots, since a
    move is judged moving (§PW600).
    """
    from polyweave.layers.engine import driving
    from polyweave.loop import verdict

    config = load(root)
    where, declared = _source(source, config)
    if bool(camera) == bool(clip):
        raise PolyweaveError(
            "clip.camera-absent",
            "clip.shots frames the camera the game plays, or a clip it stands up "
            "itself, and was given " + ("both" if camera else "neither"),
            "pass camera, the playing camera's node, or clip, the built clip's .tscn",
        )
    kept = _kept(keep, len(declared["shots"]), config.root)
    folder = Path(out) if Path(out).is_absolute() else config.root / out
    own = not session
    if own:
        session = driving.opened(root, display=True, args=args)["session"]
    call = {"source": provenance.relative(where, config.root), "camera": camera,
            "clip": clip, "anchors": dict(anchors or {}), "place": place,
            "hide": list(hide or ()), "into": into, **_opened_as(session, args, root)}
    try:
        if clip:
            camera = _stood_up(session, declared, clip, anchors, place, root)
        elif own:
            _awaited(session, camera, args, root)
    except PolyweaveError:
        if own:
            driving.closed(session, root=root)
        raise
    taken, records = [], []
    try:
        for node in hide or ():
            driving.set_value(session, path=node, prop="visible", value="false",
                              root=root)
        for index, when in enumerate(moments(declared, into)):
            driving.set_value(session, path=camera, prop="pinned", value=str(when),
                              root=root)
            if clip:
                # Nothing in the game seeks a camera it did not make, so it is placed.
                driving.called(session, path=camera, method="seek", args=[when],
                               root=root)
            driving.stepped(session, frames=2, root=root)
            picture = folder / f"{declared['name']}-{index + 1}.png"
            said = driving.shot(session, out=str(picture), root=root) or {}
            mark = declared["shots"][index]["mark"]
            one = {"shot": index + 1, "at": round(when, 3), "mark": mark,
                   "picture": provenance.relative(picture, config.root)}
            environment = said.get("environment") or call["environment"]
            for at in (picture, *([kept[index + 1]] if index + 1 in kept else [])):
                if at != picture:
                    at.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(picture, at)
                    one["kept"] = provenance.relative(at, config.root)
                framed = {**call, "environment": environment}
                records.append(_shot_record(at, one, framed, where, clip, config.root))
            taken.append(one)
        played = _filmed(session, camera, declared, loop, folder, bool(clip), root)
    finally:
        driving.set_value(session, path=camera, prop="pinned", value="-1", root=root)
        for node in hide or ():
            driving.set_value(session, path=node, prop="visible", value="true",
                              root=root)
        if own:
            driving.closed(session, root=root)
    members = [{"name": f"shot {one['shot']}" + (f" ({one['mark']})" if one["mark"]
                                                   else ""),
                "new": one["picture"]} for one in taken]
    if played:
        # The whole move, played, ahead of the shots it passes through (§PW600).
        members.insert(0, {"name": "the whole clip", "new": taken[0]["picture"],
                           "motion": provenance.relative(played, config.root)})
    laid = verdict.sitting(
        {declared["name"]: members},
        out=str(verdict._sitting_folder(config, declared["name"], folder)),
        root=str(config.root),
        about=f"Each shot of {source}, framed in the running game "
              f"{into:.0%} of the way through its hold.",
    )
    return {"source": source, "shots": taken, "sitting": laid["manifest"],
            "page": laid["page"], "records": records,
            **({"loop": provenance.relative(played, config.root)} if played else {}),
            "says": f"{len(taken)} shot(s) of {declared['name']} to judge at "
                    f"{laid['page']}"
                    + "".join(f"; shot {one['shot']} kept at {one['kept']}"
                              for one in taken if one.get("kept"))}


def _filmed(session: str, camera: str, declared: dict, fps: int, folder: Path,
            seeks: bool, root: str) -> Path | None:
    """The whole clip pinned frame by frame and encoded as a loop, or None at 0 fps."""
    from polyweave.layers.engine import driving
    from polyweave.layers.engine.capture import looped

    if not fps:
        return None
    total = sum(shot["hold"] for shot in declared["shots"])
    count = max(2, round(total * fps))
    frames = []
    for index in range(count):
        when = index / fps
        driving.set_value(session, path=camera, prop="pinned", value=str(when),
                          root=root)
        if seeks:
            driving.called(session, path=camera, method="seek", args=[when], root=root)
        driving.stepped(session, frames=1, root=root)
        frame = folder / "loop" / f"{index:05d}.png"
        driving.shot(session, out=str(frame), root=root)
        frames.append(frame)
    return looped(frames, fps, folder / f"{declared['name']}.mp4")


def _kept(keep: dict | None, count: int, here: Path) -> dict[int, Path]:
    """Each shot to keep, by its number, at its path under the project (§PW597)."""
    found = {}
    for key, path in (keep or {}).items():
        number = int(key) if str(key).strip().isdigit() else 0
        if not 1 <= number <= count:
            raise PolyweaveError(
                "clip.bad-camera",
                f"keep names shot {key!r}, and the clip has shots 1 to {count}",
                "key keep by a shot's number, as the answer's shots list it",
                given=str(key),
            )
        at = Path(path) if Path(path).is_absolute() else here / path
        found[number] = at
    return found


def _opened_as(session: str, args: list | None, root: str) -> dict:
    """How the game framing the shots was opened, as far as its session says.

    The scene, the game's own flags and the environment asked are what capture.again
    opens it with; a game driven by hand before it was given here is opened that way
    too, so what was done to it by hand is not in the record (§PW597).
    """
    from polyweave.layers.engine import driving

    try:
        held = driving._session(session, root)
    except PolyweaveError:
        held = {}
    environment = held.get("environment") or {}
    return {"scene": held.get("scene", ""),
            "args": [str(one) for one in held.get("args") or args or ()],
            "environment": {"resolution": environment.get("resolution"),
                            "locale": environment.get("locale")}}


def _shot_record(at: Path, one: dict, call: dict, where: Path, clip: str,
                 here: Path) -> str:
    """The record beside one framed shot: the clip, the shot and how it was framed."""
    inputs = [provenance.source("camera", where, here)]
    built = here / clip.removeprefix("res://").lstrip("/") if clip else None
    if built is not None and built.is_file():
        inputs.append(provenance.source("clip", built, here))
    written = provenance.write(provenance.build(
        "shot", at, engine={"name": "clip.shots"}, inputs=inputs,
        params={"shot": one["shot"], "at": one["at"], "mark": one["mark"]},
        extra={"call": call}, root=here,
    ), here)
    return provenance.relative(written, here)


def framed_again(picture: str, record: dict, environment: dict | None,
                 root: str) -> dict:
    """A kept shot framed again from its record, only the environment changed (§PW597).

    capture.again's answer for a `shot` record: the game is opened as the record says,
    the clip framed, and the shot written over the picture with a new record.
    """
    from polyweave.layers.engine import driving

    call = record.get("call") or {}
    asked = {**(call.get("environment") or {}), **(environment or {})}
    size = str(asked.get("resolution") or "")
    session = driving.opened(
        root, display=True, scene=call.get("scene") or "", args=call.get("args"),
        resolution=[int(v) for v in size.split("x")] if "x" in size else None,
        locale=asked.get("locale"),
    )["session"]
    try:
        if call.get("camera") and not call.get("clip"):
            _awaited(session, call["camera"], call.get("args"), root)
        return shots(
            call["source"], out=f".polyweave/clip-again/{Path(picture).stem}",
            camera="" if call.get("clip") else call.get("camera", ""),
            clip=call.get("clip", ""), anchors=call.get("anchors"),
            place=call.get("place", ""), session=session, into=call.get("into", 0.5),
            keep={str(record["params"]["shot"]): picture}, hide=call.get("hide"),
            root=root,
        )
    finally:
        driving.closed(session, root=root)


def _awaited(session: str, camera: str, args: list | None, root: str) -> None:
    """The playing camera, waited for in a game clip.shots opened itself (§PW553)."""
    from polyweave.layers.engine import driving

    found = driving.waited(session, node=camera, frames=OPEN_FRAMES, root=root)
    if not found.get("met"):
        raise PolyweaveError(
            "clip.camera-absent",
            f"the game opened with {args or 'no arguments'} made no {camera} in "
            f"{OPEN_FRAMES} frames",
            "pass the args that open the game where the clip plays, or drive it "
            "there yourself and pass session; or pass clip to stand it up here",
            given=camera,
        )


def _stood_up(session: str, declared: dict, clip: str, anchors: dict | None,
              place: str, root: str) -> str:
    """The built clip stood up in the game as it stands, its anchors found (§PW591).

    Spinhold builds a world's camera only while its cutscene plays, which only a dive
    from the map starts, so framing one meant driving the menus for every world.
    """
    from polyweave.layers.engine import driving

    scene = clip if clip.startswith("res://") else "res://" + clip.lstrip("/")
    names = sorted({shot["anchor"] for shot in declared["shots"] if shot["anchor"]})
    # A game that places points itself needs no anchor nodes found.
    said = driving.send(session, "clip_camera", root=root, scene=scene, place=place,
                        names=[] if place else names, anchors=dict(anchors or {}))
    missing = (said.get("result") or {}).get("missing")
    if missing:
        raise PolyweaveError(
            "clip.anchor-absent",
            f"{scene} places its shots in {', '.join(missing)}, and nothing in the "
            "game as it stands answers " + ("that name" if len(missing) == 1 else
                                            "those names"),
            "pass anchors naming each one's node path, or the args that build them",
            allowed=missing,
        )
    return said["result"]["path"]
