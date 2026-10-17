"""What the store layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Subject

LAYER = Layer(
    name="store",
    summary="What a game shows outside itself: store art, teasers, icons, sheets.",
    modules=(
        "polyweave.layers.store.compose",
        "polyweave.layers.store.icons",
        "polyweave.layers.store.store",
        "polyweave.layers.store.video",
    ),
    subjects=(
        Subject(
            about="a teaser video",
            measures="polyweave.layers.store.video:VIDEOS",
            target="polyweave.layers.store.video:predicate",
        ),
    ),
)
