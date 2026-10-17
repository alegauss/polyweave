"""What the sound layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

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
)
