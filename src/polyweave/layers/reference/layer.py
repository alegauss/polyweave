"""What the reference layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="reference",
    summary="Reference videos and paintings, read for what a game copies.",
    modules=(
        "polyweave.layers.reference.reference",
        "polyweave.layers.reference.reference_compare",
        "polyweave.layers.reference.reference_concept",
        "polyweave.layers.reference.reference_events",
        "polyweave.layers.reference.reference_objects",
        "polyweave.layers.reference.reference_regions",
        "polyweave.layers.reference.reference_register",
        "polyweave.layers.reference.reference_transcription",
    ),
)
