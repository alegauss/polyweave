"""A material's finish asked for in a few numbers, the shader inputs derived (§PW494).

What makes a piece read as moulded plastic is mostly its finish: a tight bright
highlight under a clear coat, a soft rim of light at the silhouette, and light going a
little way into the body so a pastel glows rather than greys. A material that states a
`colour` and a `roughness` asks for none of that, and the plastic city baked as painted
clay.

So, as `surface` does for a fuzz (§PW50), a declaration states the intent and this
derives the inputs:

```toml
[materials."pink plastic"]
colour     = "#F27BA8"
roughness  = 0.35
coat       = { weight = 1.0, roughness = 0.04 }
sheen      = 0.2
rim        = 0.6
subsurface = { weight = 0.3, depth = 0.05, tint = "#FF8080" }
```

`coat` and `subsurface` may be a number, their weight, or a table; `sheen` and `rim` are
numbers. Each is an expression over the document's parameters, resolved before it
arrives here, so PW32's search turns them as it turns a shape. Every input but the rim
is a socket of the Principled BSDF; the rim is a light at the silhouette, which the bake
builds from the view's angle to the surface.
"""

from __future__ import annotations

import math
from typing import Any

from polyweave.kernel.errors import PolyweaveError

__all__ = ["ASKS", "asked", "godot", "inputs", "says", "write_godot"]

#: The finish a material may ask for, beside the sockets it already names.
ASKS = ("coat", "sheen", "rim", "subsurface")

#: What a coat or a subsurface table may state, and what each is when left out.
COAT = {"weight": 1.0, "roughness": 0.03}
SUBSURFACE = {"weight": 1.0, "depth": 0.05, "tint": None}

#: How rough a sheen is: a soft glow across the surface, not a second highlight.
SHEEN_ROUGHNESS = 0.3

#: The roughness at or below which a surface reads glossy, and at or above which matte.
GLOSSY, MATTE = 0.3, 0.7


def asked(material: Any) -> dict:
    """The finish a material asks for, checked, each table filled out; {} if none."""
    if not isinstance(material, dict):
        return {}
    found: dict = {}
    for name in ("sheen", "rim"):
        if name in material:
            found[name] = _share(material[name], name)
    for name, fields in (("coat", COAT), ("subsurface", SUBSURFACE)):
        if name in material:
            found[name] = _table(material[name], name, fields)
    return found


def _table(stated: Any, name: str, fields: dict) -> dict:
    """A coat or a subsurface: a number is its weight, a table says more."""
    if not isinstance(stated, dict):
        return {**fields, "weight": _share(stated, name)}
    unknown = sorted(set(stated) - set(fields))
    if unknown:
        raise PolyweaveError(
            "geom.bad-surface",
            f"a {name} takes no {', '.join(unknown)}",
            f"it takes {', '.join(fields)}; or write it as one number, its weight",
            given=unknown[0],
            allowed=tuple(fields),
        )
    made = {**fields, **stated}
    made["weight"] = _share(made["weight"], f"{name} weight")
    if "roughness" in made:
        made["roughness"] = _share(made["roughness"], f"{name} roughness")
    if "depth" in made:
        made["depth"] = _number(made["depth"], f"{name} depth")
        if made["depth"] <= 0:
            raise PolyweaveError(
                "geom.bad-surface",
                f"light goes {made['depth']:g} into the body, which is not into it",
                "give the subsurface a depth above zero, in the declaration's units",
            )
    tint = made.get("tint")
    if tint is not None and not (isinstance(tint, str) and tint.startswith("#")):
        raise PolyweaveError(
            "geom.bad-surface",
            f"a subsurface's tint is {tint!r}, which is not a colour",
            "write it as #RRGGBB, the colour the light inside the body turns",
        )
    return made


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PolyweaveError(
            "geom.bad-surface",
            f"a material's {name} is {value!r}, which is not a number",
            "state it as a number, or as an expression over the document's own "
            "parameters so that a search can turn it",
        )
    return float(value)


def _share(value: Any, name: str) -> float:
    found = _number(value, name)
    if not 0.0 <= found <= 1.0:
        raise PolyweaveError(
            "geom.bad-surface",
            f"a material's {name} is {found:g}, outside nought to one",
            "give it from 0, none of it, to 1, all of it",
        )
    return found


