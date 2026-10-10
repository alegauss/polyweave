"""Visual effects as declarations, built into what the engine plays (§PW259).

Starship's trails were game data, a Resource per trail tuned by looking at captures,
which is the tuning by eye every other part of a game here has left behind. An effect is
declared in a `*.vfx.toml` instead, and `vfx.build` writes it as a Godot scene:

    [effect.spark_trail]
    kind = "particles"            # ribbon: a trail through each particle's path, or
                                  # path_ribbon: one through the path the emitter flew
    amount = 64                   # the particles alive at once: the effect's budget
    lifetime = 0.8                # seconds
    speed = [2.0, 3.0]            # metres a second, least and most
    direction = [0, 0, 1]
    spread = 15.0                 # degrees
    size = 0.2                    # a quad's side, or a ribbon's width, in metres
    size_over_life = [1.0, 0.0]   # evenly across the life
    colour_over_life = ["#ffd24aff", "#ff4a1a00"]
    blend = "add"                 # or mix
    damping = [6.0, 10.0]         # metres a second lost each second, or one number
    angle = [0, 360]              # a particle's turn at birth, in degrees
    angular_velocity = [-240, 240]  # its spin, degrees a second
    shape = "dot"                 # square, dot, ring, flake, or a picture's path
    randomness = 0.3              # how unevenly they start, 0 to 1 (§PW285)

`emission` is a point, a sphere of `radius` or a box of half-`extents` (§PW281), and a
`shape` other than a square is a texture on each quad: a soft dot, a ring or a flake
drawn from a gradient, as Starship's accepted trails draw them, or a picture of the
project's own.

A `path_ribbon` is a ribbon of light behind a moving emitter, as a ship's engine leaves
(§PW281): a Node3D the game puts where the engine is, whose own script keeps the points
its parent carried it through, `amount` of them at most, each living `lifetime`, and
draws a strip `size` wide across `facing`, coloured and narrowed by its age along
`colour_over_life` and `size_over_life`. The script is inside the scene, so the game
still holds no code of its own.

An effect can be made of parts, one look the game places once (§PW284): a trail is the
ribbon the engine leaves and the particles it throws, each a sub-table,

    [effect.sparks.ribbon]        # kind = "path_ribbon", ...
    [effect.sparks.particles]     # amount, lifetime, ...

built as the children of one Node3D in one scene, measured together and watched as one.

The scene is a GPUParticles3D with its process material, its curves and its draw pass,
all in the one file, so the game instances it and holds no numbers of its own. What it
measures is worked out from the declaration, since a particle's reach and a budget are
arithmetic: `reach` is the furthest a particle can travel in its life, `alive` the
particles alive at once, `rate` how many start a second and `brightness` the brightest
stop of its gradient. Whether its look is right stays a person's call.
"""

from __future__ import annotations

import difflib
import math
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: Every key an effect may hold: its type, and a default where it has one.
KEYS: dict[str, tuple[type | tuple, Any]] = {
    "kind": (str, "particles"),
    "amount": (int, None),
    "lifetime": (float, None),
    "explosiveness": (float, 0.0),
    "randomness": (float, 0.0),
    "one_shot": (bool, False),
    "emission": (str, "point"),
    "radius": (float, 0.0),
    "direction": (list, [0.0, 0.0, 1.0]),
    "spread": (float, 0.0),
    "speed": (list, [1.0, 1.0]),
    "gravity": (list, [0.0, 0.0, 0.0]),
    "size": (float, 0.1),
    "size_over_life": (list, [1.0, 1.0]),
    "colour_over_life": (list, ["#ffffffff", "#ffffff00"]),
    "blend": (str, "add"),
    "trail": (float, 0.3),
    "damping": (list, [0.0, 0.0]),
    "angle": (list, [0.0, 0.0]),
    "angular_velocity": (list, [0.0, 0.0]),
    "extents": (list, [0.0, 0.0, 0.0]),
    "shape": (str, "square"),
    "facing": (list, [0.0, 1.0, 0.0]),
    "step": (float, 1 / 60),
    "gap": (float, 0.3),
}

#: Every effect measure a predicate may bound, and what it says.
EFFECTS: dict[str, str] = {
    "lifetime": "seconds a particle lives",
    "reach": "the furthest a particle travels in its life, in metres",
    "alive": "the particles alive at once, the effect's budget",
    "rate": "the particles started a second",
    "brightness": "the brightest stop of its colour over life, luminance times alpha",
}


def is_effect(name: str) -> bool:
    return name in EFFECTS


def measures_of(path: Path, root: Path) -> dict:
    """What a built effect measures, as its record says: the scene is not re-read."""
    try:
        record = provenance.read(str(path), root=str(root))
    except PolyweaveError as missing:
        raise PolyweaveError(
            "spec.not-effect",
            f"{path.name} has no record of an effect vfx.build made",
            "check the spec against a .tscn vfx.build wrote, or add of = \"<it>\"",
            detail=missing.message,
        ) from missing
    if record.get("kind") != "vfx":
        raise PolyweaveError(
            "spec.not-effect",
            f"{path.name} is a {record.get('kind')} record, not an effect's",
            "check the spec against a .tscn vfx.build wrote",
        )
    return record.get("measurements") or {}


KINDS = ("particles", "ribbon", "path_ribbon")
EMISSIONS = ("point", "sphere", "box")

