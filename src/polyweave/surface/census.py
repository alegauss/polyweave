"""What of this package a caller can find without reading it (§PW124).

`describe` knew one operation, and every function added since arrived as plain Python,
so the rest of the surface was known only to a reader of docstrings: the failure
CLAUDE.md names, a feature that needs a source read to use. Shio's lesson is about
order — a consistency defect became a permanent guard and a reachability defect a
one-off fix that came back — so the instrument comes first.

Every public function in the package is exactly one of three things:

- **registered**: an `@operation`, which `describe` returns;
- **entry**: a read a caller starts from (`capabilities`, `describe`, `explain`), which
  is how everything else is found;
- **internal** or **pending**, by its module, with the reason. Internal is a helper an
  operation calls and a caller never needs. Pending is surface not yet registered, and
  `capabilities()` names it so it is at least findable. That list only shrinks:
  `tests/test_census.py` pins its size, and a module registered comes off it.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

#: The reads a caller starts from, by `module:function`.
ENTRY = {
    "polyweave.surface.capabilities:capabilities": (
        "what this machine can do, the first read"),
    "polyweave.kernel.describe:describe": "one operation's parameters",
    "polyweave.kernel.describe:operations": "every operation's name",
    "polyweave.kernel.describe:validate": "a call checked against what it declared",
    "polyweave.kernel.errors:explain": "what a code means and how to answer it",
    "polyweave.kernel.errors:codes": "every code, or one area's",
    "polyweave.surface.census:census": "what is registered, and what is still pending",
    "polyweave.surface.cli:main": "the command line",
    "polyweave:readable": "a runner's output made UTF-8 before it prints",
}

#: Every other module with public functions: internal, or pending registration. A key
#: may also be one `module:function`, for a helper left in a module that is registered.
CORE: dict[str, tuple[str, str]] = {
    # -- functions left in a registered module --------------------------------------
    "polyweave.loop.accept:read": (
        "internal", "a Spec in process; accept.check reads it"),
    "polyweave.loop.accept:parse": (
        "internal", "a Spec from a table already in memory"),
    "polyweave.loop.accept:check": (
        "internal", "the in-process check, on a Spec object"),
    "polyweave.loop.accept:margin": ("internal", "one predicate's margin"),
    "polyweave.loop.accept:headroom": ("internal", "one predicate's headroom"),
    "polyweave.loop.search": (
        "internal", "the search's parts; search.sweep is the whole"),
    "polyweave.loop.calibrate": (
        "internal", "the parts calibrate.run and .apply assemble"),
    "polyweave.loop.loop:recording": (
        "internal", "in process only: bakes report into it"),
    "polyweave.loop.loop:bake_seen": ("internal", "what a bake calls on its way out"),
    "polyweave.loop.loop:overruled": ("internal", "one run's count, in loop.finish"),
    "polyweave.loop.trace": ("internal", "search.sweep writes it, trace.read reads it"),
    "polyweave.kernel.provenance": ("internal", "what producers use to write a record"),
    "polyweave.loop.measure": (
        "internal", "the arithmetic under measure.take and .same"),
    "polyweave.surface.adoption:scan": (
        "internal", "each surface's files; project.adoption"),
    "polyweave.loop.person": (
        "internal", "the codes and guards an accept is checked by"),
    "polyweave.loop.verdict:address": (
        "internal", "a sitting's page path; verdict.sitting"),
    "polyweave.loop.review:waiting_at": (
        "internal", "each waiting sitting's link; review"),
    "polyweave.loop.verdict:kept_answers": (
        "internal", "every answer, at its sitting now"),
    "polyweave.loop.verdict:answering": (
        "internal", "a sitting's answers since it was laid out"),
    "polyweave.loop.verdict:unanswered": (
        "internal", "a sitting's families with no answer since"),
    "polyweave.loop.verdict:members_of": (
        "internal", "a sheet's members, checked first"),
    "polyweave.surface.revision:hooked": (
        "internal", "the `hook revision` verb's answer"),
    "polyweave.surface.revision:paid": (
        "internal", "the paid tools a revision always asks"),
    "polyweave.loop.review_text": (
        "internal", "a sitting's words, from the catalogs"),
    "polyweave.loop.review:sittings": (
        "internal", "the sittings laid out; review.state"),
    "polyweave.loop.review:difference": ("internal", "the compare map; review.compare"),
    "polyweave.loop.review:answer": ("internal", "the page's write; review.answer"),
    "polyweave.loop.review:newest": (
        "internal", "the package's newest code, for staleness"),
    "polyweave.loop.review:staleness": (
        "internal", "whether the code changed under it"),
    "polyweave.loop.review:server": (
        "internal", "the local page's server, behind `review`"),
    "polyweave.loop.review:run": ("internal", "serve the page until interrupted"),
    "polyweave.kernel.provenance:internal": (
        "internal", "whether a file is kept internal"),
    "polyweave.kernel.provenance:leaked": (
        "internal", "tracked files kept internal; verify"),
    "polyweave.surface.cli": (
        "internal", "the command line's own parsing and printing"),
    "polyweave.services.client": (
        "internal", "every paid service's request, key, price and bytes"),
    "polyweave.services.purchase": ("internal", "what a fetch writes when it has paid"),
    "polyweave.services.service": (
        "internal", "the adapter seam and the one buy every purchase goes through"),
    "polyweave.services.elevenlabs": ("internal", "ElevenLabs' adapter"),
    "polyweave.services.ideogram": ("internal", "Ideogram's adapter"),
    "polyweave.services.meshy": ("internal", "Meshy's adapter"),
    "polyweave.services.tripo": ("internal", "Tripo's adapter"),
    "polyweave.services.rodin": ("internal", "Rodin's adapter"),
    "polyweave.services.scenario": ("internal", "Scenario's adapter"),
    "polyweave.services.schema": (
        "internal", "learning the schema, which sends requests"),
    "polyweave.loop.verdict:record_answer": ("internal", "the page's answer, appended"),
    "polyweave.loop.loop:held": ("internal", "the open run kept between calls"),
    "polyweave.loop.loop:judging": (
        "internal", "the run verdict.judge opens with asset="),
    "polyweave.loop.loop:was_made": (
        "internal", "a run that made its asset, not a verdict"),
    "polyweave.surface.project:proposed": (
        "internal", "the tables, inside project.init"),
    "polyweave.surface.project:wire": ("internal", "project.init's agent half"),
    "polyweave.surface.project:agent_section": (
        "internal", "the AGENTS.md section, drawn"),
    # -- internal: helpers an operation calls, never a caller's first call ----------
    "polyweave.kernel.cache": (
        "internal", "the render cache, reached through bake's cached"),
    "polyweave.surface.census": ("internal", "this census's own walk"),
    "polyweave.surface.migrate": (
        "internal", "the `migrate` verb's rewrite across the layout break"),
    "polyweave.surface.commands": (
        "internal", "the command line derived from the registry"),
    "polyweave.surface.server": (
        "internal", "the MCP server derived from the registry"),
    "polyweave.kernel.doors": (
        "internal", "a remedy's call as data, carried by errors"),
    "polyweave.kernel.codes": (
        "internal", "the code table, read through errors.explain"),
    "polyweave.kernel.config": (
        "internal", "the project file, reported by capabilities"),
    "polyweave.kernel.describe": ("internal", "the registry's own machinery"),
    "polyweave.kernel.layer": ("internal", "each layer's declaration, for describe"),
    "polyweave.kernel.git": ("internal", "a committed file read back, for a sitting"),
    "polyweave.kernel.errors": ("internal", "the error type and its lookup"),
    "polyweave.kernel.files": ("internal", "atomic writes"),
    "polyweave.kernel.image": ("internal", "one image loader under every measure"),
    "polyweave.kernel.jobs.children": ("internal", "a worker's process tree"),
    "polyweave.kernel.jobs.process": ("internal", "starting a worker"),
    "polyweave.kernel.jobs.record": ("internal", "a job's record on disk"),
    "polyweave.kernel.jobs.stages": (
        "internal", "the stage vocabulary, in capabilities"),
    "polyweave.kernel.jobs.worker": ("internal", "the worker's own loop"),
    "polyweave.kernel.post": (
        "internal", "assertions every operation runs on its output"),
    "polyweave.kernel.post.files": ("internal", "an assertion"),
    "polyweave.kernel.post.mesh": ("internal", "an assertion"),
    "polyweave.kernel.post.pixels": ("internal", "an assertion"),
    "polyweave.kernel.post.voxels": ("internal", "an assertion"),
    "polyweave.loop.extend": (
        "internal", "a project's own measures, which accept.check and "
        "measure.available read"),
    "polyweave.loop.ladder": (
        "internal", "the rung map, answered by render.plan"),
}


def public() -> dict[str, str]:
    """Every public function in the package, as `module:function` to its module."""
    import polyweave

    out = {"polyweave:readable": "polyweave"}
    for found in pkgutil.walk_packages(polyweave.__path__, "polyweave."):
        if found.name.endswith("__main__"):
            continue  # running it is the command line
        module = importlib.import_module(found.name)
        for name, value in vars(module).items():
            if (
                not name.startswith("_")
                and inspect.isfunction(value)
                and value.__module__ == found.name
            ):
                out[f"{found.name}:{name}"] = found.name
    return out


def classified() -> dict[str, tuple[str, str]]:
    """The core's helpers and every layer's, each with its kind and reason (§PW511).

    A layer lists only its own: an entry naming a module outside the layer that lists
    it is refused, since two places classifying one module is how they come to differ.
    """
    from polyweave.kernel.errors import PolyweaveError
    from polyweave.kernel.layer import layer_of, layers

    found = dict(CORE)
    for name, declared in layers().items():
        for key, said in declared.census.items():
            if layer_of(key.split(":")[0]) != name or key in found:
                raise PolyweaveError(
                    "layer.declared-twice",
                    f"layer {name} classifies {key}, which is not its own to classify",
                    "list it in the layer.py of the layer it is inside",
                    given=key,
                )
            found[key] = said
    return found


def census() -> dict:
    """Every public function, as registered, entry, internal or pending."""
    from polyweave.kernel.describe import _REGISTRY, load

    load()
    registered = {op.target for op in _REGISTRY.values()}
    listed = classified()
    found: dict[str, list[str]] = {
        "registered": [],
        "entry": [],
        "internal": [],
        "pending": [],
        "unclassified": [],
    }
    for target, module in sorted(public().items()):
        if target in registered:
            found["registered"].append(target)
        elif target in ENTRY:
            found["entry"].append(target)
        elif target in listed:
            # A function listed by itself, where its module is otherwise registered.
            found[listed[target][0]].append(target)
        elif module in listed:
            found[listed[module][0]].append(target)
        elif module.rsplit(".", 1)[-1].startswith("_"):
            # Internal by its own name, the convention Python already reads (§PW511).
            found["internal"].append(target)
        else:
            found["unclassified"].append(target)
    return found


def pending_modules() -> dict[str, str]:
    """The modules still to register, with what each is for, for `capabilities`."""
    return {
        module: reason
        for module, (kind, reason) in classified().items()
        if kind == "pending" and ":" not in module
    }
