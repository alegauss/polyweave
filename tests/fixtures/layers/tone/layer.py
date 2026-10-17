from polyweave.kernel.layer import Judge, Layer, Producer, Subject

LAYER = Layer(
    name="tone",
    summary="A fixture medium: a sine tone made from a declaration.",
    modules=("polyweave.layers.tone.make",),
    tools=1_500,
    codes="polyweave.layers.tone.codes",
    config="polyweave.layers.tone.settings",
    kinds=("tone",),
    staleness={"tone-source": "polyweave.layers.tone.reads:still"},
    outdated={"tone": "polyweave.layers.tone.reads:behind"},
    subjects=(
        Subject(
            about="a tone's wav",
            measures="polyweave.layers.tone.reads:MEASURES",
            target="polyweave.layers.tone.reads:predicate",
        ),
    ),
    producers=(
        Producer(
            name="tone",
            about="a tone at a pitch",
            target="polyweave.layers.tone.reads:sample",
        ),
    ),
    judges=(
        Judge(
            name="tone",
            about="a tone's verdict is kept in tone.verdicts.json",
            claims=lambda member: "hz" in member,
            target="polyweave.layers.tone.reads:judged",
        ),
    ),
    parts={
        "brief:tone": "polyweave.layers.tone.reads:briefed",
        "report:tone": "polyweave.layers.tone.reads:reported",
        "review:tone": "polyweave.layers.tone.reads:shown",
    },
    census={
        "polyweave.layers.tone.reads": ("internal", "what the shared surfaces call"),
        "polyweave.layers.tone.wave": ("internal", "writes a tone and reads it back"),
    },
)