#: A particle's shape, as the gradient its texture is drawn from: stops of white at each
#: alpha, and whether it fills out from the middle. A square draws no texture at all.
SHAPES: dict[str, tuple[tuple[tuple[float, float], ...], bool]] = {
    "dot": (((0.0, 1.0), (0.25, 0.6), (1.0, 0.0)), True),
    "ring": (((0.0, 0.0), (0.62, 0.0), (0.78, 1.0), (0.9, 0.3), (1.0, 0.0)), True),
    "flake": (((0.0, 1.0), (0.7, 1.0), (0.75, 0.0)), False),
}

#: A shape that names a picture instead, by its file's suffix.
PICTURES = (".png", ".webp", ".jpg", ".jpeg", ".svg")
BLENDS = ("add", "mix")

#: A colour as a gradient stop takes it: #rrggbb, or #rrggbbaa.
_COLOUR = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?")


def _bad(name: str, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("vfx.bad-effect", f"effect {name}: {what}", remedy, **extra)


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _vector(name: str, key: str, value: Any, length: int) -> list[float]:
    if (not isinstance(value, list) or len(value) != length
            or not all(_number(v) for v in value)):
        raise _bad(name, f"sets {key} to {value!r}",
                   f"write {key} as {length} numbers, such as "
                   f"{[0.0] * length}")
    return [float(v) for v in value]


def _range(name: str, key: str, value: Any, *, least: float | None = 0.0) -> list:
    """One number, or the least and the most, as the two a range is written with."""
    pair = [value, value] if _number(value) else value
    if (not isinstance(pair, list) or len(pair) != 2
            or not all(_number(v) for v in pair)
            or (least is not None and min(pair) < least)):
        floor = "" if least is None else f", none below {least:g}"
        raise _bad(name, f"sets {key} to {value!r}",
                   f"write {key} as a number or as [least, most]{floor}")
    return sorted(float(v) for v in pair)


def _shape(name: str, value: Any, root: Path | None) -> str:
    if not isinstance(value, str) or not value:
        raise _bad(name, f"sets shape to {value!r}",
                   f"name one of square, {', '.join(SHAPES)}, or a picture's path")
    if value == "square" or value in SHAPES:
        return value
    if Path(value).suffix.lower() not in PICTURES:
        raise _bad(name, f"has shape {value!r}",
                   f"name one of square, {', '.join(SHAPES)}, or a picture "
                   f"({', '.join(PICTURES)}) under the project",
                   given=value, allowed=["square", *SHAPES])
    picture = value.removeprefix("res://")
    if root is not None and not (root / picture).is_file():
        raise _bad(name, f"has shape {value!r}, and there is no picture there",
                   "name a picture relative to the project root")
    return picture


def _colour(name: str, value: Any) -> tuple[float, float, float, float]:
    found = _COLOUR.fullmatch(value) if isinstance(value, str) else None
    if not found:
        raise _bad(name, f"has a colour {value!r}",
                   "write each stop as #rrggbb, or #rrggbbaa with its alpha")
    rgb, alpha = found.group(1), found.group(2) or "ff"
    return (*(int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)), int(alpha, 16) / 255)


