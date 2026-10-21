"""What the motion layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="motion",
    uses=("engine", "geometry", "store", "vfx",),
    summary="Clips, cameras and skeletons, baked to what a game plays.",
    modules=(
        "polyweave.layers.motion.camera",
        "polyweave.layers.motion.clip",
        "polyweave.layers.motion.motion",
        "polyweave.layers.motion.skeleton",
        "polyweave.layers.motion.sprites",
        "polyweave.layers.motion.timeline",
    ),
    requires=("blender",),
    kinds=("camera", "timeline"),
    codes="polyweave.layers.motion.codes",
    config="polyweave.layers.motion.settings",
    # 7,104 with clip.shots, each camera shot framed in the running game (§PW372).
    # Raised with clip.timeline, a scene's own properties keyed and built (§PW554).
    # 8,088 once clip.shots stands up a clip the game is not playing (§PW591).
    tools=8_400,
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
        "polyweave.layers.motion.camera:moments": (
            "internal", "the moment of each shot clip.shots frames"),
        "polyweave.layers.motion.clip": (
            "internal", "compiling needs a mesh and a rig: motion.bake"),
        "polyweave.layers.motion.skeleton": (
            "internal", "fitting a mesh in memory: motion.bake"),
        "polyweave.layers.motion.sprites": (
            "internal", "baking needs a mesh and a rig: motion.bake"),
    },
)
