"""What the store layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="store",
    summary="What a game shows outside itself: store art, teasers, icons, sheets.",
    modules=(
        "polyweave.layers.store.compose",
        "polyweave.layers.store.icons",
        "polyweave.layers.store.store",
        "polyweave.layers.store.video",
    ),
)