def inputs(material: dict) -> dict:
    """The material in the shader's words: its finish expanded, everything else kept.

    `rim` stays a key of its own, because it is not a socket: the bake builds it.
    """
    finish = asked(material)
    out = {key: value for key, value in material.items() if key not in ASKS}
    if "coat" in finish:
        out["coat_weight"] = finish["coat"]["weight"]
        out["coat_roughness"] = finish["coat"]["roughness"]
    if "sheen" in finish:
        out["sheen_weight"] = finish["sheen"]
        out["sheen_roughness"] = SHEEN_ROUGHNESS
    if "subsurface" in finish:
        inside = finish["subsurface"]
        out["subsurface_weight"] = inside["weight"]
        out["subsurface_scale"] = inside["depth"]
        if inside["tint"]:
            # How far each colour travels in the body: the tint's own channels, so a
            # red tint carries red furthest and the pastel glows warm.
            tint = inside["tint"]
            channels = [int(tint[at : at + 2], 16) / 255.0 for at in (1, 3, 5)]
            most = max(max(channels), 1e-6)
            out["subsurface_radius"] = [one / most for one in channels]
    if "rim" in finish:
        out["rim"] = finish["rim"]
    return out


#: What Blender's Principled BSDF holds where a material says nothing, so the game is
#: given the numbers the bake drew with and not Godot's own defaults (§PW495).
BAKED = {"colour": (0.906, 0.906, 0.906, 1.0), "roughness": 0.5, "metallic": 0.0}

_STANDARD = """[gd_resource type="StandardMaterial3D" format=3]

[resource]
resource_name = %(name)s
%(fields)s
"""

_SHADED = """[gd_resource type="ShaderMaterial" load_steps=2 format=3]

[ext_resource type="Shader" path="%(shader)s" id="1"]

[resource]
resource_name = %(name)s
shader = ExtResource("1")
%(fields)s
"""

#: A finish StandardMaterial3D has no field for, drawn by a spatial shader: the sheen,
#: a soft lift of the surface's own colour where it turns from the view.
_SHADER = """shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.906, 0.906, 0.906, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float clearcoat : hint_range(0.0, 1.0) = 0.0;
uniform float clearcoat_roughness : hint_range(0.0, 1.0) = 0.03;
uniform float rim : hint_range(0.0, 1.0) = 0.0;
uniform float subsurface : hint_range(0.0, 1.0) = 0.0;
uniform float sheen : hint_range(0.0, 1.0) = 0.0;

void fragment() {
\tALBEDO = albedo.rgb;
\tROUGHNESS = roughness;
\tMETALLIC = metallic;
\tCLEARCOAT = clearcoat;
\tCLEARCOAT_ROUGHNESS = clearcoat_roughness;
\tRIM = rim;
\tRIM_TINT = 0.0;
\tSSS_STRENGTH = subsurface;
\tfloat grazing = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
\tEMISSION = albedo.rgb * sheen * pow(grazing, 4.0);
}
"""


#: The same finish opened to the project (§PW569): `%(head)s` holds its include and its
#: instance uniform, and the colour passes through `%(colour)s` before it is lit.
_OPEN = """shader_type spatial;
%(head)s
uniform vec4 albedo : source_color = vec4(0.906, 0.906, 0.906, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float clearcoat : hint_range(0.0, 1.0) = 0.0;
uniform float clearcoat_roughness : hint_range(0.0, 1.0) = 0.03;
uniform float rim : hint_range(0.0, 1.0) = 0.0;
uniform float subsurface : hint_range(0.0, 1.0) = 0.0;
uniform float sheen : hint_range(0.0, 1.0) = 0.0;

varying float hue;
%(give)s
// `c` turned `turns` of the way round the colour wheel, keeping its lightness
vec3 turned(vec3 c, float turns) {
\tfloat a = turns * 6.2831853;
\tvec3 k = vec3(0.57735);
\treturn c * cos(a) + cross(k, c) * sin(a) + k * dot(k, c) * (1.0 - cos(a));
}

void vertex() {
\thue = %(hue)s;
%(sway)s}

void fragment() {
\tvec3 colour = max(turned(albedo.rgb, hue), vec3(0.0));
\tALBEDO = %(colour)s;
\tROUGHNESS = roughness;
\tMETALLIC = metallic;
\tCLEARCOAT = clearcoat;
\tCLEARCOAT_ROUGHNESS = clearcoat_roughness;
\tRIM = rim;
\tRIM_TINT = 0.0;
\tSSS_STRENGTH = subsurface;
\tfloat grazing = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
\tEMISSION = ALBEDO * sheen * pow(grazing, 4.0);
}
"""

