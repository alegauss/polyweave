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


@dataclass(frozen=True)
class Code:
    means: str
    when: str
    doors: tuple[str, ...] = field(default_factory=tuple)


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
    # -- spec: the vocabularies a caller names things by ---------------------
    "spec.unknown-code": Code(
        means="the code asked about is not one this plugin publishes",
        when="an explain names a code that does not exist, usually a misspelling",
        doors=("list the codes", "name one of the near matches"),
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
