"""What the vfx layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="vfx",
    summary="Visual effects declared, built into what the engine plays.",
    modules=(
        "polyweave.layers.vfx.vfx",
    ),
    kinds=("vfx",),
)