#: What `hue` may be: none, or each instance's own INSTANCE_CUSTOM.x.
HUES = ("", "instance")

#: A finish that gives when struck (§PW574): the same squash and swing `vfx` gives a
#: struck piece (§PW496), its uniforms and its vertex body, so a piece keeps its judged
#: finish and jiggles where a strike lands. `height` is how tall a piece's swing is
#: measured over, so a tall one swings more and the ground barely moves.
_GIVE_UNIFORMS = """
uniform float give = 0.1;
uniform float wobble = 3.0;
uniform float settle = 3.7;
uniform float falloff = 1.5;
uniform float height = 1.0;
uniform float felt = 1.0;
uniform vec4 hits[%(most)d];
uniform float ages[%(most)d];
"""

_GIVE_BODY = """\tvec3 origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
\tfloat bend = pow(clamp(VERTEX.y / height, 0.0, 1.0), falloff);
\tvec3 sway = vec3(0.0);
\tfloat squash = 0.0;
\tfor (int i = 0; i < %(most)d; i++) {
\t\tif (hits[i].w <= 0.0 || ages[i] < 0.0) {
\t\t\tcontinue;
\t\t}
\t\tvec3 away = origin - hits[i].xyz;
\t\tfloat near = 1.0 - clamp(length(away) / felt, 0.0, 1.0);
\t\tfloat swing = hits[i].w * near * exp(-settle * ages[i])
\t\t\t* cos(6.2831853 * wobble * ages[i]);
\t\tvec3 local = (vec4(away, 0.0) * MODEL_MATRIX).xyz;
\t\tlocal.y = 0.0;
\t\tlocal = length(local) > 0.0001 ? normalize(local) : vec3(0.0);
\t\tsway += local * swing * give * bend;
\t\tsquash += abs(swing) * give / height;
\t}
\tsquash = clamp(squash, 0.0, 0.5);
\tVERTEX.y *= 1.0 - squash * bend;
\tVERTEX.xz *= 1.0 + 0.5 * squash * bend;
\tVERTEX += sway;
"""

#: What a struck finish states, and the bounds each is held to.
STRUCK = {"give": (0.0, None), "wobble": (0.0, None), "lifetime": (0.0, None),
          "falloff": (None, None), "height": (0.0, None), "radius": (0.0, None),
          "amount": (0.0, 16.0)}

#: The script beside a struck finish's materials: `strike(at, strength)` ages each
#: strike and hands every material it was given the points, so a game holds one node
#: and calls one method (§PW574).
_STRIKES = """extends Node
## Strikes for every material a struck finish wrote (polyweave §PW574): `watch` the
## materials the pieces wear, then `strike` where a hit lands.

@export var most := %(most)d
@export var life := %(life)s
var hits: Array = []
var ages: Array = []
var _looks: Array[ShaderMaterial] = []

func _init() -> void:
\tfor i in most:
\t\thits.append(Vector4.ZERO)
\t\tages.append(-1.0)

## hand strikes to `look` too, once
func watch(look: Material) -> void:
\tif look is ShaderMaterial and not _looks.has(look):
\t\t_looks.append(look)
\t\t_hand_one(look)

func strike(at: Vector3, strength: float = 1.0) -> void:
\tvar slot := 0
\tfor i in most:
\t\tif ages[i] < 0.0 or ages[i] > ages[slot]:
\t\t\tslot = i
\t\t\tif ages[i] < 0.0:
\t\t\t\tbreak
\thits[slot] = Vector4(at.x, at.y, at.z, strength)
\tages[slot] = 0.0
\t_hand()

## whether any strike is still swinging
func swinging() -> bool:
\treturn ages.any(func(age: float) -> bool: return age >= 0.0)

func _process(delta: float) -> void:
\tif not swinging():
\t\treturn
\tfor i in most:
\t\tif ages[i] >= 0.0:
\t\t\tages[i] += delta
\t\t\tif ages[i] > life * 2.0:
\t\t\t\tages[i] = -1.0
\t\t\t\thits[i] = Vector4.ZERO
\t_hand()

func _hand() -> void:
\tfor look in _looks:
\t\t_hand_one(look)

func _hand_one(look: ShaderMaterial) -> void:
\tlook.set_shader_parameter("hits", hits)
\tlook.set_shader_parameter("ages", ages)
"""


