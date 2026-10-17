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
    config="polyweave.layers.engine.settings",
    tools=29_000,
    census={
        "polyweave.layers.engine.port:read": (
            "internal", "a family file checked, inside port.run"),
        "polyweave.layers.engine.port:port": (
            "internal", "port.run with its renderer as a test hook"),
        "polyweave.layers.engine.contrast:targets_in": (
            "internal", "the targets a log's lines name"),
        "polyweave.layers.engine.contrast:contrasts": (
            "internal", "each target against its ring"),
        "polyweave.layers.engine.states:machines": (
            "internal", "each enum state machine in a script"),
        "polyweave.layers.engine.states:held": (
            "internal", "one machine's unreachable and stuck states"),
        "polyweave.layers.engine.presets:combinations": (
            "internal", "every grid combination to run"),
        "polyweave.layers.engine.presets:choose": (
            "internal", "each preset's run within its budget"),
        "polyweave.layers.engine.perf:held": (
            "internal", "a run's measures against budget and baseline"),
        "polyweave.layers.engine.tables:schema": (
            "internal", "every table a project declares"),
        "polyweave.layers.engine.tables:rows": (
            "internal", "one table file's rows and lines"),
        "polyweave.layers.engine.tables:check_table": (
            "internal", "one table's rows held to it"),
        "polyweave.layers.engine.tables:generated": (
            "internal", "the typed script a table loads by"),
        "polyweave.layers.engine.testing:declared": (
            "internal", "a project's test convention"),
        "polyweave.layers.engine.testing:read": (
            "internal", "one test run's counts and failures"),
        "polyweave.layers.engine.integrity:scan": ("internal", "the tree read as text"),
        "polyweave.layers.engine.runs:declared": (
            "internal", "each [run.<name>], checked"),
        "polyweave.layers.engine.pack:files_in": (
            "internal", "a pack's file table; game.pack"),
        "polyweave.layers.engine.pack:source_of": (
            "internal", "an imported file's source; game.pack"),
        "polyweave.layers.engine.integrity:parsed": (
            "internal", "every script parsed after an import"),
        "polyweave.layers.engine.flashes:count": (
            "internal", "each kind's worst second over frames"),
        "polyweave.layers.engine.flashes:measured": (
            "internal", "what a flashes bound reads"),
        "polyweave.layers.engine.driving:left_out": (
            "internal", "why the export leaves a path out"),
        "polyweave.layers.engine.capture": (
            "internal", "the environment's parts, inside capture.run"),
        "polyweave.layers.engine.driving": (
            "internal", "the socket call every game.* operation makes"),
        "polyweave.layers.engine.engine": (
            "internal", "run with its launch hook, behind engine.run"),
        "polyweave.layers.engine.offscreen": (
            "internal", "a route as an object; offscreen.routes"),
        "polyweave.layers.engine.contrast:picture_measure": (
            "internal", "contrast as a picture measure, for measure"),
        "polyweave.layers.engine.flashes:predicate": (
            "internal", "a flash predicate, for accept.check"),
    },
)
