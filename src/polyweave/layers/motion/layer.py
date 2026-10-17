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
    tools=6_500,
    census={
        "polyweave.layers.motion.camera:checked": (
            "internal", "a camera clip's table, with defaults"),
        "polyweave.layers.motion.camera:measured": (
            "internal", "a camera clip's measures"),
        "polyweave.layers.motion.camera:scene": (
            "internal", "a camera clip as the scene build writes"),
        "polyweave.layers.motion.camera:eased": (
            "internal", "a drift's easing, as the scene eases it"),
        "polyweave.layers.motion.camera:shot_at": (
            "internal", "the shot showing at a moment"),
        "polyweave.layers.motion.camera:at": (
            "internal", "the camera at a moment, as the scene frames"),
        "polyweave.layers.motion.clip": (
            "internal", "compiling needs a mesh and a rig: motion.bake"),
        "polyweave.layers.motion.skeleton": (
            "internal", "fitting a mesh in memory: motion.bake"),
        "polyweave.layers.motion.sprites": (
            "internal", "baking needs a mesh and a rig: motion.bake"),
    },
)