def _struck(table: Any) -> dict | None:
    """A `[finish] struck` table checked, or None where the finish does not give."""
    if not table:
        return None
    if not isinstance(table, dict):
        raise PolyweaveError(
            "geom.bad-surface", "[finish] struck is not a table",
            "write struck = { give = 0.3, wobble = 3, lifetime = 0.9, falloff = 1.5, "
            "height = 6, radius = 8, amount = 8 }")
    unknown = set(table) - set(STRUCK)
    if unknown:
        raise PolyweaveError(
            "geom.bad-surface", f"[finish] struck takes no {sorted(unknown)[0]}",
            f"write only {', '.join(STRUCK)}", given=sorted(unknown)[0],
            allowed=tuple(STRUCK))
    found = {"falloff": 1.5, "amount": 8, **table}
    for key, (low, high) in STRUCK.items():
        if key not in found:
            raise PolyweaveError(
                "geom.bad-surface", f"[finish] struck states no {key}",
                f"write {key} in it, as vfx's struck pieces state it")
        value = found[key]
        below = low is not None and isinstance(value, int | float) and value <= low
        above = high is not None and isinstance(value, int | float) and value > high
        if isinstance(value, bool) or not isinstance(value, int | float) or below \
                or above:
            raise PolyweaveError(
                "geom.bad-surface", f"[finish] struck {key} is {value!r}",
                f"write {key} as a number"
                + (f" above {low:g}" if low is not None else "")
                + (f" and at most {high:g}" if high is not None else ""),
                given=value)
    found["amount"] = int(found["amount"])
    return found


def opened(table: dict) -> dict | None:
    """The project's `[finish]` checked, or None where it leaves the finish closed."""
    hue = str(table.get("hue") or "")
    include = str(table.get("include") or "")
    hold = str(table.get("hold") or "")
    amount = str(table.get("amount") or "backdrop")
    if hue not in HUES:
        raise PolyweaveError(
            "geom.bad-surface",
            f"[finish] hue is {hue!r}, and a finish turns its hue by nothing or by "
            f"each instance's own",
            'write hue = "instance", or leave it out',
            given=hue, allowed=HUES,
        )
    if bool(include) != bool(hold):
        raise PolyweaveError(
            "geom.bad-surface",
            "[finish] names " + ("an include and no hold" if include else
                                  "a hold and no include") +
            ", and a hold is a function the include declares",
            "name both: include, the res:// shader include, and hold, its function "
            "taking (vec3 colour, float amount)",
        )
    for name, value in (("hold", hold), ("amount", amount)):
        if value and not value.replace("_", "a").isalnum():
            raise PolyweaveError(
                "geom.bad-surface",
                f"[finish] {name} is {value!r}, which is not a shader name",
                f"write {name} as the name alone, such as dimmed_day",
                given=value,
            )
    if include and not include.startswith("res://"):
        raise PolyweaveError(
            "geom.bad-surface",
            f"[finish] include is {include!r}, and Godot includes a shader by its "
            f"res:// path",
            "write include as res://path/to/file.gdshaderinc",
            given=include,
        )
    struck = _struck(table.get("struck"))
    if not (hue or include or struck):
        return None
    return {"hue": hue, "include": include, "hold": hold, "amount": amount,
            "struck": struck}


def _opened_shader(hooks: dict) -> str:
    head = ""
    colour = "colour"
    if hooks["include"]:
        head = (f"// 1 unless the instance says (§PW569)\n"
                f"instance uniform float {hooks['amount']} = 1.0;\n\n"
                f'#include "{hooks["include"]}"\n')
        colour = f"{hooks['hold']}(colour, {hooks['amount']})"
    hue = "INSTANCE_CUSTOM.x" if hooks["hue"] == "instance" else "0.0"
    struck = hooks.get("struck")
    most = {"most": struck["amount"]} if struck else {}
    return _OPEN % {
        "head": head, "colour": colour, "hue": hue,
        "give": _GIVE_UNIFORMS % most if struck else "",
        "sway": _GIVE_BODY % most if struck else "",
    }


def settle_rate(lifetime: float) -> float:
    """The decay that leaves a twentieth of a strike's give at `lifetime` seconds."""
    return math.log(20.0) / lifetime


