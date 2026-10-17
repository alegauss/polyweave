"""What the engine layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Subject

LAYER = Layer(
    name="engine",
    summary="The running game: Godot driven, captured, timed and tested.",
    modules=(
        "polyweave.layers.engine.capture",
        "polyweave.layers.engine.contrast",
        "polyweave.layers.engine.driving",
        "polyweave.layers.engine.engine",
        "polyweave.layers.engine.flashes",
        "polyweave.layers.engine.frame_cost",
        "polyweave.layers.engine.godot",
        "polyweave.layers.engine.integrity",
        "polyweave.layers.engine.offscreen",
        "polyweave.layers.engine.pack",
        "polyweave.layers.engine.perf",
        "polyweave.layers.engine.port",
        "polyweave.layers.engine.presets",
        "polyweave.layers.engine.pressure",
        "polyweave.layers.engine.runs",
        "polyweave.layers.engine.states",
        "polyweave.layers.engine.tables",
        "polyweave.layers.engine.testing",
    ),
    requires=("godot",),
    kinds=("capture",),
    ships="polyweave.layers.engine.driving:ships",
    subjects=(
        Subject(
            about="the flashes of a captured run",
            measures="polyweave.layers.engine.flashes:FLASHES",
            target="polyweave.layers.engine.flashes:predicate",
        ),
    ),
    pictures={
        key: "polyweave.layers.engine.contrast:picture_measure"
        for key in (
            "contrast_min", "contrast_median", "delta_e_min", "text_contrast_min",
        )
    },
    codes="polyweave.layers.engine.codes",
)