def checked(name: str, table: Any, root: Path | None = None) -> dict:
    """One effect's table with its defaults, every key and value refused unless it
    means something. A picture a shape names is looked for under `root`."""
    if not isinstance(table, dict):
        raise _bad(name, "is not a table", f"write it as [effect.{name}]")
    for key in table:
        if key not in KEYS:
            near = difflib.get_close_matches(key, KEYS, n=1)
            raise _bad(name, f"has no key {key!r}",
                       f"did you mean {near[0]!r}?" if near
                       else f"name one of {', '.join(KEYS)}",
                       given=key, allowed=list(KEYS))
    for key in ("amount", "lifetime"):
        if key not in table:
            raise _bad(name, f"states no {key}",
                       f"write {key}: every effect has a budget and a life")
    own = {key: table.get(key, default) for key, (_, default) in KEYS.items()}
    for key, choices in (("kind", KINDS), ("emission", EMISSIONS), ("blend", BLENDS)):
        if own[key] not in choices:
            raise _bad(name, f"has {key} {own[key]!r}",
                       f"name one of {', '.join(choices)}",
                       given=str(own[key]), allowed=list(choices))
    if isinstance(own["amount"], bool) or not isinstance(own["amount"], int) \
            or own["amount"] < 1:
        raise _bad(name, f"sets amount to {own['amount']!r}",
                   "write amount as a whole number of particles, at least 1")
    for key in ("lifetime", "explosiveness", "randomness", "radius", "spread", "size",
                "trail"):
        if not _number(own[key]) or own[key] < 0:
            raise _bad(name, f"sets {key} to {own[key]!r}",
                       f"write {key} as a number no less than 0")
    if (own["lifetime"] <= 0 or own["explosiveness"] > 1 or own["randomness"] > 1
            or own["spread"] > 180):
        raise _bad(name, "has a lifetime of 0, an explosiveness or randomness past 1, "
                   "or a spread past 180", "a life is longer than nothing, "
                   "explosiveness and randomness run 0 to 1, spread 0 to 180 degrees")
    if not isinstance(own["one_shot"], bool):
        raise _bad(name, f"sets one_shot to {own['one_shot']!r}",
                   "write one_shot as true or false")
    own["direction"] = _vector(name, "direction", own["direction"], 3)
    own["gravity"] = _vector(name, "gravity", own["gravity"], 3)
    own["speed"] = sorted(_vector(name, "speed", own["speed"], 2))
    own["damping"] = _range(name, "damping", own["damping"])
    own["angle"] = _range(name, "angle", own["angle"], least=None)
    own["angular_velocity"] = _range(name, "angular_velocity",
                                     own["angular_velocity"], least=None)
    own["extents"] = _vector(name, "extents", own["extents"], 3)
    if own["emission"] == "box" and (min(own["extents"]) < 0
                                     or not any(own["extents"])):
        raise _bad(name, f"emits from a box of extents {own['extents']!r}",
                   "write extents as the box's three half-sizes, none below 0, in "
                   "metres, such as [0.1, 1.0, 0.1]")
    own["shape"] = _shape(name, own["shape"], root)
    own["facing"] = _vector(name, "facing", own["facing"], 3)
    for key in ("step", "gap"):
        if not _number(own[key]) or own[key] <= 0:
            raise _bad(name, f"sets {key} to {own[key]!r}",
                       f"write {key} as a number above 0: a path ribbon adds a point "
                       "each step seconds, or each gap metres the emitter moves")
        own[key] = float(own[key])
    # Paced by time, a ribbon holds lifetime / step points whatever the frame rate
    # (§PW286); a ceiling under that would cut it short, so it is refused here.
    needs = math.ceil(float(own["lifetime"]) / own["step"]) + 1
    if own["kind"] == "path_ribbon" and own["amount"] < needs:
        raise _bad(name, f"holds {own['amount']} points, and a {own['lifetime']:g} s "
                   f"ribbon at a step of {own['step']:g} s needs {needs}",
                   f"raise amount to {needs} or more, or lengthen step")
    if not any(own["facing"]):
        raise _bad(name, "faces [0, 0, 0], so a path ribbon has no width",
                   "write facing as the direction its width lies along, such as "
                   "[0, 1, 0]")
    sizes = own["size_over_life"]
    if not isinstance(sizes, list) or len(sizes) < 2 or not all(
            _number(v) and v >= 0 for v in sizes):
        raise _bad(name, f"sets size_over_life to {sizes!r}",
                   "write at least two scales no less than 0, evenly across the life")
    own["size_over_life"] = [float(v) for v in sizes]
    stops = own["colour_over_life"]
    if not isinstance(stops, list) or len(stops) < 2:
        raise _bad(name, f"sets colour_over_life to {stops!r}",
                   "write at least two colours, evenly across the life")
    own["colour_over_life"] = [_colour(name, stop) for stop in stops]
    for key in ("lifetime", "explosiveness", "randomness", "radius", "spread", "size",
                "trail"):
        own[key] = float(own[key])
    return own


def declared(name: str, table: Any, root: Path | None = None) -> dict:
    """One effect, or one made of parts: a table whose every value is a table (§PW284).

    Each part is checked as an effect of its own, named `<effect>.<part>`, so a
    refusal says which part it came from.
    """
    if isinstance(table, dict) and table and all(
            isinstance(v, dict) for v in table.values()):
        return {"kind": "parts",
                "parts": {part: checked(f"{name}.{part}", sub, root)
                          for part, sub in table.items()}}
    if isinstance(table, dict) and any(isinstance(v, dict) for v in table.values()):
        tables = sorted(k for k, v in table.items() if isinstance(v, dict))
        raise _bad(name, f"mixes keys of its own with parts ({', '.join(tables)})",
                   f"write every key inside a part, as [effect.{name}.<part>], or "
                   "make it one effect with no sub-tables")
    return checked(name, table, root)


def measured_whole(effect: dict) -> dict:
    """What an effect measures, a whole made of parts included: the budget is every
    part's, and the reach, life and brightness the largest any part has."""
    if effect["kind"] != "parts":
        return measured(effect)
    each = [measured(part) for part in effect["parts"].values()]
    return {
        "lifetime": max(m["lifetime"] for m in each),
        "reach": max(m["reach"] for m in each),
        "alive": sum(m["alive"] for m in each),
        "rate": round(sum(m["rate"] for m in each), 4),
        "brightness": max(m["brightness"] for m in each),
    }


def measured(effect: dict) -> dict:
    """What an effect measures, from its declaration alone."""
    life = effect["lifetime"]
    pull = math.sqrt(sum(g * g for g in effect["gravity"]))
    fastest, brake = effect["speed"][1], effect["damping"][0]
    # Damping takes speed off at a rate, so the fastest, least braked particle stops
    # once it has spent its speed, or runs its whole life first (§PW281).
    moving = min(life, fastest / brake) if brake > 0 else life
    travel = fastest * moving - 0.5 * brake * moving * moving
    start = (effect["radius"] if effect["emission"] == "sphere" else
             math.sqrt(sum(e * e for e in effect["extents"]))
             if effect["emission"] == "box" else 0.0)
    reach = travel + 0.5 * pull * life * life + start
    if effect["kind"] == "path_ribbon":
        # It stays where the emitter was: its reach is the half-width it spreads.
        reach = effect["size"] / 2
    brightness = max(
        (0.2126 * r + 0.7152 * g + 0.0722 * b) * a
        for r, g, b, a in effect["colour_over_life"]
    )
    return {
        "lifetime": round(life, 4),
        "reach": round(reach, 4),
        "alive": effect["amount"],
        "rate": round(effect["amount"] / life, 4),
        "brightness": round(brightness, 4),
    }


