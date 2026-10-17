"""What the engine layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

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
)
