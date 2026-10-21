"""A keyed timeline of a scene's own properties, declared and built (§PW554).

Met in Spinhold (RK155): the title's logo reveal (a halo rising out of the dark, an
orbit spinning in, a light wiping the letters on, a hit as it settles) was to have its
timing and curves declared, as the cutscenes are with `clip.camera`. A clip keys joints
and a camera clip frames shots; neither keys a Control's modulate or a shader's
parameter, so the curves were constants in the game's code. A timeline is that list
declared in a `*.timeline.toml`, one to a file:

    name = "logo_reveal"
    easing = "in_out"            # each key's way to the next, where the key says none

    [[track]]
    target = "Halo:modulate"     # node:property, as an Animation track names it
    keys = [
      { at = 0.0, value = [1, 1, 1, 0] },
      { at = 0.8, value = [1, 1, 1, 1], ease = "out" },
    ]

    [[track]]
    target = "Letters:material:shader_parameter/wipe"
    keys = [{ at = 0.6, value = 0.0 }, { at = 1.8, value = 1.0 }]

    [[mark]]
    at = 2.6
    name = "hit"                 # said through mark(name) when the play reaches it

A value is a number, a bool, two to four numbers (a Vector2, a Vector3, a Color) or a
`#rrggbb` colour, one kind to a track. `clip.timeline` writes it as a Godot scene: an
AnimationPlayer holding the one Animation, which the game plays or seeks by time with
the node it is a child of as the root its paths start from, and which emits mark(name)
at each mark, so the game plays a sound or a hit where the timeline says.

A move the game also plays the other way is declared once (§PW592): `[mirror]` names a
second animation and the tracks whose values it negates, a number's sign or, by `axes`,
chosen components of a vector, and both land in the one player:

    [mirror]
    name = "bank_left"
    negate = ["Tender/Bank:rotation", { target = "Tender:position", axes = ["x"] }]
"""

from __future__ import annotations

import difflib
import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: How a key eases to the next, as Godot's key transition: as it goes, in slow, out
#: slow, both, or held until the next key.
EASINGS: dict[str, float] = {
    "linear": 1.0, "in": 2.0, "out": 0.5, "in_out": -2.0, "step": 0.0,
}

TIMELINE_KEYS = ("name", "easing", "length", "track", "mark", "mirror")
TRACK_KEYS = ("target", "keys", "easing")
KEY_KEYS = ("at", "value", "ease")
MARK_KEYS = ("at", "name")
MIRROR_KEYS = ("name", "negate")
NEGATE_KEYS = ("target", "axes")

#: Which component of a vector each axis names.
AXES = {"x": 0, "y": 1, "z": 2}


