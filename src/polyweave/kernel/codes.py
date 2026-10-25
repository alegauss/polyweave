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

import functools
import importlib
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
KERNEL_AREAS: dict[str, str] = {
    "fetch": "asking the paid service for something",
    "post": "what an operation asserts about its own output",
    "config": "resolving a value from a call, a project file or a default",
    "job": "long work held by a handle",
    "spec": "an acceptance spec and its vocabulary",
    "op": "an operation's own arguments, against what it declared",
    "prov": "the record written beside an artefact, and the cache key it defines",
    "search": "looking for parameter values that satisfy a spec",
    "loop": "what one asset cost to make, each way",
    "verdict": "the members a person's verdict is laid out from and carried to",
    "adopt": "a project's adoption: its config, its server and its agent's section",
    "review": "the local page a person answers a sitting on, and the server behind it",
    "layer": "a medium's own declaration, which the kernel finds by walking layers/",
}

KERNEL_CODES: dict[str, Code] = {
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
    # -- layer: a medium's own declaration (§PW500) ---------------------------
    "layer.undeclared": Code(
        means="a package under layers/ says nothing about what it adds",
        when="a layer's folder has no layer.py, or it holds no LAYER of that name",
        doors=("write layer.py with one LAYER = Layer(name=..., ...)",),
    ),
    "layer.unnamed-module": Code(
        means="a module registers an operation that its own layer does not name",
        when="an operation module under layers/<name>/ is missing from LAYER.modules",
        doors=("add the module to modules in that layer's layer.py",),
    ),
    "layer.cycle": Code(
        means="two or more layers use each other in a circle",
        when="a layer.py's uses names a layer whose own uses lead back to it",
        doors=("move what both need below both", "turn one edge into a part"),
    ),
    "layer.declared-twice": Code(
        means="two layers declare one record kind, source role or outdated section",
        when="a layer.py names something another layer, or the kernel, already owns",
        doors=("keep it in the layer that owns it and drop it from the other",),
    ),
    "layer.missing-part": Code(
        means="a call needs a read that no installed layer answers",
        when="the review page or the brief asks for a part only one layer provides",
        doors=("install the layer whose layer.py declares the part",),
    ),
    "layer.two-judges": Code(
        means="two layers declare a judge under one name",
        when="a judge's name, the key its answer is reported under, is taken already",
        doors=("rename one of the two judges",),
    ),
    "layer.off": Code(
        means="the operation is a layer's that this project has switched off",
        when="a tool or command of a layer [layers] on leaves out, or a table it reads",
        doors=("add the layer to [layers] on in polyweave.toml",),
    ),
    "layer.unknown": Code(
        means="[layers] on names a layer polyweave does not have",
        when="a typo, or a layer from another version, in polyweave.toml",
        doors=("name a layer capabilities lists", "drop [layers] for every one"),
    ),
    "layer.unknown-requirement": Code(
        means="a layer requires something polyweave has no way to find",
        when="LAYER.requires names a word outside blender, godot, audio and text",
        doors=("require one of the four", "drop the requirement"),
    ),
    # -- op: an operation's arguments against what it declared ---------------
    "op.project-failed": Code(
        means="an operation the project declares failed when it ran",
        when="the project's own function raised, or answered nothing polyweave could "
        "read, in the interpreter it runs in apart",
        doors=("run the function yourself with those arguments", "fix its fn"),
    ),
    "op.unknown": Code(
        means="no operation is registered under that name",
        when="a describe or a validate names an operation that does not exist",
        doors=("describe with no argument to list them",),
    ),
    "op.crashed": Code(
        means="an operation raised where it should have refused: a defect in polyweave",
        when="a call the operation did not check reached code that assumed its shape",
        doors=("read the detail for where it raised, and file it",
               "the server still answers every other call"),
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
        when="a `--set` with no `=` in it, or a key the declaration does not take",
        doors=("write it as name=value", "set one of the keys `allowed` lists"),
    ),
    # -- config: what a project declares, and how a value is resolved --------
    "config.malformed": Code(
        means="the project's config file could not be read as TOML",
        when="a syntax error in polyweave.toml, or a file that cannot be opened",
        doors=("fix the syntax the detail points at",),
    ),
    "config.exists": Code(
        means="polyweave.toml already exists, and init does not overwrite it",
        when="project.init with write in a project that has already been configured",
        doors=("pass merge to add only the tables it lacks", "edit the file by hand"),
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
    "config.bad-language": Code(
        means="[review] language names a language the review page has no catalog for",
        when="a sitting laid out, or the page read, under a language not in "
        "review_page/locales/",
        doors=("set [review] language to en or pt-BR",
               "add review_page/locales/<language>.json"),
    ),
    "config.bad-measure": Code(
        means="a measure the project declares under [extend.measures] cannot be used",
        when="a declaration misses fn, subject, unit, range or about, names a function "
        "not as file.py:function, or gives a range that is not two numbers, low first",
        doors=("write the declaration with every field it takes",),
    ),
    "config.bad-operation": Code(
        means="an operation the project declares under [extend.operations] cannot be "
        "served",
        when="a declaration misses fn or about, names a function not as "
        "file.py:function, a job kind there is none of, a parameter with no type or "
        "about, or is a producer with no out parameter",
        doors=("write the declaration with what it takes",),
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
    "config.services-mixed": Code(
        means="a paid service or its ceiling is declared two ways at once",
        when="bare [service] keys beside a [service.<name>] table, a bare [budget] "
        "beside named services, or a [budget.<name>] for no declared service",
        doors=(
            "move every service under its own [service.<name>]",
            "name the ceiling after a declared service",
        ),
    ),
    # -- fetch: asking the paid service for something -------------------------
    "fetch.no-reference": Code(
        means="there is no drawing to check the returned shape against",
        when="a shape check with no reference, or one pointing at a path that is empty",
        doors=("point it at the drawing that asked for this shape",),
    ),
    "fetch.reference-changed": Code(
        means="a registered reference video is not the file it was registered as",
        when="the video was replaced, re-encoded or cut since reference.register "
        "took its digest, so a reading would silently be of another file (§PW407)",
        doors=("register it again with reference.register",
               "put back the video that was registered"),
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
    "fetch.bad-mode": Code(
        means="a way of telling background from subject that is not one",
        when="reference.prepare given a mode other than edge or colour (§PW626)",
        doors=("say edge, which stops at the subject's own edge",
               "say colour, which takes every pixel near the ground's colour"),
    ),
    "fetch.no-expiry": Code(
        means="a ceiling is declared with no date, and a ceiling without one is never "
        "spendable",
        when="[budget] expires left empty beside an amount above 0 (§PW625): a "
        "person's approval to spend says until when",
        doors=("give the ceiling's expires a date, YYYY-MM-DD",),
    ),
    "fetch.budget-closed": Code(
        means="nothing may be spent, because no live budget says it may",
        when="a project with no [budget], an expired one, or one already used up; an "
        "absent ceiling is never read as permission",
        doors=("set credits and an expiry in the project config",),
    ),
    "fetch.not-paid": Code(
        means="a quote was asked of an operation that spends nothing",
        when="purchase.quote given an operation describe does not mark `spends` "
        "(§PW308)",
        doors=("quote one of the paid operations the refusal lists",),
    ),
    "fetch.over-budget": Code(
        means="the spend would pass the ceiling a person set",
        when="a fetch costing more than the credits left against [budget]",
        doors=("raise the ceiling", "ask for something that costs less"),
    ),
    "fetch.service-unnamed": Code(
        means="the project declares more than one paid service and the call named none",
        when="a spend or a read of the ceiling with several [service.<name>] tables; "
        "guessing which balance to draw on is what a ceiling exists to prevent",
        doors=("pass the service by name",),
    ),
    "fetch.unknown-service": Code(
        means="the service named is not one the project declares",
        when="a misspelled service name, or one whose [service.<name>] was removed",
        doors=("name a declared service",),
    ),
    "fetch.ledger-unattributed": Code(
        means="a ledger entry names no service, and several could have been charged",
        when="a ledger written while the project had one service, read after it "
        "declared a second",
        doors=("add the service each entry was bought from to its `service` field",),
    ),
    "fetch.seed-unproved": Code(
        means="nothing has proved the service reads a seed, so asking with one may be "
        "dropped in silence",
        when="a picture asked for with a seed where the learned schema has not proved "
        "the field; a dropped seed records a picture as repeatable when it is not",
        doors=("learn the schema", "ask without a seed and keep the one reported"),
    ),
    "fetch.ocr-failed": Code(
        means="the OCR engine is present and could not read the picture",
        when="tesseract without the language data the project's locale needs, or a "
        "file it cannot open",
        doors=("install the language data", "pass languages"),
    ),
    "fetch.no-region": Code(
        means="an edit's region names no single described element of the parent",
        when="a region matching none or several of the boxes picture.describe found, "
        "or a parent never described",
        doors=(
            "describe the parent",
            "name one element by more of its words",
            "pass a mask",
        ),
    ),
    "fetch.no-parent": Code(
        means="the picture records no parent to measure it against",
        when="a picture bought directly rather than as a variation of an approved one",
        doors=("measure it against its canon with style.drift",),
    ),
    "fetch.picture-ungated": Code(
        means="a mesh was asked for from a picture the gate never passed",
        when="a picture never put through picture.gate, one it refused, or one changed "
        "since; a silhouette is settled on the picture before the mesh is paid for",
        doors=("run picture.gate and buy from the picture it chooses",),
    ),
    "fetch.unpriced": Code(
        means="no price is declared for what is being bought, so its cost is not known",
        when="a picture on a model and speed with no row in the service's prices; it "
        "is refused rather than priced at zero, which would under-count the ceiling",
        doors=("add the row to [service.<name>] prices",),
    ),
    "fetch.uncounted": Code(
        means="the price is by a unit, such as a character, and the call states no "
        "count of it",
        when="a prices row { per = \"character\", rate = ... } quoted or charged with "
        "no text to count (§PW320)",
        doors=("pass the text the call would send",),
    ),
    "fetch.sample-short": Code(
        means="the line a voice is designed on is shorter than the service accepts",
        when="voice.design with a sample under the service's voice_sample_least, 100 "
        "characters for ElevenLabs unless its table says otherwise (§PW482)",
        doors=("write a longer sample in the voice, or pass one as sample",),
    ),
    "fetch.service-unconfigured": Code(
        means="the service named cannot be reached: no base, or no key in this "
        "environment",
        when="a [service.<name>] with no base, or a key_env that is unset here",
        doors=("set base under the service", "export the variable key_env names"),
    ),
    "fetch.prompt-refused": Code(
        means="the service refused the prompt as failing its safety check",
        when="a 422 from the picture service, or an answer marked unsafe with no "
        "picture in it; a refused request is not charged",
        doors=("reword the prompt",),
    ),
    "fetch.rate-limited": Code(
        means="the account has more requests in flight than the service allows",
        when="a 429, from calls made elsewhere on the same account",
        doors=("wait for the calls already out to finish, then ask again",),
    ),
    "fetch.plan-lacks": Code(
        means="the account's plan does not include what was asked of the service",
        when="a 403 from the speech service, such as voice design asked of a free "
        "plan; a refused call is not charged",
        doors=("move the account to a plan that has the feature, at the service",
               "or choose a voice the plan can use, from the service's library"),
    ),
    "fetch.service-error": Code(
        means="the service answered with something other than what was asked for",
        when="an unreachable host, a 401 for a key it refuses, a 400 for a payload it "
        "refuses, or a body that is not JSON",
        doors=("read the detail the service sent",),
    ),
    "fetch.ledger-malformed": Code(
        means="the purchase ledger is not readable",
        when="a ledger edited by hand, or truncated, or neither a list of entries nor "
        "a lock keyed by name (§PW457)",
        doors=("restore it from version control, where it belongs",),
    ),
    "fetch.ledger-by-name": Code(
        means="the ledger is an adopting project's lock keyed by name, read but never "
        "rewritten",
        when="a buy, or anything else that writes the ledger, while [paths] purchases "
        "names such a lock (§PW457)",
        doors=("point [paths] purchases at a new ledger",
               "purchase.adopt the lock's entries into it"),
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
    # -- verdict: the members a verdict is laid out from --------------------------
    "verdict.judged-twice": Code(
        means="two layers' judges claim one member, so its verdict has two homes",
        when="a member carries the keys of two media, such as canon and line",
        doors=("lay the member out with one medium's keys",),
    ),
    "verdict.bad-member": Code(
        means="a member of a sheet, a sitting or a verdict is not one",
        when="a member that is a number or a list, a table with no name or no new, or "
        "an old, new or capture that names no file",
        doors=("write each member as a table, or as the picture's path",),
    ),
    "verdict.bad-family": Code(
        means="a family's name leaves nothing a sheet's file can be named by",
        when="a family named by nothing, or by spaces and dots alone (§PW616); any "
        "other name is laid out as written, its file named safely",
        doors=("name the family with a word a person reads",),
    ),
    "verdict.no-old": Code(
        means="a member's old names a committed picture git cannot give back",
        when="old = '<rev>:<path>' where the revision or the path is not in the "
        "repository, or the picture is a Git LFS pointer git lfs cannot fetch (§PW481)",
        doors=("name a revision and a path the repository holds, as HEAD:<path>",),
    ),
    "verdict.not-the-person": Code(
        means="a tool call accepts a look without the code the review page shows, so "
        "nothing says a person gave it (§PW443)",
        when="an agent accepting its own work, or relaying a person's yes without the "
        "code the page shows for that sitting",
        doors=("the person answers on the review page",
               "the person says the page's code for the sitting, passed as code"),
    ),
    "verdict.bad-move": Code(
        means="a sitting cannot move where it was asked to",
        when="verdict.move to a folder that already exists, lies outside the project, "
        "or lies inside the sitting itself (§PW436)",
        doors=("name a folder under the project that does not exist yet",),
    ),
    "verdict.bad-place": Code(
        means="an accepted member cannot be placed where it was asked to",
        when="verdict.place to a path outside the project, or onto the member's own "
        "review copy (§PW549)",
        doors=("name the path under the project the game loads it from",),
    ),
    "verdict.unaccepted": Code(
        means="a member is placed for the game, and no person accepted it",
        when="verdict.place on a member whose record's last verdict, or the latest "
        "answer naming it, is not an accept (§PW549)",
        doors=("let a person accept it on the review page first",),
    ),
    # -- review: the page a person answers on, and its server ---------------------
    "review.stale-server": Code(
        means="the review server runs older code than the plugin it was started from",
        when="polyweave changed after `polyweave review` started, so a spec using a "
        "measure added since would be refused by the server's own copy (§PW294)",
        doors=("stop the server and start it again: python -m polyweave review",),
    ),
    "review.restarting": Code(
        means="the review server saw polyweave change and is starting again on the new "
        "code, on the same port (§PW463)",
        when="polyweave changed while `python -m polyweave review` was serving",
        doors=("send the same request again in a moment; the page does so itself",),
    ),
    "review.not-served": Code(
        means="the picture named is not one the page may show",
        when="a path outside the project, or a file that is not a picture or record",
        doors=("name a picture by its path under the project root",),
    ),
    # -- adopt: an adoption, checked (§PW220) --------------------------------
    "adopt.not-adopted": Code(
        means="the project has no polyweave.toml",
        when="project.check in a tree polyweave was never set up in",
        doors=("run init --write --agent",),
    ),
    "adopt.path-missing": Code(
        means="a path the project states in [paths] does not exist",
        when="a folder moved or renamed after the config was written",
        doors=("create it", "correct the path in polyweave.toml"),
    ),
    "adopt.no-server": Code(
        means="no polyweave server is declared, so a session sees no tool",
        when="a project configured but never wired to its agent",
        doors=("run init --agent",),
    ),
    "adopt.server-twice": Code(
        means="polyweave is served by the enabled plugin and by .mcp.json at once",
        when="the plugin enabled after init --agent declared the server",
        doors=("remove polyweave from .mcp.json",),
    ),
    "adopt.no-agent-section": Code(
        means="AGENTS.md has no section init wrote, so none can be checked current",
        when="a project never wired with init --agent, or one whose section was "
        "written by hand",
        doors=("run init --agent",),
    ),
    "adopt.stale-section": Code(
        means="the AGENTS.md section was written by another version, or names an "
        "operation this one lacks",
        when="the plugin upgraded or an operation renamed since init --agent ran",
        doors=("run init --agent to rewrite it",),
    ),
    "adopt.key-unset": Code(
        means="a service's key variable is not set in this environment",
        when="a desk that never set the key, or a shell that does not inherit it",
        doors=("set the variable the service's key_env names",),
    ),
    "adopt.budget-lapsed": Code(
        means="a service can spend nothing: its budget is absent, empty or expired",
        when="a ceiling past its expiry date, or one a person has not written yet",
        doors=("a person sets the budget in polyweave.toml",),
    ),
    "adopt.unrecorded": Code(
        means="produced files carry no provenance record",
        when="an artefact made outside polyweave, or a record deleted",
        doors=("produce it again through polyweave", "list it under handmade"),
    ),
    "adopt.build-beside": Code(
        means="a geometry build sits beside the declaration it was built from",
        when="it was built before a build with no out went to the work area, or its "
             "out named the declaration's own folder, which an engine may import",
        doors=("delete it and build again, which writes under [paths] work",
               "give the build an out where the engine should read it"),
    ),
    "adopt.internal-tracked": Code(
        means="git tracks a file derived from a reference kept internal",
        when="frames of another game's video, or something made from them, committed "
        "where only the work area should hold it (§PW407)",
        doors=("remove it from git and keep it in the work area",),
    ),
    "adopt.own-surface": Code(
        means="the project's own code does what a polyweave call already does: starts "
        "the engine, drives Blender, calls a service or measures a picture (§PW59)",
        when="a runner, rig, client or check written beside the call, or one ported "
        "and written again",
        doors=("move it onto the call the finding names",
               "keep it under [adoption] own with the reason"),
    ),
    # -- search: looking for values that satisfy a spec -----------------------
    "search.unknown-producer": Code(
        means="no layer declares a producer by that name, so nothing makes a sample",
        when="search.sweep names a producer that no layer.py declares",
        doors=("name one of the producers the layers declare",),
    ),
    "search.downstream-failed": Code(
        means="a sample was made, and the declared run it is judged after did not run",
        when="search.sweep with then= whose engine run failed, so no capture was made "
        "to check (§PW621)",
        doors=("run engine.run_declared with those runs and read its log",),
    ),
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
    "loop.unknown-sitting": Code(
        means="the verdict names a sitting or a family the project never laid out",
        when="an answer from the review page for a sitting folder since removed, or a "
        "family not in it",
        doors=("answer a sitting the page lists",),
    ),
    "loop.pick-one": Code(
        means="an accept of a family of alternatives names no one of its members",
        when="a sitting laid a slot's alternatives as one family (a voice's previews, "
        "§PW547) and the accept carried no member, or one not in it",
        doors=("pass member, the name of the alternative the person picked",),
    ),
    "loop.bad-moment": Code(
        means="a moment marked on an answer is not a time in a member's loop",
        when="the page's answer carrying a moment on a member with no motion, or a "
        "time that is not a number of seconds from zero (§PW600)",
        doors=("mark a moment on a member that plays a loop",),
    ),
    "loop.bad-view": Code(
        means="a view marked on an answer is not a camera on a member's model",
        when="the page's answer carrying a view on a member with no model, or a camera "
        "or target that is not three numbers (§PW601)",
        doors=("mark a view on a member that shows a model",),
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
    "loop.bad-target": Code(
        means="a person's target is not a bar the look has still to reach",
        when="verdict.target given no number, one today's look already meets, one "
        "looser than its bound, or one on a side the predicate does not bound (§PW620)",
        doors=("name a number past today's value", "say accept",
               "write the missing min or max in the spec first"),
    ),
    "loop.malformed": Code(
        means="the ledger is not readable",
        when="a hand edit that left invalid JSON behind",
        doors=("fix the syntax the detail points at",),
    ),
    # -- capture: the environment a picture is taken in ------------------------
    "spec.unlevel-tier": Code(
        means="the worlds offered on one tier of a route are not worth the same",
        when="a world whose total threat is outside the band of its tier's first "
        "world's, or which saves a different count of the named kind",
        doors=("change the worlds' waves until the tier is level",
               "widen the band where the owner says so"),
    ),
    # -- prov: what produced an artefact -------------------------------------
    "prov.unknown-kind": Code(
        means="the record names a kind of artefact that is not one of the four",
        when="a record is built for something outside render, mesh, capture and fetch",
        doors=("name one of the declared kinds",),
    ),
    "prov.no-preset": Code(
        means="what a Godot build ships cannot be read off an export preset",
        when="provenance.generated with no paths, in a Godot project with no "
        "export_presets.cfg or no preset by the name given (§PW455)",
        doors=("name one of the project's presets", "pass the paths a build ships"),
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
    "spec.measure-failed": Code(
        means="a measure the project declares failed on its subject",
        when="the project's function raised, took too long, answered nothing, or names "
        "a file that is not there",
        doors=("run the function on that file yourself", "fix the declaration's fn"),
    ),
    "spec.measure-out-of-range": Code(
        means="a measure the project declares answered outside its declared range",
        when="the project's function returned a value below or above the range its "
        "declaration states, or no number at all; it is never clamped",
        doors=("fix the function", "widen the range it declares"),
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
    "spec.not-sound": Code(
        means="a sound predicate was checked on something that is not a sound",
        when="a seam_step bound in a spec checked against a picture",
        doors=("check it against the audio file, or name that file with `of`",),
    ),
    "adopt.not-empty": Code(
        means="project.new was pointed at a folder that already holds files",
        when="starting a game where one, or anything else, already is (§PW369)",
        doors=("adopt a game that exists with project.init --write --agent",
               "name an empty folder, or one not there"),
    ),
    "spec.no-targets": Code(
        means="a contrast measure has no target to measure, or one outside the picture",
        when="a contrast bound with no targets, a log with no `target:` line, or a "
        "target off the picture's edge",
        doors=("pass targets, each a point or a box",
               "name the log whose target lines place them"),
    ),
    "spec.ring-inside-target": Code(
        means="a target's ring reads as the target, so it is larger than its radius",
        when="a contrast radius smaller than the shot, which would read near 1.0",
        doors=("widen the radius", "give the target as a box that covers it"),
    ),
    "spec.not-effect": Code(
        means="an effect predicate was checked on something vfx.build did not make",
        when="a reach bound checked against a picture, or a scene with no vfx record",
        doors=("check it against the .tscn vfx.build wrote, or name it with `of`",),
    ),
    "spec.unreadable-sound": Code(
        means="a sound file is missing, unreadable, undecodable or empty",
        when="an .ogg with no ffmpeg on PATH, a 12-bit WAV, a service's error page "
        "saved as .mp3, or a file with no samples",
        doors=("give a 16-bit PCM WAV, or put ffmpeg on PATH",),
    ),
    "spec.no-seam": Code(
        means="a seam is bounded on a sound too short to have one",
        when="a seam_flux bound in a one-shot effect's spec, which only a loop has",
        doors=("bound loudness, peak or duration instead",
               "bound the seam on the loop it belongs to"),
    ),
    "spec.unbounded-measure": Code(
        means="the measure answers with something a bound cannot hold",
        when="a bound on a measure that returns a set or a colour rather than a number",
        doors=("bound a statistic of it instead",),
    ),
    "review.unknown-item": Code(
        means="a revision names an item the inventory does not list",
        when="revision.ask given a name or a path project.inventory has no row for "
        "(§PW301)",
        doors=("name the item by the id project.inventory gives it",),
    ),
    "review.no-words": Code(
        means="a revision was asked with nothing said",
        when="revision.ask given empty words",
        doors=("pass what the person asked for, in their words",),
    ),
    "review.no-mask": Code(
        means="the mask a revision names is not on disk",
        when="revision.ask given a mask path with no file there",
        doors=("pass a mask image under the project",),
    ),
    "review.bad-span": Code(
        means="a revision's span is not a stretch of time",
        when="span not two numbers, a negative start, or a start not before the end",
        doors=("pass [start, end] in seconds",),
    ),
    "review.not-open": Code(
        means="the revision named is not an open one",
        when="revision.close on an id never asked, or one already closed",
        doors=("close one revision.open lists",),
    ),
    "review.unanswered": Code(
        means="a revision was closed with neither an answer nor a reason",
        when="revision.close without run and sitting together, or without withdrawn, "
        "or with both",
        doors=(
            "pass the run and the sitting that answered it",
            "pass withdrawn with the reason",
        ),
    ),
    "spec.no-subject": Code(
        means="a render was asked of a spec's subject and the spec names none",
        when="render.bake given a spec, and no model, where the spec has no `subject` "
        "(§PW298)",
        doors=(
            "pass the mesh as `model`",
            'add subject = "<declaration>.toml" to the spec',
        ),
    ),
    "spec.subject-not-declaration": Code(
        means="a spec's `subject` names something that is not a geometry declaration",
        when="a mesh, a picture or another spec given where the declaration whose "
        "build the spec measures belongs (§PW298)",
        doors=("name the declaration's .toml, as a path under the project",),
    ),
    "spec.subject-unbuilt": Code(
        means="the declaration a spec names as its subject has no build to render",
        when="no mesh record names that declaration as its input, or the mesh it names "
        "is gone (§PW298)",
        doors=("build the declaration with geometry.build",),
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


def area_of(code: str) -> str:
    return code.split(".", 1)[0]


@functools.cache
def _every() -> tuple[dict[str, str], dict[str, Code], dict[str, str]]:
    """The kernel's codes and every layer's, with the layer that owns each (§PW507).

    Built on the first read rather than on import: `errors` imports this module, and
    the layers are found by a walk that imports `errors`. A layer's code must sit in an
    area that layer declares, and neither a code nor an area may be declared twice.
    """
    from .errors import PolyweaveError
    from .layer import layers

    areas, codes, owner = dict(KERNEL_AREAS), dict(KERNEL_CODES), {}
    for name, declared in layers().items():
        if not declared.codes:
            continue
        module = importlib.import_module(declared.codes)
        for area, about in module.AREAS.items():
            if area in areas:
                raise PolyweaveError(
                    "layer.declared-twice",
                    f"layer {name} declares the error area {area!r}, which is taken",
                    "keep the area in the layer that owns it, and drop it elsewhere",
                    given=area,
                )
            areas[area] = about
        for code, one in module.CODES.items():
            if area_of(code) not in module.AREAS or code in codes:
                raise PolyweaveError(
                    "layer.declared-twice",
                    f"layer {name} declares {code!r}, which is outside its own areas "
                    "or declared already",
                    "declare it once, under an area the declaring layer owns",
                    given=code,
                )
            codes[code], owner[code] = one, name
    return areas, codes, owner


def __getattr__(name: str):
    # `AREAS` and `CODES` read as they always did, as the whole union (§PW507).
    if name == "AREAS":
        return _every()[0]
    if name == "CODES":
        return _every()[1]
    raise AttributeError(name)


def known(code: str) -> bool:
    # The kernel's own first: a refusal raised while the layers are being walked must
    # not need the walk to finish to be raised.
    return code in KERNEL_CODES or code in _every()[1]


def owner_of(code: str) -> str | None:
    """The layer that declares a code, or None for one the kernel declares."""
    return None if code in KERNEL_CODES else _every()[2].get(code)


def in_area(area: str) -> list[str]:
    return sorted(c for c in _every()[1] if area_of(c) == area)
