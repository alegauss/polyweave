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
    codes="polyweave.layers.words.codes",
    config="polyweave.layers.words.settings",
    tools=3_000,
    census={
        "polyweave.layers.words.svgtext:texts": (
            "internal", "every <text> in an SVG (§PW453)"),
        "polyweave.layers.words.svgtext:outlined": (
            "internal", "an SVG's live text replaced by glyph outlines (§PW453)"),
        "polyweave.layers.words.page": ("internal", "a line, for asset.brief"),
        "polyweave.layers.words.world:find": (
            "internal", "which world file, inside world.read"),
        "polyweave.layers.words.world:declared": (
            "internal", "the parsed world, for words.check"),
        "polyweave.layers.words.world:brief": (
            "internal", "one entity, for a purchase's entity="),
        "polyweave.layers.words.world:described": (
            "internal", "an entity's look as a prompt"),
        "polyweave.layers.words.world:look_digest": (
            "internal", "what a purchase records it drew"),
        "polyweave.layers.words.world:still_drawn": (
            "internal", "provenance.outdated, per entity"),
        "polyweave.layers.words.world:still": (
            "internal", "the world role's staleness check"),
        "polyweave.layers.words.world:voice_in": (
            "internal", "a locale's voice over the shared one"),
        "polyweave.layers.words.world:voice_digest": (
            "internal", "what a spoken line records"),
        "polyweave.layers.words.world:voiced": (
            "internal", "sound.speak's entity, read once"),
        "polyweave.layers.words.world:keep_voice": (
            "internal", "voice.choose's one write"),
        "polyweave.layers.words.words:said_digest": (
            "internal", "what a spoken take records"),
        "polyweave.layers.words.words:characters": (
            "internal", "a font's character map"),
        "polyweave.layers.words.words:still_said": (
            "internal", "provenance.outdated, per row"),
        "polyweave.layers.words.words:still": (
            "internal", "the words role's staleness check"),
        "polyweave.layers.words.words:table": (
            "internal", "the string table, inside words.check"),
        "polyweave.layers.words.words:held": (
            "internal", "every verdict on a line, oldest first"),
        "polyweave.layers.words.words:verdicts": (
            "internal", "the latest verdict on each line"),
        "polyweave.layers.words.words:approved": (
            "internal", "a speaker's canon, in world.read"),
        "polyweave.layers.words.words:judged": (
            "internal", "verdict.judge is the one caller"),
    },
)