def _struck_fields(struck: dict) -> dict:
    """A struck finish's numbers as the shader's uniforms, as vfx sets a piece's.

    The settle is vfx's `settle_rate`, written out here: importing vfx would make
    geometry need Godot, which vfx's engine layer does. tests/test_finish.py holds the
    two to one curve.
    """
    return {"give": struck["give"], "wobble": struck["wobble"],
            "settle": settle_rate(struck["lifetime"]), "falloff": struck["falloff"],
            "height": struck["height"], "felt": struck["radius"]}


def _rgba(value: Any) -> tuple:
    """A declared colour as the sRGB parts Godot's Color holds, as a hex already is."""
    if isinstance(value, str) and value.startswith("#") and len(value) in (7, 9):
        parts = [int(value[at : at + 2], 16) / 255.0 for at in range(1, len(value), 2)]
    elif isinstance(value, list | tuple) and len(value) in (3, 4):
        parts = [float(v) for v in value]
    else:
        parts = []
    if parts:
        return (*parts[:3], parts[3] if len(parts) == 4 else 1.0)
    raise PolyweaveError(
        "geom.bad-surface",
        f"a material's colour is {value!r}, which a Godot material cannot hold",
        "write it as #RRGGBB or #RRGGBBAA",
    )


def _color(parts: tuple) -> str:
    return "Color(" + ", ".join(f"{float(one):.6g}" for one in parts) + ")"


def godot(material: dict, hooks: dict | None = None) -> dict:
    """The material as Godot loads it, with the numbers the bake used (§PW495).

    A `.tres` StandardMaterial3D for a coat, a rim and a subsurface, which it has fields
    for; with a sheen, which it has not, a ShaderMaterial over the spatial shader this
    writes beside it. Where the project opens the finish (`hooks`, §PW569) it is always
    that shader, with the project's hue and hold in it. Answers `material` (the .tres
    text), `shader` (the .gdshader text or None) and `fields`, what was set, by Godot's
    names.
    """
    finish = asked(material)
    colour = _rgba(material.get("colour", material.get("color", BAKED["colour"])))
    rough = float(material.get("roughness", BAKED["roughness"]))
    metal = float(material.get("metallic", BAKED["metallic"]))
    coat = finish.get("coat", {})
    inside = finish.get("subsurface", {})
    if "sheen" in finish or hooks:
        fields = {
            "albedo": _color(colour), "roughness": rough, "metallic": metal,
            "clearcoat": coat.get("weight", 0.0),
            "clearcoat_roughness": coat.get("roughness", COAT["roughness"]),
            "rim": finish.get("rim", 0.0), "subsurface": inside.get("weight", 0.0),
            "sheen": finish.get("sheen", 0.0),
        }
        if hooks and hooks.get("struck"):
            fields.update(_struck_fields(hooks["struck"]))
        lines = [f"shader_parameter/{k} = {_value(v)}" for k, v in fields.items()]
        shader = _opened_shader(hooks) if hooks else _SHADER
        return {"material": lines, "shader": shader, "fields": fields}
    fields = {"albedo_color": _color(colour), "roughness": rough, "metallic": metal}
    if coat.get("weight"):
        fields.update(clearcoat_enabled=True, clearcoat=coat["weight"],
                      clearcoat_roughness=coat["roughness"])
    if finish.get("rim"):
        fields.update(rim_enabled=True, rim=finish["rim"], rim_tint=0.0)
    if inside.get("weight"):
        fields.update(subsurf_scatter_enabled=True,
                      subsurf_scatter_strength=inside["weight"])
        if inside["tint"]:
            fields.update(subsurf_scatter_transmittance_enabled=True,
                          subsurf_scatter_transmittance_color=_color(_rgba(inside["tint"])),
                          subsurf_scatter_transmittance_depth=inside["depth"])
    lines = [f"{k} = {_value(v)}" for k, v in fields.items()]
    return {"material": lines, "shader": None, "fields": fields}


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return f"{float(value):.6g}"
    return str(value)