def _floats(values) -> str:
    return ", ".join(f"{v:.6g}" for v in values)


#: The emission shapes as ParticleProcessMaterial numbers them.
_EMITS = {"point": 0, "sphere": 1, "box": 3}


def _shaped(effect: dict) -> tuple[str, str, str]:
    """The external picture, the texture's own resources and the material's line."""
    shape = effect["shape"]
    if shape == "square":
        return "", "", ""
    if shape not in SHAPES:
        external = f'[ext_resource type="Texture2D" path="res://{shape}" id="picture"]'
        return f"{external}\n\n", "", 'albedo_texture = ExtResource("picture")\n'
    stops, radial = SHAPES[shape]
    whites = [c for _, alpha in stops for c in (1.0, 1.0, 1.0, alpha)]
    fill = ("fill = 1\nfill_from = Vector2(0.5, 0.5)\nfill_to = Vector2(1, 0.5)\n"
            if radial else "")
    own = ('[sub_resource type="Gradient" id="outline"]\n'
           f"offsets = PackedFloat32Array({_floats(o for o, _ in stops)})\n"
           f"colors = PackedColorArray({_floats(whites)})\n\n"
           '[sub_resource type="GradientTexture2D" id="shape"]\n'
           'gradient = SubResource("outline")\nwidth = 64\nheight = 64\n'
           f"{fill}\n")
    return "", own, 'albedo_texture = SubResource("shape")\n'


#: A path ribbon's own script, inside the scene: it keeps the points its parent passed,
#: newest last, and rebuilds the strip from them each frame, in the world.
_FOLLOWS = """extends Node3D

@export var colours: Gradient
@export var sizes: Curve
@export var look: Material
@export var width := 0.2
@export var life := 1.0
@export var most := 64
@export var facing := Vector3.UP
@export var step := 1.0 / 60.0
@export var gap := 0.3

var points: Array = []
var since := 0.0
var strip := ImmediateMesh.new()
var drawn := MeshInstance3D.new()
var offset := Vector3.ZERO

func _ready() -> void:
\toffset = position
\ttop_level = true
\tglobal_transform = Transform3D.IDENTITY
\tdrawn.mesh = strip
\tdrawn.material_override = look
\tdrawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
\tadd_child(drawn)

func _process(delta: float) -> void:
\tvar parent := get_parent() as Node3D
\tvar here: Vector3 = parent.global_transform * offset if parent else offset
\tfor point in points:
\t\tpoint[1] += delta
\twhile not points.is_empty() and points[0][1] > life:
\t\tpoints.pop_front()
\tsince += delta
\t# Paced by time and by distance, never by frame, so the ribbon is as long at 600
\t# frames a second as at 60.
\tvar moved: bool = not points.is_empty() and (
\t\t(points.back()[0] as Vector3).distance_to(here) > gap)
\t# A hair under step, so a step of 1/60 at 60 frames a second takes every frame.
\tif points.is_empty() or since >= step - 0.0001 or moved:
\t\tpoints.append([here, 0.0])
\t\tsince = 0.0
\twhile points.size() > most:
\t\tpoints.pop_front()
\tstrip.clear_surfaces()
\tif points.size() < 2:
\t\treturn
\tvar across := facing.normalized()
\tstrip.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
\tfor point in points:
\t\tvar aged: float = clampf(point[1] / life, 0.0, 1.0)
\t\tvar half: float = width * 0.5 * sizes.sample(aged)
\t\tvar shade: Color = colours.sample(aged)
\t\tstrip.surface_set_color(shade)
\t\tstrip.surface_add_vertex(point[0] + across * half)
\t\tstrip.surface_set_color(shade)
\t\tstrip.surface_add_vertex(point[0] - across * half)
\tstrip.surface_end()
"""


def _path_ribbon(name: str, effect: dict, colours: str, sizes: str) -> str:
    """A path ribbon's scene: its gradient, its curve, its look and its script."""
    source = _FOLLOWS.replace("\\", "\\\\").replace('"', '\\"')
    return (
        '[gd_scene load_steps=5 format=3]\n\n'
        + colours + sizes +
        '[sub_resource type="StandardMaterial3D" id="look"]\n'
        f"transparency = 1\nblend_mode = {1 if effect['blend'] == 'add' else 0}\n"
        "shading_mode = 0\nvertex_color_use_as_albedo = true\ncull_mode = 2\n\n"
        '[sub_resource type="GDScript" id="follows"]\n'
        f'script/source = "{source}"\n\n'
        f'[node name="{name}" type="Node3D"]\n'
        'script = SubResource("follows")\n'
        'colours = SubResource("colours")\nsizes = SubResource("sizes")\n'
        'look = SubResource("look")\n'
        f"width = {effect['size']:.6g}\nlife = {effect['lifetime']:.6g}\n"
        f"most = {effect['amount']}\nfacing = Vector3({_floats(effect['facing'])})\n"
        f"step = {effect['step']:.9g}\ngap = {effect['gap']:.6g}\n"
    )


