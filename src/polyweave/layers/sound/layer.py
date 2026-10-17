"""What the sound layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer, Subject

LAYER = Layer(
    name="sound",
    uses=("words",),
    summary="Sound held to a spec: seeded effects, scored music, bought clips.",
    modules=(
        "polyweave.layers.sound.music",
        "polyweave.layers.sound.music_render",
        "polyweave.layers.sound.sfx",
        "polyweave.layers.sound.sound",
        "polyweave.layers.sound.sound_buy",
        "polyweave.layers.sound.sound_loop",
    ),
    judges=(
        Judge(
            name="heard",
            about="a sound laid out by sound.sitting is kept in its own record",
            claims=lambda member: bool(member.get("sound")),
            target="polyweave.layers.sound.sound:judged",
        ),
    ),
    kinds=("sound",),
    subjects=(
        Subject(
            about="a sound's loudness, peak, length and loop seam",
            measures="polyweave.layers.sound.sound:SOUNDS",
            target="polyweave.layers.sound.sound:predicate",
        ),
    ),
    parts={
        "brief.read:music": "polyweave.layers.sound.page:music",
    },
    codes="polyweave.layers.sound.codes",
    config="polyweave.layers.sound.settings",
    tools=11_000,
    census={
        "polyweave.layers.sound.sound": (
            "internal", "what sound.measure and a sound bound read"),
        "polyweave.layers.sound.music": (
            "internal", "the notation and compiler music.validate calls"),
        "polyweave.layers.sound.music_render": (
            "internal", "the engines and the mix music.render runs"),
        "polyweave.layers.sound.sfxr": (
            "internal", "sfxr's synth and generators, for sound.synth"),
        "polyweave.layers.sound.sfx:kit": (
            "internal", "a chip kit's hits, made for music.render"),
        "polyweave.layers.sound.page": ("internal", "a music cue, for asset.brief"),
        "polyweave.layers.sound.licences": (
            "internal", "the instruments a sound's record names"),
        "polyweave.layers.sound.sound_buy:language_of": (
            "internal", "voice.lines' language_code"),
        "polyweave.layers.sound.sfx:hz": ("internal", "a note name as Hz"),
        "polyweave.layers.sound.sfx:tuned": (
            "internal", "an effect's notes as sfxr's numbers"),
        "polyweave.layers.sound.sound:note_of": (
            "internal", "a pitch as its nearest note"),
    },
)
