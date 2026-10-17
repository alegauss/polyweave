"""What the vfx layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Subject

LAYER = Layer(
    name="vfx",
    summary="Visual effects declared, built into what the engine plays.",
    modules=(
        "polyweave.layers.vfx.vfx",
    ),
    kinds=("vfx",),
    subjects=(
        Subject(
            about="a built effect, as its record says",
            measures="polyweave.layers.vfx.vfx:EFFECTS",
            target="polyweave.layers.vfx.vfx:predicate",
        ),
    ),
)