def scene(name: str, effect: dict) -> str:
    """The effect as a Godot 4 scene: the particles node and all it draws with."""
    stops = effect["colour_over_life"]
    offsets = [i / (len(stops) - 1) for i in range(len(stops))]
    sizes = effect["size_over_life"]
    top = max(1.0, *sizes)
    points = ", ".join(
        f"Vector2({i / (len(sizes) - 1):.6g}, {v:.6g}), 0.0, 0.0, 0, 0"
        for i, v in enumerate(sizes)
    )
    colours = (
        '[sub_resource type="Gradient" id="colours"]\n'
        f"offsets = PackedFloat32Array({_floats(offsets)})\n"
        f"colors = PackedColorArray({_floats(c for s in stops for c in s)})\n\n"
    )
    curve = (
        '[sub_resource type="Curve" id="sizes"]\n'
        f"max_value = {top:.6g}\n_data = [{points}]\npoint_count = {len(sizes)}\n\n"
    )
    if effect["kind"] == "path_ribbon":
        return _path_ribbon(name, effect, colours, curve)
    ribbon = effect["kind"] == "ribbon"
    draw = (
        f'[sub_resource type="RibbonTrailMesh" id="draw"]\n'
        f'material = SubResource("look")\nshape = 0\nsize = {effect["size"]:.6g}\n'
        if ribbon else
        f'[sub_resource type="QuadMesh" id="draw"]\nmaterial = SubResource("look")\n'
        f'size = Vector2({effect["size"]:.6g}, {effect["size"]:.6g})\n'
    )
    picture, shaped, textured = _shaped(effect)
    steps = 8 + bool(picture) + 2 * bool(shaped)
    return (
        f'[gd_scene load_steps={steps} format=3]\n\n'
        + picture + shaped + colours +
        '[sub_resource type="GradientTexture1D" id="ramp"]\n'
        'gradient = SubResource("colours")\n\n'
        + curve +
        '[sub_resource type="CurveTexture" id="scale"]\n'
        'curve = SubResource("sizes")\n\n'
        '[sub_resource type="ParticleProcessMaterial" id="process"]\n'
        f"emission_shape = {_EMITS[effect['emission']]}\n"
        f"emission_sphere_radius = {effect['radius']:.6g}\n"
        f"emission_box_extents = Vector3({_floats(effect['extents'])})\n"
        f"direction = Vector3({_floats(effect['direction'])})\n"
        f"spread = {effect['spread']:.6g}\n"
        f"initial_velocity_min = {effect['speed'][0]:.6g}\n"
        f"initial_velocity_max = {effect['speed'][1]:.6g}\n"
        f"gravity = Vector3({_floats(effect['gravity'])})\n"
        f"damping_min = {effect['damping'][0]:.6g}\n"
        f"damping_max = {effect['damping'][1]:.6g}\n"
        f"angle_min = {effect['angle'][0]:.6g}\n"
        f"angle_max = {effect['angle'][1]:.6g}\n"
        f"angular_velocity_min = {effect['angular_velocity'][0]:.6g}\n"
        f"angular_velocity_max = {effect['angular_velocity'][1]:.6g}\n"
        'scale_curve = SubResource("scale")\ncolor_ramp = SubResource("ramp")\n\n'
        '[sub_resource type="StandardMaterial3D" id="look"]\n'
        f"transparency = 1\nblend_mode = {1 if effect['blend'] == 'add' else 0}\n"
        "shading_mode = 0\nvertex_color_use_as_albedo = true\n" + textured
        + ("use_particle_trails = true\n" if ribbon else "billboard_mode = 3\n")
        + "\n" + draw + "\n"
        f'[node name="{name}" type="GPUParticles3D"]\n'
        f"amount = {effect['amount']}\nlifetime = {effect['lifetime']:.6g}\n"
        f"one_shot = {'true' if effect['one_shot'] else 'false'}\n"
        f"explosiveness = {effect['explosiveness']:.6g}\n"
        f"randomness = {effect['randomness']:.6g}\n"
        + (f"trail_enabled = true\ntrail_lifetime = {effect['trail']:.6g}\n"
           if ribbon else "")
        + 'process_material = SubResource("process")\n'
        'draw_pass_1 = SubResource("draw")\n'
    )


#: Where one section of a scene begins, so a part's scene can be taken apart.
_SECTION = re.compile(r"(?m)^(?=\[(?:gd_scene|ext_resource|sub_resource|node)\b)")


def _composed(name: str, parts: dict) -> str:
    """One scene holding every part under a Node3D, each part's resources renamed for
    it so two parts' `look` never collide."""
    external, internal, nodes = [], [], []
    for part, effect in parts.items():
        text = scene(part, effect)
        text = re.sub(r'id="([^"]+)"', rf'id="{part}_\1"', text)
        text = re.sub(r'(Sub|Ext)Resource\("([^"]+)"\)', rf'\1Resource("{part}_\2")',
                      text)
        for block in _SECTION.split(text):
            block = block.rstrip("\n") + "\n\n"
            if block.startswith("[ext_resource"):
                external.append(block)
            elif block.startswith("[sub_resource"):
                internal.append(block)
            elif block.startswith("[node"):
                nodes.append(re.sub(r"^\[node (.*?)\]", r'[node \1 parent="."]', block,
                                    count=1))
    steps = len(external) + len(internal) + 1
    return (f"[gd_scene load_steps={steps} format=3]\n\n" + "".join(external)
            + "".join(internal) + f'[node name="{name}" type="Node3D"]\n\n'
            + "".join(nodes)).rstrip("\n") + "\n"


