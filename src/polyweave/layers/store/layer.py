"""What the store layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Subject

LAYER = Layer(
    name="store",
    uses=("geometry", "picture",),
    summary="What a game shows outside itself: store art, teasers, icons, sheets.",
    modules=(
        "polyweave.layers.store.card",
        "polyweave.layers.store.compose",
        "polyweave.layers.store.footage",
        "polyweave.layers.store.icons",
        "polyweave.layers.store.safe",
        "polyweave.layers.store.store",
        "polyweave.layers.store.thumbnail",
        "polyweave.layers.store.video",
        "polyweave.layers.store.web",
    ),
    subjects=(
        Subject(
            about="a teaser video",
            measures="polyweave.layers.store.video:VIDEOS",
            target="polyweave.layers.store.video:predicate",
        ),
    ),
    parts={"contact.sheet": "polyweave.layers.store.compose:sheet"},
    codes="polyweave.layers.store.codes",
    # 4,353 once capture.web films a product video's browser scenes (§PW690).
    # 5,376 with video.buy, a clip bought from a Scenario video model (§PW692).
    # 6,331 with video.safe_area, burned-in text against a platform's controls (§PW698).
    # 7,149 with store.thumbnail, a thumbnail against its title and a feed (§PW699).
    # 8,102 with store.thumbnails, the passing variants laid for a person (§PW699).
    # 9,242 with capture.card, an HTML card rendered to a still (§PW700).
    tools=9_800,
    census={
        "polyweave.layers.store.video:measured": (
            "internal", "what a video bound reads, off the MP4"),
        "polyweave.layers.store.video:read": (
            "internal", "a cut's clips, checked; video.cut"),
        "polyweave.layers.store.store:thinnest": (
            "internal", "a logo's thinnest stroke at a scale"),
        "polyweave.layers.store.compose": (
            "internal", "the Image objects compose.place returns"),
        "polyweave.layers.store.icons:read": (
            "internal", "icons.build's declaration, resolved"),
        "polyweave.layers.store.icons:draw": ("internal", "one icon at one size"),
        "polyweave.layers.store.icons:legibility": (
            "internal", "what icons.build holds a set to"),
        "polyweave.layers.store.icons:model_legibility": (
            "internal", "what icons.build holds a model's icon to"),
        "polyweave.layers.store.web:read": (
            "internal", "a visit's steps, checked; capture.web"),
        "polyweave.layers.store.safe:read": (
            "internal", "an .ass file's styles and lines; video.safe_area"),
        "polyweave.layers.store.video:predicate": (
            "internal", "a video predicate, for accept.check"),
    },
)
