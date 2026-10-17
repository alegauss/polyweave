"""What the words layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="words",
    summary="The text a player reads, held to the world it is set in.",
    modules=(
        "polyweave.layers.words.words",
        "polyweave.layers.words.world",
    ),
)