def scene_whole(name: str, effect: dict) -> str:
    """The scene an effect builds to, whether it is one effect or made of parts."""
    if effect["kind"] == "parts":
        return _composed(name, effect["parts"])
    return scene(name, effect)


def _source(source: str, config) -> tuple[Path, dict]:
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError("vfx.no-source", f"there is no effects file at {source}",
                             "name a *.vfx.toml relative to the project root")
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("vfx.no-source", f"{source} is not TOML",
                             "fix the syntax the detail names",
                             detail=str(exc)) from exc
    stray = sorted(set(declared) - {"effect"})
    if stray or not isinstance(declared.get("effect"), dict) or not declared["effect"]:
        raise PolyweaveError("vfx.no-source",
                             f"{source} holds no [effect.<name>] tables",
                             "write each effect as [effect.<name>] with its amount "
                             "and lifetime")
    return where, declared["effect"]


def shipped_folder(config, where: Path, out: str | None, address: str | None,
                   code: str) -> Path:
    """Where a scene built from the declaration at `where` is written (§PW374).

    A call's `out` first, then the project's folder at `address` where it names one.
    With neither, beside the declaration, unless the export leaves the declaration out:
    a scene there loads in the editor and not in the shipped game, so it is refused.
    """
    if out:
        return config.path("paths.work", out)
    if address and config.get(address):
        return config.path(address)
    from .driving import left_out

    why = left_out(config.root, where)
    if why:
        setting = f" or set [{address.replace('.', '] ')} in polyweave.toml" \
            if address else ""
        raise PolyweaveError(
            code,
            f"{provenance.relative(where, config.root)} sits where the game's export "
            f"leaves it out ({why}), so a scene built beside it would not ship",
            f"pass out, a folder the game ships{setting}",
            given=provenance.relative(where, config.root),
        )
    return where.parent


@operation("vfx.build")
def build(
    source: Annotated[str, Param("the *.vfx.toml, relative to the project")],
    effect: Annotated[str, Param("one effect; left out, every one")] = None,
    out: Annotated[
        str, Param("the folder the scenes go to; [paths] vfx, else beside the source")
    ] = None,
    root: Annotated[str, Param("the project the effects belong to")] = ".",
) -> dict:
    """Build declared particle and ribbon effects into Godot scenes, each recorded.

    Each lands as <name>.tscn the game instances as it is; an effect made of parts is
    one scene with each part under a Node3D, never beside a source the export leaves
    out. The answer says what each measures from its declaration: lifetime, reach,
    alive, rate and brightness.
    """
    config = load(root)
    where, tables = _source(source, config)
    if effect is not None and effect not in tables:
        near = difflib.get_close_matches(effect, tables, n=1)
        raise PolyweaveError(
            "vfx.bad-effect", f"{source} has no effect {effect!r}",
            f"did you mean {near[0]!r}?" if near
            else f"name one of {', '.join(tables)}",
            given=effect, allowed=sorted(tables),
        )
    chosen = {effect: tables[effect]} if effect else tables
    effects = {name: declared(name, table, config.root)
               for name, table in chosen.items()}
    folder = shipped_folder(config, where, out, "paths.vfx", "vfx.unshipped")
    folder.mkdir(parents=True, exist_ok=True)
    made = {}
    for name, own in effects.items():
        target = folder / f"{name}.tscn"
        target.write_text(scene_whole(name, own), encoding="utf-8", newline="\n")
        numbers = measured_whole(own)
        provenance.write(provenance.build(
            "vfx", target, engine={"name": "vfx.build"},
            inputs=[provenance.source("effects", where, config.root)],
            params={"effect": name, "kind": own["kind"]},
            measurements=numbers, root=config.root,
        ), config.root)
        made[name] = {
            "file": provenance.relative(target, config.root),
            "kind": own["kind"],
            **({"parts": {part: one["kind"] for part, one in own["parts"].items()}}
               if own["kind"] == "parts" else {}),
            **numbers,
        }
    return {"source": provenance.relative(where, config.root), "effects": made}


# -- a look a person can judge ---------------------------------------------------------

#: What a person can say of an effect watched over its life.
VFX_CHOICES = {
    "accept": "it looks right: the game plays what was built",
    "look": "it does not: say why, and the declaration goes back",
}

#: The grey an effect is watched against, neither of the light it adds nor of a scene.
NEUTRAL = (0.18, 0.18, 0.18)

#: The size each still is shown at on the sheet, a 16:9 window's shape.
FRAME = (320, 180)

