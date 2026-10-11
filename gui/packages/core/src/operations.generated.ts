// Generated from `python -m polyweave describe` by tools/operations_ts.py (§PW377).
// Do not edit: run `python tools/operations_ts.py`. tests/test_operations_ts.py
// fails when this file and describe disagree.

import type { Client } from './client'

/** Check one picture against one spec: each predicate's value, verdict and margin. */
export interface AcceptCheckArgs {
  /** the acceptance spec, as a path under the project */
  spec: string
  /** the picture to check, as a path under the project */
  subject: string
  /** the rung the picture was made at, if known */
  rung?: "sphere" | "preview" | "final" | ""
  /** the project the paths resolve against; default "." */
  root?: string
}

/** The same spec, held to where the asset stands in a capture (§PW112). */
export interface AcceptCheckScreenArgs {
  /** the acceptance spec, as a path under the project */
  spec: string
  /** the project the spec and capture are under; default "." */
  root?: string
}

/** Every spec under `[paths] specs` against the artefact it names (§PW111). */
export interface AcceptVerifyArgs {
  /** the project the specs and artefacts are under; default "." */
  root?: string
  /** where the specs are; [paths] specs by default */
  under?: string
}

/** Where one item stands, in one read: shape, bar, artefact, verdict and budget. */
export interface AssetBriefArgs {
  /** the asset's name, or an id project.inventory gave the item */
  asset: string
  /** the project the asset is in; default "." */
  root?: string
}

