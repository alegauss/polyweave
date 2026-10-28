"""The engine layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "engine": "running a scene script and reading its verdict",
    "capture": "the environment a picture of the running game is taken in",
    "game": "a game held open between an agent's calls",
    "driver": "the driver inside a held game, answering one command",
    "tables": "a game's data tables, held to the schema of one row",
}

CODES: dict[str, Code] = {
    # -- engine: running a scene script and reading its verdict ---------------
    # -- game: a game held open between an agent's calls ----------------------
    "game.not-listening": Code(
        means="the game never said where its driver listens",
        when="a main scene that fails to load, or a game that quits before its first "
        "frame",
        doors=("read the log the refusal names",),
    ),
    "game.no-session": Code(
        means="no open session has that name in this project",
        when="a session closed, one that idled out, or one from another project",
        doors=("open the game again",),
    ),
    "game.gone": Code(
        means="the game behind the session stopped answering",
        when="a crash, a script that quit, or [driving] idle seconds with no call",
        doors=("read the log", "open the game again"),
    ),
    "game.bad-target": Code(
        means="the call did not say what to act on, or said it two ways",
        when="a query with no path, group or class, or an input with none of its kinds",
        doors=("give exactly one of the targets the operation lists",),
    ),
    "game.no-flow": Code(
        means="there is no flow this driver can replay at that path",
        when="a flow not yet kept, a path relative to somewhere else, or a flow kept "
        "in an older format",
        doors=("keep the flow with game.keep",),
    ),
    "game.no-trace": Code(
        means="there is no run trace to compare at that path, or no pair is declared",
        when="game.compare_runs before the run wrote its trace, or with neither trace "
        "named and no [trace] pairs (§PW612)",
        doors=("name both traces, or declare [trace] pairs",),
    ),
    "game.bad-trace": Code(
        means="a run trace has a line that is not a stamped sample, or a pair is "
        "malformed",
        when="a line with no time or id, a repeated sample, an empty trace, or a "
        "[trace] time that is neither frame nor t (§PW612)",
        doors=("write each line as {frame, id, kind, fields}",),
    ),
    "engine.frame-timed": Code(
        means="a script times play by frames where it should by ticks",
        when="engine.check reads frame-timed play in a script (§PW657)",
        doors=("move it onto the physics clock",),
    ),
    "engine.headless-picture": Code(
        means="a headless sweep was given a script that saves a picture",
        when="engine.sweep without display on a script calling save_png (§PW655)",
        doors=("pass display=true",),
    ),
    "game.no-driver": Code(
        means="the driver a game is launched with is not where this copy of polyweave "
        "says it is",
        when="a copy of polyweave installed over, or removed, under a running server "
        "(§PW651)",
        doors=("restart the MCP server", "install polyweave again"),
    ),
    "game.no-determinism": Code(
        means="the project has no determinism kit, so there is no run to fly again",
        when="game.replay_rates in a game the kit was never installed in (§PW640)",
        doors=("install the determinism kit with kit.install",),
    ),
    "game.bad-rates": Code(
        means="the frame rates asked for cannot be held against one another",
        when="fewer than two rates, a repeated one, or one that is not a whole number "
        "of frames a second from 1 (§PW640)",
        doors=("name two or more distinct frame rates, the first the reference",),
    ),
    "game.flow-broke": Code(
        means="a flow being re-keyed broke on a step, so nothing was written",
        when="game.rekey on a flow the game no longer follows",
        doors=("replay it with game.replay and mend it first",),
    ),
    "game.driver-exported": Code(
        means="an export preset would put the driver into a release",
        when="a preset exporting all resources with no exclusion for the addon, or one "
        "whose include filter pulls it in",
        doors=('add "addons/polyweave_driver/*" to the preset\'s exclude_filter',),
    ),
    "game.driver-autoloaded": Code(
        means="an autoload loads the driver in every run of the game",
        when="the driver registered as an autoload by hand, when it is meant to be "
        "launched with --script",
        doors=("remove the autoload from project.godot",),
    ),
    "game.part-not-licensed": Code(
        means="a file in a sold game was made on a plan licensing it non-commercially",
        when="game.release_check where [project] sells and a record's plan is free, "
        "as the service said or [service] plan declared (§PW448)",
        doors=("make it again on a paid plan", "set [project] sells = false"),
    ),
    "game.driver-in-pack": Code(
        means="an exported pack holds the driver's files",
        when="a pack exported before the preset excluded the addon",
        doors=("exclude the addon from the preset and export again",),
    ),
    "game.pack-unread": Code(
        means="the pack cannot be read: its directory is encrypted, it is no Godot "
        "pack, or its format is older than 4",
        when="a release exported with directory encryption on, or a file that is not "
        "a .pck",
        doors=("rely on the preset check", "export without directory encryption"),
    ),
    "game.pack-unwritten": Code(
        means="game.pack's export wrote no pack (§PW470)",
        when="a preset name export_presets.cfg does not hold, or an export Godot "
        "abandoned",
        doors=("check the preset's name", "read what Godot printed in the detail"),
    ),
    "game.no-pack": Code(
        means="there is no exported pack at the path given",
        when="a release not yet exported, or a path relative to somewhere else",
        doors=("export first", "check the presets alone by leaving pack out"),
    ),
    "game.refused": Code(
        means="the driver refused a command without naming why",
        when="a driver older than this plugin",
        doors=("install the driver again with godot.install",),
    ),
    # -- driver: the driver inside a held game --------------------------------
    "driver.bad-token": Code(
        means="the token does not match the one the driver printed",
        when="a session file from an earlier run of the game",
        doors=("open the game again",),
    ),
    "driver.bad-command": Code(
        means="a command the driver does not know, or one missing a field",
        when="a caller written against another version of docs/specs/driving.md",
        doors=("read the commands in docs/specs/driving.md",),
    ),
    "driver.no-node": Code(
        means="the path, group or class finds nothing in the running game",
        when="a node not yet created, or a path relative to the wrong node",
        doors=("query a parent to see what is there", "wait for the node first"),
    ),
    "driver.no-method": Code(
        means="the node has no method of that name",
        when="a setup method the game does not expose",
        doors=("call a method the node declares",),
    ),
    "driver.no-picture": Code(
        means="the game draws nothing, so there is no picture to save",
        when="a shot in a session opened headless",
        doors=("open the game with display",),
    ),
    "driver.shot-not-written": Code(
        means="the shot was asked for and no file was written",
        when="a folder that cannot be made, or the engine failing to save the PNG; "
        "the message carries the engine's error, and no out is answered for a file "
        "that is not there",
        doors=("name a folder under the project the game can write to",),
    ),
    "driver.off-screen": Code(
        means="the click lands outside the viewport, where nothing is hovered",
        when="a point past the declared window size, or a node scrolled off screen",
        doors=("click inside the viewport", "set display/window/size in project.godot"),
    ),
    "game.no-preset": Code(
        means="game.export_smoke found no export_presets.cfg to export from",
        when="a project no one has set an export preset up in (§PW363)",
        doors=("add a preset for this platform in the editor's Export dialog",),
    ),
    "game.no-capture": Code(
        means="game.crash_read found no capture to read, or the file named is none",
        when="a game that never opened the crash kit's log, or a file that is no "
        "capture (§PW361)",
        doors=("install the crash kit and open its log first thing",
               "name the capture a person sent"),
    ),
    "driver.no-state": Code(
        means="game.query asked for declared state, and the game carries no state kit",
        when="state= on a game that never installed the state kit (§PW359)",
        doors=("kit.install state, then name the state in res://polyweave_state.gd",),
    ),
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
    "engine.bad-grid": Code(
        means="a sweep's grid gives an argument no values, or values not as a list",
        when="a grid of scalars, or an empty one",
        doors=('give grid as {"seed": [1, 2, 3]}, one list per argument',),
    ),
    "engine.cost-no-revision": Code(
        means="a frame cost names a revision git cannot find, or runs outside git",
        when="engine.cost with against or on naming no commit",
        doors=("name a commit, branch or tag the repository has",),
    ),
    "engine.cost-import": Code(
        means="a revision's worktree did not import cleanly before it was timed",
        when="engine.cost against a revision whose resources the editor cannot load",
        doors=("open that revision in the editor once", "name another revision"),
    ),
    "engine.cost-same": Code(
        means="a frame cost was asked to compare a build with itself",
        when="engine.cost with on and against naming the same thing",
        doors=("leave on unset for the working tree, and name against",),
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
    "engine.budget-ended": Code(
        means="the frame budget ended the run before the script printed its line",
        when="a script whose own frame count, printed as `frames: N`, reached the "
        "run's frame budget, as a long simulation does at the default 6000 (§PW487)",
        doors=("pass a larger frames", "print the line sooner"),
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
    "capture.internal-input": Code(
        means="a capture would run on something derived from internal footage",
        when="a scene script, or a path among its arguments, whose record or an "
        "input's says internal (§PW407)",
        doors=("run the capture on the game's own scene and files",),
    ),
    "capture.bad-transcription": Code(
        means="a transcription read from a reference video cannot be checked",
        when="a file not JSON or TOML, no rows, a row with no id or span, a row "
        "missing a column, or one citing a frame or track that does not exist",
        doors=("cite the frames or reference.objects tracks each row was read from",),
    ),
    "capture.unknown-reference": Code(
        means="the reference video named is not one the project declares",
        when="a name no [reference.<name>] table carries, or none where several do",
        doors=("name one the answer lists",
               "declare [reference.<name>] with its size and regions"),
    ),
    "capture.bad-concept": Code(
        means="a capture cannot be held to its concept painting as declared",
        when="a *.concept.toml missing or not TOML, naming no painting file or no "
        "region, a region without both rectangles, a rectangle that runs off its "
        "picture, or a capture that is not there (§PW477)",
        doors=(
            "write each [region.<name>] with painting and capture as [x, y, w, h]",
            "measure each rectangle on the picture it names",
        ),
    ),
    "capture.unknown-region": Code(
        means="the region named is not the reference's, or it declares no minimap",
        when="a region name the [reference.<name>] regions do not carry, or a minimap "
        "read on a reference that names none",
        doors=("name one of its regions", "set its minimap to one of its regions"),
    ),
    "capture.wrong-size": Code(
        means="the frames are not the size the reference's regions were declared at",
        when="frames read from another video, or the video resampled",
        doors=("read the frames from the video the regions were taken from",
               "declare the reference again at this size"),
    ),
    "capture.no-reference-frames": Code(
        means="there are no frames to count objects in",
        when="a folder or frames.json reference.frames never wrote",
        doors=("name the folder reference.frames wrote, or its frames.json",),
    ),
    "capture.bad-kinds": Code(
        means="the kinds of object to look for mean nothing",
        when="no kinds, a colour not written #rrggbb, a size not [least, most] pixels, "
        "a tolerance outside 0 to 1, or an area not [left, top, right, bottom]",
        doors=("declare each kind with its colour and size",),
    ),
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
    "capture.not-visible": Code(
        means="no try saw the capture's subject on screen before the picture was taken",
        when="a moment in play whose spawns vary between runs, or a script that never "
        "prints the `visible: <group>` line it was asked to wait for",
        doors=(
            "print `visible: <group>` once a node of the group is in the camera's view",
            "raise `tries`, or capture a frame the subject is always in",
        ),
    ),
    "capture.no-frames": Code(
        means="what was named as a captured run holds fewer than two frames, or is not "
        "there",
        when="measure.flashes, or a flashes bound in a spec, on a folder capture.movie "
        "never wrote (§PW354)",
        doors=("capture the run with capture.movie and name the folder it wrote",),
    ),
    "engine.no-project": Code(
        means="engine.check was pointed at a folder with no project.godot",
        when="engine.check outside a Godot project (§PW358)",
        doors=("check the Godot project's own folder",),
    ),
    "tables.no-schema": Code(
        means="tables.check found no table schema, or one it cannot read",
        when="no data/tables.toml (or [kit.tables] schema), or a table with no file, "
        "columns or a column type (§PW364)",
        doors=("declare each table, its file and its columns' types",),
    ),
    "engine.unreachable-state": Code(
        means="a state machine's state that nothing assigns and it does not start in",
        when="engine.states reading a script's enum and its assignments (§PW368)",
        doors=("assign it where the game should reach it", "drop it from the enum"),
    ),
    "engine.stuck-state": Code(
        means="a state machine's state that nothing leaves, not marked final",
        when="engine.states finding no assignment out of a state (§PW368)",
        doors=("assign the way out", "mark its enum line # final where that is meant"),
    ),
    "engine.no-budget": Code(
        means="engine.perf found no [perf.<name>] budget to run",
        when="a project that declares no scene's performance budget (§PW365)",
        doors=("declare [perf.<name>]: its scene and the most each measure may be",),
    ),
    "engine.no-tests": Code(
        means="game.test found no test script by the project's convention",
        when="a game with no tests/*_test.gd and no [kit.tests] scripts (§PW362)",
        doors=("write tests/<name>_test.gd", "declare [kit.tests] scripts"),
    ),
    "engine.bad-run": Code(
        means="a [run.<name>] in polyweave.toml cannot be run as written (§PW467)",
        when="a run with no script or no expect, or a key a run does not take",
        doors=("give the run a script and the line that means it worked",),
    ),
    "engine.unknown-run": Code(
        means="engine.run_declared was asked for a run the project does not declare",
        when="a misspelled name, or a run not yet declared as [run.<name>]",
        doors=("declare it in polyweave.toml", "name a declared run"),
    ),
    "engine.broken-reference": Code(
        means="a scene, resource or project.godot refers to a file by a UID and a path "
        "that both resolve to nothing",
        when="a file moved or was deleted without what refers to it (§PW358)",
        doors=("point the reference at the file as it is now", "put the file back"),
    ),
    "engine.moved-reference": Code(
        means="a reference's path is gone but its UID names the file where it is now",
        when="a file moved with its .uid; Godot finds it and warns on every load",
        doors=("engine.check fix=true repoints it",),
    ),
    "engine.stale-uid": Code(
        means="a reference names a UID nothing declares, and Godot falls back to its "
        "path",
        when="a scene written as text, or a resource saved again under a new UID",
        doors=("open and save the scene in the editor", "drop the uid attribute"),
    ),
    "engine.missing-path": Code(
        means="a script names a res:// or uid:// path that is not there",
        when="a script loads a file that moved, or one a project may keep (a warning)",
        doors=("point it at a file that is there", "check it exists before loading"),
    ),
    "engine.orphan-uid": Code(
        means="a .uid file sits beside no file",
        when="a script moved or was deleted without its .uid",
        doors=("engine.check fix=true removes it", "put its file back"),
    ),
    "engine.orphan-import": Code(
        means="an .import file imports a source that is not there",
        when="an asset moved or was deleted without its .import",
        doors=("engine.check fix=true removes it", "put its source back"),
    ),
    "engine.stale-import": Code(
        means="a source changed since Godot last imported it",
        when="an asset written by a tool with no editor open",
        doors=("import it again; engine.check imports where an engine is set",),
    ),
    "engine.parse-error": Code(
        means="a script does not parse, so nothing that loads it works",
        when="engine.check parses every script after an import, with an engine set",
        doors=("fix the line Godot names",),
    ),
    "capture.no-rate": Code(
        means="nothing says at what rate a captured run's frames were taken",
        when="measure.flashes on a folder of PNGs with no sequence.json, no fps passed "
        "and no [engine] fixed_fps",
        doors=("pass fps", "capture with capture.movie, whose sequence.json says it"),
    ),
    "capture.no-ffmpeg": Code(
        means="a loop for the review page is encoded with ffmpeg, and it is not here",
        when="clip.shots given loop, or panel.capture given loop, with no ffmpeg on "
        "PATH (§PW600)",
        doors=("install ffmpeg and put it on PATH", "leave loop out"),
    ),
    "capture.unrecorded": Code(
        means="a picture capture.again was asked to take again has no record of how "
        "it was taken",
        when="no record beside it, a record of another kind, or a capture recorded "
        "before its call was kept",
        doors=("take it once with capture.run, whose record then says how",),
    ),
    "capture.override-held": Code(
        means="a movie or an outsized picture writes an override.cfg, and the project "
        "has one",
        when="capture.movie asked a resolution, or capture.run one past the desktop, "
        "in a project with an override.cfg of its own",
        doors=("set its window overrides to the size for the run",
               "ask no resolution, and take the project's window size"),
    ),
}
