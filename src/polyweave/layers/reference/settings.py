"""The reference layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "reference": {
        # A reference video's fixed places, declared once (§PW380): `[reference.<name>]`
        # per video or game, as rectangles [left, top, right, bottom] in pixels of the
        # source frame `size` was read at, so a call names a region and never repeats
        # numbers, and frames of another size are refused rather than misread.
        "size": [],
        "regions": {},
        # The region that is a minimap, and its shape: `strip`, a band whose left and
        # right edges meet (a cylinder seen whole), or `rect`, a flat level from above.
        "minimap": "",
        "map": "strip",
        # The player's blip colour, which every other blip is measured from, and each
        # other blip by name and #rrggbb colour; nothing about a game is known here.
        "player": "",
        "blips": {},
        "tolerance": 0.15,
        # The pixels of the source frame one blip covers, least and most.
        "blip_size": [1, 64],
    },
}

#: Tables that hold one thing, or several named ones.
NAMED = ("reference",)

#: Settings in a named table whose value is itself a table.
SETTINGS = ("regions", "blips",)

#: Settings whose value is one of a few words.
CHOICES = {
    "map": ('strip', 'rect'),
}
