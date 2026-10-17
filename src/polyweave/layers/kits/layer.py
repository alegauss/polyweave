"""What the kits layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="kits",
    summary="Parts every game repeats, made once, proved and installed.",
    modules=(
        "polyweave.layers.kits",
    ),
    requires=("godot",),
    outdated={"kits": "polyweave.layers.kits:behind"},
    codes="polyweave.layers.kits.codes",
    config="polyweave.layers.kits.settings",
    tools=2_000,
    census={
        "polyweave.layers.kits:read": ("internal", "one kit.toml, checked"),
        "polyweave.layers.kits:every": (
            "internal", "every kit the plugin carries, checked"),
        "polyweave.layers.kits:behind": ("internal", "provenance.outdated's kits"),
    },
)
