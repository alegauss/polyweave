"""The words layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "words": {
        # The text a player reads, as the game reads it (§PW197): Godot's translation
        # CSV, one key per row and one column per locale. A column whose header starts
        # with an underscore is one Godot skips, and `speaker` names the one that says
        # who speaks the line, as an entity id of the world.
        "table": "",
        "speaker": "_speaker",
        # Where a spoken take of a row lands, `audio/voice/{locale}/{key}.ogg` (§PW322):
        # one file per key and locale, in the format its suffix names.
        "voiced": "",
        # The fonts the game draws its lines with (§PW335): each `{ path, keys }`,
        # `keys` the glob patterns of the rows it draws, every row where unset.
        "fonts": [],
        # Capitalised words that are not names, such as START on a title screen, so the
        # name check passes over them.
        "ordinary": [],
        # The ordinary words of one locale alone, `{ pt_BR = ["VIDAS", ...] }`
        # (§PW329), so a word another language writes in capitals is not read as a
        # name there, and an English column cannot lean on it.
        "ordinary_in": {},
        # The copy a buyer reads before the game, held to the same names (§PW419): a
        # Markdown or HTML file under the project and the locale it is written in,
        # `{ "art/store/page.md" = "en", "art/store/page.pt-BR.md" = "pt_BR" }`.
        "copy": {},
        # Where a person's verdicts on lines are kept, as JSON (§PW199): the approved
        # ones are the lines canon, and only `verdict.judge` writes it.
        "canon": "",
    },
}
