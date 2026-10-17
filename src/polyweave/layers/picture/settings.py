"""The picture layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "style": {
        # What a project's pictures look like, declared once and never in the plugin:
        # two games have two looks (§PW166). `[style.<family>]` gives each asset family
        # its own, so a sprite sheet is never held to a title screen's canon.
        # The directory of pictures a person approved; only a verdict adds to it.
        "canon": "",
        # Globs under the project of pictures a person may admit to the canon from the
        # review page without a gate run (§PW266): key art and wordmarks have no
        # outline to gate, and they are what a brand's canon starts from.
        "candidates": [],
        # The colours a picture may use, as #rrggbb values rather than names.
        "palette": [],
        # The style block every structured prompt starts from, as the service spells
        # it: medium, lighting, aesthetics. It wins over a prompt that says otherwise.
        "skeleton": {},
        # Canon pictures, by file name, sent with every picture of the family as style
        # references (§PW180). Only Ideogram 3.0 takes one, with a text prompt, so a
        # family that names any draws on 3.0 with its skeleton and palette in the words.
        "references": [],
        # The grid a picture of this family is put on when it arrives (§PW171): the
        # cell in pixels as [width, height], empty to leave the size alone; the margin
        # inside it; where the subject sits, `centre` for an icon and `base` for what
        # stands on the ground; and the filter, `smooth` for painted art and `pixel` for
        # pixel art, which is never smoothed and is quantised to the palette.
        "cell": [],
        "margin": 0,
        "anchor": "centre",
        "filter": "smooth",
        # A palette kept in code (§PW387): `{ file = "tools/art/palette.py", names =
        # ["PIPING", ...] }` reads each `NAME = "#rrggbb"` the file holds, in the order
        # named, or every one in the file's order where `names` is empty.
        "palette_source": {},
        # Another project's palette, borrowed rather than copied (§PW387): `{ root =
        # "../cottony", family = "", lightness = -0.1, saturation = 0.0, pinned = "" }`.
        # Its resolved palette is shifted in lightness and saturation for this game,
        # and `pinned`, the source palette's digest when it was last looked at, makes
        # a source that moved since say so.
        "borrow": {},
        # A family of meshes is measured through renders at one rig (§PW451):
        # render.bake's camera and light settings (azimuth, elevation, margin, key,
        # rung...) and `seen`, the width in pixels a player sees one at.
        "rig": {},
    },
}

#: Tables that hold one thing, or several named ones.
NAMED = ("style",)

#: Settings in a named table whose value is itself a table.
SETTINGS = ("skeleton", "palette_source", "borrow", "rig",)

#: Settings whose value is one of a few words.
CHOICES = {
    "anchor": ('centre', 'base'),
    "filter": ('smooth', 'pixel'),
}