_WATCH = """extends SceneTree

var mover := Node3D.new()

func _initialize() -> void:
\tvar world := Node3D.new()
\tvar backdrop := WorldEnvironment.new()
\tbackdrop.environment = Environment.new()
\tbackdrop.environment.background_mode = Environment.BG_COLOR
\tbackdrop.environment.background_color = Color(%(grey)s)
\tworld.add_child(backdrop)
\tvar camera := Camera3D.new()
\tcamera.transform = Transform3D(
\t\tBasis.looking_at(Vector3(%(centre)s) - Vector3(%(eye)s), Vector3(%(up)s)),
\t\tVector3(%(eye)s))
\tworld.add_child(camera)
\tmover.position = Vector3(%(centre)s)
\tworld.add_child(mover)
\tmover.add_child(load("%(scene)s").instantiate())
\troot.add_child.call_deferred(world)

func _process(_delta: float) -> bool:
\tvar frame := Engine.get_process_frames()
\tvar turn := TAU * frame / %(turn)s
\tmover.position = Vector3(%(centre)s) + %(round)s * (
\t\tcos(turn) * Vector3(%(along)s) + sin(turn) * Vector3(%(across)s))
\tif frame == %(start)d:
\t\tprint("environment: resolution=%%dx%%d" %% [root.size.x, root.size.y])
\tif frame == %(start)d:
\t\tprint("movie: from %%d" %% frame)
\tif frame == %(stop)d:
\t\tprint("movie: to %%d" %% frame)
\treturn frame >= %(stop)d + 3
"""


def _watched_as(effect: dict) -> dict:
    """The one effect a whole is framed as: its farthest-reaching part, living as long
    as the longest, still only where every part is a one-shot burst."""
    if effect["kind"] != "parts":
        return effect
    parts = list(effect["parts"].values())
    widest = max(parts, key=lambda one: measured(one)["reach"])
    return {**widest,
            "lifetime": max(one["lifetime"] for one in parts),
            "size": max(one["size"] for one in parts),
            "one_shot": all(one["one_shot"] for one in parts)}


def _framing(effect: dict, fps: int = 60) -> dict:
    """Where the camera stands to see the whole of an effect's reach from its side, and
    the circle the emitter is carried round in its view: a trail reads only in motion
    (§PW281), and a one-shot burst is watched standing still."""
    reach = max(measured(effect)["reach"], 0.5, effect["size"] * 6)
    d = effect["direction"]
    norm = math.sqrt(sum(v * v for v in d)) or 1.0
    d = [v / norm for v in d]
    centre = [v * reach / 2 for v in d]
    # From across the direction, upright where the effect is not itself vertical.
    up = [0.0, 1.0, 0.0] if abs(d[1]) < 0.9 else [0.0, 0.0, 1.0]
    side = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2],
            d[0] * up[1] - d[1] * up[0]]
    size = math.sqrt(sum(v * v for v in side)) or 1.0
    eye = [c + s / size * reach * 0.9 for c, s in zip(centre, side, strict=True)]
    # The view's other axis: the circle lies across the camera, in its frame.
    across = [side[1] * d[2] - side[2] * d[1], side[2] * d[0] - side[0] * d[2],
              side[0] * d[1] - side[1] * d[0]]
    wide = math.sqrt(sum(v * v for v in across)) or 1.0
    still = effect["one_shot"]
    return {"centre": _floats(centre), "eye": _floats(eye), "up": _floats(up),
            "along": _floats(d), "across": _floats(v / wide for v in across),
            "round": f"{0.0 if still else reach * 0.4:.6g}",
            # Once round in two lives, so the trail behind it curves and fades.
            "turn": f"{max(1.0, 2 * effect['lifetime'] * fps):.6g}"}


def _filmed(name: str, scene: str, own: dict, fps: int, work: Path, here: Path) -> list:
    """One scene played under the watch camera, as the frames Movie Maker kept."""
    from . import capture

    start, span = 2, max(2, round(own["lifetime"] * 1.5 * fps))
    script = work / f"{name}.watch.gd"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(_WATCH % {
        "grey": _floats(NEUTRAL), "scene": scene,
        "start": start, "stop": start + span, **_framing(own, fps),
    }, encoding="utf-8", newline="\n")
    shot = capture.movie(
        provenance.relative(script, here), out=str(work / name / "frames"),
        # Asked at the size the sheet draws, which capture.movie sizes Movie Maker
        # to for the run (§PW273).
        root=str(here), environment={"resolution": f"{FRAME[0]}x{FRAME[1]}"},
    )
    if not shot["ok"]:
        raise PolyweaveError(
            "vfx.unwatched",
            f"effect {name} could not be watched: {shot.get('why')}",
            "run it where a display is, or through the offscreen route; the log "
            "is named in the detail",
            detail=shot.get("log"),
        )
    return sorted(Path(shot["out"]).glob("*.png"))


#: Faces that carry accents, tried in order: a sheet's words are in the project's
#: language (§PW287), and Pillow's own face draws "Construído" with a box for the í.
FACES = ("DejaVuSans.ttf", "segoeui.ttf", "arial.ttf", "Arial.ttf", "Helvetica.ttc")


def _face(size: int = 14):
    """A face that draws the project's language, or Pillow's own where none is found."""
    from PIL import ImageFont

    for name in FACES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _animated(filmed: list, fps: int, target: Path) -> Path:
    """A film as one looping picture, since a trail is judged moving (§PW287)."""
    from PIL import Image

    frames = []
    for frame in filmed:
        with Image.open(frame) as still:
            frames.append(still.convert("RGB").resize(FRAME))
    target.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(target, save_all=True, append_images=frames[1:], loop=0,
                   duration=max(1, round(1000 / fps)), quality=80)
    return target