def _bad(where: str, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("clip.bad-timeline", f"{where}: {what}", remedy, **extra)


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _only(where: str, table: Any, allowed: tuple[str, ...], shape: str) -> dict:
    if not isinstance(table, dict):
        raise _bad(where, "is not a table", f"write it as {shape}")
    for key in table:
        if key not in allowed:
            near = difflib.get_close_matches(key, allowed, n=1)
            raise _bad(where, f"has no key {key!r}",
                       f"did you mean {near[0]!r}?" if near
                       else f"name one of {', '.join(allowed)}",
                       given=key, allowed=list(allowed))
    return table


def _easing(where: str, value: Any) -> str:
    if value not in EASINGS:
        raise _bad(where, f"asks for an easing {value!r}",
                   f"name one of {', '.join(EASINGS)}", given=str(value),
                   allowed=list(EASINGS))
    return value


def _time(where: str, value: Any) -> float:
    if not _number(value) or value < 0:
        raise _bad(where, f"is at {value!r}", "write at as seconds from 0")
    return float(value)


def _value(where: str, value: Any) -> tuple[str, Any]:
    """A key's value and its kind: float, bool, vector2, vector3, color."""
    if isinstance(value, bool):
        return "bool", value
    if _number(value):
        return "float", float(value)
    if isinstance(value, str) and value.startswith("#") and len(value) in (7, 9):
        try:
            channels = [int(value[i:i + 2], 16) / 255.0
                        for i in range(1, len(value), 2)]
        except ValueError:
            channels = []
        if channels:
            return "color", channels + [1.0] * (4 - len(channels))
    if isinstance(value, list) and 2 <= len(value) <= 4 and all(_number(v)
                                                                for v in value):
        kind = {2: "vector2", 3: "vector3", 4: "color"}[len(value)]
        return kind, [float(v) for v in value]
    raise _bad(where, f"has the value {value!r}",
               "write a number, true or false, two to four numbers, or #rrggbb")


def _track(index: int, table: Any, easing: str) -> dict:
    where = f"track {index + 1}"
    _only(where, table, TRACK_KEYS, "[[track]] with a target and its keys")
    target = table.get("target")
    if not isinstance(target, str) or ":" not in target or target.startswith(":"):
        raise _bad(where, f"targets {target!r}",
                   'name a node and its property, as "Halo:modulate" or '
                   '"Letters:material:shader_parameter/wipe"')
    own = _easing(where, table["easing"]) if "easing" in table else easing
    keys = table.get("keys")
    if not isinstance(keys, list) or not keys:
        raise _bad(where, "has no key",
                   "write keys as [{ at = 0.0, value = ... }, ...]")
    out, kinds, last = [], set(), -1.0
    for number, key in enumerate(keys):
        at = f"{where} key {number + 1}"
        _only(at, key, KEY_KEYS, "{ at = seconds, value = ... }")
        if "at" not in key or "value" not in key:
            raise _bad(at, "states no at or no value", "every key has both")
        when = _time(at, key["at"])
        if when <= last:
            raise _bad(at, f"is at {when:g}, not after the key before it",
                       "write a track's keys in order, each later than the last")
        kind, value = _value(at, key["value"])
        kinds.add(kind)
        out.append({"at": when, "value": value,
                    "ease": _easing(at, key["ease"]) if "ease" in key else own})
        last = when
    if len(kinds) > 1:
        raise _bad(where, f"mixes values of kinds {sorted(kinds)}",
                   "keep one kind of value to a track, as the property holds one")
    return {"target": target, "kind": kinds.pop(), "keys": out}


def _checked(table: Any, source: str) -> dict:
    """One timeline with its defaults, every key and value refused unless it means
    something."""
    _only(source, table, TIMELINE_KEYS, "a name and [[track]] tables")
    name = table.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        raise _bad(source, f"is named {name!r}",
                   "name it as a word of letters, digits and underscores; it is the "
                   "scene's file name, its node's and its animation's")
    easing = _easing(source, table.get("easing", "linear"))
    tracks = table.get("track")
    if not isinstance(tracks, list) or not tracks:
        raise _bad(source, "has no track", "write at least one [[track]]")
    built = [_track(i, track, easing) for i, track in enumerate(tracks)]
    marks = []
    for index, mark in enumerate(table.get("mark") or ()):
        where = f"mark {index + 1}"
        _only(where, mark, MARK_KEYS, "[[mark]] with at and name")
        if not isinstance(mark.get("name"), str) or not mark["name"]:
            raise _bad(where, f"is named {mark.get('name')!r}", "name it with a word")
        marks.append({"at": _time(where, mark.get("at")), "name": mark["name"]})
    ends = max([one["keys"][-1]["at"] for one in built] + [m["at"] for m in marks])
    length = table.get("length", ends)
    if not _number(length) or length < ends or length <= 0:
        raise _bad(source, f"lasts {length!r}",
                   f"write length as seconds from {ends:g}, its last key or mark, on")
    line = {"name": name, "length": float(length), "tracks": built,
            "marks": sorted(marks, key=lambda one: one["at"])}
    if "mirror" in table:
        line["mirror"] = _mirror(table["mirror"], line)
    return line


def _mirror(table: Any, line: dict) -> dict:
    """The mirror's name and, per track it negates, the components it negates."""
    where = "mirror"
    _only(where, table, MIRROR_KEYS, "[mirror] with a name and negate")
    name = table.get("name")
    if not isinstance(name, str) or not name.isidentifier() or name == line["name"]:
        raise _bad(where, f"is named {name!r}",
                   "name it as a word of letters, digits and underscores, other than "
                   "the timeline's own; it is the second animation's name")
    kinds = {track["target"]: track["kind"] for track in line["tracks"]}
    negate = table.get("negate")
    if not isinstance(negate, list) or not negate:
        raise _bad(where, "negates nothing",
                   "list in negate the tracks whose sign the mirror flips")
    flips: dict[str, list[int] | None] = {}
    for one in negate:
        said = {"target": one} if isinstance(one, str) else _only(
            where, one, NEGATE_KEYS, "a target, or { target, axes = [\"x\"] }")
        target = said.get("target")
        if target not in kinds:
            raise _bad(where, f"negates {target!r}, which no track targets",
                       "name a track's target exactly as it is written",
                       given=str(target), allowed=list(kinds))
        kind = kinds[target]
        if kind in ("bool", "color"):
            raise _bad(where, f"negates {target}, a {kind}, which has no sign",
                       "negate a number or a vector's components")
        axes = said.get("axes")
        if axes is None:
            flips[target] = None
            continue
        width = {"vector2": 2, "vector3": 3}.get(kind, 0)
        named = [AXES.get(axis) for axis in axes] if isinstance(axes, list) else [None]
        if not width or not named or any(i is None or i >= width for i in named):
            raise _bad(where, f"negates {target} on axes {axes!r}",
                       "name axes of its vector, as [\"x\"] or [\"x\", \"z\"]; a "
                       "number is negated whole")
        flips[target] = sorted(set(named))
    return {"name": name, "negate": flips}


def _mirrored(line: dict) -> dict:
    """The timeline with the mirror's tracks negated, as its own animation."""
    flips = line["mirror"]["negate"]

    def flipped(track: dict, value: Any) -> Any:
        # Taken from 0.0, so a zero stays 0 and is never written -0.
        axes = flips[track["target"]]
        if track["kind"] == "float":
            return 0.0 - value
        return [0.0 - v if axes is None or i in axes else v
                for i, v in enumerate(value)]

    tracks = [
        {**track, "keys": [{**key, "value": flipped(track, key["value"])}
                           for key in track["keys"]]}
        if track["target"] in flips else track
        for track in line["tracks"]
    ]
    return {**line, "name": line["mirror"]["name"], "tracks": tracks}


def _godot(kind: str, value: Any) -> str:
    if kind == "bool":
        return "true" if value else "false"
    if kind == "float":
        # Always with a point: a bare `0` is an int to Godot, and a track mixing an int
        # key with a float one never moves, as a bank keyed 0, 0.32, 0 did not.
        said = f"{value:.9g}"
        return said if any(c in said for c in ".en") else f"{said}.0"
    numbers = ", ".join(f"{v:.9g}" for v in value)
    return {"vector2": "Vector2", "vector3": "Vector3", "color": "Color"}[kind] + \
        f"({numbers})"


def _text(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _floats(values: list[float]) -> str:
    return "PackedFloat32Array(" + ", ".join(f"{v:.9g}" for v in values) + ")"


#: The player's script: it says each mark the animation reaches.
_PLAYS = """extends AnimationPlayer
## A timeline polyweave built (clip.timeline, §PW554). Play it, or seek it by time; the
## paths of its tracks start from the node this player is a child of.

signal mark(name: String)


func _mark(name: String) -> void:
\tmark.emit(name)
"""


def _scene(line: dict) -> str:
    """The timeline as a Godot 4 scene: an AnimationPlayer holding its Animation, and
    its mirror's beside it in the one library where it declares one (§PW592)."""
    name = line["name"]
    played = [("timeline", line)]
    if line.get("mirror"):
        played.append(("mirror", _mirrored(line)))
    animations = "\n\n".join(_animation(at, one, name) for at, one in played)
    library = ",\n".join(f'&{_text(one["name"])}: SubResource("{at}")'
                         for at, one in played)
    source = _PLAYS.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f"[gd_scene load_steps={len(played) + 3} format=3]\n\n"
        '[sub_resource type="GDScript" id="plays"]\n'
        f'script/source = "{source}"\n\n'
        + animations + "\n\n"
        '[sub_resource type="AnimationLibrary" id="library"]\n'
        f"_data = {{\n{library}\n}}\n\n"
        f'[node name="{name}" type="AnimationPlayer"]\n'
        # A mark is said as the play reaches it, not deferred to the frame's end.
        "callback_mode_method = 1\n"
        'script = SubResource("plays")\n'
        'libraries = {\n&"": SubResource("library")\n}\n'
    )


def _animation(at: str, line: dict, player: str) -> str:
    """One Animation sub-resource: its value tracks, and its marks on the player."""
    name = line["name"]
    lines = [
        f'[sub_resource type="Animation" id="{at}"]',
        f"resource_name = {_text(name)}",
        f"length = {line['length']:.9g}",
    ]
    for index, track in enumerate(line["tracks"]):
        keys = track["keys"]
        values = ", ".join(_godot(track["kind"], key["value"]) for key in keys)
        lines += [
            f'tracks/{index}/type = "value"',
            f"tracks/{index}/imported = false",
            f"tracks/{index}/enabled = true",
            f'tracks/{index}/path = NodePath({_text(track["target"])})',
            f"tracks/{index}/interp = 1",
            f"tracks/{index}/loop_wrap = true",
            f"tracks/{index}/keys = {{",
            f'"times": {_floats([key["at"] for key in keys])},',
            f'"transitions": {_floats([EASINGS[key["ease"]] for key in keys])},',
            # Discrete for a bool, which no curve runs between; continuous otherwise.
            f'"update": {1 if track["kind"] == "bool" else 0},',
            f'"values": [{values}]',
            "}",
        ]
    if line["marks"]:
        index = len(line["tracks"])
        calls = ", ".join(f'{{"args": [{_text(m["name"])}], "method": &"_mark"}}'
                          for m in line["marks"])
        lines += [
            f'tracks/{index}/type = "method"',
            f"tracks/{index}/imported = false",
            f"tracks/{index}/enabled = true",
            # The marks are said by the player, whichever animation it plays.
            f'tracks/{index}/path = NodePath({_text(player)})',
            f"tracks/{index}/interp = 1",
            f"tracks/{index}/loop_wrap = true",
            f"tracks/{index}/keys = {{",
            f'"times": {_floats([m["at"] for m in line["marks"]])},',
            f'"transitions": {_floats([1.0] * len(line["marks"]))},',
            f'"values": [{calls}]',
            "}",
        ]
    return "\n".join(lines)


def _source(source: str, config) -> tuple[Path, dict]:
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError(
            "clip.no-timeline", f"there is no timeline at {source}",
            "name a *.timeline.toml relative to the project root",
        )
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "clip.no-timeline", f"{source} is not TOML",
            "fix the syntax the detail names", detail=str(exc),
        ) from exc
    return where, _checked(declared, source)


