"""Visual effects as declarations, built into what the engine plays (§PW259).

Starship's trails were game data, a Resource per trail tuned by looking at captures,
which is the tuning by eye every other part of a game here has left behind. An effect is
declared in a `*.vfx.toml` instead, and `vfx.build` writes it as a Godot scene:

    [effect.spark_trail]
    kind = "particles"            # or ribbon: a trail through each particle's path
    amount = 64                   # the particles alive at once: the effect's budget
    lifetime = 0.8                # seconds
    speed = [2.0, 3.0]            # metres a second, least and most
    direction = [0, 0, 1]
    spread = 15.0                 # degrees
    size = 0.2                    # a quad's side, or a ribbon's width, in metres
    size_over_life = [1.0, 0.0]   # evenly across the life
    colour_over_life = ["#ffd24aff", "#ff4a1a00"]
    blend = "add"                 # or mix

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


KINDS = ("particles", "ribbon")
EMISSIONS = ("point", "sphere")
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


def _colour(name: str, value: Any) -> tuple[float, float, float, float]:
    found = _COLOUR.fullmatch(value) if isinstance(value, str) else None
    if not found:
        raise _bad(name, f"has a colour {value!r}",
                   "write each stop as #rrggbb, or #rrggbbaa with its alpha")
    rgb, alpha = found.group(1), found.group(2) or "ff"
    return (*(int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)), int(alpha, 16) / 255)


def checked(name: str, table: Any) -> dict:
    """One effect's table with its defaults, every key and value refused unless it
    means something."""
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
    for key in ("lifetime", "explosiveness", "radius", "spread", "size", "trail"):
        if not _number(own[key]) or own[key] < 0:
            raise _bad(name, f"sets {key} to {own[key]!r}",
                       f"write {key} as a number no less than 0")
    if own["lifetime"] <= 0 or own["explosiveness"] > 1 or own["spread"] > 180:
        raise _bad(name, "has a lifetime of 0, an explosiveness past 1 or a spread "
                   "past 180", "a life is longer than nothing, explosiveness runs "
                   "0 to 1 and spread 0 to 180 degrees")
    if not isinstance(own["one_shot"], bool):
        raise _bad(name, f"sets one_shot to {own['one_shot']!r}",
                   "write one_shot as true or false")
    own["direction"] = _vector(name, "direction", own["direction"], 3)
    own["gravity"] = _vector(name, "gravity", own["gravity"], 3)
    own["speed"] = sorted(_vector(name, "speed", own["speed"], 2))
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
    for key in ("lifetime", "explosiveness", "radius", "spread", "size", "trail"):
        own[key] = float(own[key])
    return own


def measured(effect: dict) -> dict:
    """What an effect measures, from its declaration alone."""
    life = effect["lifetime"]
    pull = math.sqrt(sum(g * g for g in effect["gravity"]))
    reach = effect["speed"][1] * life + 0.5 * pull * life * life + effect["radius"]
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
    ribbon = effect["kind"] == "ribbon"
    draw = (
        f'[sub_resource type="RibbonTrailMesh" id="draw"]\n'
        f'material = SubResource("look")\nshape = 0\nsize = {effect["size"]:.6g}\n'
        if ribbon else
        f'[sub_resource type="QuadMesh" id="draw"]\nmaterial = SubResource("look")\n'
        f'size = Vector2({effect["size"]:.6g}, {effect["size"]:.6g})\n'
    )
    return (
        '[gd_scene load_steps=8 format=3]\n\n'
        '[sub_resource type="Gradient" id="colours"]\n'
        f"offsets = PackedFloat32Array({_floats(offsets)})\n"
        f"colors = PackedColorArray({_floats(c for s in stops for c in s)})\n\n"
        '[sub_resource type="GradientTexture1D" id="ramp"]\n'
        'gradient = SubResource("colours")\n\n'
        '[sub_resource type="Curve" id="sizes"]\n'
        f"max_value = {top:.6g}\n_data = [{points}]\npoint_count = {len(sizes)}\n\n"
        '[sub_resource type="CurveTexture" id="scale"]\n'
        'curve = SubResource("sizes")\n\n'
        '[sub_resource type="ParticleProcessMaterial" id="process"]\n'
        f"emission_shape = {1 if effect['emission'] == 'sphere' else 0}\n"
        f"emission_sphere_radius = {effect['radius']:.6g}\n"
        f"direction = Vector3({_floats(effect['direction'])})\n"
        f"spread = {effect['spread']:.6g}\n"
        f"initial_velocity_min = {effect['speed'][0]:.6g}\n"
        f"initial_velocity_max = {effect['speed'][1]:.6g}\n"
        f"gravity = Vector3({_floats(effect['gravity'])})\n"
        'scale_curve = SubResource("scale")\ncolor_ramp = SubResource("ramp")\n\n'
        '[sub_resource type="StandardMaterial3D" id="look"]\n'
        f"transparency = 1\nblend_mode = {1 if effect['blend'] == 'add' else 0}\n"
        "shading_mode = 0\nvertex_color_use_as_albedo = true\n"
        + ("use_particle_trails = true\n" if ribbon else "billboard_mode = 3\n")
        + "\n" + draw + "\n"
        f'[node name="{name}" type="GPUParticles3D"]\n'
        f"amount = {effect['amount']}\nlifetime = {effect['lifetime']:.6g}\n"
        f"one_shot = {'true' if effect['one_shot'] else 'false'}\n"
        f"explosiveness = {effect['explosiveness']:.6g}\n"
        + (f"trail_enabled = true\ntrail_lifetime = {effect['trail']:.6g}\n"
           if ribbon else "")
        + 'process_material = SubResource("process")\n'
        'draw_pass_1 = SubResource("draw")\n'
    )


def _source(source: str, config) -> tuple[Path, dict]:
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError("vfx.no-source", f"there is no effects file at {source}",
                             "name a *.vfx.toml relative to the project root")
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8"))
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


@operation("vfx.build")
def build(
    source: Annotated[str, Param("the *.vfx.toml, relative to the project")],
    effect: Annotated[str, Param("one effect; left out, every one")] = None,
    out: Annotated[
        str, Param("the folder the scenes are written to; beside the source if unset")
    ] = None,
    root: Annotated[str, Param("the project the effects belong to")] = ".",
) -> dict:
    """Build declared particle and ribbon effects into Godot scenes, each recorded.

    Each lands as <name>.tscn, a GPUParticles3D the game instances as it is, and the
    answer says what each measures from its declaration: lifetime, reach, alive, rate
    and brightness.
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
    effects = {name: checked(name, table) for name, table in chosen.items()}
    folder = config.path("paths.work", out) if out else where.parent
    folder.mkdir(parents=True, exist_ok=True)
    made = {}
    for name, own in effects.items():
        target = folder / f"{name}.tscn"
        target.write_text(scene(name, own), encoding="utf-8", newline="\n")
        numbers = measured(own)
        provenance.write(provenance.build(
            "vfx", target, engine={"name": "vfx.build"},
            inputs=[provenance.source("effects", where, config.root)],
            params={"effect": name, "kind": own["kind"]},
            measurements=numbers, root=config.root,
        ), config.root)
        made[name] = {
            "file": provenance.relative(target, config.root),
            "kind": own["kind"],
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
\tworld.add_child(load("%(scene)s").instantiate())
\troot.add_child.call_deferred(world)

func _process(_delta: float) -> bool:
\tvar frame := Engine.get_process_frames()
\tif frame == %(start)d:
\t\tprint("environment: resolution=%%dx%%d" %% [root.size.x, root.size.y])
\tif frame == %(start)d:
\t\tprint("movie: from %%d" %% frame)
\tif frame == %(stop)d:
\t\tprint("movie: to %%d" %% frame)
\treturn frame >= %(stop)d + 3
"""


def _framing(effect: dict) -> dict:
    """Where the camera stands to see the whole of an effect's reach from its side."""
    reach = max(measured(effect)["reach"], 0.5)
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
    return {"centre": _floats(centre), "eye": _floats(eye), "up": _floats(up)}


@operation("vfx.preview", kind="capture")
def preview(
    source: Annotated[str, Param("the *.vfx.toml, relative to the project")],
    *,
    out: Annotated[str, Param("the folder the sitting is laid out in")],
    effect: Annotated[str, Param("one effect; left out, every one")] = None,
    stills: Annotated[int, Param("frames on each sheet", lo=2, hi=12)] = 6,
    root: Annotated[str, Param("the project the effects belong to")] = ".",
) -> dict:
    """Watch each effect over its life on a neutral grey, as a sitting for a person.

    Each effect is built, then played in the engine from its side, with the camera
    framing its reach, for one and a half lifetimes; the frames are kept by
    capture.movie and `stills` of them, evenly spaced, are laid out on one sheet with
    their times and what the effect measures. The sheets are a sitting on the review
    page, one family an effect; the answer lands through verdict.judge.
    """
    from PIL import Image, ImageDraw

    from . import capture, verdict

    config = load(root)
    here = config.root
    built = build(source, effect=effect, root=root)["effects"]
    _, tables = _source(source, config)
    fps = int(config.get("engine.fixed_fps"))
    folder = config.path("paths.work", out)
    work = config.path("paths.work") / "vfx"
    families, sheets, watched = {}, {}, {}
    for name, made in built.items():
        own = checked(name, tables[name])
        start, span = 2, max(2, round(own["lifetime"] * 1.5 * fps))
        script = work / f"{name}.watch.gd"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(_WATCH % {
            "grey": _floats(NEUTRAL), "scene": "res://" + made["file"],
            "start": start, "stop": start + span, **_framing(own),
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
        frames = sorted(Path(shot["out"]).glob("*.png"))
        picked = [frames[round(i * (len(frames) - 1) / (stills - 1))]
                  for i in range(stills)]
        gap, line = 8, 16
        sheet = Image.new("RGBA", (gap + stills * (FRAME[0] + gap),
                                   FRAME[1] + 2 * gap + 3 * line), (40, 40, 40, 255))
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(picked):
            with Image.open(frame) as still:
                sheet.alpha_composite(still.convert("RGBA").resize(FRAME),
                                      (gap + i * (FRAME[0] + gap), gap))
            at = (frames.index(frame)) / fps
            draw.text((gap + i * (FRAME[0] + gap), FRAME[1] + gap + 2),
                      f"t = {at:.2f} s", fill=(235, 235, 235, 255))
        said = ", ".join(f"{k} {made[k]:g}" for k in
                         ("lifetime", "reach", "alive", "rate", "brightness"))
        draw.text((gap, FRAME[1] + gap + line + 4), f"{name}: {said}",
                  fill=(255, 210, 90, 255))
        drawn = folder / f"{name}.png"
        drawn.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(drawn)
        member = {"name": name, "new": provenance.relative(drawn, here),
                  "effect": made["file"], "passed": True, "measured": said}
        families[name] = [member]
        sheets[name] = {"sheet": str(drawn),
                        "members": [{"name": name, "passed": True, "failed": []}]}
        watched[name] = {"sheet": member["new"], "frames": len(frames),
                         "scene": made["file"]}
    verdict._manifest(folder, families, sheets, here, choices=VFX_CHOICES)
    return {
        "sitting": provenance.relative(folder / verdict.MANIFEST, here),
        "effects": watched,
        "choices": dict(VFX_CHOICES),
        "says": f"{len(watched)} effect{'' if len(watched) == 1 else 's'} for a person "
        "to watch on the review page; verdict.answers resumes from what they said",
    }
