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
    tools=11_000,
    census={
        "polyweave.layers.reference.reference_concept:concept_value": (
            "internal", "one concept measure, which accept.check reads"),
        "polyweave.layers.reference.reference_objects:declared": (
            "internal", "the kinds, checked"),
        "polyweave.layers.reference.reference_events:flashes": (
            "internal", "the frames that spike"),
        "polyweave.layers.reference.reference_compare:counted": (
            "internal", "objects per frame, by second"),
        "polyweave.layers.reference.reference_transcription:read": (
            "internal", "a sheet, as written"),
        "polyweave.layers.reference.reference_transcription:checked": (
            "internal", "its rows' citations"),
        "polyweave.layers.reference.reference_transcription:judged": (
            "internal", "a row's answer, kept"),
        "polyweave.layers.reference.reference_compare:nearest": (
            "internal", "the nearest second's index"),
        "polyweave.layers.reference.reference_compare:declared_at": (
            "internal", "a wave's alive, a second"),
        "polyweave.layers.reference.reference_events:onsets": (
            "internal", "the soundtrack's onsets"),
        "polyweave.layers.reference.reference_events:numbers": (
            "internal", "the numbers read, changed"),
        "polyweave.layers.reference.reference_events:drawn": (
            "internal", "the timeline as a picture"),
        "polyweave.layers.reference.reference_events:soundtrack": (
            "internal", "a video's sound, decoded"),
        "polyweave.layers.reference.reference_events:sections": (
            "internal", "where the music turns"),
        "polyweave.layers.reference.reference_events:thumbnailed": (
            "internal", "the timeline's frames"),
        "polyweave.layers.reference.reference_events:placed": (
            "internal", "an event's thumbnail"),
        "polyweave.layers.reference.reference_register:registered": (
            "internal", "the registry, by name"),
        "polyweave.layers.reference.reference_register:video_of": (
            "internal", "a named video, checked"),
        "polyweave.layers.reference.reference_objects:islands": (
            "internal", "a mask's islands, labelled"),
        "polyweave.layers.reference.reference_objects:detect": (
            "internal", "one frame's objects"),
        "polyweave.layers.reference.reference_objects:likeness": (
            "internal", "a crop against its samples"),
        "polyweave.layers.reference.reference_objects:tracked": (
            "internal", "detections joined to tracks"),
        "polyweave.layers.reference.reference_objects:formation": (
            "internal", "a group's rough shape"),
        "polyweave.layers.reference.reference_objects:grouped": (
            "internal", "tracks born together"),
        "polyweave.layers.reference.reference": (
            "internal", "the cut and its tests, inside .prepare"),
        "polyweave.layers.reference.reference_concept:predicate": (
            "internal", "a concept predicate, for accept.check"),
    },
)
