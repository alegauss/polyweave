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


def godot(material: dict) -> dict:
    """The material as Godot loads it, with the numbers the bake used (§PW495).

    A `.tres` StandardMaterial3D for a coat, a rim and a subsurface, which it has fields
    for; with a sheen, which it has not, a ShaderMaterial over the spatial shader this
    writes beside it. Answers `material` (the .tres text), `shader` (the .gdshader text
    or None) and `fields`, what was set, by Godot's names.
    """
    finish = asked(material)
    colour = _rgba(material.get("colour", material.get("color", BAKED["colour"])))
    rough = float(material.get("roughness", BAKED["roughness"]))
    metal = float(material.get("metallic", BAKED["metallic"]))
    coat = finish.get("coat", {})
    inside = finish.get("subsurface", {})
    if "sheen" in finish:
        fields = {
            "albedo": _color(colour), "roughness": rough, "metallic": metal,
            "clearcoat": coat.get("weight", 0.0),
            "clearcoat_roughness": coat.get("roughness", COAT["roughness"]),
            "rim": finish.get("rim", 0.0), "subsurface": inside.get("weight", 0.0),
            "sheen": finish["sheen"],
        }
        lines = [f"shader_parameter/{k} = {_value(v)}" for k, v in fields.items()]
        return {"material": lines, "shader": _SHADER, "fields": fields}
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

    `<stem>.<name>.tres`, the name's spaces as underscores, and with a sheen
    `<stem>.<name>.gdshader` beside it, named by its res:// path under `root`.
    """
    import json
    from pathlib import Path

    made = godot(material)
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    out = Path(folder) / f"{stem}.{slug}.tres"
    written = []
    said = json.dumps(name)
    body = "\n".join(made["material"])
    if made["shader"] is None:
        text = _STANDARD % {"name": said, "fields": body}
    else:
        shader = out.with_suffix(".gdshader")
        shader.write_text(made["shader"], encoding="utf-8", newline="\n")
        written.append(shader)
        place = shader.resolve().relative_to(Path(root).resolve()).as_posix()
        text = _SHADED % {"name": said, "shader": f"res://{place}", "fields": body}
    out.write_text(text, encoding="utf-8", newline="\n")
    return [out, *written]


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
