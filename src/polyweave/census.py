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
    "polyweave.capabilities:capabilities": "what this machine can do, the first read",
    "polyweave.describe:describe": "one operation's parameters",
    "polyweave.describe:operations": "every operation's name",
    "polyweave.describe:validate": "a call checked against what it declared",
    "polyweave.errors:explain": "what a code means and how to answer it",
    "polyweave.errors:codes": "every code, or one area's",
    "polyweave.census:census": "what is registered, and what is still pending",
    "polyweave.cli:main": "the command line",
    "polyweave:readable": "a runner's output made UTF-8 before it prints",
}

#: Every other module with public functions: internal, or pending registration. A key
#: may also be one `module:function`, for a helper left in a module that is registered.
MODULES: dict[str, tuple[str, str]] = {
    # -- functions left in a registered module --------------------------------------
    "polyweave.accept:read": ("internal", "a Spec in process; accept.check reads it"),
    "polyweave.accept:parse": ("internal", "a Spec from a table already in memory"),
    "polyweave.accept:check": ("internal", "the in-process check, on a Spec object"),
    "polyweave.accept:margin": ("internal", "one predicate's margin"),
    "polyweave.accept:headroom": ("internal", "one predicate's headroom"),
    "polyweave.search": ("internal", "the search's parts; search.sweep is the whole"),
    "polyweave.calibrate": ("internal", "the parts calibrate.run and .apply assemble"),
    "polyweave.loop:recording": ("internal", "in process only: bakes report into it"),
    "polyweave.loop:bake_seen": ("internal", "what a bake calls on its way out"),
    "polyweave.loop:overruled": ("internal", "one run's count, in loop.finish"),
    "polyweave.port:read": ("internal", "a family file checked, inside port.run"),
    "polyweave.port:port": ("internal", "port.run with its renderer as a test hook"),
    "polyweave.trace": ("internal", "search.sweep writes it, trace.read reads it"),
    "polyweave.provenance": ("internal", "what producers use to write a record"),
    "polyweave.units": ("internal", "a rectangle's arithmetic, inside units.check"),
    "polyweave.measure": ("internal", "the arithmetic under measure.take and .same"),
    "polyweave.cost": ("internal", "the readers under cost.read and a cost predicate"),
    "polyweave.cli": ("internal", "the command line's own parsing and printing"),
    "polyweave.geometry": ("internal", "a declaration's machinery; geometry.build"),
    "polyweave.geometry.build": ("internal", "the mesh a build writes"),
    "polyweave.geometry.review": ("internal", "the words geometry.describe says"),
    "polyweave.geometry.tuning": ("internal", "a shape search, with callable hooks"),
    "polyweave.geometry.voxels": ("internal", "the voxel model a build writes"),
    "polyweave.purchase": ("internal", "what a fetch writes when it has paid"),
    "polyweave.schema": ("internal", "learning the schema, which sends requests"),
    "polyweave.capture": ("internal", "the environment's parts, inside capture.run"),
    "polyweave.engine": ("internal", "run with its launch hook, behind engine.run"),
    "polyweave.offscreen": ("internal", "a route as an object; offscreen.routes"),
    "polyweave.shape": ("internal", "silhouette with its bake hook, and the gate"),
    "polyweave.reference": ("internal", "the cut and its tests, inside .prepare"),
    "polyweave.normalise": ("internal", "a mesh's maths, in memory, inside ingest"),
    "polyweave.compose": ("internal", "the Image objects compose.place returns"),
    "polyweave.texture": ("internal", "the scrub on pixels in memory, in the bake"),
    "polyweave.clip": ("internal", "compiling needs a mesh and a rig: motion.bake"),
    "polyweave.skeleton": ("internal", "fitting a mesh in memory: motion.bake"),
    "polyweave.sprites": ("internal", "baking needs a mesh and a rig: motion.bake"),
    # -- internal: helpers an operation calls, never a caller's first call ----------
    "polyweave.cache": ("internal", "the render cache, reached through bake's cached"),
    "polyweave.census": ("internal", "this census's own walk"),
    "polyweave.commands": ("internal", "the command line derived from the registry"),
    "polyweave.server": ("internal", "the MCP server derived from the registry"),
    "polyweave.doors": ("internal", "a remedy's call as data, carried by errors"),
    "polyweave.codes": ("internal", "the code table, read through errors.explain"),
    "polyweave.config": ("internal", "the project file, reported by capabilities"),
    "polyweave.describe": ("internal", "the registry's own machinery"),
    "polyweave.errors": ("internal", "the error type and its lookup"),
    "polyweave.files": ("internal", "atomic writes"),
    "polyweave.image": ("internal", "one image loader under every measure"),
    "polyweave.jobs.children": ("internal", "a worker's process tree"),
    "polyweave.jobs.process": ("internal", "starting a worker"),
    "polyweave.jobs.record": ("internal", "a job's record on disk"),
    "polyweave.jobs.stages": ("internal", "the stage vocabulary, in capabilities"),
    "polyweave.jobs.worker": ("internal", "the worker's own loop"),
    "polyweave.post": ("internal", "assertions every operation runs on its output"),
    "polyweave.post.files": ("internal", "an assertion"),
    "polyweave.post.mesh": ("internal", "an assertion"),
    "polyweave.post.pixels": ("internal", "an assertion"),
    "polyweave.post.voxels": ("internal", "an assertion"),
    "polyweave.render.blender": ("internal", "bpy, behind the bake"),
    "polyweave.render.ladder": ("internal", "the rung map, answered by render.plan"),
    "polyweave.render.rig": ("internal", "the rig's arithmetic, behind the bake"),
    "polyweave.geometry.expr": ("internal", "a declaration's arithmetic"),
    "polyweave.geometry.solver": ("internal", "a declaration's constraints"),
    "polyweave.geometry.solid": ("internal", "the solid ops a build runs"),
    "polyweave.geometry.outline": ("internal", "the outline ops a build runs"),
    "polyweave.geometry.surface": ("internal", "the surface ops a build runs"),
    "polyweave.geometry.fracture": ("internal", "an op a build runs"),
    "polyweave.geometry.custom": ("internal", "the way back to code, called by build"),
    "polyweave.geometry.voxel_colour": ("internal", "a voxel build's palette"),
    "polyweave.geometry.voxel_fit": ("internal", "a voxel build's fitting"),
    "polyweave.geometry.voxel_sheet": ("internal", "a voxel build's contact sheet"),
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


def census() -> dict:
    """Every public function, as registered, entry, internal or pending."""
    from .describe import _REGISTRY, load

    load()
    registered = {op.target for op in _REGISTRY.values()}
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
        elif target in MODULES:
            # A function listed by itself, where its module is otherwise registered.
            found[MODULES[target][0]].append(target)
        elif module in MODULES:
            found[MODULES[module][0]].append(target)
        else:
            found["unclassified"].append(target)
    return found


def pending_modules() -> dict[str, str]:
    """The modules still to register, with what each is for, for `capabilities`."""
    return {
        module: reason
        for module, (kind, reason) in MODULES.items()
        if kind == "pending" and ":" not in module
    }
