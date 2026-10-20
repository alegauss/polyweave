"""What a material asks for beyond its colour, one module per look (§PW515).

A material states a colour and a roughness; a look is an intent on top of them, such as
a moulded-plastic finish or a fuzz, each stated in a few numbers. A look says which keys
it reads, what it makes of them for the bake's shader, what it writes for the engine,
and how the review sheet says it. The bake, the mesh writer and the review iterate over
the looks, so a toon ramp or brushed metal is one new module, not a branch in each.
"""

from __future__ import annotations

import functools
import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Look:
    name: str
    #: The material keys this look reads, which no other look may read.
    asks: tuple[str, ...]
    #: `(material) -> bool`: whether a material asks for this look at all.
    asked: Callable[[Any], bool]
    #: `(material) -> str`: the look in the review sheet's words, "" where not asked.
    says: Callable[[Any], str]
    #: `(material) -> dict`: the material as the bake's shader takes it, this look's
    #: keys turned into the sockets they stand for; None where the bake has nothing
    #: to do with it.
    bake: Callable[[dict], dict] | None = None
    #: `(material, name, folder, stem, root) -> list`: the engine's own material files
    #: for a look glTF cannot carry; None where the engine needs nothing more.
    godot: Callable | None = None

    @property
    def targets(self) -> tuple[str, ...]:
        """Which targets this look reaches, so one it cannot is said, never dropped."""
        return tuple(one for one in ("bake", "godot") if getattr(self, one) is not None)


#: The order the review sheet says looks in.
ORDER = ("fuzz", "finish")


@functools.cache
def every() -> dict[str, Look]:
    """Every look this folder holds, by name, in the order the sheet says them."""
    found = {}
    for one in pkgutil.iter_modules(__path__):
        if one.name.startswith("_"):
            continue
        declared = importlib.import_module(f"{__name__}.{one.name}").LOOK
        found[declared.name] = declared
    return {name: found[name] for name in ORDER if name in found} | {
        name: look for name, look in found.items() if name not in ORDER}


def baked(material: dict) -> dict:
    """A material as the bake's shader takes it: each look it asks for expanded."""
    out = dict(material)
    for look in every().values():
        if look.bake is not None:
            out = look.bake(out)
    return out


def for_godot(material: Any) -> list[str]:
    """The looks a material asks for that write the engine's own files, by name."""
    return [name for name, look in every().items()
            if look.godot is not None and look.asked(material)]


def godot(material: Any, name: str, folder: Any, stem: str, root: Any) -> list:
    """The engine's material files for each look a material asks for that glTF drops."""
    return [
        path
        for look in every().values()
        if look.godot is not None and look.asked(material)
        for path in look.godot(material, name, folder, stem, root)
    ]


def says(material: Any) -> list[str]:
    """Each look a material asks for, in the review sheet's words."""
    return [said for look in every().values() if (said := look.says(material))]
