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

from ..errors import PolyweaveError

__all__ = ["ASKS", "asked", "inputs", "says"]

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
