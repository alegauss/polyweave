"""What the words layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer

LAYER = Layer(
    name="words",
    summary="The text a player reads, held to the world it is set in.",
    modules=(
        "polyweave.layers.words.words",
        "polyweave.layers.words.world",
    ),
    judges=(
        Judge(
            name="line",
            about="a line of text laid out by words.sheet is kept in the lines canon",
            claims=lambda member: bool(member.get("line")) and not member.get("sound"),
            target="polyweave.layers.words.words:judged",
        ),
    ),
    staleness={
        "words": "polyweave.layers.words.words:still",
        "world": "polyweave.layers.words.world:still",
    },
    parts={
        "brief.read:line": "polyweave.layers.words.page:read",
    },
)
