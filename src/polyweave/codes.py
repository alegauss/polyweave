"""Every error code this plugin publishes, declared once.

`docs/specs/tool-surface.md` §3: a code is a stable string and part of the contract.
That only means something if the set of them can be read without grepping the source, so
the whole set is here, and `PolyweaveError` refuses a code this table does not declare.

The division of labour: **`doors` here are the general shape of the fix**, and the
`remedy` on a raised error is the specific one, with the arguments filled in. A caller
answering a failure reads the remedy; a caller planning for one reads this.

This module imports nothing from the package. `errors.explain` is the public read, and
it lives there so the lookup can refuse in the same shape as everything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .doors import Blank, door


@dataclass(frozen=True)
class Code:
    means: str
    when: str
    doors: tuple[str, ...] = field(default_factory=tuple)
    #: The doors that are calls, as data a test parses (§PW127).
    calls: tuple[dict, ...] = field(default_factory=tuple)


#: What each area is about, so an unknown code can at least be placed.
AREAS: dict[str, str] = {
    "render": "producing a picture from a scene",
    "mesh": "building or transforming geometry",
    "fetch": "asking the paid service for something",
    "post": "what an operation asserts about its own output",
    "config": "resolving a value from a call, a project file or a default",
    "job": "long work held by a handle",
    "geom": "a shape declared as data",
    "spec": "an acceptance spec and its vocabulary",
    "op": "an operation's own arguments, against what it declared",
    "prov": "the record written beside an artefact, and the cache key it defines",
    "compose": "putting an asset where it will actually be seen",
    "search": "looking for parameter values that satisfy a spec",
    "engine": "running a scene script and reading its verdict",
    "units": "the scale an asset is baked at, against the one the engine draws it at",
    "capture": "the environment a picture of the running game is taken in",
    "rig": "fitting a skeleton to a mesh, and moving a pose between skeletons",
    "clip": "motion over time, as something with a name and a duration",
    "texture": "the pixels a service painted, and what has to come back out of them",
    "loop": "what one asset cost to make, each way",
}

CODES: dict[str, Code] = {
    # -- job: long work held by a handle ------------------------------------
    "job.unknown": Code(
        means="no job with that handle exists under this project's work directory",
        when="a poll, result or cancel names a handle that was never started, or one a "
        "sweep has already collected",
        doors=("list the jobs", "start the work again"),
    ),
    "job.unknown-kind": Code(
        means="the operation kind named has no stage vocabulary",
        when="a start passes a kind outside bake, capture, fetch and search",
        doors=("pass one of the declared kinds",),
    ),
    "job.unknown-stage": Code(
        means="the stage reported is not one this kind of job may reach",
        when="a target reports a stage belonging to another kind of operation",
        doors=("report a stage this kind declares",),
    ),
    "job.stage-terminal": Code(
        means="a target tried to declare itself finished",
        when="a target calls report.stage with done, failed or cancelled",
        doors=("return a value to finish", "raise to fail"),
    ),
    "job.bad-progress": Code(
        means="progress is a fraction of one and the value was outside it",
        when="a target reports a percentage or a count instead of a fraction",
        doors=("divide by the total before reporting",),
    ),
    "job.at-capacity": Code(
        means="as many jobs are already running as this project allows at once",
        when="a start would exceed [render] max_parallel",
        doors=(
            "wait for a running job",
            "cancel one",
            "raise [render] max_parallel",
        ),
    ),
    "job.not-finished": Code(
        means="the result was asked for while the job was still running",
        when="result is called without wait on a job that has not reached a terminal "
        "stage",
        doors=("poll it", "call result with wait"),
    ),
    "job.timeout": Code(
        means="the job did not finish inside the time the caller allowed",
        when="result waits past its timeout; the job is untouched and still running",
        doors=("poll it", "wait again with a longer timeout", "cancel it"),
    ),
    "job.worker-gone": Code(
        means="the process doing the work is no longer running and left no result",
        when="a poll or a sweep finds the process id dead, or alive with a heartbeat "
        "that stopped moving, which is how a reused id is caught",
        doors=("read the job's log", "start the work again"),
    ),
    "job.schema": Code(
        means="the job record was written by another version of this plugin",
        when="a handle survives an upgrade that changed the record's fields",
        doors=("delete the record", "start the work again"),
    ),
    "job.bad-target": Code(
        means="the target does not name a function",
        when="a start passes a target with no colon in it",
        doors=("write it as module:function or path/to/file.py:function",),
    ),
    "job.target-not-found": Code(
        means="the module, file or function the target names is not there",
        when="a misspelled target, or one whose directory the worker's path misses",
        doors=("check the spelling", "pass the directory as path"),
    ),
    "job.unknown-arg": Code(
        means="an argument was passed that the target does not take",
        when="a typo in an argument name; it is refused rather than dropped, or a typo "
        "would be indistinguishable from a working call",
        doors=("pass the arguments the target declares",),
    ),
    "job.target-failed": Code(
        means="the target raised something that was not already a typed failure",
        when="an exception inside the work, whose traceback is in detail and never in "
        "the message",
        doors=("read the job's log", "read the traceback in detail"),
    ),
    # -- mesh: building or transforming geometry ------------------------------
    "mesh.too-few-vertices": Code(
        means="there are not enough vertices to determine a frame",
        when="a normalisation of an empty or nearly empty mesh",
        doors=("check that the file imported",),
    ),
    "mesh.bad-frame": Code(
        means="a mesh was asked to be sized on an axis or held from an origin that "
        "does not exist",
        when="size_on other than height, length or longest, or origin other than base "
        "or centre",
        doors=("name one of the axes", "name one of the origins"),
    ),
    "mesh.degenerate": Code(
        means="the mesh is flat or collinear, so its own axes say nothing about which "
        "way it faces",
        when="a normalisation of a plane, a line, or a mesh with no height",
        doors=("orient it against a reference drawing", "state the rotation"),
    ),
    "mesh.ambiguous-forward": Code(
        means="every orientation matches the reference equally well",
        when="a symmetric mesh, or a reference that does not distinguish its front; "
        "guessing which way is forward is a judgement this does not make",
        doors=("give a reference that shows the front", "state the rotation"),
    ),
    # -- post: what an operation asserts about its own output ---------------
    "post.unknown-output": Code(
        means="nothing is asserted about that kind of output",
        when="a check names an output kind outside the declared set",
        doors=("name a declared output kind",),
    ),
    "post.unknown-field": Code(
        means="an expectation was passed that this check does not take",
        when="a typo in an expectation name",
        doors=("pass the expectations the check declares",),
    ),
    "post.unknown-check": Code(
        means="the optional assertion named does not exist",
        when="an opt-in check is asked for by a name nothing declares",
        doors=("name a declared optional assertion",),
    ),
    "post.check-misapplied": Code(
        means="the optional assertion does not apply to that kind of output",
        when="a mesh assertion is asked for on a picture, or the reverse",
        doors=("apply it to an output kind it covers",),
    ),
    "post.not-a-mesh": Code(
        means="the subject carries no vertices and faces",
        when="a mesh check is handed something that is not a mesh",
        doors=("pass a mesh, a mapping of vertices and faces, or a pair of the two",),
    ),
    "post.mesh-empty": Code(
        means="the operation produced a mesh with no faces",
        when="an operation that should have built geometry built none",
        doors=("check the operation's inputs before rendering anything",),
    ),
    "post.voxels-empty": Code(
        means="a voxel build filled no cells",
        when="a grid coarser than the smallest part, or a carve that took the whole "
        "shape away",
        doors=("make the cells smaller", "check what the carve cuts"),
    ),
    "post.mesh-nan": Code(
        means="vertices carry NaN coordinates, so the mesh has no position",
        when="a degenerate transform, or a normal of zero length",
        doors=("check the last modifier applied",),
    ),
    "post.mesh-unbounded": Code(
        means="vertices sit at infinity, so the mesh has no bounds to fit or frame",
        when="a division by a zero scale",
        doors=("check the scale of every operand",),
    ),
    "post.mesh-non-manifold": Code(
        means="edges are not each shared by exactly two faces",
        when="the opt-in manifold assertion runs on a mesh with holes or loose edges",
        doors=("close the holes", "drop the manifold assertion"),
    ),
    "post.bad-operands": Code(
        means="a boolean was checked against a number of operands that is not two",
        when="a boolean check is passed one operand, or three",
        doors=("pass the two meshes, or their two face counts",),
    ),
    "post.boolean-empty": Code(
        means="a boolean returned no faces although both operands had some",
        when="Blender's EXACT solver on a target bevelled first, which returns an "
        "empty mesh and raises nothing",
        doors=("bevel after the boolean", "switch the solver to FAST"),
    ),
    "post.render-size": Code(
        means="the render is not the size that was asked for",
        when="a renderer clamps or ignores a requested resolution",
        doors=("ask for the size again", "drop the size expectation"),
    ),
    "post.render-uniform": Code(
        means="every visible pixel of the render is one colour, so it carries no image",
        when="an empty scene, or a light that never fired",
        doors=("check the scene and the lighting",),
    ),
    "post.render-transparent": Code(
        means="every pixel of the render is below the alpha floor",
        when="the subject was outside the frame, or the camera never saw it",
        doors=("check the framing before spending another render",),
    ),
    "post.uv-mismatched": Code(
        means="a mesh's texture coordinates do not line up with its own vertices",
        when="an array one short, the wrong shape, or holding something that is not a "
        "number; a picture placed by one of those is on the wrong part of the shape "
        "from that vertex on, and nothing about the render says so",
        doors=(
            "give one pair per vertex, in the same order",
            "leave them off; most meshes carry none",
        ),
    ),
    "post.render-speck": Code(
        means="something is in the frame and it is too small to be worth judging",
        when="a camera that framed the subject far away or almost missed it; the two "
        "opaque pixels left behind clear the alpha floor and differ from each other, "
        "so neither the transparency nor the flatness check fires",
        doors=(
            "check the framing before spending another render",
            "lower [tolerance] subject_extent if the asset is really this small",
        ),
    ),
    "post.texture-size": Code(
        means="the texture is not the size that was asked for",
        when="a bake writes at a resolution other than the one requested",
        doors=("ask for the size again", "drop the size expectation"),
    ),
    "post.texture-uniform": Code(
        means="every visible pixel of the texture is one colour",
        when="a bake that found nothing to bake; a flat colour may also be intended",
        doors=("check what was baked", "allow a uniform texture deliberately"),
    ),
    "post.texture-transparent": Code(
        means="every pixel of the texture is below the alpha floor",
        when="a bake whose source had no coverage at all",
        doors=("check the UVs and the source",),
    ),
    "texture.not-pixels": Code(
        means="what was handed over is not a texture",
        when="an array that is not height x width x channels, where a scrub or a mark "
        "count was asked for",
        doors=("pass the texture as floats in 0..1, with at least three channels",),
    ),
    "post.tolerance-unstated": Code(
        means="a check that needs a tolerance was given none",
        when="a render, texture, field or capture check with no alpha_floor. It used "
        "to default to zero while the config declared 0.02, so a caller who forgot "
        "measured the background as part of the subject and got an answer rather "
        "than a refusal (§PW40)",
        doors=(
            "resolve it once with Config.tolerances() and pass it down",
            "state the floor this particular check should use",
        ),
    ),
    "post.field-size": Code(
        means="the field is not the size that was asked for",
        when="a bake writes at a resolution other than the one requested",
        doors=("ask for the size again", "drop the size expectation"),
    ),
    "post.field-shallow": Code(
        means="the file holds fewer bits per channel than the field needs",
        when="a renderer that wrote eight bits where sixteen were asked for. Distinct "
        "from post.field-quantised on purpose: this is the renderer writing too "
        "little, and the remedy is in the render settings",
        doors=(
            "ask the renderer for the depth the field needs",
            "lower the depth expected",
        ),
    ),
    "post.field-quantised": Code(
        means="the field holds too few distinct values to be the gradient it should be",
        when="a height field that went through an eight-bit buffer and came back a "
        "staircase (§PW38). Invisible in a shadow, ruinous under a specular, and "
        "every colour and coverage check passes it",
        doors=(
            "find the conversion between the renderer and the disk",
            "lower the levels expected, if this flat was intended",
        ),
    ),
    "post.capture-size": Code(
        means="the capture is not the size that was asked for",
        when="an engine window opens at a resolution other than the declared one",
        doors=("declare the resolution the engine actually uses",),
    ),
    "post.file-missing": Code(
        means="nothing exists at the path the operation said it wrote",
        when="an operation that reported success without writing anything",
        doors=("read the operation's log", "run it again"),
    ),
    "post.not-an-image": Code(
        means="the file is not in any image format this can read",
        when="a script printed an error where a picture was expected",
        doors=("read the file as text to see what was written instead",),
    ),
    "post.unreadable": Code(
        means="the image could not be read to the end",
        when="a file that is truncated, or still being written",
        doors=("run the operation again",),
    ),
    "post.download-length": Code(
        means="the bytes that arrived are not the number the response declared",
        when="a transfer that stopped early",
        doors=("download it again rather than reading it",),
    ),
    "post.download-digest": Code(
        means="the bytes do not hash to what was expected",
        when="a service serving something other than what it promised",
        doors=("download it again", "compare the two if it differs twice"),
    ),
    # -- op: an operation's arguments against what it declared ---------------
    "op.unknown": Code(
        means="no operation is registered under that name",
        when="a describe or a validate names an operation that does not exist",
        doors=("describe with no argument to list them",),
    ),
    "op.duplicate": Code(
        means="two operations were registered under one name",
        when="a module registers a name another module already took",
        doors=("rename one", "delete the one it shadows"),
    ),
    "op.undocumented": Code(
        means="the operation has no docstring, so describe has nothing to return",
        when="an operation is registered without a sentence saying what it does",
        doors=("write one sentence",),
    ),
    "op.unannotated": Code(
        means="a parameter does not say what it is for",
        when="a parameter carries no Param annotation and is not named in injects",
        doors=("annotate the parameter", "name it in injects"),
    ),
    "op.open-signature": Code(
        means="the operation takes *args or **kwargs, so its parameters are not a set",
        when="an operation is registered with an open signature",
        doors=("name every parameter",),
    ),
    "op.unknown-argument": Code(
        means="an argument was passed that the operation does not declare",
        when="a typo in an argument name",
        doors=("describe the operation to see what it takes",),
    ),
    "op.missing-argument": Code(
        means="a required argument was not passed",
        when="a call omits a parameter that has no default",
        doors=("pass the named argument",),
    ),
    "op.out-of-range": Code(
        means="a value falls outside the range the operation declared",
        when="a call passes a number the operation would refuse",
        doors=("pass a value inside the declared range",),
    ),
    "op.bad-choice": Code(
        means="a value is not one of the choices the operation declared",
        when="a call passes a word outside the declared set",
        doors=("pass one of the declared choices",),
    ),
    "op.bad-type": Code(
        means="a value is not the type the operation declared",
        when="a number arrives as a string, or the reverse",
        doors=("pass the declared type",),
    ),
    "op.bad-setting": Code(
        means="a value set on the command line does not name what it sets",
        when="a `--set` with no `=` in it, or nothing before it",
        doors=("write it as name=value",),
    ),
    # -- config: what a project declares, and how a value is resolved --------
    "config.malformed": Code(
        means="the project's config file could not be read as TOML",
        when="a syntax error in polyweave.toml, or a file that cannot be opened",
        doors=("fix the syntax the detail points at",),
    ),
    "config.unknown-table": Code(
        means="the config declares a table the plugin has no settings under",
        when="a misspelled table heading; it is refused rather than ignored, or a "
        "setting would read as in effect while it was not",
        doors=("name a declared table",),
    ),
    "config.unknown-key": Code(
        means="the config sets a key that is not a setting",
        when="a misspelled key, or one borrowed from another tool",
        doors=("name a declared key", "read the table to see what it takes"),
    ),
    "config.unknown-address": Code(
        means="the address asked for does not name a setting",
        when="a read of a table or key that the schema does not carry",
        doors=("list the addresses",),
    ),
    "config.bad-type": Code(
        means="a setting was given a value of the wrong type",
        when="a number written as a string, a table given a value, or a date that is "
        "not one",
        doors=("write the value as the declared type",),
    ),
    "config.path-outside": Code(
        means="a path setting points out of the project tree",
        when="an absolute path where only a binary may be absolute, or one that climbs "
        "out with ..",
        doors=("write the path relative to the project root",),
    ),
    "config.env-unset": Code(
        means="a setting names an environment variable that is not set here",
        when="a ${NAME} reference on a machine where NAME was never exported",
        doors=("set the variable", "write the value in the config instead"),
    ),
    # -- render: producing a picture from a scene -----------------------------
    "render.no-renderer": Code(
        means="Blender is not importable here, so nothing can render",
        when="the bpy module is not installed in the interpreter running the work",
        doors=("install bpy", "point [paths] blender at one that runs the worker"),
    ),
    "render.unknown-rung": Code(
        means="the rung named is not one of the three the ladder renders",
        when="a project renames a rung, or a caller misspells one",
        doors=("name sphere, preview or final",),
    ),
    "render.rung-disabled": Code(
        means="the question needs a rung this project does not enable",
        when="a measure that needs the real mesh on a project that enables only sphere",
        doors=("add the rung to [render] rungs", "ask a cheaper question"),
    ),
    "render.no-rungs": Code(
        means="the project enables no rungs at all",
        when="[render] rungs is empty",
        doors=("name some of sphere, preview and final",),
    ),
    "render.no-samples": Code(
        means="no sample count is declared for the rung being rendered",
        when="a project names a rung in [render] rungs and omits it from samples",
        doors=("set samples for that rung",),
    ),
    "render.placed-off-front": Code(
        means="a rectangle with a place was asked for from a camera not in front",
        when="covers given as [x0, y0, x1, y1] with a non-zero azimuth or elevation, "
        "where the corners would land wherever the turn put them",
        doors=("look straight on", "give covers as [width, height]"),
    ),
    "render.size-with-covers": Code(
        means="a size was asked for where a world rectangle already decides it",
        when="size given beside covers; the rectangle and its scale fix both axes",
        doors=("leave size out", "change pixels_per_unit instead"),
    ),
    "render.no-mesh": Code(
        means="the rung renders the real mesh and there is none to render",
        when="no model was named, the file is not there, or it imported empty",
        doors=("pass the model", "ask a question the sphere rung carries"),
    ),
    "render.unknown-format": Code(
        means="the mesh file is not in a format this reads",
        when="an .obj or another format where a .blend, glTF or FBX was expected",
        doors=("give it a .blend", "export as .glb, .gltf or .fbx"),
    ),
    "render.unknown-primitive": Code(
        means="the primitive named does not exist",
        when="a rung asks for a shape other than the sphere a surface is read on",
        doors=("use the sphere",),
    ),
    "render.bad-ratio": Code(
        means="a decimation ratio is not a fraction of one",
        when="a preview rung is given a ratio at or below zero, or above one",
        doors=("pass a ratio above 0 and at most 1",),
    ),
    "render.no-material": Code(
        means="this Blender has no standard shader to build a material on",
        when="a build without the Principled BSDF node",
        doors=("render with a Blender that ships the standard shader nodes",),
    ),
    "render.unknown-material-field": Code(
        means="a material names an input the shader does not have",
        when="a misspelled Principled BSDF socket, refused rather than dropped",
        doors=("name a socket the shader declares",),
    ),
    # -- compose: an asset where it will be seen ------------------------------
    "compose.no-tiles": Code(
        means="a contact sheet was asked for with nothing to put on it",
        when="an empty list of assets",
        doors=("pass the asset and the siblings it is seen beside",),
    ),
    "compose.unknown-anchor": Code(
        means="the anchor named is not one an asset can be placed by",
        when="a placement asking for something other than footprint or centre",
        doors=("anchor on the footprint, or on the centre",),
    ),
    "compose.outside": Code(
        means="the asset lands entirely outside the capture it was placed into",
        when="a position in the coordinates of a different capture, or of the asset",
        doors=("place it within the capture's own pixels",),
    ),
    # -- fetch: asking the paid service for something -------------------------
    "fetch.no-reference": Code(
        means="there is no drawing to check the returned shape against",
        when="a shape check with no reference, or one pointing at a path that is empty",
        doors=("point it at the drawing that asked for this shape",),
    ),
    "fetch.no-schema": Code(
        means="nothing is known about what this service accepts",
        when="a payload checked before the schema has been learned once",
        doors=("learn the schema by probing", "keep it in the project"),
    ),
    "fetch.schema-malformed": Code(
        means="the learned schema is not readable",
        when="a schema file edited into invalid TOML",
        doors=("fix the syntax", "learn the schema again"),
    ),
    "fetch.unknown-field": Code(
        means="the payload names a field the service does not have",
        when="a typo in a field name; the service would drop it in silence, so it is "
        "refused here instead",
        doors=("name a field the schema carries",),
    ),
    "fetch.missing-field": Code(
        means="the payload leaves out a field the service requires",
        when="a request that would be refused remotely for a reason known locally",
        doors=("pass the required field",),
    ),
    "fetch.bad-choice": Code(
        means="the value is not one the service was proved to accept for that field",
        when="a value outside the set a probe made the service print",
        doors=("pass one of the proved choices",),
    ),
    "fetch.no-task": Code(
        means="a purchase carries no task id, so nothing traces it to what was bought",
        when="a capture recorded without the service's own id for the task",
        doors=("pass the task id the service returned",),
    ),
    "fetch.unknown-purchase": Code(
        means="the kind of thing being bought is not one this records",
        when="a capture of something outside the declared set",
        doors=("name a declared kind of purchase",),
    ),
    "fetch.nothing-arrived": Code(
        means="there is nothing on disk to take delivery of",
        when="a capture whose transfer never completed",
        doors=("ask the service again before recording anything",),
    ),
    "fetch.budget-closed": Code(
        means="nothing may be spent, because no live budget says it may",
        when="a project with no [budget], an expired one, or one already used up; an "
        "absent ceiling is never read as permission",
        doors=("set credits and an expiry in the project config",),
    ),
    "fetch.over-budget": Code(
        means="the spend would pass the ceiling a person set",
        when="a fetch costing more than the credits left against [budget]",
        doors=("raise the ceiling", "ask for something that costs less"),
    ),
    "fetch.ledger-malformed": Code(
        means="the purchase ledger is not readable",
        when="a ledger edited by hand, or truncated",
        doors=("restore it from version control, where it belongs",),
    ),
    "fetch.background-fused": Code(
        means="the subject cannot be told apart from what it is standing on",
        when="a photograph whose background is not uniform enough to cut away, which "
        "the service would return as geometry",
        doors=("cut the subject out first", "photograph it against a plain ground"),
    ),
    "fetch.subject-small": Code(
        means="the subject fills too little of the frame to be read from",
        when="a photograph taken from far off, or one where the cut kept the wrong "
        "region",
        doors=("crop to the subject", "lower [tolerance] subject_coverage"),
    ),
    "fetch.shape-rejected": Code(
        means="what came back does not match the silhouette that was asked for",
        when="a generative service reinterpreting a shape: a wide low cap sent and a "
        "tall dome returned, which the check exists to catch before the credits go",
        doors=(
            "look at the picture beside the drawing",
            "ask again with a clearer reference",
        ),
    ),
    # -- search: looking for values that satisfy a spec -----------------------
    "search.nothing-to-search": Code(
        means="the spec names no parameter a search is permitted to turn",
        when="an acceptance spec with predicates and no search ranges; a parameter not "
        "named there is not searched, whatever an optimiser would like",
        doors=("add a search range for each parameter it may turn",),
    ),
    "search.no-evaluator": Code(
        means="a search was given no way to evaluate a sample, or two ways",
        when="both `evaluate` and `evaluate_all` are passed, or neither. They are not "
        "combined: one renders a sample at a time and the other hands a pass to "
        "four job handles at once (§PW45)",
        doors=(
            "pass `evaluate` for one sample at a time",
            "pass `evaluate_all` for a whole pass at once",
        ),
    ),
    "search.batch-mismatch": Code(
        means="a batched evaluator returned a different number of results than samples",
        when="an `evaluate_all` that dropped, added or reordered a sample. The results "
        "are matched to the samples by position, so a short list would attach a "
        "score to the wrong parameters",
        doors=("return one result per sample, in the order they were given",),
    ),
    "search.no-budget": Code(
        means="the search was given no renders to spend",
        when="a budget below one",
        doors=("give it a budget of at least one render",),
    ),
    "search.unknown-parameter": Code(
        means="the spec names a parameter the renderer has no knob for",
        when="a [search.<name>] the renderer cannot receive. Found adopting Cottony "
        "(§PW36): its rig calls the whole-rig scale `light` and the shape's weight "
        "`form`, and neither is a parameter here, so the search died on its first "
        "sample with a bare TypeError after the setup was already paid for",
        doors=(
            "rename the range to a parameter the renderer takes",
            "drop the range if nothing here turns it",
        ),
    ),
    "search.bad-family": Code(
        means="a family file cannot be ported as it is written",
        when="an unknown key, a rig that is neither searched nor given, no axes or "
        "values for it, no members, or a member without a name, spec, out and exactly "
        "one of model and declaration (§PW120)",
        doors=("fix the family file as the message says",),
    ),
    "search.noise-axis": Code(
        means="the spec asks a search to turn something that only moves the noise",
        when="a [search.seed], [search.samples] or [search.size]: the best sample "
        "would be whichever the noise favoured, which is fitting it (§PW107)",
        doors=("drop the range", "calibrate the bounds against that noise instead"),
        calls=(
            door("calibrate.run", spec=Blank("the spec"), accepted=Blank("the render")),
        ),
    ),
    # -- engine: running a scene script and reading its verdict ---------------
    "engine.not-found": Code(
        means="no engine binary could be found to run the script with",
        when="neither [paths] godot, nor $GODOT, nor PATH names one",
        doors=("set [paths] godot to the console build", "put it on PATH"),
    ),
    "engine.not-a-project": Code(
        means="the folder an addon was to go into is not a Godot project",
        when="a path one level off, or a project not yet created",
        doors=("point it at the folder holding project.godot",),
    ),
    "engine.unknown-addon": Code(
        means="no addon of that name ships with polyweave",
        when="a typo in the addon's name",
        doors=("name one the refusal lists",),
    ),
    "engine.no-script": Code(
        means="the scene script named does not exist",
        when="a path relative to somewhere other than the project root",
        doors=("write the path relative to the project root",),
    ),
    "engine.script-error": Code(
        means="the engine reported an error while the script ran",
        when="a parse error, a compile error, or a runtime error inside a block, "
        "any of which the engine can still exit zero after",
        doors=("read the errors, each with the script line it came from",),
    ),
    "engine.no-signal": Code(
        means="the run printed nothing that says it did what it was for",
        when="a script that never reached its own last line, or one whose success line "
        "is spelled differently from the pattern the run was given",
        doors=("read the log the run wrote", "check the success pattern"),
    ),
    "engine.missing-artefact": Code(
        means="the run said it wrote a file, and the file is not there",
        when="a script that printed its line before the write finished, or one writing "
        "somewhere other than where it said",
        doors=("check what the script wrote and where",),
    ),
    "engine.no-offscreen-route": Code(
        means="nothing on this machine gets the engine to draw real pixels",
        when="a capture where there is no display server at all; the engine's own "
        "headless mode offers only a dummy renderer, which draws nothing",
        doors=("install xvfb-run", "run where there is a display server"),
    ),
    "engine.timed-out": Code(
        means="the run was still going when its wall clock ran out",
        when="a script that never quits; the frame budget is the other bound and this "
        "is the one that catches a hang the engine itself does not end",
        doors=("read the log", "raise [engine] timeout if the run is honestly slow"),
    ),
    # -- geom: a shape declared as data ----------------------------------------
    "geom.unreadable": Code(
        means="the declaration is not readable as the format it claims",
        when="a hand edit that left invalid TOML behind",
        doors=("fix the syntax the detail points at",),
    ),
    "geom.malformed": Code(
        means="the file is TOML and is not a shape",
        when="a document with no name, no nodes, or no output named",
        doors=("give it a name, a node and an output",),
    ),
    "geom.bad-expression": Code(
        means="the expression is not one this evaluates",
        when="a call, an attribute, a comparison or a name outside the parameters and "
        "the repeat variables; nothing here evaluates arbitrary code, because a value "
        "that can depend on anything but its parameters breaks the cache key",
        doors=("write it with the operators and functions the grammar names",),
    ),
    "geom.unknown-field": Code(
        means="a declaration or a node carries a key nothing reads",
        when="`sizee = 9` beside `size` on a primitive, or `materails` at the top",
        doors=("spell it as one of the fields the refusal lists",),
    ),
    "geom.unknown-name": Code(
        means="the expression names something the document does not declare",
        when="a parameter spelled differently here than in [params], or a repeat "
        "variable used on a node that does not repeat",
        doors=("declare it in [params]", "name a variable this node repeats over"),
    ),
    "geom.duplicate-id": Code(
        means="two nodes claim the same id",
        when="a node copied and not renamed; ids are how every other node refers to "
        "one, so two of them makes every reference ambiguous",
        doors=("give each node an id of its own",),
    ),
    "geom.unknown-node": Code(
        means="a node refers to an id no node has",
        when="a typo in an input, or a node deleted while something still points at it",
        doors=("name a node the document declares",),
    ),
    "geom.cycle": Code(
        means="the nodes refer to each other in a circle, so none can be built first",
        when="a node taking its own output as an input, directly or through others",
        doors=("break the circle; a graph of shapes has to have a beginning",),
    ),
    "geom.bad-outline": Code(
        means="what was given is not an outline",
        when="fewer than three points, a mapping naming no shape, or a star of one "
        "point",
        doors=("give it a shape, an image, or at least three points",),
    ),
    "loop.baseline-too-late": Code(
        means="a baseline was started for an asset the plugin has already made",
        when="the before side recorded after the after side; a baseline written once "
        "the answer is known is not a baseline, it is a justification",
        doors=("record the baseline first", "measure a different asset"),
    ),
    "loop.unknown-way": Code(
        means="a run claims to be neither the old way nor the new one",
        when="a way outside the two being compared",
        doors=("say before or after",),
    ),
    "loop.unfinished": Code(
        means="the run was never judged, so it says nothing about either way",
        when="a comparison over a run that recorded no verdict; an asset nobody "
        "accepted or rejected did not finish being made",
        doors=("judge it before finishing it",),
    ),
    "loop.nothing-to-compare": Code(
        means="only one way has been recorded, so there is nothing to compare it with",
        when="a comparison before the same asset has been made both ways",
        doors=("record the other way", "list what has been recorded"),
    ),
    "loop.unknown-measure": Code(
        means="a run says it left unmeasured a number the ledger does not record",
        when="unmeasured naming something other than seconds, renders, calls, credits "
        "or person_minutes (§PW116)",
        doors=("name one of the costs a run records",),
    ),
    "loop.not-ported": Code(
        means="a change was measured on an asset not yet made both ways",
        when="a run naming a change for an asset with no first-port before and after "
        "(§PW114); the change has nothing to be measured against",
        doors=("record the port first, both ways",),
        calls=(door("loop.start", asset=Blank("the asset"), way="before"),),
    ),
    "loop.unknown-predicate": Code(
        means="a verdict blames a predicate the check it was given does not carry",
        when="a named id misspelled, or named with no check to name it from (§PW108)",
        doors=("pass the check the person judged", "name an id from that check"),
    ),
    "loop.unknown-choice": Code(
        means="a verdict is none of the things a person says of a family",
        when="a choice other than accept, look or number (§PW109)",
        doors=("say accept, look or number",),
    ),
    "loop.no-reason": Code(
        means="a verdict came without the person's sentence",
        when="judge called with an empty why",
        doors=("pass the person's own words",),
    ),
    "loop.no-failed-bound": Code(
        means="a bound was called wrong for refusing a look, and none refused it",
        when="number said of a family every member of which passes",
        doors=("say accept", "say look and name the bound that let it through"),
    ),
    "loop.malformed": Code(
        means="the ledger is not readable",
        when="a hand edit that left invalid JSON behind",
        doors=("fix the syntax the detail points at",),
    ),
    "geom.no-function": Code(
        means="the custom node names a function nothing here can load",
        when="a path that does not resolve, or a function the file does not have",
        doors=("write it as path/to/file.py:name", "check the name"),
    ),
    "geom.not-geometry": Code(
        means="a custom node returned something that is not geometry",
        when="a project function returning None, or a value with no vertices and faces "
        "on it; the rest of the graph has nothing to compose with",
        doors=("return a mesh, or a mapping of vertices and faces",),
    ),
    "geom.bad-solid": Code(
        means="the solid's own numbers do not describe a shape",
        when="an annulus whose inner radius is not inside its outer one, or a union of "
        "nothing at all",
        doors=("check the numbers the node states",),
    ),
    "geom.unknown-op": Code(
        means="a node names an operation nothing here builds",
        when="a typo in an `op`, or a shape reaching for a vocabulary this does not "
        "have; the declaration parses either way, because what an op means is the "
        "vocabulary's question and not the document's",
        doors=("name a declared op", "write it as a `custom` node of your own"),
    ),
    "geom.bad-surface": Code(
        means="the surface stated on a material is not one this can build",
        when="a fuzz with no depth or no coarseness, a depth at or below zero, a "
        "coarseness outside nought to one, or one of the shell constants named as "
        "though it were the way to ask; those are derived from the two that are",
        doors=(
            "state a depth and a coarseness",
            "read the derived constants back with `construction`",
        ),
    ),
    "geom.unknown-shape": Code(
        means="there is no outline generator by that name",
        when="a shape named outside the small library the scripts were read off",
        doors=("name a declared generator", "trace a drawing instead"),
    ),
    "geom.nothing-to-trace": Code(
        means="the drawing has no subject in it to trace an outline from",
        when="an image that is entirely background",
        doors=("point it at a drawing with a subject in it",),
    ),
    "geom.bad-repeat": Code(
        means="the repeat does not describe a range",
        when="a range with no variable, or a step of zero, which is a loop that never "
        "ends rather than one that repeats nothing",
        doors=("give each range a var, a from and a to", "use a step above zero"),
    ),
    "geom.bad-voxels": Code(
        means="the document asks for cells and does not say how big one is",
        when="a [voxels] table with neither `cell` nor `across`, or with both, or a "
        "size that is not above zero; two ways of saying one number would disagree",
        doors=("give [voxels] a `cell` size", "give [voxels] an `across` count"),
    ),
    "geom.bad-fracture": Code(
        means="the fracture plan does not describe fragments that can exist",
        when="a size that is not two whole numbers, a smallest fragment under one "
        "cell, or a smallest above the largest",
        doors=(
            "write size = [smallest, largest] in cells, with 1 <= smallest <= largest",
        ),
    ),
    "geom.bad-fit": Code(
        means="a voxel fit was asked for something it cannot compare",
        when="no parameter to move, a view that is not front, side or top, or a "
        "drawing asked to stand for a view it does not show",
        doors=(
            "give ranges, or a [search.<param>] table in the document",
            "name views among front, side and top",
            "fit a drawing on the front view, or give a mesh for more",
        ),
    ),
    "geom.bad-cells": Code(
        means="a `cells` node's text does not describe a block of cells",
        when="layers or rows of different lengths, a character the legend does not "
        "name, or no size for a cell because [voxels] states only `across`",
        doors=(
            "make every row and every layer the same size",
            "add the character to `legend`, or use `.` for an empty cell",
            "give the node or [voxels] a `cell` size",
        ),
    ),
    # -- clip: motion over time ------------------------------------------------
    "clip.empty": Code(
        means="the clip moves nothing",
        when="a clip with no channels, or channels with no keys in them; a clip that "
        "changes nothing over its duration is a still with a duration attached",
        doors=("give it a channel with keys", "render it as a still instead"),
    ),
    "clip.unknown-property": Code(
        means="a channel drives something a joint does not have",
        when="a property outside the three glTF animates: rotation, scale, translation",
        doors=("name rotation, scale or translation",),
    ),
    "clip.unknown-easing": Code(
        means="the keyframe asks for an interpolation nothing implements",
        when="an easing named outside the declared set",
        doors=("name a declared easing",),
    ),
    "clip.outside-duration": Code(
        means="a keyframe sits outside the clip it belongs to",
        when="a key at a negative time, or past the duration; the duration is the clip "
        "and a key beyond it never plays",
        doors=("move the key inside", "lengthen the clip"),
    ),
    "clip.frames-differ": Code(
        means="the frames of one clip are not all the same size",
        when="frames rendered at different rungs, or gathered from two runs; a sheet "
        "of cells that are not one size is a sheet nothing can index",
        doors=("render every frame at one rung",),
    ),
    "clip.nothing-drawn": Code(
        means="no frame of the clip has anything in it to trim to",
        when="a clip rendered with the subject out of frame, or on a rung that drew "
        "nothing at all",
        doors=("check the rig and the rung", "look at the frames the run wrote"),
    ),
    "clip.unreadable": Code(
        means="the clip file is not readable as the format it claims",
        when="a hand edit that left invalid TOML behind; the format is text so that a "
        "person can change it, which is also how it gets broken",
        doors=("fix the syntax the detail points at",),
    ),
    "clip.malformed": Code(
        means="the file is TOML and is not a clip",
        when="a file missing a name, a duration, or any channel at all",
        doors=("give it a name, a duration and a channel with keys",),
    ),
    "clip.no-frames": Code(
        means="the clip is too short or too slow to have a single frame in it",
        when="a duration or a frame rate at or below zero",
        doors=("give it a duration above zero", "give it a frame rate"),
    ),
    # -- rig: fitting a skeleton to a mesh ------------------------------------
    "rig.unknown-plan": Code(
        means="there is no body plan by that name",
        when="a plan named outside the small library of the body plans that recur",
        doors=("name a declared plan", "state the joints"),
    ),
    "rig.bad-plan": Code(
        means="the body plan does not describe a skeleton",
        when="a joint whose parent is not in the plan, a cycle, or no root at all",
        doors=("give every joint a parent that comes before it",),
    ),
    "rig.unbound-vertices": Code(
        means="some vertices are attached to no bone, so posing leaves them behind",
        when="a mesh with a part no bone reaches, usually a plan that does not match "
        "the shape",
        doors=("fit a plan that covers the shape", "widen the falloff"),
    ),
    "rig.tearing": Code(
        means="a test pose stretches the mesh past what the weights should allow",
        when="two neighbouring vertices bound to bones that move apart; one influence "
        "per vertex is the worst case, and either end of the falloff is the next",
        doors=(
            "give a vertex more influences",
            "move the falloff off its extreme",
            "fit a plan that matches",
        ),
    ),
    "rig.unmatched-joints": Code(
        means="the pose names joints the skeleton does not have",
        when="a clip authored against one plan played on another that spells its "
        "joints differently; a name is the contract and a near miss is not a match",
        doors=(
            "name the joints the skeleton has",
            "retarget through a plan that shares them",
        ),
    ),
    # -- capture: the environment a picture is taken in ------------------------
    "capture.undeclared": Code(
        means="a setting the project says matters has no value to take",
        when="a name in `[capture] declared` that nothing sets; leaving it to chance "
        "is exactly how one machine's picture differs from another's",
        doors=("give it a value in [capture]", "pass it to the capture"),
    ),
    "capture.not-reported": Code(
        means="the script never said what environment it took the picture in",
        when="a capture script that does not print its environment line back",
        doors=("print the settings the run passed it, as it applied them",),
    ),
    "capture.not-applied": Code(
        means="the script left out a setting it was given",
        when="a script that names a setting and never passes it on; naming it without "
        "setting it passes a naive check and still gives the wrong picture",
        doors=("apply it and report it", "drop it from [capture] declared"),
    ),
    "capture.differs": Code(
        means="the script applied a different value from the one it was given",
        when="a default inside the script winning over the argument it was passed",
        doors=("take the value from the run rather than from a constant",),
    ),
    "capture.not-reproduced": Code(
        means="the picture moved although every declared setting held still",
        when="a project with `[capture] reproducible` on, whose capture has stopped "
        "drawing what it drew last time; off by default, because a capture nobody has "
        "pinned would fail every run",
        doors=(
            "declare whatever moved, so the run passes it and the script applies it",
            "commit the new picture, which re-anchors what the next run is compared to",
        ),
    ),
    # -- units: the scale an asset is baked at --------------------------------
    "units.undeclared": Code(
        means="nothing says what scale this asset is baked at",
        when="a check with no world rectangle, or a project that names no scale of its "
        "own and no file to read one from",
        doors=("state the rectangle the asset covers", "set [units] pixels_per_unit"),
    ),
    "units.unreadable": Code(
        means="the file the project points at holds no such number",
        when="a constant renamed or moved in the engine's own source; the point of "
        "reading it there is that this is what happens when it moves",
        doors=("check the name [units] source addresses", "state the number here"),
    ),
    "units.mismatch": Code(
        means="the asset is baked at one scale and the engine draws at another",
        when="a render rectangle tuned by hand to match a cell size held separately, "
        "after either of the two moved",
        doors=("bake at the engine's scale", "change the engine's, deliberately"),
    ),
    "units.not-whole": Code(
        means="the rectangle and the scale do not come to a whole number of pixels",
        when="a rectangle whose width times the scale lands between two pixels, which "
        "is a sprite that cannot sit on the grid whatever else is right",
        doors=("round the rectangle", "use a scale the rectangle divides by"),
    ),
    "units.wrong-size": Code(
        means="the picture is not the size the declaration asks for",
        when="a bake whose size came from the rung rather than from the rectangle",
        doors=("render at the size the declaration gives",),
    ),
    # -- prov: what produced an artefact -------------------------------------
    "prov.unknown-kind": Code(
        means="the record names a kind of artefact that is not one of the four",
        when="a record is built for something outside render, mesh, capture and fetch",
        doors=("name one of the declared kinds",),
    ),
    "prov.missing-artefact": Code(
        means="there is nothing at the path the record would describe",
        when="a record is built before the artefact is written, or beside the wrong "
        "path",
        doors=("write the artefact first", "record the path it was written to"),
    ),
    "prov.missing-input": Code(
        means="an input the record names is not on disk",
        when="a path recorded from an argument rather than from what was read",
        doors=("record the path the operation actually read",),
    ),
    "prov.bad-key": Code(
        means="the string is not a cache key",
        when="a lookup by something other than a digest over a provenance record",
        doors=("compute the key from the record",),
    ),
    "prov.no-record": Code(
        means="the artefact has no record beside it",
        when="something produced it without one, which is how a paid mesh was lost",
        doors=("produce it again", "verify what the project holds"),
    ),
    "prov.malformed": Code(
        means="the record is not readable as JSON",
        when="a record edited by hand, or truncated",
        doors=("produce the artefact again",),
    ),
    # -- spec: the vocabularies a caller names things by ---------------------
    "spec.unknown-code": Code(
        means="the code asked about is not one this plugin publishes",
        when="an explain names a code that does not exist, usually a misspelling",
        doors=("list the codes", "name one of the near matches"),
    ),
    "spec.unknown-measure": Code(
        means="the name is not a measure the vocabulary carries",
        when="an acceptance spec or a question names a measure that does not exist; "
        "the vocabulary is closed, or a spec would silently check nothing",
        doors=("name a declared measure", "add the measure it needs"),
    ),
    "spec.unmeasured": Code(
        means="the measure is in the vocabulary and nothing computes it yet",
        when="a call asks for a measure a later line builds; it is refused by name "
        "rather than quietly left out of the answer",
        doors=("ask for a measure that exists", "wait for the line that builds it"),
    ),
    "spec.bad-region": Code(
        means="the region a measurement would be taken over is not one",
        when="a rectangle outside the image, a mask of another size, or a word that is "
        "neither frame nor subject",
        doors=("give frame, subject, a rectangle, or a mask the same size",),
    ),
    "spec.measure-needs": Code(
        means="the measure needs an argument the call did not give",
        when="luma_bands without the display size it counts at; a default would answer "
        "a question nobody asked",
        doors=("pass the argument the measure names",),
    ),
    "spec.unknown-field": Code(
        means="the acceptance spec names a field nothing reads",
        when="a misspelled key in a spec or a predicate; refused rather than ignored, "
        "or a claim would read as checked while it was not",
        doors=("name a declared field",),
    ),
    "spec.missing": Code(
        means="the asset has no acceptance spec",
        when="a check on an asset nobody has written the predicates for",
        doors=("write one beside the asset", "write one under [paths] specs"),
    ),
    "spec.malformed": Code(
        means="the acceptance spec is not readable as TOML",
        when="a syntax error in the spec file",
        doors=("fix the syntax the detail points at",),
    ),
    "spec.no-predicates": Code(
        means="the spec states nothing, so it checks nothing",
        when="a spec file with no predicate in it",
        doors=("add a predicate naming a measure and a bound",),
    ),
    "spec.anonymous-predicate": Code(
        means="a predicate has no id",
        when="a predicate written without one; a search reports a score per predicate "
        "and the trace addresses them by name, so an anonymous one cannot be discussed",
        doors=("give the predicate an id",),
    ),
    "spec.duplicate-id": Code(
        means="two predicates share one id",
        when="a spec that was copied and not renamed",
        doors=("give each predicate a name of its own",),
    ),
    "spec.no-measure": Code(
        means="a predicate names no measure, so there is nothing to compute",
        when="a predicate with bounds and nothing to bound",
        doors=("name a measure from the vocabulary",),
    ),
    "spec.no-bound": Code(
        means="nothing bounds the value, so nothing can fail",
        when="a predicate with neither min nor max, or a search range open at one end",
        doors=("give it a min, a max, or both",),
    ),
    "spec.bad-bound": Code(
        means="a bound is not a number",
        when="an expression where a bound belongs; a predicate states a bound, and "
        "never an expression",
        doors=("write a number", "add the measure that answers the question"),
    ),
    "spec.bad-origin": Code(
        means="a bound written as a table does not say where its number came from",
        when="an origin missing, or other than measured, margin or person",
        doors=("say measured, margin or person", "write the bound as a bare number"),
    ),
    "spec.no-variants": Code(
        means="a bound was to be calibrated with nothing to measure its noise against",
        when="a proposal given the accepted picture and no variant of it (§PW107)",
        doors=("render the accepted request again under a harmless change",),
    ),
    "spec.stale-proposal": Code(
        means="the spec moved after the calibration it is being given was measured",
        when="a bound edited, or a predicate renamed or removed, between calibrating "
        "and applying",
        doors=("calibrate again against the spec as it is now",),
    ),
    "spec.unwritable-bound": Code(
        means="a bound is not written on one line, so it cannot be rewritten in place",
        when="a bound spread over a sub-table or a multi-line inline table",
        doors=("write it as a number or an inline table on one line",),
    ),
    "spec.no-screen": Code(
        means="the spec cannot be found on screen",
        when="a screen check on a spec with no `screen`, or a region the capture's "
        "record does not carry (§PW112)",
        doors=(
            "add screen = { capture, region } to the spec",
            "have the capture script print `region: <name>=x0,y0,x1,y1`",
        ),
    ),
    "spec.bad-colour": Code(
        means="the target is not a colour",
        when="a name or a malformed hex where #RRGGBB was expected",
        doors=("write it as #RRGGBB",),
    ),
    "spec.no-cost-source": Code(
        means="a cost predicate has no file to read off, or one that cannot say",
        when="a triangles bound with no `of` on a picture recording no mesh, or a "
        "texture's byte count asked of a voxel model",
        doors=("name the .glb, .voxels.json or .png the game draws with `of`",),
    ),
    "spec.unbounded-measure": Code(
        means="the measure answers with something a bound cannot hold",
        when="a bound on a measure that returns a set or a colour rather than a number",
        doors=("bound a statistic of it instead",),
    ),
    "spec.rung-too-low": Code(
        means="the render was taken lower on the ladder than the spec allows",
        when="a verdict taken at the sphere on an asset whose spec names a floor",
        doors=("render at the rung the spec needs",),
    ),
    "spec.size-mismatch": Code(
        means="two images being compared are not the same size",
        when="a comparison between renders taken at different rungs",
        doors=("render both at the same rung", "scale one before comparing"),
    ),
    "spec.empty-region": Code(
        means="the region a measurement was asked for holds no pixels",
        when="a subject region on an image whose alpha is everywhere below the floor",
        doors=("widen the region", "lower the alpha floor"),
    ),
    "spec.unknown-area": Code(
        means="the area named is not one codes are namespaced under",
        when="a listing asks for an area outside the declared set",
        doors=("name a declared area",),
    ),
}


def known(code: str) -> bool:
    return code in CODES


def area_of(code: str) -> str:
    return code.split(".", 1)[0]


def in_area(area: str) -> list[str]:
    return sorted(c for c in CODES if area_of(c) == area)
