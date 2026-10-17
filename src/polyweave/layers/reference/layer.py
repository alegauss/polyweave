"""What the reference layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer, Subject

LAYER = Layer(
    name="reference",
    summary="Reference videos and paintings, read for what a game copies.",
    modules=(
        "polyweave.layers.reference.reference",
        "polyweave.layers.reference.reference_compare",
        "polyweave.layers.reference.reference_concept",
        "polyweave.layers.reference.reference_events",
        "polyweave.layers.reference.reference_objects",
        "polyweave.layers.reference.reference_regions",
        "polyweave.layers.reference.reference_register",
        "polyweave.layers.reference.reference_transcription",
    ),
    judges=(
        Judge(
            name="row",
            about="a transcription row is kept in the answers beside its sheet",
            claims=lambda member: bool(member.get("transcription")),
            target="polyweave.layers.reference.reference_transcription:judged",
        ),
    ),
    subjects=(
        Subject(
            about="a capture against the concept painting it copies",
            measures="polyweave.layers.reference.reference_concept:CONCEPTS",
            target="polyweave.layers.reference.reference_concept:predicate",
        ),
    ),
    config="polyweave.layers.reference.settings",
)
