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
MODULES: dict[str, tuple[str, str]] = {
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
    "polyweave.layers.engine.port:read": (
        "internal", "a family file checked, inside port.run"),
    "polyweave.layers.engine.port:port": (
        "internal", "port.run with its renderer as a test hook"),
    "polyweave.loop.trace": ("internal", "search.sweep writes it, trace.read reads it"),
    "polyweave.kernel.provenance": ("internal", "what producers use to write a record"),
    "polyweave.layers.geometry.units": (
        "internal", "a rectangle's arithmetic, inside units.check"),
    "polyweave.loop.measure": (
        "internal", "the arithmetic under measure.take and .same"),
    "polyweave.layers.geometry.cost": (
        "internal", "the readers under cost.read and a cost predicate"),
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
    "polyweave.layers.engine.contrast:targets_in": (
        "internal", "the targets a log's lines name"),
    "polyweave.layers.engine.contrast:contrasts": (
        "internal", "each target against its ring"),
    "polyweave.layers.engine.states:machines": (
        "internal", "each enum state machine in a script"),
    "polyweave.layers.engine.states:held": (
        "internal", "one machine's unreachable and stuck states"),
    "polyweave.layers.engine.presets:combinations": (
        "internal", "every grid combination to run"),
    "polyweave.layers.engine.presets:choose": (
        "internal", "each preset's run within its budget"),
    "polyweave.layers.engine.perf:held": (
        "internal", "a run's measures against budget and baseline"),
    "polyweave.layers.engine.tables:schema": (
        "internal", "every table a project declares"),
    "polyweave.layers.engine.tables:rows": (
        "internal", "one table file's rows and lines"),
    "polyweave.layers.engine.tables:check_table": (
        "internal", "one table's rows held to it"),
    "polyweave.layers.engine.tables:generated": (
        "internal", "the typed script a table loads by"),
    "polyweave.layers.engine.testing:declared": (
        "internal", "a project's test convention"),
    "polyweave.layers.engine.testing:read": (
        "internal", "one test run's counts and failures"),
    "polyweave.layers.engine.integrity:scan": ("internal", "the tree read as text"),
    "polyweave.surface.adoption:scan": (
        "internal", "each surface's files; project.adoption"),
    "polyweave.loop.person": (
        "internal", "the codes and guards an accept is checked by"),
    "polyweave.layers.engine.runs:declared": ("internal", "each [run.<name>], checked"),
    "polyweave.layers.engine.pack:files_in": (
        "internal", "a pack's file table; game.pack"),
    "polyweave.layers.engine.pack:source_of": (
        "internal", "an imported file's source; game.pack"),
    "polyweave.loop.verdict:address": (
        "internal", "a sitting's page path; verdict.sitting"),
    "polyweave.loop.review:waiting_at": (
        "internal", "each waiting sitting's link; review"),
    "polyweave.layers.engine.integrity:parsed": (
        "internal", "every script parsed after an import"),
    "polyweave.layers.engine.flashes:is_flash": (
        "internal", "whether a spec bounds a run's flashes"),
    "polyweave.layers.engine.flashes:count": (
        "internal", "each kind's worst second over frames"),
    "polyweave.layers.engine.flashes:measured": (
        "internal", "what a flashes bound reads"),
    "polyweave.loop.verdict:kept_answers": (
        "internal", "every answer, at its sitting now"),
    "polyweave.layers.store.video:is_video": (
        "internal", "whether a spec's measure is a video's"),
    "polyweave.layers.reference.reference_concept:is_concept": (
        "internal", "whether a spec's measure is a concept region's"),
    "polyweave.layers.reference.reference_concept:concept_value": (
        "internal", "one concept measure, which accept.check reads for a predicate"),
    "polyweave.layers.store.video:measured": (
        "internal", "what a video bound reads, off the MP4"),
    "polyweave.layers.store.video:read": (
        "internal", "a cut's clips, checked; video.cut"),
    "polyweave.layers.store.store:thinnest": (
        "internal", "a logo's thinnest stroke at a scale"),
    "polyweave.layers.geometry.cost:bounds": (
        "internal", "a .glb's stored extent (§PW451)"),
    "polyweave.layers.words.svgtext:texts": (
        "internal", "every <text> in an SVG (§PW453)"),
    "polyweave.layers.words.svgtext:outlined": (
        "internal", "an SVG's live text replaced by glyph outlines (§PW453)"),
    "polyweave.loop.verdict:members_of": (
        "internal", "a sheet's members, checked first"),
    "polyweave.layers.vfx.vfx:checked": (
        "internal", "an effect's table, with defaults"),
    "polyweave.layers.vfx.vfx:measured": (
        "internal", "an effect's measures from its declaration"),
    "polyweave.layers.vfx.vfx:scene": (
        "internal", "an effect as the Godot scene build writes"),
    "polyweave.layers.vfx.vfx:is_effect": (
        "internal", "whether a spec's measure is an effect's"),
    "polyweave.layers.vfx.vfx:measures_of": (
        "internal", "a built effect's measures, for accept"),
    "polyweave.layers.vfx.vfx:declared": (
        "internal", "one effect, or one made of parts"),
    "polyweave.layers.picture.panel:declared": (
        "internal", "a panel's states, checked; panel.build"),
    "polyweave.layers.picture.panel:wipe": (
        "internal", "a wipe's kind and uniforms, for panel.build"),
    "polyweave.loop.revision:hooked": ("internal", "the `hook revision` verb's answer"),
    "polyweave.loop.revision:paid": (
        "internal", "the paid tools a revision always asks"),
    "polyweave.loop.review_text": (
        "internal", "a sitting's words, from the catalogs"),
    "polyweave.layers.vfx.vfx:measured_whole": (
        "internal", "a whole's measures, over its parts"),
    "polyweave.layers.vfx.vfx:scene_whole": (
        "internal", "a whole's scene, its parts under one"),
    "polyweave.layers.vfx.vfx:shipped_folder": (
        "internal", "where a built scene lands, shipped"),
    "polyweave.layers.vfx.vfx:settle_rate": (
        "internal", "a struck piece's decay, from its life"),
    "polyweave.layers.vfx.vfx:swing": ("internal", "a struck piece's swing at an age"),
    "polyweave.layers.engine.driving:left_out": (
        "internal", "why the export leaves a path out"),
    "polyweave.loop.review:sittings": (
        "internal", "the sittings laid out; review.state"),
    "polyweave.loop.review:looked_at": ("internal", "the gate runs; review.state"),
    "polyweave.loop.review:turntables": ("internal", "the turntables; review.state"),
    "polyweave.loop.review:difference": ("internal", "the compare map; review.compare"),
    "polyweave.loop.review:answer": ("internal", "the page's write; review.answer"),
    "polyweave.loop.review:newest": (
        "internal", "the package's newest code, for staleness"),
    "polyweave.loop.review:staleness": (
        "internal", "whether the code changed under it"),
    "polyweave.loop.review:server": (
        "internal", "the local page's server, behind `review`"),
    "polyweave.loop.review:run": ("internal", "serve the page until interrupted"),
    "polyweave.layers.reference.reference_objects:declared": (
        "internal", "the kinds, checked"),
    "polyweave.kernel.provenance:internal": (
        "internal", "whether a file is kept internal"),
    "polyweave.kernel.provenance:leaked": (
        "internal", "tracked files kept internal; verify"),
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
    "polyweave.layers.motion.camera:checked": (
        "internal", "a camera clip's table, with defaults"),
    "polyweave.layers.motion.camera:measured": ("internal", "a camera clip's measures"),
    "polyweave.layers.motion.camera:scene": (
        "internal", "a camera clip as the scene build writes"),
    "polyweave.layers.motion.camera:eased": (
        "internal", "a drift's easing, as the scene eases it"),
    "polyweave.layers.motion.camera:shot_at": (
        "internal", "the shot showing at a moment"),
    "polyweave.layers.motion.camera:at": (
        "internal", "the camera at a moment, as the scene frames"),
    "polyweave.layers.sound.licences": (
        "internal", "the instruments a sound's record names"),
    "polyweave.surface.cli": (
        "internal", "the command line's own parsing and printing"),
    "polyweave.layers.geometry": (
        "internal", "a declaration's machinery; geometry.build"),
    "polyweave.layers.geometry.build": ("internal", "the mesh a build writes"),
    "polyweave.layers.geometry.review": (
        "internal", "the words geometry.describe says"),
    "polyweave.layers.geometry.tuning": (
        "internal", "a shape search, with callable hooks"),
    "polyweave.layers.geometry.voxels": ("internal", "the voxel model a build writes"),
    "polyweave.services.purchase": ("internal", "what a fetch writes when it has paid"),
    "polyweave.services.schema": (
        "internal", "learning the schema, which sends requests"),
    "polyweave.layers.picture.style": (
        "internal", "compose and admit; verdict.judge is admit's door"),
    "polyweave.loop.verdict:record_answer": ("internal", "the page's answer, appended"),
    "polyweave.layers.picture.variation:person_marked": (
        "internal", "a person's mark, inside vary"),
    "polyweave.layers.picture.picture:gates": (
        "internal", "the gate's log, read by the review page"),
    "polyweave.layers.picture.picture:sent_bytes": (
        "internal", "a picture as every upload sends it"),
    "polyweave.layers.engine.capture": (
        "internal", "the environment's parts, inside capture.run"),
    "polyweave.layers.engine.driving": (
        "internal", "the socket call every game.* operation makes"),
    "polyweave.layers.engine.engine": (
        "internal", "run with its launch hook, behind engine.run"),
    "polyweave.layers.engine.offscreen": (
        "internal", "a route as an object; offscreen.routes"),
    "polyweave.layers.geometry.shape": (
        "internal", "silhouette with its bake hook, and the gate"),
    "polyweave.layers.reference.reference": (
        "internal", "the cut and its tests, inside .prepare"),
    "polyweave.layers.geometry.normalise": (
        "internal", "a mesh's maths, in memory, inside ingest"),
    "polyweave.layers.store.compose": (
        "internal", "the Image objects compose.place returns"),
    "polyweave.layers.geometry.texture": (
        "internal", "the scrub on pixels in memory, in the bake"),
    "polyweave.layers.motion.clip": (
        "internal", "compiling needs a mesh and a rig: motion.bake"),
    "polyweave.layers.motion.skeleton": (
        "internal", "fitting a mesh in memory: motion.bake"),
    "polyweave.layers.motion.sprites": (
        "internal", "baking needs a mesh and a rig: motion.bake"),
    "polyweave.layers.words.world:find": (
        "internal", "which world file, inside world.read"),
    "polyweave.layers.words.world:declared": (
        "internal", "the parsed world, for words.check"),
    "polyweave.layers.words.world:brief": (
        "internal", "one entity, for a purchase's entity="),
    "polyweave.layers.words.world:described": (
        "internal", "an entity's look as a prompt"),
    "polyweave.layers.words.world:look_digest": (
        "internal", "what a purchase records it drew"),
    "polyweave.layers.words.world:still_drawn": (
        "internal", "provenance.outdated, per entity"),
    "polyweave.layers.words.world:still": (
        "internal", "the world role's staleness check"),
    "polyweave.layers.words.world:voice_in": (
        "internal", "a locale's voice over the shared one"),
    "polyweave.layers.sound.sound_buy:language_of": (
        "internal", "voice.lines' language_code"),
    "polyweave.layers.words.world:voice_digest": (
        "internal", "what a spoken line records"),
    "polyweave.layers.words.world:voiced": (
        "internal", "sound.speak's entity, read once"),
    "polyweave.layers.words.world:keep_voice": ("internal", "voice.choose's one write"),
    "polyweave.layers.words.words:said_digest": (
        "internal", "what a spoken take records"),
    "polyweave.layers.store.icons:read": (
        "internal", "icons.build's declaration, resolved"),
    "polyweave.loop.loop:held": ("internal", "the open run kept between calls"),
    "polyweave.layers.kits:read": ("internal", "one kit.toml, checked"),
    "polyweave.layers.kits:every": (
        "internal", "every kit the plugin carries, checked"),
    "polyweave.layers.kits:behind": ("internal", "provenance.outdated's kits"),
    "polyweave.loop.loop:judging": (
        "internal", "the run verdict.judge opens with asset="),
    "polyweave.loop.loop:was_made": (
        "internal", "a run that made its asset, not a verdict"),
    "polyweave.layers.sound.sfx:hz": ("internal", "a note name as Hz"),
    "polyweave.layers.words.words:characters": ("internal", "a font's character map"),
    "polyweave.layers.sound.sfx:tuned": (
        "internal", "an effect's notes as sfxr's numbers"),
    "polyweave.layers.sound.sound:note_of": ("internal", "a pitch as its nearest note"),
    "polyweave.layers.store.icons:draw": ("internal", "one icon at one size"),
    "polyweave.layers.store.icons:legibility": (
        "internal", "what icons.build holds a set to"),
    "polyweave.layers.words.words:still_said": (
        "internal", "provenance.outdated, per row"),
    "polyweave.layers.words.words:still": (
        "internal", "the words role's staleness check"),
    "polyweave.layers.picture.picture:from_world": (
        "internal", "entity= on picture and mesh.buy"),
    "polyweave.layers.picture.scenario:serves": (
        "internal", "whether a service is Scenario (§PW450)"),
    "polyweave.layers.picture.scenario:trained_model": (
        "internal", "the model a family's canon trained (§PW450)"),
    "polyweave.layers.picture.scenario:bought": (
        "internal", "picture.buy on Scenario, from the trained model (§PW450)"),
    "polyweave.layers.words.words:table": (
        "internal", "the string table, inside words.check"),
    "polyweave.layers.words.words:held": (
        "internal", "every verdict on a line, oldest first"),
    "polyweave.layers.words.words:verdicts": (
        "internal", "the latest verdict on each line"),
    "polyweave.layers.words.words:approved": (
        "internal", "a speaker's canon, in world.read"),
    "polyweave.layers.words.words:judged": (
        "internal", "verdict.judge is the one caller"),
    "polyweave.surface.project:proposed": (
        "internal", "the tables, inside project.init"),
    "polyweave.surface.project:wire": ("internal", "project.init's agent half"),
    "polyweave.surface.project:agent_section": (
        "internal", "the AGENTS.md section, drawn"),
    # -- internal: helpers an operation calls, never a caller's first call ----------
    "polyweave.kernel.cache": (
        "internal", "the render cache, reached through bake's cached"),
    "polyweave.surface.census": ("internal", "this census's own walk"),
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
    "polyweave.layers.geometry.render.blender": ("internal", "bpy, behind the bake"),
    "polyweave.layers.geometry.render.ladder": (
        "internal", "the rung map, answered by render.plan"),
    "polyweave.layers.geometry.render.rig": (
        "internal", "the rig's arithmetic, behind the bake"),
    "polyweave.layers.geometry.expr": ("internal", "a declaration's arithmetic"),
    "polyweave.layers.geometry.solver": ("internal", "a declaration's constraints"),
    "polyweave.layers.geometry.solid": ("internal", "the solid ops a build runs"),
    "polyweave.layers.geometry.outline": ("internal", "the outline ops a build runs"),
    "polyweave.layers.geometry.surface": ("internal", "the surface ops a build runs"),
    "polyweave.layers.geometry.finish": (
        "internal", "a material's finish, read by the bake"),
    "polyweave.layers.geometry.blend": (
        "internal", "the blend op's fields, built by build"),
    "polyweave.layers.geometry.fracture": ("internal", "an op a build runs"),
    "polyweave.layers.geometry.custom": (
        "internal", "the way back to code, called by build"),
    "polyweave.layers.geometry.voxel_colour": ("internal", "a voxel build's palette"),
    "polyweave.layers.geometry.voxel_fit": ("internal", "a voxel build's fitting"),
    "polyweave.layers.geometry.voxel_compare": (
        "internal", "geometry.compare's two models"),
    "polyweave.layers.geometry.voxel_sheet": (
        "internal", "a voxel build's contact sheet"),
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
    from polyweave.kernel.describe import _REGISTRY, load

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
