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
    parts={
        "brief.read:vfx": "polyweave.layers.vfx.page:read",
    },
    codes="polyweave.layers.vfx.codes",
    tools=1_600,
    census={
        "polyweave.layers.vfx.vfx:checked": (
            "internal", "an effect's table, with defaults"),
        "polyweave.layers.vfx.vfx:measured": (
            "internal", "an effect's measures from its declaration"),
        "polyweave.layers.vfx.vfx:scene": (
            "internal", "an effect as the Godot scene build writes"),
        "polyweave.layers.vfx.vfx:measures_of": (
            "internal", "a built effect's measures, for accept"),
        "polyweave.layers.vfx.vfx:declared": (
            "internal", "one effect, or one made of parts"),
        "polyweave.layers.vfx.vfx:measured_whole": (
            "internal", "a whole's measures, over its parts"),
        "polyweave.layers.vfx.vfx:scene_whole": (
            "internal", "a whole's scene, its parts under one"),
        "polyweave.layers.vfx.vfx:shipped_folder": (
            "internal", "where a built scene lands, shipped"),
        "polyweave.layers.vfx.vfx:settle_rate": (
            "internal", "a struck piece's decay, from its life"),
        "polyweave.layers.vfx.vfx:swing": (
            "internal", "a struck piece's swing at an age"),
        "polyweave.layers.vfx.page": ("internal", "an effect, for asset.brief"),
        "polyweave.layers.vfx.vfx:predicate": (
            "internal", "an effect predicate, for accept.check"),
    },
)