def _sheet(rows: list[tuple[str, list]], stills: int, fps: int, footer: str):
    """The stills of each row side by side, a row a film, each row named above it."""
    from PIL import Image, ImageDraw

    gap, line = 8, 24
    face = _face()
    height = len(rows) * (line + FRAME[1] + gap) + gap + 2 * line
    sheet = Image.new("RGBA", (gap + stills * (FRAME[0] + gap), height),
                      (40, 40, 40, 255))
    draw = ImageDraw.Draw(sheet)
    top = gap
    frames = rows[0][1]
    for label, filmed in rows:
        draw.text((gap, top + 2), label, fill=(255, 210, 90, 255), font=face)
        top += line
        picked = [filmed[round(i * (len(filmed) - 1) / (stills - 1))]
                  for i in range(stills)]
        for i, frame in enumerate(picked):
            with Image.open(frame) as still:
                sheet.alpha_composite(still.convert("RGBA").resize(FRAME),
                                      (gap + i * (FRAME[0] + gap), top))
        top += FRAME[1] + gap
    for i in range(stills):
        at = round(i * (len(frames) - 1) / (stills - 1)) / fps
        draw.text((gap + i * (FRAME[0] + gap), top + 2), f"t = {at:.2f} s",
                  fill=(235, 235, 235, 255), font=face)
    draw.text((gap, top + line + 2), footer, fill=(200, 200, 200, 255), font=face)
    return sheet


@operation("vfx.preview", kind="capture")
def preview(
    source: Annotated[str, Param("the *.vfx.toml, relative to the project")],
    *,
    out: Annotated[str, Param("the folder the sitting is laid out in")],
    effect: Annotated[str, Param("one effect; left out, every one")] = None,
    stills: Annotated[int, Param("frames on each sheet", lo=2, hi=12)] = 6,
    against: Annotated[
        dict, Param("each effect's scene as the game draws it now, filmed above it")
    ] = None,
    about: Annotated[str, Param("what the person should know, under the summary")] = "",
    root: Annotated[str, Param("the project the effects belong to")] = ".",
) -> dict:
    """Watch each effect over its life on a neutral grey, as a sitting for a person.

    Each effect is built, then played in the engine from its side, with the camera
    framing its reach and the emitter carried round a circle in view unless it is a
    one-shot burst, for one and a half lifetimes; `stills` frames, evenly spaced, are
    laid out on one sheet. `against` names, per effect, the scene that draws it in the
    game today: it is filmed the same way and laid above, so a person sees the two in
    one look (§PW287). The sheets are a sitting on the review page in the project's
    language, one family an effect; the answer lands through verdict.judge.
    """
    from . import review_text, verdict

    config = load(root)
    here = config.root
    built = build(source, effect=effect, root=root)["effects"]
    _, tables = _source(source, config)
    fps = int(config.get("engine.fixed_fps"))
    folder = config.path("paths.work", out)
    work = config.path("paths.work") / "vfx"
    speaks = review_text.language(here)
    words = review_text.kind("effect", speaks)
    against = dict(against or {})
    unknown = sorted(set(against) - set(built))
    if unknown:
        raise PolyweaveError(
            "vfx.bad-effect", f"against names {', '.join(unknown)}, which is not built",
            f"key against by the effects built: {', '.join(built)}",
            given=unknown[0], allowed=sorted(built),
        )
    families, sheets, watched, abouts = {}, {}, {}, {}
    for name, made in built.items():
        own = _watched_as(declared(name, tables[name], here))
        rows = []
        if name in against:
            scene = str(against[name]).removeprefix("res://")
            if not (here / scene).is_file():
                raise PolyweaveError(
                    "vfx.bad-effect", f"against names {scene} for {name}, which is not "
                    "there", "name the scene the game draws the effect with now")
            rows.append((words["rows"][0], _filmed(
                f"{name}.today", "res://" + scene, own, fps, work, here)))
        filmed = _filmed(name, "res://" + made["file"], own, fps, work, here)
        rows.append((words["rows"][1], filmed))
        said = ", ".join(f"{k} {made[k]:g}" for k in
                         ("lifetime", "reach", "alive", "rate", "brightness"))
        drawn = folder / f"{name}.png"
        drawn.parent.mkdir(parents=True, exist_ok=True)
        _sheet(rows, stills, fps, f"{name}: {said}").save(drawn)
        # Each film looping as well, labelled, so the page plays today beside built.
        films = [{"label": label, "path": provenance.relative(_animated(
                     one, fps, folder / f"{name}.{index}.webp"), here)}
                 for index, (label, one) in enumerate(rows)]
        member = {"name": name, "new": provenance.relative(drawn, here),
                  "effect": made["file"], "passed": True, "measured": said,
                  "films": films}
        families[name] = [member]
        sheets[name] = {"sheet": str(drawn),
                        "members": [{"name": name, "passed": True, "failed": []}]}
        parts = list(made.get("parts") or {})
        made_of = words["parts"].format(parts=", ".join(parts)) if parts else ""
        abouts[name] = (words["family"].format(name=name) + made_of
                        + (words["against"] if name in against else ""))
        watched[name] = {"sheet": member["new"], "frames": len(filmed),
                         "scene": made["file"], "against": name in against}
    verdict._manifest(folder, families, sheets, here, kind="effect", about=about,
                      abouts=abouts)
    return {
        "sitting": provenance.relative(folder / verdict.MANIFEST, here),
        "effects": watched,
        "choices": dict(VFX_CHOICES),
        "says": f"{len(watched)} effect{'' if len(watched) == 1 else 's'} for a person "
        "to watch on the review page; verdict.answers resumes from what they said",
    }