def write_godot(material: dict, name: str, folder: Any, stem: str, root: Any) -> list:
    """The Godot material written beside a build, and its shader where it needs one.

    `<stem>.<name>.tres`, the name's spaces as underscores. Where it is a ShaderMaterial
    its shader is the folder's one copy, `finish.gdshader` (`finish_sheen.gdshader` for
    a sheen on a closed finish), named by its res:// path under `root`: the code is the
    same for every material, whose numbers are its own parameters, so twelve pieces no
    longer carry fifty copies for the game to compile apart (§PW571). It is written only
    where its text changed.
    """
    import json
    from pathlib import Path

    from polyweave.kernel.config import load

    hooks = opened(load(root).table("finish"))
    made = godot(material, hooks)
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    out = Path(folder) / f"{stem}.{slug}.tres"
    written = []
    if hooks and hooks.get("struck"):
        # one script for every struck material in the folder, the game's door (§PW574)
        struck = hooks["struck"]
        strikes = Path(folder) / "finish_strikes.gd"
        strikes.write_text(_STRIKES % {"most": struck["amount"],
                                       "life": f"{float(struck['lifetime']):.6g}"},
                           encoding="utf-8", newline="\n")
        written.append(strikes)
    said = json.dumps(name)
    body = "\n".join(made["material"])
    if made["shader"] is None:
        text = _STANDARD % {"name": said, "fields": body}
    else:
        shared = "finish.gdshader" if hooks else "finish_sheen.gdshader"
        shader = Path(folder) / shared
        if not shader.is_file() or shader.read_text(encoding="utf-8") != made["shader"]:
            shader.write_text(made["shader"], encoding="utf-8", newline="\n")
        written.append(shader)
        place = shader.resolve().relative_to(Path(root).resolve()).as_posix()
        text = _SHADED % {"name": said, "shader": f"res://{place}", "fields": body}
    out.write_text(text, encoding="utf-8", newline="\n")
    return [out, *written]


#: The import settings written for a mesh Godot has not imported yet: it fills in the
#: rest of its own defaults and keeps these (§PW570).
_IMPORT = """[remap]

importer="scene"
importer_version=1

[params]

_subresources=%s
"""


def wire_import(mesh: Any, worn: dict, root: Any) -> Any:
    """`<mesh>.import`, written so Godot imports each material as its written .tres.

    Only in a Godot project (a project.godot at the root) and only for materials a
    `.tres` was written for. An existing import keeps every setting but its
    `_subresources`, which this owns while it holds only materials; one the project
    filled with more is left alone and None answered, as for no Godot project.
    """
    import json
    from pathlib import Path

    here = Path(root).resolve()
    if not worn or not (here / "project.godot").is_file():
        return None
    mapping = {
        name: {
            "use_external/enabled": True,
            "use_external/path": "res://" + Path(path).resolve().relative_to(here)
            .as_posix(),
        }
        for name, path in sorted(worn.items())
    }
    value = json.dumps({"materials": mapping}, indent=1)
    target = Path(f"{mesh}.import")
    if not target.is_file():
        target.write_text(_IMPORT % value, encoding="utf-8", newline="\n")
        return target
    lines = target.read_text(encoding="utf-8").split("\n")
    start = next((i for i, line in enumerate(lines)
                  if line.startswith("_subresources=")), None)
    if start is None:
        lines += ["_subresources=" + value]
    else:
        end, depth = start, 0
        for end in range(start, len(lines)):
            depth += lines[end].count("{") - lines[end].count("}")
            if depth <= 0:
                break
        held = "\n".join(lines[start:end + 1]).partition("=")[2].strip()
        try:
            kinds = set(json.loads(held)) if held != "{}" else set()
        except ValueError:
            return None
        if kinds - {"materials"}:
            return None
        lines[start:end + 1] = ["_subresources=" + value]
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return target


def says(material: Any) -> str:
    """The finish in words, `clear-coated, glossy`, or "" where none is asked for."""
    finish = asked(material)
    if not finish:
        return ""
    words = []
    if finish.get("coat", {}).get("weight"):
        words.append("clear-coated")
    if finish.get("sheen"):
        words.append("with a sheen")
    if finish.get("rim"):
        words.append("rim-lit")
    if finish.get("subsurface", {}).get("weight"):
        words.append("lit from within")
    rough = material.get("roughness")
    coat = finish.get("coat", {})
    if coat.get("weight"):
        rough = coat["roughness"] if rough is None else min(rough, coat["roughness"])
    if isinstance(rough, int | float) and not isinstance(rough, bool):
        if rough <= GLOSSY:
            words.append("glossy")
        elif rough >= MATTE:
            words.append("matte")
    return ", ".join(words)
