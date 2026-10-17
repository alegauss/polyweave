"""Moulded plastic: a coat, a sheen, a rim and light under the skin (§PW494, §PW495)."""

from __future__ import annotations

from .. import finish
from . import Look

LOOK = Look(
    name="finish",
    asks=finish.ASKS,
    asked=lambda material: bool(finish.asked(material)),
    says=finish.says,
    bake=finish.inputs,
    godot=finish.write_godot,
)