@operation("clip.timeline")
def build(
    source: Annotated[str, Param("the *.timeline.toml, relative to the project")],
    out: Annotated[
        str, Param("the folder the scene is written to; beside the source if unset")
    ] = None,
    root: Annotated[str, Param("the project the timeline belongs to")] = ".",
) -> dict:
    """Build keyed tracks of a scene's own properties into a scene the game plays.

    It lands as <name>.tscn: an AnimationPlayer whose animation keys each target's
    property, emitting mark(name) at each mark (§PW554). A [mirror] adds a second
    animation with the tracks it names negated, played by its own name (§PW592).
    """
    from polyweave.layers.vfx.vfx import shipped_folder

    config = load(root)
    where, line = _source(source, config)
    folder = shipped_folder(config, where, out, None, "clip.unshipped")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{line['name']}.tscn"
    target.write_text(_scene(line), encoding="utf-8", newline="\n")
    numbers = {"duration": line["length"], "tracks": len(line["tracks"]),
               "keys": sum(len(track["keys"]) for track in line["tracks"]),
               "marks": len(line["marks"])}
    provenance.write(provenance.build(
        "timeline", target, engine={"name": "clip.timeline"},
        inputs=[provenance.source("timeline", where, config.root)],
        params={"timeline": line["name"],
                **({"mirror": line["mirror"]["name"]} if line.get("mirror") else {})},
        measurements=numbers, root=config.root,
    ), config.root)
    return {
        "source": provenance.relative(where, config.root),
        "file": provenance.relative(target, config.root),
        "animations": [line["name"]]
        + ([line["mirror"]["name"]] if line.get("mirror") else []),
        "targets": [track["target"] for track in line["tracks"]],
        "marks": [mark["name"] for mark in line["marks"]],
        **numbers,
    }