/** Write a calibration's proposed bounds into the spec, leaving a person's alone. */
export interface CalibrateApplyArgs {
  /** the acceptance spec the proposal was measured on */
  spec: string
  /** what calibrate.run returned */
  proposal: Record<string, unknown>
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Render an accepted picture again under harmless changes, and propose its bounds. */
export interface CalibrateRunArgs {
  /** the acceptance spec, as a path under the project */
  spec: string
  /** the render a person accepted, with its record */
  accepted: string
  /** how many spreads of noise a bound leaves; from 0 to …; default 3.0 */
  multiple?: number
  /** the project the paths resolve against; default "." */
  root?: string
}

/** The settings this project says a picture depends on. */
export interface CaptureDeclaredArgs {
  /** the project whose [capture] declared is read; default "." */
  root?: string
}

/** Every frame between two marks the script prints, at the engine's fixed rate. */
export interface CaptureMovieArgs {
  /** the scene script that flies the shot */
  script: string
  /** the folder the frames go to, under the project */
  out: string
  /** the project the engine runs; default "." */
  root?: string
  /** the settings to take it in; [capture] where unset */
  environment?: Record<string, unknown>
  /** the script's own arguments; default [] */
  args?: unknown[]
  /** write the sequence's record; default true */
  record?: boolean
}

/** Take a picture in a stated environment, and check it was the stated one. */
export interface CaptureRunArgs {
  /** the scene script, as a path under the project */
  script: string
  /** the line naming the picture, as a pattern */
  expect: string
  /** the project the engine runs; default "." */
  root?: string
  /** the settings to take it in; [capture] where unset */
  environment?: Record<string, unknown>
  /** write the environment beside the picture; default true */
  record?: boolean
  /** refuse, as require does, rather than report a failed run; default false */
  strict?: boolean
  /** the script's own arguments, e.g. ["--boss", "--frames=420"]; they go after the engine's and after --, beside the environment's; default [] */
  args?: unknown[]
  /** a group the script reports with a `visible: <group>` line; the run is taken again until it does */
  until_visible?: string
  /** how many runs until_visible may take; from 1 to 20; default 3 */
  tries?: number
  /** the frame budget; [engine] frames if unset; from 1 to 1e+07 */
  frames?: number
  /** the wall clock; [engine] timeout if unset; from 1 to …; in s */
  timeout?: number
}

/** Build a declared camera move, its shots cut one to the next, into a Godot scene. */
export interface ClipCameraArgs {
  /** the *.camera.toml, relative to the project */
  source: string
  /** the folder the scene is written to; beside the source if unset */
  out?: string
  /** the project the clip belongs to; default "." */
  root?: string
}

/** What a written file actually carries, read back off the file itself. */
export interface ClipCompiledArgs {
  /** a compiled animation file */
  path: string
}

/** One clip, checked for being motion at all. */
export interface ClipNewArgs {
  /** what the clip is called */
  name: string
  /** how long it lasts; from 0 to …; in s */
  duration: number
  /** the rate it is authored at; from 1 to …; default 24 */
  fps?: number
  /** each joint's keyed properties, if any */
  channels?: Record<string, unknown>
  /** the easing between keys; default "linear" */
  easing?: "linear" | "step" | "ease"
}

/** Read one back, refusing a file that is TOML and is not a clip. */
export interface ClipReadArgs {
  /** the clip file, as a path under the project */
  path: string
  /** the project the path resolves against; default "." */
  root?: string
}

/** The same shape over a different span — the change that gets made most. */
export interface ClipRetimeArgs {
  /** the clip, as clip.read or clip.new returns it */
  subject: Record<string, unknown>
  /** the new span; from 0 to …; in s */
  duration: number
}

/** A key set or replaced, as a new clip. The change an agent makes directly. */
export interface ClipSetKeyArgs {
  /** the clip, as clip.read or clip.new returns it */
  subject: Record<string, unknown>
  /** the joint keyed */
  joint: string
  /** the property keyed on it */
  prop: string
  /** where in the clip; from 0 to …; in s */
  when: number
  /** the value at that moment */
  value: unknown
  /** the easing into this key; the clip's if empty */
  ease?: string
}

/** Write the authored clip, the source and not an export, and say where. */
export interface ClipWriteArgs {
  /** the clip, as clip.read or clip.new returns it */
  subject: Record<string, unknown>
  /** where the clip file is written */
  path: string
  /** the project the path resolves against; default "." */
  root?: string
}

/** An asset put where it will actually be seen, written with its record. */
export interface ComposePlaceArgs {
  /** the asset's picture, by path */
  asset: string
  /** the scene or background it is put in, by path */
  into: string
  /** where the composed picture is written */
  out: string
  /** where it stands, [x, y] in pixels; default [0, 0] */
  at?: unknown[]
  /** the width it is drawn at, if not its own */
  width?: number
  /** what `at` names; default "footprint" */
  anchor?: "footprint" | "centre"
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Several pictures laid out on one sheet, in order, written with its record. */
export interface ComposeSheetArgs {
  /** the pictures to lay out, by path */
  tiles: unknown[]
  /** where the sheet is written */
  out: string
  /** how many across; square if unset */
  columns?: number
  /** each tile's cell; from 8 to …; in px; default 256 */
  cell?: number
  /** the project the paths resolve against; default "." */
  root?: string
}

/** What a file costs the game to draw: the numbers a cost predicate bounds. */
export interface CostReadArgs {
  /** the mesh, voxel model or texture, under the project */
  of: string
  /** the project the path resolves against; default "." */
  root?: string
}

/** Every reference that resolves to nothing and every script that does not parse. */
export interface EngineCheckArgs {
  /** the Godot project: the folder of project.godot; default "." */
  root?: string
  /** repoint moved references and remove orphaned .uid and .import; default false */
  fix?: boolean
  /** import headless and parse every script, where an engine is set; default true */
  parse?: boolean
}

/** What a change costs: one timing script on two builds, and how sure the gap is. */
export interface EngineCostArgs {
  /** the timing script, as a path under the project */
  script: string
  /** the line holding its numbers, as a pattern; name=number pairs */
  expect: string
  /** the revision to compare with; default "HEAD" */
  against?: string
  /** the revision measured; the working tree if unset */
  on?: string
  /** runs each side, alternating; from 2 to 20; default 5 */
  runs?: number
  /** the script's own arguments, after --; default [] */
  args?: unknown[]
  /** only these names off the line; default [] */
  measures?: unknown[]
  /** no window, for a CPU-only script; default false */
  headless?: boolean
  /** each run's frame budget; the project's */
  frames?: number
  /** each run's wall clock; in s */
  timeout?: number
  /** the project the engine runs; default "." */
  root?: string
}

/** The engine binary: what the project names, then $GODOT, then PATH. */
export interface EngineFindArgs {
  /** the project whose [paths] godot is read; default "." */
  root?: string
}

/** Each declared scene measured and held to its budget and this machine's baseline. */
export interface EnginePerfArgs {
  /** the [perf.<name>] budgets to run; every one declared where unset; default [] */
  scenes?: unknown[]
  /** write this run as the baseline for this machine and device; default false */
  rebase?: boolean
  /** the Godot project whose scenes these are; default "." */
  root?: string
}

/** For each preset, the settings that fit its frame budget and lose least (§PW367). */
export interface EnginePresetSearchArgs {
  /** the scene searched, as res://… */
  scene: string
  /** each preset's frame budget at p95, in ms: {low: 33.3, high: 8.3} */
  budgets: Record<string, unknown>
  /** the values each setting may take, full quality first */
  grid?: Record<string, unknown>
  /** frames timed in each run; from 10 to …; default 120 */
  frames?: number
  /** the Godot project the scene is in; default "." */
  root?: string
}

/** Run one scene script and say what happened: the verdict, not the log. */
export interface EngineRunArgs {
  /** the scene script, as a path under the project */
  script: string
  /** the line that means it worked, as a pattern */
  expect: string
  /** the project the engine runs; default "." */
  root?: string
  /** the named groups of expect that are paths it must have written; default [] */
  produces?: unknown[]
  /** the frame budget; the project's if unset */
  frames?: number
  /** the wall clock; the project's if unset; in s */
  timeout?: number
  /** run with no window; default false */
  headless?: boolean
  /** user arguments passed after the script; default [] */
  args?: unknown[]
}

/** Every state machine the game's scripts write, held to reach and leave each state. */
export interface EngineStatesArgs {
  /** the Godot project whose scripts are read; default "." */
  root?: string
}

/** Run one script over every combination of arguments, and keep the runs that show a pattern (§PW250). */
export interface EngineSweepArgs {
  /** the scene script, as a path under the project */
  script: string
  /** each argument's values, as {"seed": [1, 2], "policy": ["a"]} */
  grid: Record<string, unknown>
  /** the log line a run must show to be a hit */
  pattern: string
  /** the project the engine runs; default "." */
  root?: string
  /** user arguments every run is given as well; default [] */
  args?: unknown[]
  /** stop after this many hits; 0 runs all; from 0 to …; default 0 */
  first?: number
  /** how many runs at once; from 1 to 16; default 4 */
  lanes?: number
  /** each run's frame budget; the project's */
  frames?: number
  /** fly it again though this build was swept; default false */
  again?: boolean
}

/** Send several commands to a held game in one call, answering each (§PW271). */
export interface GameBatchArgs {
  /** the session game.open answered */
  session: string
  /** the commands in order, each as the driver takes it: {"cmd": "input", "click": {"path": "UI/Play"}} */
  commands: unknown[]
  /** carry on past a refused command; default false */
  keep_going?: boolean
  /** the project the game belongs to; default "." */
  root?: string
}

/** Call a method the game exposes for setup, and answer what it returned. */
export interface GameCallArgs {
  /** the session game.open answered */
  session: string
  /** the node the method is on */
  path: string
  /** a method the game exposes for setup */
  method: string
  /** its arguments; default [] */
  args?: unknown[]
  /** the project the game belongs to; default "." */
  root?: string
}

/** End the game, and say whether it ended when asked. */
export interface GameCloseArgs {
  /** the session game.open answered */
  session: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** What a crash left: its error, script and line, the state and the log (§PW361). */
export interface GameCrashReadArgs {
  /** a capture a person sent; the newest on this machine where unset */
  capture?: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Each export preset built and launched, as a player would launch it (§PW363). */
export interface GameExportSmokeArgs {
  /** a kept flow to run in each export, through to the menu and back */
  flow?: string
  /** the presets to export; every one for this machine where unset; default [] */
  presets?: unknown[]
  /** frames the plain run plays before it quits; from 1 to …; default 120 */
  frames?: number
  /** the project the game belongs to; default "." */
  root?: string
}

/** Press an action or a key, or click a node or a point; it lands next frame. */
export interface GameInputArgs {
  /** the session game.open answered */
  session: string
  /** an input action, pressed and released */
  action?: string
  /** a key by name, e.g. Space */
  key?: string
  /** a node's path to click at the centre of */
  click?: string
  /** a point in the viewport to click, [x, y]; default [] */
  at?: unknown[]
  /** press the action or key and keep it held; default false */
  hold?: boolean
  /** release an action or key held before; default false */
  release?: boolean
  /** the project the game belongs to; default "." */
  root?: string
}

/** Write what the session did as a flow that replays without an agent (§PW214). */
export interface GameKeepArgs {
  /** the session game.open answered */
  session: string
  /** the flow file to write, under the project's tests */
  out: string
  /** what the flow proves, in a sentence */
  proves: string
  /** the steps of queries whose values the flow must see again; default [] */
  expect?: unknown[]
  /** the steps that were wrong turns, left out; default [] */
  drop?: unknown[]
  /** the project the game belongs to; default "." */
  root?: string
}

/** Launch the game held at its first frame, and answer the session to drive it with. */
export interface GameOpenArgs {
  /** the project the game belongs to; default "." */
  root?: string
  /** a scene to load instead of the main one, res:// */
  scene?: string
  /** seed for the global random functions; 0 leaves it; default 0 */
  seed?: number
  /** draw real pixels, through the offscreen route, so game.shot works; default false */
  display?: boolean
  /** [width, height] of the window; [capture]'s where unset */
  resolution?: unknown[]
  /** the game's language; [capture]'s if unset */
  locale?: string
}

/** The nodes a path, group or class finds, with their properties, the game held. */
export interface GameQueryArgs {
  /** the session game.open answered */
  session: string
  /** a node's path, from /root or from the main scene */
  path?: string
  /** a group, every node in it */
  group?: string
  /** a class, engine or script, every node of it */
  of_class?: string
  /** the properties to read; a default set if unset; default [] */
  properties?: unknown[]
  /** names the state kit declares, or ['*'] for every one; default [] */
  state?: unknown[]
  /** the project the game belongs to; default "." */
  root?: string
}

/** A run a player recorded, written as a flow game.replay runs in the gate (§PW360). */
export interface GameRecordFlowArgs {
  /** a record PolyweaveRecorder saved, as a path */
  record: string
  /** the flow file to write, under the project's tests */
  out: string
  /** what the flow proves, in a sentence */
  proves: string
  /** {path, property, equals} the run must end on, the bug's place; default [] */
  expect?: unknown[]
  /** the project the game belongs to; default "." */
  root?: string
}

/** Put a selector in place of each generated path an older flow reaches by (§PW276). */
export interface GameRekeyArgs {
  /** the flow file to re-key, as game.keep wrote it */
  flow: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Whether the driver could ship to a player: presets, autoloads, a pack (§PW215). */
export interface GameReleaseCheckArgs {
  /** the project the game belongs to; default "." */
  root?: string
  /** an exported .pck to look inside, if there is one */
  pack?: string
  /** refuse on the first finding, as a gate; default false */
  strict?: boolean
}

/** Run a kept flow in one launch, no agent: every expectation held or the first that broke, with the frame it broke on (§PW214). */
export interface GameReplayArgs {
  /** the flow file game.keep wrote */
  flow: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Set a property for setup, such as the seed of a generator the game made itself. */
export interface GameSetArgs {
  /** the session game.open answered */
  session: string
  /** the node the property is on */
  path: string
  /** the property; a nested one as rng:seed */
  prop: string
  /** the value to set, as JSON */
  value: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Save the screen as it is now, answering the path and size, not the picture. */
export interface GameShotArgs {
  /** the session game.open answered */
  session: string
  /** where the PNG goes, under the project */
  out: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Let a number of frames pass, then hold the game again. */
export interface GameStepArgs {
  /** the session game.open answered */
  session: string
  /** how many frames pass; from 1 to …; default 1 */
  frames?: number
  /** the project the game belongs to; default "." */
  root?: string
}

/** Every test of a game, run headless the one way, and what failed with its line. */
export interface GameTestArgs {
  /** test scripts to run; every one the convention finds where unset; default [] */
  scripts?: unknown[]
  /** the Godot project the tests are in; default "." */
  root?: string
}

/** Every visible Label and Button, and whether its text fits on screen (§PW336). */
export interface GameTextFitArgs {
  /** the session game.open answered */
  session: string
  /** a locale to switch the game to first, such as pt_BR */
  locale?: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Let frames pass until a signal fires, a node exists or a value is reached. */
export interface GameWaitArgs {
  /** the session game.open answered */
  session: string
  /** the most frames the wait may spend; from 1 to …; default 60 */
  frames?: number
  /** the node the signal or property is on */
  path?: string
  /** a signal of that node to wait for */
  signal?: string
  /** a path or group that must come to exist */
  node?: string
  /** a property of that node to wait on */
  prop?: string
  /** the value the property must reach, as JSON */
  equals?: string
  /** the project the game belongs to; default "." */
  root?: string
}

/** Build one declaration and say what came out; a refusal is an answer too. */
export interface GeometryBuildArgs {
  /** the declaration, as a path under the project */
  source: string
  /** where to write; its own folder if unset */
  out?: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** params by name, or fields as voxels.cell */
  given?: Record<string, unknown>
  /** also write a cheap look: a silhouette; default false */
  preview?: boolean
  /** build even where the stamp still matches; default true */
  force?: boolean
  /** write the .glb beside a voxel build's cells; false for the cells alone; default true */
  mesh?: boolean
}

/** Every declaration under a folder, skipping the ones whose stamp still matches. */
export interface GeometryBuildAllArgs {
  /** the folder whose declarations are built */
  folder: string
  /** where to write; each one's folder if unset */
  out?: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** params or fields, for every declaration */
  given?: Record<string, unknown>
  /** also write a cheap look for each; default false */
  preview?: boolean
  /** write the .glb beside a voxel build's cells; false for the cells alone; default true */
  mesh?: boolean
}

/** Two voxel models compared cell by cell, materials by name (§PW240). */
export interface GeometryCompareArgs {
  /** a .voxels.json, or a voxel declaration to build, under the project */
  first: string
  /** the other one, either kind */
  second: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** A declaration read back in words, with its warnings, and nothing built. */
export interface GeometryDescribeArgs {
  /** the declaration, as a path under the project */
  source: string
  /** values set for the declaration's params */
  given?: Record<string, unknown>
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Fit a voxel declaration's [search] parameters to a drawing or a mesh (§PW230). */
export interface GeometryFitArgs {
  /** the voxel declaration, as a path under the project */
  source: string
  /** a drawing or a mesh under the project to fit its proportions to */
  reference: string
  /** the views scored, of front, side and top; a drawing is front only */
  views?: unknown[]
  /** how many samples the search may build; from 1 to …; default 400 */
  budget?: number
  /** the grid points per parameter; from 2 to …; default 7 */
  points?: number
  /** where the best model's contact sheet goes */
  sheet?: string
  /** put the best values into the declaration's [params]; default false */
  write?: boolean
  /** score shape inside each view's box, not the box itself; default false */
  boxed?: boolean
  /** a part of a drawing: {colours: [hex], materials: [name]} */
  region?: Record<string, unknown>
  /** the project the paths resolve against; default "." */
  root?: string
}

/** The members a declaration names beside itself, one per variant. */
export interface GeometryVariantsArgs {
  /** the declaration, as a path under the project */
  source: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Copy an addon into a Godot project's `addons/`, replacing an older copy. */
export interface GodotInstallArgs {
  /** the Godot project to install into */
  project: string
  /** which addon; default "polyweave_voxels" */
  addon?: string
}

/** Build a declared icon set at each size, held to its legibility bounds (§PW331). */
export interface IconsBuildArgs {
  /** the *.icons.toml declaration under the project */
  source: string
  /** the folder it lands in; the declaration's if unset */
  out?: string
  /** lay the set out for a person's verdict on the review page; default true */
  sitting?: boolean
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Land one kit in the game and prove it there, in one call (§PW341). */
export interface KitInstallArgs {
  /** the kit, as kit.list names it */
  name: string
  /** false answers what it would do and writes nothing; default true */
  write?: boolean
  /** the Godot project the kit lands in; default "." */
  root?: string
}

/** The kits the plugin carries, each its name, version, summary and requirements. */
export interface KitListArgs {
  /** unused; kits are the plugin's own; default "." */
  root?: string
}

/** Every kit installed into its own fixture and proved there (§PW342). */
export interface KitProveArgs {
  /** one kit; every kit the plugin carries if unset */
  name?: string
  /** unused; a kit is proved in its own fixture; default "." */
  root?: string
}

/** Bring an installed kit to the version the plugin carries, proved or not at all. */
export interface KitUpdateArgs {
  /** an installed kit */
  name: string
  /** false answers what it would do, writing nothing; default true */
  write?: boolean
  /** the Godot project the kit is installed in; default "." */
  root?: string
}

/** Every asset the ledger has a run for. */
export interface LoopAssetsArgs {
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Which bounds a person overruled, which way, and with what values (§PW108). */
export interface LoopBoundsArgs {
  /** the project whose ledger this is; default "." */
  root?: string
  /** one asset only; every asset where unset */
  asset?: string
}

/** Every change an asset has been measured through, in the order first recorded. */
export interface LoopChangesArgs {
  /** the asset */
  asset: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** The two ways side by side, with what changed between them. */
export interface LoopCompareArgs {
  /** the asset made both ways */
  asset: string
  /** the project whose ledger this is; default "." */
  root?: string
  /** the change to compare after; the first port where unset */
  change?: string
}

/** Close the run and append it to the ledger, which is append-only. */
export interface LoopFinishArgs {
  /** the open run, as loop.start returned it, or just its id */
  run: Record<string, unknown>
  /** the project whose ledger this is; default "." */
  root?: string
  /** whether it was accepted; the last verdict where unset */
  accepted?: boolean
}

/** One result, as the tool called it and as a person called it. */
export interface LoopJudgedArgs {
  /** the open run, as loop.start returned it, or just its id */
  run: Record<string, unknown>
  /** whether the tool passed the result */
  tool_passed: boolean
  /** whether a person accepted it */
  person_accepted: boolean
  /** the person's sentence */
  why?: string
  /** what accept.check said of the result */
  check?: Record<string, unknown>
  /** the predicates the person blamed; default [] */
  named?: unknown[]
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Which assets wait on a person's look, and where every asset stands (§PW110). */
export interface LoopPendingArgs {
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Every run recorded, oldest first. */
export interface LoopRunsArgs {
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Add to what this run has cost so far. Called as the work happens. */
export interface LoopSpentArgs {
  /** the open run, as loop.start returned it, or just its id */
  run: Record<string, unknown>
  /** fresh renders spent; from 0 to …; default 0 */
  renders?: number
  /** tool calls spent; from 0 to …; default 0 */
  calls?: number
  /** service credits spent; from 0 to …; default 0 */
  credits?: number
  /** wall-clock spent; from 0 to …; in s; default 0 */
  seconds?: number
  /** a person's own time spent; from 0 to …; in min; default 0 */
  person_minutes?: number
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Begin recording one asset made one way. */
export interface LoopStartArgs {
  /** the asset being made */
  asset: string
  /** which of the two ways */
  way: "before" | "after"
  /** the project whose ledger this is; default "." */
  root?: string
  /** what was asked for, in a sentence */
  brief?: string
  /** who is doing the work */
  who?: string
  /** the change to a ported asset this run measures, if any */
  change?: string
  /** the costs this run will not measure, from seconds, renders, calls, credits and person_minutes; default [] */
  unmeasured?: unknown[]
}

/** What can be measured now, and what is declared and still ahead of its code. */
export interface MeasureAvailableArgs {
}

/** How well each target stands out from the ring around it, the worst named. */
export interface MeasureContrastArgs {
  /** the picture, as a path under the project */
  picture: string
  /** each {at: [x, y], radius} or {box: [l, t, r, b]}, in pixels */
  targets?: unknown[]
  /** a `target: x y [r]` log or JSON list of targets, instead */
  log?: string
  /** the frame without its text, for text lines */
  behind?: string
  /** the surround's width; from 1 to …; in px; default 6 */
  ring?: number
  /** a point's default radius; from 0 to …; in px; default 3.0 */
  radius?: number
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Whether the outline moved or only the look: two short hashes a later session can compare without the pictures (§PW141). */
export interface MeasureDigestArgs {
  /** a picture, as a path under the project */
  subject: string
  /** the rung it was baked at; else its record's */
  rung?: string
  /** the alpha below which a pixel is background; the project's if unset */
  alpha_floor?: number
  /** the project the paths resolve against; default "." */
  root?: string
}

/** The worst second of flashes in a captured run, held to the guidance's limit. */
export interface MeasureFlashesArgs {
  /** the folder capture.movie wrote, its sequence.json, or PNG frames */
  capture: string
  /** the frames' rate; sequence.json's, or [engine] fixed_fps; from 0 to …; default 0.0 */
  fps?: number
  /** the project the path resolves against; default "." */
  root?: string
}

/** A wave timeline's threat per second, in its two bounding cases, and its gaps. */
export interface MeasurePressureArgs {
  /** the events, each {second, kind, weight, until} */
  events?: unknown[]
  /** or a JSON file of them under the project, as the game wrote it */
  file?: string
  /** an earlier timeline, laid beside this one */
  compare?: unknown[]
  /** or the earlier timeline's file */
  compare_file?: string
  /** seconds an enemy warps in before it can be shot; from 0 to …; in s; default 0.0 */
  warp?: number
  /** the gap past which a gap is named; 0 names none; from 0 to …; in s; default 0.0 */
  window?: number
  /** a JSON file under the project to keep it in */
  out?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Whether two renders are the same picture, with a tolerance rather than equality. */
export interface MeasureSameArgs {
  /** a picture, as a path under the project */
  subject: unknown
  /** the other picture, as a path under the project */
  against: unknown
  /** the distance still called the same; measured or the rung's */
  tolerance?: number
  /** the colour difference a pixel may move by */
  delta?: number
  /** where to measure: frame, subject, a rectangle, or a mask file */
  region?: unknown
  /** the alpha below which a pixel is background; the project's if unset */
  alpha_floor?: number
  /** a second render of the unchanged scene, to measure the floor */
  twin?: unknown
  /** the rung both were rendered at */
  rung?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Take measurements of a picture, each with the region and rung it was taken at. */
export interface MeasureTakeArgs {
  /** a picture, as a path under the project */
  subject: string
  /** the measures to take, by name; default ["saturation", "luma", "alpha_coverage"] */
  measures?: unknown[]
  /** where to measure: frame, subject, a rectangle, or a mask file */
  region?: unknown
  /** the alpha below which a pixel is background; the project's if unset */
  alpha_floor?: number
  /** the rung the picture was made at, if known */
  rung?: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** the colour delta_e is measured to */
  target?: string
  /** the picture a silhouette or distance compares with */
  against?: string
  /** the size luma_bands counts at */
  display?: unknown[]
  /** the difference changed_fraction counts */
  delta?: number
}

/** Buy one untextured mesh, from a prompt or a gated picture, against the ceiling. */
export interface MeshBuyArgs {
  /** where the .glb is written, under the project */
  out?: string
  /** what to model, in words */
  prompt?: string
  /** a picture picture.gate passed, to model from instead of words */
  picture_path?: string
  /** the service's model, e.g. meshy-6-lite; default "meshy-6-lite" */
  model?: string
  /** the triangles to aim at; from 100 to …; default 8000 */
  polycount?: number
  /** a world entity to compose the prompt from */
  entity?: string
  /** the *.world.toml, needed only among several */
  world?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Fit, weight, compile and bake one clip on one mesh, by name. */
export interface MotionBakeArgs {
  /** the clip file, as a path under the project */
  clip: string
  /** the mesh the clip moves, a .glb under the project */
  mesh: string
  /** where to write, without a suffix: <out>.glb and <out>.png */
  out: string
  /** the body plan to fit; the project's [rig] plan if unset */
  plan?: string
  /** the rung the sheet's frames render at; default "preview" */
  rung?: "sphere" | "preview" | "final"
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Render a valid score to the formats a game loads through Surge XT and FluidSynth. */
export interface MusicRenderArgs {
  /** the *.music.toml, relative to the project */
  source: string
  /** where to write, without a suffix; beside the score if unset */
  out?: string
  /** the project the score belongs to; default "." */
  root?: string
  /** the formats the game loads, wav and/or ogg; its cue's if unset */
  formats?: unknown[]
}

/** Write a valid score as a Standard MIDI File a DAW opens, one track per part. */
export interface MusicToMidiArgs {
  /** the *.music.toml, relative to the project */
  source: string
  /** where the .mid goes; beside the score if unset */
  out?: string
  /** the project the score belongs to; default "." */
  root?: string
}

/** Compile a score and answer every problem at once, each with its line and fix. */
export interface MusicValidateArgs {
  /** the *.music.toml, relative to the project */
  source: string
  /** the project the score belongs to; default "." */
  root?: string
}

/** A mesh brought to the conventions: upright, centred, sized, and recorded. */
export interface NormaliseIngestArgs {
  /** the mesh a service or a person made */
  path: string
  /** where the normalised mesh is written */
  out?: string
  /** a drawing to orient it by, if any */
  against?: string
  /** the size it is scaled to; from 0 to …; default 1.0 */
  height?: number
  /** which extent height means; default "height" */
  size_on?: "height" | "length" | "longest"
  /** where its origin goes; default "base" */
  origin?: "base" | "centre"
  /** the drawing's alpha floor, if any */
  alpha_floor?: number
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Which routes draw on this machine, proved rather than assumed. */
export interface OffscreenRoutesArgs {
  /** the project whose engine is probed; default "." */
  root?: string
  /** probe again rather than read the last; default false */
  recheck?: boolean
}

/** Build declared menu panels and screen wipes for the engine, each recorded. */
export interface PanelBuildArgs {
  /** the *.panel.toml, relative to the project */
  source: string
  /** one panel; left out, every one */
  panel?: string
  /** the folder the textures are written to; beside the source if unset */
  out?: string
  /** also write each panel as a canvas shader, with a material a state; default false */
  shader?: boolean
  /** the project the panels belong to; default "." */
  root?: string
}

/** Film each panel's shader in each state, and each wipe at each progress step. */
export interface PanelCaptureArgs {
  /** the *.panel.toml, relative to the project */
  source: string
  /** the folder the stills go to, under the project */
  out: string
  /** how many stills of a wipe, from progress 0 to 1; from 2 to 32; default 5 */
  steps?: number
  /** screen pixels to one of a panel's; from 1 to 8; default 2 */
  scale?: number
  /** the project the panels belong to; default "." */
  root?: string
}

/** What a variation changed that it was not asked to, against its parent. */
export interface PictureAgainstParentArgs {
  /** a picture picture.vary bought, under the project */
  variation: string
  /** the asset family, needed only among several */
  family?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Buy one picture against the service's ceiling and keep it before anything else. */
export interface PictureBuyArgs {
  /** where it is written, under the project */
  out?: string
  /** what it shows, as text the service may rewrite */
  prompt?: string
  /** what it shows, structured, which 4.0 draws without rewriting */
  json_prompt?: Record<string, unknown>
  /** a PNG with alpha, read as a drawing; default true */
  transparent?: boolean
  /** the model; default "4.0" */
  model?: "4.0" | "3.0"
  /** as the service spells it */
  aspect_ratio?: string
  /** as the service spells it */
  rendering_speed?: string
  /** for a picture that can be asked for again */
  seed?: number
  /** the asset family whose [style] it is held to */
  family?: string
  /** a world entity to compose the prompt from */
  entity?: string
  /** the *.world.toml, needed only among several */
  world?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Take delivery of a picture that was paid for and never arrived (§PW179). */
export interface PictureCollectArgs {
  /** the purchase's task id, as the refusal named it */
  task_id: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Turn an approved picture into the structured prompt 4.0 draws it from (§PW165). */
export interface PictureDescribeArgs {
  /** an approved picture, under the project */
  picture: string
  /** where the description goes; beside it if unset */
  out?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Put a picture on its family's grid: defringed, trimmed, fitted and anchored. */
export interface PictureFitArgs {
  /** the picture as it arrived, under the project */
  picture: string
  /** where the fitted picture the engine loads is written */
  out: string
  /** the asset family, needed only among several */
  family?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Settle the silhouette on the pictures, before a mesh is bought from one (§PW168). */
export interface PictureGateArgs {
  /** the pictures bought for one asset, by path */
  candidates: unknown[]
  /** the declared silhouette they must match */
  outline: string
  /** the asset family whose canon they are held to */
  family?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Read the lettering back off a picture and hold it to what was asked (§PW169). */
export interface PictureLettersArgs {
  /** the picture, under the project */
  picture: string
  /** the lettering it must carry; its record's text elements if unset */
  texts?: unknown[]
  /** the reader's languages, as tesseract names them */
  languages?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Buy a variation of an approved picture, with its parent on the record. */
export interface PictureVaryArgs {
  /** the approved picture, under the project */
  parent: string
  /** where the variation is written, under the project */
  out: string
  /** what the variation should show; a reframe takes none */
  prompt?: string
  /** remix the whole, edit in a mask, or reframe; default "edit" */
  change?: "remix" | "edit" | "reframe"
  /** for a reframe: the new frame, as WIDTHxHEIGHT the service offers */
  resolution?: string
  /** for an edit: the described element to change, by its words */
  region?: string
  /** for an edit: a mask file, black where it may change */
  mask?: string
  /** for a remix: how much of the parent is kept */
  strength?: number
  /** as the service spells it */
  rendering_speed?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Draw a vector to a PNG at a width, filters and masks included, with its record. */
export interface PictureVectorArgs {
  /** the SVG, as a path under the project */
  source: string
  /** where the whole picture is written, as a PNG */
  out: string
  /** the width to draw at; from 1 to 16384; in px */
  width: number
  /** each layer's name to the element it draws alone: #id, or its place among the top-level elements from 1 */
  layers?: Record<string, unknown>
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Port a family from its file: build, search as one, bake if every member passes. */
export interface PortRunArgs {
  /** the family file, as a path under the project */
  family: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** an open loop run every render counts into */
  run?: Record<string, unknown>
  /** search even where the kept rig passes; default false */
  fresh?: boolean
}

/** Every gap between this tree and a working adoption, each with its remedy. */
export interface ProjectCheckArgs {
  /** the adopted project; default "." */
  root?: string
}

/** Propose polyweave.toml from what the project's tree already holds. */
export interface ProjectInitArgs {
  /** the project whose tree is read; default "." */
  root?: string
  /** write it, not only propose it; default false */
  write?: boolean
  /** add only the tables a file lacks; default false */
  merge?: boolean
  /** wire the agent: server, AGENTS.md; default false */
  agent?: boolean
}

/** Every item the project governs, by kind, in one bounded read (§PW299). */
export interface ProjectInventoryArgs {
  /** the project to list; default "." */
  root?: string
  /** only this kind */
  kind?: "mesh" | "picture" | "sound" | "music" | "vfx" | "clip" | "line" | "capture"
  /** rows to skip: the last answer's next; from 0 to …; default 0 */
  offset?: number
  /** rows to return; from 1 to …; default 200 */
  limit?: number
}

/** A new game, created already adopted: Godot project, repository files, config, agent, base kits each proved, a first test and a gate, in one call (§PW369). */
export interface ProjectNewArgs {
  /** the folder the game is made in, empty or not there */
  root: string
  /** the game's name, as Godot shows it */
  name: string
  /** the kits it starts with; input, menus, options, saves and tests */
  kits?: unknown[]
  /** start a git repository, where git is here; default true */
  git?: boolean
}

/** Copy an artefact another project made into this one, recording where from. */
export interface ProvenanceBorrowArgs {
  /** the file to bring in: another project's, as an absolute path */
  path: string
  /** where it lands here, as a path under the project */
  out: string
  /** the licence it comes under, e.g. CC-BY-4.0 */
  licence?: string
  /** the credit its licence requires; the credits screen shows it */
  credit?: string
  /** the project the records are under; default "." */
  root?: string
}

/** The credits a game owes, and what else its licences say. */
export interface ProvenanceCreditsArgs {
  /** the project the records are under; default "." */
  root?: string
  /** write the answer here for the game's credits screen, as JSON */
  out?: string
  /** answer whether the file at `out` still matches the records; default false */
  check?: boolean
}

/** Every artefact whose record names this file as an input (§PW119). */
export interface ProvenanceDependentsArgs {
  /** the input file, under the project */
  path: string
  /** the project the records are under; default "." */
  root?: string
}

/** Which files a build ships a paid generator made, and through what (§PW248). */
export interface ProvenanceGeneratedArgs {
  /** the files a build ships, or folders of them, under the project; default [] */
  paths?: unknown[]
  /** the project the records are under; default "." */
  root?: string
}

/** Artefacts made from a file that has changed since, and not made again (§PW119). */
export interface ProvenanceOutdatedArgs {
  /** the project the records are under; default "." */
  root?: string
}

/** Read a record, by its own path or by the path of the artefact it describes. */
export interface ProvenanceReadArgs {
  /** an artefact, or its .prov.json, under the project */
  path: string
  /** the project the records are under; default "." */
  root?: string
}

/** Produced files carrying no record — the half `verify` could not ask about. */
export interface ProvenanceUnrecordedArgs {
  /** the project the records are under; default "." */
  root?: string
}

/** Is every artefact the records claim to hold present, and still what it was. */
export interface ProvenanceVerifyArgs {
  /** the project the records are under; default "." */
  root?: string
}

/** Bring a ledger somebody else kept into this one, spending nothing (§PW55). */
export interface PurchaseAdoptArgs {
  /** another ledger's entries, or the file holding them */
  entries: unknown
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Refuse a spend that would pass the ceiling. Never asks; the answer is the file. */
export interface PurchaseAllowArgs {
  /** what the spend would cost, in the service's own unit; from 0 to … */
  cost: number
  /** the project whose ledger this is; default "." */
  root?: string
  /** the date the ceiling is judged on; today if unset */
  today?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
}

/** The entry for a file, looked up by **its hash rather than a remote id**. */
export interface PurchaseFindArgs {
  /** the sha256 of the file bought */
  sha: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Is everything this project paid for still here, and still what it was. */
export interface PurchaseHeldArgs {
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Everything this project has bought, oldest first. */
export interface PurchaseLedgerArgs {
  /** the project whose ledger this is; default "." */
  root?: string
}

/** What one paid call would cost, and what the ceiling leaves, spending nothing. */
export interface PurchaseQuoteArgs {
  /** the paid operation, as describe names it */
  operation: string
  /** the arguments the call would pass */
  arguments?: Record<string, unknown>
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Hold each quoted price against what the service's usage export says it billed. */
export interface PurchaseReconcileArgs {
  /** the service's usage rows, each {at, cost, count}, or their file */
  rows: unknown
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** What is left of one service's ceiling, against what was spent on that service. */
export interface PurchaseRemainingArgs {
  /** the project whose ledger this is; default "." */
  root?: string
  /** the date the ceiling is judged on; today if unset */
  today?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
}

/** What this project has spent against one service's ceiling, by its own ledger. */
export interface PurchaseSpentArgs {
  /** the project whose ledger this is; default "." */
  root?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
}

/** A reference video sampled into frames and contact sheets an agent can read. */
export interface ReferenceFramesArgs {
  /** the gameplay video, anywhere; it is never copied in */
  video: string
  /** frames a second across the video; from 0.01 to …; default 2.0 */
  rate?: number
  /** denser stretches: [start, end, rate] in seconds and per second */
  ranges?: unknown[]
  /** keep a frame only where it differs by this share; 0 keeps all; from 0 to 1; default 0.0 */
  changed?: number
  /** [left, top, right, bottom] pixels: a second sheet of that strip */
  crop?: unknown[]
  /** the folder under the project the frames land in */
  out?: string
  /** the project the frames are written into; default "." */
  root?: string
}

/** Which of several pictures is the one to fetch from, and why. */
export interface ReferencePickArgs {
  /** the pictures to choose between, by path */
  candidates: unknown[]
  /** the project the paths resolve against; default "." */
  root?: string
}

/** A photograph cut from its background and sized, ready to send to the service. */
export interface ReferencePrepareArgs {
  /** the photograph, as a path under the project */
  photo: string
  /** where the prepared reference is written */
  out?: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** how far from the edge colour is still background */
  tolerance?: number
  /** the least of the frame it fills */
  coverage?: number
  /** the longest side it is sized to; from 16 to …; default 1024 */
  longest?: number
}

/** Render one subject at the cheapest rung that can answer the question. */
export interface RenderBakeArgs {
  /** where to write the picture, under the project */
  out: string
  /** the mesh to render; not read at the sphere rung */
  model?: string
  /** a spec whose subject's build is the mesh */
  spec?: string
  /** which rung to render at */
  rung?: "sphere" | "preview" | "final"
  /** the measures the answer has to carry, if no rung is named; default [] */
  asking?: unknown[]
  /** the lowest rung a verdict on this asset may be taken at */
  floor?: "sphere" | "preview" | "final"
  /** Principled BSDF inputs to put on the subject */
  material?: Record<string, unknown>
  /** which measurements to take of the render, in the same call; default [] */
  measures?: unknown[]
  /** where to measure: frame, subject, a rectangle, or a mask file */
  region?: string
  /** carry the picture back with the numbers, base64 encoded; default true */
  inline?: boolean
  /** return an identical render already paid for rather than repeat it; default true */
  cached?: boolean
  /** where the camera sits around the subject; from -360 to 360; in deg; default 35.0 */
  azimuth?: number
  /** how far above the subject; from -89 to 89; in deg; default 20.0 */
  elevation?: number
  /** how much room around the subject; from 1 to 4; default 1.15 */
  margin?: number
  /** camera focal length; from 8 to 400; in mm; default 50.0 */
  focal_mm?: number
  /** key light power; from 0 to 10000; in W at the sphere rung's size; default 400.0 */
  key?: number
  /** fill light power; from 0 to 10000; in W at the sphere rung's size; default 120.0 */
  fill?: number
  /** rim light power; from 0 to 10000; in W at the sphere rung's size; default 200.0 */
  rim?: number
  /** how far the lights sit, in subject radii; from 1 to 20; default 3.0 */
  light_distance?: number
  /** world lighting; from 0 to 10; default 0.25 */
  ambient?: number
  /** film exposure; from -10 to 10; in stops; default 0.0 */
  exposure?: number
  /** leave the background empty; default true */
  transparent?: boolean
  /** a render of one flat colour is what was wanted, not a failure; default false */
  allow_uniform?: boolean
  /** take the shading a service painted into the mesh's texture back out; default false */
  scrub?: boolean
  /** the world rectangle this picture stands for: [width, height] centred on the subject, or [x0, y0, x1, y1] where it stands, seen from the front; default [] */
  covers?: unknown[]
  /** the scale it is baked at; the project's own where this is left out; default 0.0 */
  pixels_per_unit?: number
  /** the path tracer's seed; the project's where this is negative; default -1 */
  seed?: number
  /** samples per pixel; the rung's where this is zero; from 0 to …; default 0 */
  samples?: number
  /** the square's side; the rung's where this is zero; from 0 to …; in px; default 0 */
  size?: number
  /** the project to resolve settings against; default "." */
  root?: string
}

/** Which rung will answer, how big it will be, and why that one. */
export interface RenderPlanArgs {
  /** the rung to render at, if the caller names it */
  rung?: string
  /** the measures the answer has to carry, if no rung is named */
  asking?: unknown[]
  /** the lowest rung a verdict on this asset may be taken at */
  floor?: string
  /** the project to resolve settings against; default "." */
  root?: string
}

/** The page's one write, marks turned into masks and then verdict.judge, refused where this process runs older code than the package on disk. */
export interface ReviewAnswerArgs {
  /** the answer as the page sends it: sitting, family, choice, why and marks; or gate and picture; or admit or withdraw, with canon */
  body: Record<string, unknown>
  /** the project the sitting belongs to; default "." */
  root?: string
}

/** Each style family's canon board, as the page's canon tab draws it. */
export interface ReviewCanonArgs {
  /** the project the page is for; default "." */
  root?: string
}

/** Where two pictures differ above the noise floor, as a map the page shows. */
export interface ReviewCompareArgs {
  /** the picture before, under the project */
  old: string
  /** the picture after, under the project */
  new: string
  /** the project the pictures belong to; default "." */
  root?: string
}

/** Everything the decision screen shows, as the page reads it: the language, what waits on a person, the sittings, their answers, the gate runs and the turntables. */
export interface ReviewStateArgs {
  /** the project the page is for; default "." */
  root?: string
}

/** Keep a person's request to change one item, against what they were looking at. */
export interface RevisionAskArgs {
  /** the item, by the id project.inventory gives it */
  item: string
  /** what the person asked for, in their words */
  words: string
  /** a mask under the project, black where the change is wanted */
  mask?: string
  /** for a sound, [start, end] in seconds; in s; default [] */
  span?: unknown[]
  /** the project the item is in; default "." */
  root?: string
}

/** The item's own checks, run on it as it now stands (§PW307). */
export interface RevisionCheckArgs {
  /** the revision, by the id revision.ask gave it */
  revision: string
  /** the project the item is in; default "." */
  root?: string
}

/** End one revision: answered by a run and a sitting, or withdrawn with a reason. */
export interface RevisionCloseArgs {
  /** the revision, by the id revision.ask gave it */
  revision: string
  /** the id of the loop run that answered it */
  run?: string
  /** the sitting the person judged the answer in */
  sitting?: string
  /** why it is closed with no answer */
  withdrawn?: string
  /** the project the item is in; default "." */
  root?: string
}

/** The revisions still open, each with its item's brief and whether it has moved. */
export interface RevisionOpenArgs {
  /** only this item's; every open one if empty */
  item?: string
  /** the project the item is in; default "." */
  root?: string
}

/** The files a revision's session wrote outside its item from the shell (§PW378). */
export interface RevisionOutsideArgs {
  /** the revision, by the id revision.ask gave it */
  revision: string
  /** the project the item is in; default "." */
  root?: string
}

/** The Claude Code settings a session on this revision runs under (§PW307). */
export interface RevisionSettingsArgs {
  /** the revision, by the id revision.ask gave it */
  revision: string
  /** the project the item is in; default "." */
  root?: string
}

/** Keep one turn of the conversation a revision is worked through (§PW306). */
export interface RevisionTurnArgs {
  /** the revision, by the id revision.ask gave it */
  revision: string
  /** what was said, whole */
  text: string
  /** who said it; default "person" */
  by?: "person" | "session"
  /** the project the item is in; default "." */
  root?: string
}

/** The fields an invalid value was actually refused for, and nothing else. */
export interface SchemaProvedArgs {
  /** a schema, as schema.read returns it */
  schema: Record<string, unknown>
}

/** What this project has learned of one service, or nothing if it never has. */
export interface SchemaReadArgs {
  /** the project whose schema this is; default "." */
  root?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
}

/** Refuse a payload here, before sending, against what the service takes. */
export interface SchemaValidateArgs {
  /** the request about to be sent */
  payload: Record<string, unknown>
  /** the project whose schema this is; default "." */
  root?: string
  /** a schema to use instead of the learned one */
  schema?: Record<string, unknown>
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
}

/** Search a spec's permitted parameters by actually rendering, and return the best. */
export interface SearchSweepArgs {
  /** the acceptance spec, as a path under the project */
  spec: string
  /** where each sample's picture is written */
  out: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** how many renders it may spend; from 1 to …; default 24 */
  budget?: number
  /** points per axis in a pass; from 2 to …; default 3 */
  points?: number
  /** the rung, or the spec's own where empty */
  rung?: string
  /** render arguments held still, such as the model */
  fixed?: Record<string, unknown>
  /** where to write what it rejected, as <name>.json and .png */
  trace?: string
}

/** Whether four handles beat four waits, for a render that costs this much. */
export interface SearchWorthParallelArgs {
  /** what one render costs at this rung; from 0 to …; in s */
  seconds_per_render: number
  /** how many run at once; from 1 to …; default 4 */
  lanes?: number
  /** what a worker costs before it renders; from 0 to …; in s; default 0.85 */
  start_s?: number
}

/** Does this shape hold against the drawing that asked for it. */
export interface ShapeCheckArgs {
  /** the mesh, as a path under the project */
  subject: unknown
  /** the drawing its silhouette must match */
  against: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** the least IoU that passes; the project's if unset */
  threshold?: number
  /** where the silhouette render is written */
  out?: string
  /** the rung the silhouette is rendered at; default "preview" */
  rung?: string
}

/** A mesh's silhouette, rendered and cut to its alpha, from the rig's own camera. */
export interface ShapeSilhouetteArgs {
  /** the mesh, as a path under the project */
  mesh: string
  /** where the silhouette is written */
  out: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** the rung it is rendered at; default "preview" */
  rung?: string
}

/** A mesh turned at the rig's own camera, for the review page (§PW176). */
export interface ShapeTurntableArgs {
  /** the mesh, as a path under the project */
  mesh: string
  /** the folder the frames are written into */
  out: string
  /** the drawing to lay over the front view */
  against?: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** the rung the frames are rendered at; default "preview" */
  rung?: string
  /** how many frames round the up axis; from 1 to …; default 8 */
  frames?: number
}

/** The bone names a written file carries, read back off the file itself. */
export interface SkeletonJointsInArgs {
  /** a rigged file */
  path: string
}

/** One body plan, checked for being a skeleton at all. */
export interface SkeletonPlanArgs {
  /** the body plan, such as plush */
  named: string
}

/** Import what was written, turn one joint by name, and see if the mesh moved. */
export interface SkeletonPlaysArgs {
  /** a rigged file */
  path: string
  /** the joint turned */
  joint: string
  /** the turn, [x, y, z] in degrees; default [0.0, 0.0, 30.0] */
  turn?: unknown[]
}

/** Which joints two plans have in common, which is what can be retargeted. */
export interface SkeletonSharedArgs {
  /** one body plan */
  one: string
  /** the other */
  other: string
}

/** Buy one sound effect from words, at a declared cue's file, against the ceiling. */
export interface SoundBuyArgs {
  /** the sound, in words: footsteps on gravel */
  prompt?: string
  /** a cue [sound] declares; the file lands where it does */
  cue?: string
  /** or a path for it under the project, with its suffix */
  out?: string
  /** how long, 0.5 to 30; the service's choice if unset; from 0.5 to 30 */
  seconds?: number
  /** how closely it follows the words, 0 to 1; from 0 to 1; default 0.3 */
  influence?: number
  /** ask for a sound that loops, such as rain; default false */
  loop?: boolean
  /** the service's model, priced in [service]; default "eleven_text_to_sound_v2" */
  model?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** The audio a game declares: each cue's file, measured, and what is missing. */
export interface SoundDeclaredArgs {
  /** one sound family; left out, every one */
  family?: string
  /** the project whose [sound] is read; default "." */
  root?: string
}

/** A sound's seam, loudness, peak and length: what a sound predicate bounds. */
export interface SoundMeasureArgs {
  /** the sound, as a path under the project */
  subject: string
  /** the project the path resolves against; default "." */
  root?: string
}

/** Put sounds on the review page, each new one beside the one it replaces. */
export interface SoundSittingArgs {
  /** each member: name and new, and optionally old (the sound it replaces), loop, spec, its *.accept.toml, and line, the words a spoken take should say */
  members: unknown[]
  /** the folder the sitting is laid out in */
  out: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Speak one line aloud in a named voice, at a cue's file, against the ceiling. */
export interface SoundSpeakArgs {
  /** the line, word for word: Viglet Games */
  text?: string
  /** the service's voice id that speaks it */
  voice?: string
  /** a cue [sound] declares; the file lands where it does */
  cue?: string
  /** or a path for it under the project, with its suffix */
  out?: string
  /** 0 to 1; the voice's own if unset; from 0 to 1 */
  stability?: number
  /** 0 to 1; the voice's own if unset; from 0 to 1 */
  similarity?: number
  /** 0 to 1; the voice's own if unset; from 0 to 1 */
  style?: number
  /** how fast, 0.7 to 1.2; the voice's own if unset; from 0.7 to 1.2 */
  speed?: number
  /** the service's model, priced in [service]; default "eleven_multilingual_v2" */
  model?: string
  /** a world entity, whose voice speaks it */
  entity?: string
  /** the *.world.toml, where the project has several */
  world?: string
  /** draft speaks it free on a local engine; paid buys it; default "paid" */
  rung?: "paid" | "draft"
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** A spoken take held to its line and the project's `[voice]` bounds (§PW323). */
export interface SoundSpeechArgs {
  /** the spoken take, as a path under the project */
  take: string
  /** the line it should say; its record's where unset */
  text?: string
  /** the project the path resolves against; default "." */
  root?: string
}

/** Make retro effects from a seed with sfxr, each at its declared cue's file. */
export interface SoundSynthArgs {
  /** the *.sfx.toml, relative to the project */
  source: string
  /** one effect; left out, every one */
  effect?: string
  /** the project the effects belong to; default "." */
  root?: string
}

/** Whether the two outputs came from the same clip, which is the whole claim. */
export interface SpritesMatchedArgs {
  /** the compiled animation, or its record */
  animation: unknown
  /** the sheet's atlas, as a path or its table */
  atlas: unknown
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Cut a store's whole capsule set from one key art and a logo, each recorded. */
export interface StoreCapsulesArgs {
  /** the key art every capsule is cut from */
  key_art: string
  /** the game's logo, a picture with alpha */
  logo: string
  /** the folder the capsules are written into */
  out: string
  /** a store this plugin knows, such as steam, or a store file's path; default "steam" */
  store?: string
  /** the point every crop keeps, as fractions [x, y] of the key art; default [0.5, 0.5] */
  focus?: unknown[]
  /** only these of the store's shapes; all if unset */
  shapes?: unknown[]
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Refuse a picture that drifts from its family's canon by number, saying which way. */
export interface StyleDriftArgs {
  /** the picture, under the project */
  picture: string
  /** the asset family, needed only among several */
  family?: string
  /** the project whose style this is; default "." */
  root?: string
}

/** One family's declared style and the pictures a person admitted to its canon. */
export interface StyleReadArgs {
  /** the asset family; needed only among several */
  family?: string
  /** the project whose style this is; default "." */
  root?: string
}

/** Every row of every declared table held to its schema, and each typed script. */
export interface TablesCheckArgs {
  /** the project whose tables these are; default "." */
  root?: string
  /** write each table's typed script for the game to load; default false */
  write?: boolean
}

/** Whether the repair shows at this rung, measured rather than assumed. */
export interface TextureWorthScrubbingArgs {
  /** the rung the render is at */
  rung: string
}

/** Read a trace back, which is what makes a past search arguable. */
export interface TraceReadArgs {
  /** the trace's .json, as search.sweep wrote it */
  path: string
}

/** Does the asset's scale agree with the engine's, and with its own pixels. */
export interface UnitsCheckArgs {
  /** the asset's declaration: covers and pixels_per_unit, or a file */
  source: unknown
  /** the picture made, [width, height], if any */
  size?: unknown[]
  /** the project whose scale this is; default "." */
  root?: string
  /** the scale baked at, where the declaration omits it; from 0 to … */
  pixels_per_unit?: number
  /** how far apart two scales may be; the project's where unset */
  tolerance?: number
}

/** The pixels per unit the engine draws at, and where that number came from. */
export interface UnitsEngineScaleArgs {
  /** the project whose scale this is; default "." */
  root?: string
}

/** One number, out of the file the project says holds it. */
export interface UnitsReadNumberArgs {
  /** path/to/file:NAME, relative to the project */
  address: string
  /** the project whose scale this is; default "." */
  root?: string
}

/** A verdict a person gave in conversation, answering a sitting by name (§PW375). */
export interface VerdictAnswerArgs {
  /** the sitting, as its manifest or the folder the page lists it in */
  sitting: string
  /** what the person said of it */
  choice: "accept" | "look" | "number"
  /** the person's own sentence, as they said it */
  why: string
  /** one family; every family where empty */
  family?: string
  /** the project the sitting belongs to; default "." */
  root?: string
}

/** The answers a person gave on the review page since a time, to resume from. */
export interface VerdictAnswersArgs {
  /** the `latest` of the last read; everything if empty */
  since?: string
  /** the open loop run to carry each answer into */
  run?: Record<string, unknown>
  /** the project the paths resolve against; default "." */
  root?: string
}

/** What a person said of a family, carried into the ledger and the spec. */
export interface VerdictJudgeArgs {
  /** each member: name, spec and new, and optionally old, capture with box, shown, and canon, the style family an accepted picture joins */
  members: unknown[]
  /** what the person said of the family */
  choice: "accept" | "look" | "number"
  /** the person's own sentence, as they said it */
  why: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** the open loop run the verdict is recorded in */
  run?: Record<string, unknown>
  /** with no run: the asset a run is opened and closed for, here */
  asset?: string
  /** the predicates the person blamed, for look; default [] */
  named?: unknown[]
  /** the date of the verdict; today where empty */
  when?: string
}

/** A refused picture a person accepted after all, from wherever they said it. */
export interface VerdictPromoteArgs {
  /** the gate run the picture was refused in, by its id */
  gate: string
  /** the refused picture, as the gate run lists it */
  picture: string
  /** the person's own sentence, as they said it */
  why: string
  /** a style family it joins too, if the person said so */
  canon?: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** The family on one picture: old beside new at the size shown, and what failed. */
export interface VerdictSheetArgs {
  /** each member: name, spec and new, and optionally old, capture with box, shown, and canon, the style family an accepted picture joins */
  members: unknown[]
  /** where the sheet is written, under the project */
  out: string
  /** the project the paths resolve against; default "." */
  root?: string
}

/** Every pending family's sheet in one folder, so a person looks once (§PW110). */
export interface VerdictSittingArgs {
  /** each family's name to its members, as for a sheet */
  families: Record<string, unknown>
  /** the folder every family's sheet is written into */
  out: string
  /** the project the paths resolve against; default "." */
  root?: string
  /** what the person should know, under the summary */
  about?: string
}

/** Build declared particle and ribbon effects into Godot scenes, each recorded. */
export interface VfxBuildArgs {
  /** the *.vfx.toml, relative to the project */
  source: string
  /** one effect; left out, every one */
  effect?: string
  /** the folder the scenes go to; [paths] vfx, else beside the source */
  out?: string
  /** the project the effects belong to; default "." */
  root?: string
}

/** Watch each effect over its life on a neutral grey, as a sitting for a person. */
export interface VfxPreviewArgs {
  /** the *.vfx.toml, relative to the project */
  source: string
  /** the folder the sitting is laid out in */
  out: string
  /** one effect; left out, every one */
  effect?: string
  /** frames on each sheet; from 2 to 12; default 6 */
  stills?: number
  /** each effect's scene as the game draws it now, filmed above it */
  against?: Record<string, unknown>
  /** what the person should know, under the summary */
  about?: string
  /** the project the effects belong to; default "." */
  root?: string
}

/** Keep the preview a person accepted as its entity's voice, written in the world. */
export interface VoiceChooseArgs {
  /** the preview a person accepted, as a path */
  preview: string
  /** the *.world.toml, where the project has several */
  world?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Previews of an entity's described voice, laid out for a person to hear. */
export interface VoiceDesignArgs {
  /** the world entity whose voice is described */
  entity?: string
  /** the line the previews speak; the voice's own */
  sample?: string
  /** the folder the previews and the sitting go in */
  out?: string
  /** the service's model, priced in [service]; default "eleven_multilingual_ttv_v2" */
  model?: string
  /** the *.world.toml, where the project has several */
  world?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Voice the string table's lines as a set, each in its speaker's voice (§PW322). */
export interface VoiceLinesArgs {
  /** only this entity's lines; all if unset */
  speaker?: string
  /** only this locale's column; every one if unset */
  locale?: string
  /** only these keys of the table */
  keys?: unknown[]
  /** send them; false answers the plan alone; default false */
  spend?: boolean
  /** the service's model, priced in [service]; default "eleven_multilingual_v2" */
  model?: string
  /** the *.world.toml, where the project has several */
  world?: string
  /** the [service.<name>] to use; needed only where there are several */
  service?: string
  /** the project whose ledger this is; default "." */
  root?: string
}

/** Hold every line of the string table, in every locale, to the world's names and rules; each finding names the key, the locale and the rule. */
export interface WordsCheckArgs {
  /** the *.world.toml; needed only where the project holds several */
  world?: string
  /** the project whose text this is; default "." */
  root?: string
}

/** Every character a line needs that the font drawing it lacks (§PW335). */
export interface WordsGlyphsArgs {
  /** the project whose text this is; default "." */
  root?: string
}

/** Put every spoken line no verdict covers on the review page, one family a line. */
export interface WordsSheetArgs {
  /** the folder the sitting is laid out in */
  out: string
  /** approved lines shown beside each, per speaker; from 0 to 12; default 3 */
  examples?: number
  /** only lines someone says; false, every row; default true */
  spoken?: boolean
  /** what the person should know, under the summary */
  about?: string
  /** the *.world.toml; needed only where the project holds several */
  world?: string
  /** the project whose text this is; default "." */
  root?: string
}

/** The literal texts in the project's scenes that are not keys of the string table. */
export interface WordsUnlistedArgs {
  /** the project whose text this is; default "." */
  root?: string
}

/** The world's entities and rules as the project declares them, or one entity. */
export interface WorldReadArgs {
  /** one entity's id; every entity where unset */
  entity?: string
  /** the *.world.toml; needed only where the project holds several */
  world?: string
  /** the project the world belongs to; default "." */
  root?: string
}

/** Everything wrong with the world file, each finding on its own line with a remedy. */
export interface WorldValidateArgs {
  /** the *.world.toml; needed only where the project holds several */
  world?: string
  /** the project the world belongs to; default "." */
  root?: string
}

/** Every operation by its dotted name, with the arguments it takes. */
export interface Operations {
  "accept.check": AcceptCheckArgs
  "accept.check_screen": AcceptCheckScreenArgs
  "accept.verify": AcceptVerifyArgs
  "asset.brief": AssetBriefArgs
  "calibrate.apply": CalibrateApplyArgs
  "calibrate.run": CalibrateRunArgs
  "capture.declared": CaptureDeclaredArgs
  "capture.movie": CaptureMovieArgs
  "capture.run": CaptureRunArgs
  "clip.camera": ClipCameraArgs
  "clip.compiled": ClipCompiledArgs
  "clip.new": ClipNewArgs
  "clip.read": ClipReadArgs
  "clip.retime": ClipRetimeArgs
  "clip.set_key": ClipSetKeyArgs
  "clip.write": ClipWriteArgs
  "compose.place": ComposePlaceArgs
  "compose.sheet": ComposeSheetArgs
  "cost.read": CostReadArgs
  "engine.check": EngineCheckArgs
  "engine.cost": EngineCostArgs
  "engine.find": EngineFindArgs
  "engine.perf": EnginePerfArgs
  "engine.preset_search": EnginePresetSearchArgs
  "engine.run": EngineRunArgs
  "engine.states": EngineStatesArgs
  "engine.sweep": EngineSweepArgs
  "game.batch": GameBatchArgs
  "game.call": GameCallArgs
  "game.close": GameCloseArgs
  "game.crash_read": GameCrashReadArgs
  "game.export_smoke": GameExportSmokeArgs
  "game.input": GameInputArgs
  "game.keep": GameKeepArgs
  "game.open": GameOpenArgs
  "game.query": GameQueryArgs
  "game.record_flow": GameRecordFlowArgs
  "game.rekey": GameRekeyArgs
  "game.release_check": GameReleaseCheckArgs
  "game.replay": GameReplayArgs
  "game.set": GameSetArgs
  "game.shot": GameShotArgs
  "game.step": GameStepArgs
  "game.test": GameTestArgs
  "game.text_fit": GameTextFitArgs
  "game.wait": GameWaitArgs
  "geometry.build": GeometryBuildArgs
  "geometry.build_all": GeometryBuildAllArgs
  "geometry.compare": GeometryCompareArgs
  "geometry.describe": GeometryDescribeArgs
  "geometry.fit": GeometryFitArgs
  "geometry.variants": GeometryVariantsArgs
  "godot.install": GodotInstallArgs
  "icons.build": IconsBuildArgs
  "kit.install": KitInstallArgs
  "kit.list": KitListArgs
  "kit.prove": KitProveArgs
  "kit.update": KitUpdateArgs
  "loop.assets": LoopAssetsArgs
  "loop.bounds": LoopBoundsArgs
  "loop.changes": LoopChangesArgs
  "loop.compare": LoopCompareArgs
  "loop.finish": LoopFinishArgs
  "loop.judged": LoopJudgedArgs
  "loop.pending": LoopPendingArgs
  "loop.runs": LoopRunsArgs
  "loop.spent": LoopSpentArgs
  "loop.start": LoopStartArgs
  "measure.available": MeasureAvailableArgs
  "measure.contrast": MeasureContrastArgs
  "measure.digest": MeasureDigestArgs
  "measure.flashes": MeasureFlashesArgs
  "measure.pressure": MeasurePressureArgs
  "measure.same": MeasureSameArgs
  "measure.take": MeasureTakeArgs
  "mesh.buy": MeshBuyArgs
  "motion.bake": MotionBakeArgs
  "music.render": MusicRenderArgs
  "music.to_midi": MusicToMidiArgs
  "music.validate": MusicValidateArgs
  "normalise.ingest": NormaliseIngestArgs
  "offscreen.routes": OffscreenRoutesArgs
  "panel.build": PanelBuildArgs
  "panel.capture": PanelCaptureArgs
  "picture.against_parent": PictureAgainstParentArgs
  "picture.buy": PictureBuyArgs
  "picture.collect": PictureCollectArgs
  "picture.describe": PictureDescribeArgs
  "picture.fit": PictureFitArgs
  "picture.gate": PictureGateArgs
  "picture.letters": PictureLettersArgs
  "picture.vary": PictureVaryArgs
  "picture.vector": PictureVectorArgs
  "port.run": PortRunArgs
  "project.check": ProjectCheckArgs
  "project.init": ProjectInitArgs
  "project.inventory": ProjectInventoryArgs
  "project.new": ProjectNewArgs
  "provenance.borrow": ProvenanceBorrowArgs
  "provenance.credits": ProvenanceCreditsArgs
  "provenance.dependents": ProvenanceDependentsArgs
  "provenance.generated": ProvenanceGeneratedArgs
  "provenance.outdated": ProvenanceOutdatedArgs
  "provenance.read": ProvenanceReadArgs
  "provenance.unrecorded": ProvenanceUnrecordedArgs
  "provenance.verify": ProvenanceVerifyArgs
  "purchase.adopt": PurchaseAdoptArgs
  "purchase.allow": PurchaseAllowArgs
  "purchase.find": PurchaseFindArgs
  "purchase.held": PurchaseHeldArgs
  "purchase.ledger": PurchaseLedgerArgs
  "purchase.quote": PurchaseQuoteArgs
  "purchase.reconcile": PurchaseReconcileArgs
  "purchase.remaining": PurchaseRemainingArgs
  "purchase.spent": PurchaseSpentArgs
  "reference.frames": ReferenceFramesArgs
  "reference.pick": ReferencePickArgs
  "reference.prepare": ReferencePrepareArgs
  "render.bake": RenderBakeArgs
  "render.plan": RenderPlanArgs
  "review.answer": ReviewAnswerArgs
  "review.canon": ReviewCanonArgs
  "review.compare": ReviewCompareArgs
  "review.state": ReviewStateArgs
  "revision.ask": RevisionAskArgs
  "revision.check": RevisionCheckArgs
  "revision.close": RevisionCloseArgs
  "revision.open": RevisionOpenArgs
  "revision.outside": RevisionOutsideArgs
  "revision.settings": RevisionSettingsArgs
  "revision.turn": RevisionTurnArgs
  "schema.proved": SchemaProvedArgs
  "schema.read": SchemaReadArgs
  "schema.validate": SchemaValidateArgs
  "search.sweep": SearchSweepArgs
  "search.worth_parallel": SearchWorthParallelArgs
  "shape.check": ShapeCheckArgs
  "shape.silhouette": ShapeSilhouetteArgs
  "shape.turntable": ShapeTurntableArgs
  "skeleton.joints_in": SkeletonJointsInArgs
  "skeleton.plan": SkeletonPlanArgs
  "skeleton.plays": SkeletonPlaysArgs
  "skeleton.shared": SkeletonSharedArgs
  "sound.buy": SoundBuyArgs
  "sound.declared": SoundDeclaredArgs
  "sound.measure": SoundMeasureArgs
  "sound.sitting": SoundSittingArgs
  "sound.speak": SoundSpeakArgs
  "sound.speech": SoundSpeechArgs
  "sound.synth": SoundSynthArgs
  "sprites.matched": SpritesMatchedArgs
  "store.capsules": StoreCapsulesArgs
  "style.drift": StyleDriftArgs
  "style.read": StyleReadArgs
  "tables.check": TablesCheckArgs
  "texture.worth_scrubbing": TextureWorthScrubbingArgs
  "trace.read": TraceReadArgs
  "units.check": UnitsCheckArgs
  "units.engine_scale": UnitsEngineScaleArgs
  "units.read_number": UnitsReadNumberArgs
  "verdict.answer": VerdictAnswerArgs
  "verdict.answers": VerdictAnswersArgs
  "verdict.judge": VerdictJudgeArgs
  "verdict.promote": VerdictPromoteArgs
  "verdict.sheet": VerdictSheetArgs
  "verdict.sitting": VerdictSittingArgs
  "vfx.build": VfxBuildArgs
  "vfx.preview": VfxPreviewArgs
  "voice.choose": VoiceChooseArgs
  "voice.design": VoiceDesignArgs
  "voice.lines": VoiceLinesArgs
  "words.check": WordsCheckArgs
  "words.glyphs": WordsGlyphsArgs
  "words.sheet": WordsSheetArgs
  "words.unlisted": WordsUnlistedArgs
  "world.read": WorldReadArgs
  "world.validate": WorldValidateArgs
}

/** The operations whose every argument may be left out. */
export type Bare = "accept.verify" | "capture.declared" | "engine.check" | "engine.find" | "engine.perf" | "engine.states" | "game.crash_read" | "game.export_smoke" | "game.open" | "game.release_check" | "game.test" | "kit.list" | "kit.prove" | "loop.assets" | "loop.bounds" | "loop.pending" | "loop.runs" | "measure.available" | "measure.pressure" | "mesh.buy" | "offscreen.routes" | "picture.buy" | "project.check" | "project.init" | "project.inventory" | "provenance.credits" | "provenance.generated" | "provenance.outdated" | "provenance.unrecorded" | "provenance.verify" | "purchase.held" | "purchase.ledger" | "purchase.remaining" | "purchase.spent" | "render.plan" | "review.canon" | "review.state" | "revision.open" | "schema.read" | "sound.buy" | "sound.declared" | "sound.speak" | "style.read" | "tables.check" | "units.engine_scale" | "verdict.answers" | "voice.design" | "voice.lines" | "words.check" | "words.glyphs" | "words.unlisted" | "world.read" | "world.validate"

/** Every operation `describe` listed when this file was written. */
export const OPERATIONS = [
  "accept.check",
  "accept.check_screen",
  "accept.verify",
  "asset.brief",
  "calibrate.apply",
  "calibrate.run",
  "capture.declared",
  "capture.movie",
  "capture.run",
  "clip.camera",
  "clip.compiled",
  "clip.new",
  "clip.read",
  "clip.retime",
  "clip.set_key",
  "clip.write",
  "compose.place",
  "compose.sheet",
  "cost.read",
  "engine.check",
  "engine.cost",
  "engine.find",
  "engine.perf",
  "engine.preset_search",
  "engine.run",
  "engine.states",
  "engine.sweep",
  "game.batch",
  "game.call",
  "game.close",
  "game.crash_read",
  "game.export_smoke",
  "game.input",
  "game.keep",
  "game.open",
  "game.query",
  "game.record_flow",
  "game.rekey",
  "game.release_check",
  "game.replay",
  "game.set",
  "game.shot",
  "game.step",
  "game.test",
  "game.text_fit",
  "game.wait",
  "geometry.build",
  "geometry.build_all",
  "geometry.compare",
  "geometry.describe",
  "geometry.fit",
  "geometry.variants",
  "godot.install",
  "icons.build",
  "kit.install",
  "kit.list",
  "kit.prove",
  "kit.update",
  "loop.assets",
  "loop.bounds",
  "loop.changes",
  "loop.compare",
  "loop.finish",
  "loop.judged",
  "loop.pending",
  "loop.runs",
  "loop.spent",
  "loop.start",
  "measure.available",
  "measure.contrast",
  "measure.digest",
  "measure.flashes",
  "measure.pressure",
  "measure.same",
  "measure.take",
  "mesh.buy",
  "motion.bake",
  "music.render",
  "music.to_midi",
  "music.validate",
  "normalise.ingest",
  "offscreen.routes",
  "panel.build",
  "panel.capture",
  "picture.against_parent",
  "picture.buy",
  "picture.collect",
  "picture.describe",
  "picture.fit",
  "picture.gate",
  "picture.letters",
  "picture.vary",
  "picture.vector",
  "port.run",
  "project.check",
  "project.init",
  "project.inventory",
  "project.new",
  "provenance.borrow",
  "provenance.credits",
  "provenance.dependents",
  "provenance.generated",
  "provenance.outdated",
  "provenance.read",
  "provenance.unrecorded",
  "provenance.verify",
  "purchase.adopt",
  "purchase.allow",
  "purchase.find",
  "purchase.held",
  "purchase.ledger",
  "purchase.quote",
  "purchase.reconcile",
  "purchase.remaining",
  "purchase.spent",
  "reference.frames",
  "reference.pick",
  "reference.prepare",
  "render.bake",
  "render.plan",
  "review.answer",
  "review.canon",
  "review.compare",
  "review.state",
  "revision.ask",
  "revision.check",
  "revision.close",
  "revision.open",
  "revision.outside",
  "revision.settings",
  "revision.turn",
  "schema.proved",
  "schema.read",
  "schema.validate",
  "search.sweep",
  "search.worth_parallel",
  "shape.check",
  "shape.silhouette",
  "shape.turntable",
  "skeleton.joints_in",
  "skeleton.plan",
  "skeleton.plays",
  "skeleton.shared",
  "sound.buy",
  "sound.declared",
  "sound.measure",
  "sound.sitting",
  "sound.speak",
  "sound.speech",
  "sound.synth",
  "sprites.matched",
  "store.capsules",
  "style.drift",
  "style.read",
  "tables.check",
  "texture.worth_scrubbing",
  "trace.read",
  "units.check",
  "units.engine_scale",
  "units.read_number",
  "verdict.answer",
  "verdict.answers",
  "verdict.judge",
  "verdict.promote",
  "verdict.sheet",
  "verdict.sitting",
  "vfx.build",
  "vfx.preview",
  "voice.choose",
  "voice.design",
  "voice.lines",
  "words.check",
  "words.glyphs",
  "words.sheet",
  "words.unlisted",
  "world.read",
  "world.validate",
] as const

/** Call one operation with the arguments describe says it takes. */
export function call<K extends Bare>(
  client: Client, operation: K, args?: Operations[K]): Promise<unknown>
export function call<K extends keyof Operations>(
  client: Client, operation: K, args: Operations[K]): Promise<unknown>
export function call(
  client: Client, operation: keyof Operations, args?: object,
): Promise<unknown> {
  return client.call(operation, { ...(args ?? {}) })
}
