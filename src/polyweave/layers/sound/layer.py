"""What the sound layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer, Subject

LAYER = Layer(
    name="sound",
    summary="Sound held to a spec: seeded effects, scored music, bought clips.",
    modules=(
        "polyweave.layers.sound.music",
        "polyweave.layers.sound.music_render",
        "polyweave.layers.sound.sfx",
        "polyweave.layers.sound.sound",
        "polyweave.layers.sound.sound_buy",
        "polyweave.layers.sound.sound_loop",
    ),
    judges=(
        Judge(
            name="heard",
            about="a sound laid out by sound.sitting is kept in its own record",
            claims=lambda member: bool(member.get("sound")),
            target="polyweave.layers.sound.sound:judged",
        ),
    ),
    kinds=("sound",),
    subjects=(
        Subject(
            about="a sound's loudness, peak, length and loop seam",
            measures="polyweave.layers.sound.sound:SOUNDS",
            target="polyweave.layers.sound.sound:predicate",
        ),
    ),
    parts={
        "brief.read:music": "polyweave.layers.sound.page:music",
    },
    codes="polyweave.layers.sound.codes",
)
