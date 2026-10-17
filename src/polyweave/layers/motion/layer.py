"""What the motion layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="motion",
    summary="Clips, cameras and skeletons, baked to what a game plays.",
    modules=(
        "polyweave.layers.motion.camera",
        "polyweave.layers.motion.clip",
        "polyweave.layers.motion.motion",
        "polyweave.layers.motion.skeleton",
        "polyweave.layers.motion.sprites",
    ),
    requires=("blender",),
    kinds=("camera",),
    codes="polyweave.layers.motion.codes",
    config="polyweave.layers.motion.settings",
)
