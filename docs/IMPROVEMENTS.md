# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW721 A quoted sentence found and highlighted

Found moving the Scion explainer's page film into urdido (urdido UR53; marketing's
`japode/scion/bin/film-page.py`). The video quotes a published post, and each quote is
shown by filming the real page: it scrolls, eased, until the quoted sentence sits
mid-screen, then fades a highlighter in over each of its lines. The highlighter is an
overlay, never a change to the text, and a sentence the page no longer prints stops the
film.

A declared visit cannot do this. `scroll` moves by pixels, which is wrong as soon as the
page's layout or a banner changes, and no step finds a text or draws anything over it.
So the script stays a Playwright program copied into each video, outside polyweave's
record and its marks.

What capture.web should offer, as two steps:
- `{ find = "<sentence>", within = "p, li, blockquote" }`: locate the sentence across the
  block's text nodes, scroll it to the middle of the viewport with the eased scroll PW704
  brings, and refuse the visit, naming the sentence, when the page does not print it
  (whitespace folded).
- `{ highlight = "<sentence>", color = "rgba(255,200,40,.45)" }`: draw one overlay box per
  client rect of the found range, growing left to right over half a second each, with
  `pointer-events: none` and no change to the DOM text.

The record marks when each step started, so a video can time its narration against the
moment the highlight lands.

### §PW725 A review window rendered from its own clips

Split from PW713 (2026-11-23). `video.cut interval=` renders a review window through the
whole cut's own graph and seeks the output to it, which keeps the mix, the fades and
every voice's timing exact but decodes and filters every clip before the window: a
review of the last ten seconds of a six-minute cut costs nearly the whole render.

Rendering only the clips that overlap the window means rebuilding the graph for a slice,
and three things move when it is sliced: a still with `motion` zooms over its own frame
count, so a trimmed one restarts its zoom; a crossfade's offset is counted from the
cut's start; and subtitles keep the cut's times. Each needs its offset carried: the
zoom's `on` started at the frames the window skips, every xfade offset less the window's
start, music `music_from` plus it, a voice starting before the window entered with an
input seek, and subtitles shifted. Done when a window's sampled frames and audio match
the same seconds of a whole cut within the encoder's noise, and it renders in time
proportional to the window, not to where it sits.

### §PW726 A search that knows what a library rejected

Split from PW714 (2026-11-23). `video.library` keeps the ranges a person rejected, and
adding a file it holds answers that entry rather than a fresh one, and a cut refuses a
clip over a rejected range. But `stock.find` answers hits by service and id with no look
at any library, so the agent reading the search still meets a clip a person turned down
for blur or a mistaken identity as a new candidate, and spends a fetch and a review to
learn it again.

A library source fetched by `stock.fetch` has a record whose `task_id` is
`<service>:<id>`. `stock.find` given `library=<path>` (or the libraries a project
declares) marks each hit the library holds with its rights and its rejected and accepted
ranges, and a hit whose every range is rejected or whose rights are refused as
`rejected` with the first reason. It never drops the hit: hiding it is a decision the
person did not make. Done when a hit a library rejected is answered marked, with who
rejected it and why, and an uncatalogued one is answered as before.

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW449 Driven from a second MCP client

The server is MCP and nothing in the protocol ties it to Claude Code, but everything
that teaches an agent to use it arrives with the Claude Code plugin: the skill, and the
hook that guards derived files. Another client, such as Cursor or Codex, gets the tools
list and nothing else. Whether an agent there gets a call right the first time, which is
the project's one test of a feature, has never been tried.

MCP directories in 2026 compare Blender, Godot and Unity servers side by side, and they
are where a developer looks for one. Being listed there is free reach, but only honest
once the surface has been driven from a client without the skill.

The run is the line: set the server up in Claude Desktop, the client the owner has
(2026-10-15), ask it for one asset end to end, and file what it got wrong as friction.
Two findings are expected and are the reason to do it before any listing. Whatever the
skill alone teaches has to move into tool descriptions or `describe`. And every promise
that relies on the skill or a hook, rather than the server, is named; PW443 is the first
of those.

Evidence that it landed: a second client builds, checks and offers one asset for a
verdict, and each gap it met is a filed line.

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

## Block Q — Words held to the world

## Block R — Levels measured before a person plays them

### §PW327 Playtest traces measured beside the declared curve

Found in starship while planning its Block V (RK176, RK177): the owner finds the waves
unbalanced and wants balance measured, not felt.

PW205 measures what a wave declares: Spinhold's `dev/level_probe.gd` reads each
`phase_<n>.waves.toml` through `WaveFile`, so formations, rails, `follow` and `sway`
arrive as spawns, and reports the phase's threat, peak and median alive and longest gap
through `level.probe`, held as a curve by `game/waves/phases.levels.toml`. It cannot
measure what happened when a person played the phase, and it answers totals, not
seconds.

What starship still needs from polyweave:

- **A trace contract.** The game writes one event per line, each stamped with phase,
  wave and second: `spawn` (kind, weight), `kill` (kind, time alive), `hit` and
  `life_lost`. polyweave reads one trace or many and gives, per second, damage taken,
  kills and enemies alive, averaged across runs.
- **The declared curve beside it.** The same pressure per second, entering and alive in
  the two bounding cases (every enemy killed on landing; nothing killed until the time
  limit), laid under the trace so where players struggle is read against what the wave
  asked.
- **A spec over both.** Bounds such as "alive pressure never above N" and "each phase's
  peak above the one before", checked by `accept.check` and failing with the rule
  named. A person sets the bounds; the feel stays a verdict.

Until it lands, starship keeps the per-second pass in `dev/pressure.gd`, named against
this line.

### §PW722 A step held in the probe's own precision

Found holding Cottony's 20 levels to curve A (PW206, 2026-11-23). `level.curve` with
`step = 0.06` refused level 10 to 11: "level_011 is easier than level_010 by 0.06, past
the step of 0.06". The probe recorded 0.94 and 1.0; their difference in floating point
is 0.06000000000000005, and the comparison takes it as past the bound, so a set sitting
on its declared step is reported broken.

Compare the step, the region and the rise in the probe's own precision: round each
difference to the places the probe records (or compare within a small epsilon such as
1e-9) before holding it to its bound, and say the rounded figure in the finding. A test
holds a pair whose difference equals the step exactly as within it.

### §PW723 A level search keeps an integer whole

Found tuning Cottony's level 18 toward curve A (PW206, 2026-11-23):
`search.sweep(producer="level")` over `[search.moves] min = 20, max = 25`, where `moves`
is a whole number in the level, sampled 20, 21, 22, 22.5, 23 and 24. The candidate with
22.5 was written into the level and probed; Cottony's probe read it as 22, so one of six
probes, each 50 seeded games in Godot, measured a candidate it had already measured, and
the trace lists 22.5 as if it were a level that can exist.

The measurements spec says a level search keeps an integer an integer. Where the key's
value in the fixed level is an integer, every sample is rounded before it is written, a
value already measured is not measured again, and the trace never names a fraction for
it. A test sweeps an integer key with a budget past its range and finds each candidate
whole and unique.

### §PW724 A level probed by its number, from the game's curve

Found closing PW206 in Cottony (2026-11-23). Its design asks for "probing levels 21 to
200 from the curve and reporting where they leave the set spec's bounds", since every
level past the 20 shipped files is the game's fallback formula. `level.probe` refuses
`data/levels/level_025.json` with `level.no-level` because no file is there, and a level
with no file is exactly the level a fallback curve makes. The workaround was an empty
`{}` file per sampled level in the work area, which Cottony's probe reads as "the curve
decides every key".

`level.probe` (and `level.curve` over a set) should take a level by its number where the
project's probe can build it from its own curve: `[levels] curve_probe = true`, or a
`number` argument, passing `level=<number>` to the probe instead of a path, and
recording the probe against the curve's source file rather than a level file. A sampled
tail (`numbers = [25, 40, 100, 200]`) is then one call, and its record says the curve
moved when the source does.

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

### §PW311 The window proved on Starship

Every block here that reached a person was finished only when a real owner used it.
PW287 through PW295 were each found by Starship's owner on a review page that passed
every test. The window is the same kind of surface, so it is proved the same way.

On Starship, the owner does the following in their own language:
- opens the project in the window;
- finds one generated picture and one sound through the inventory, without typing a path;
- marks where the picture is wrong;
- asks for a change in their own words;
- answers the session's questions;
- judges the result in the sitting it ends on.

One of the two revisions should need a paid call, so the price stop (PW308) is exercised
on a real balance under a small ceiling. One should reach a dependent, so the scope
question (PW309) is seen.

The evidence is the two closed revision records, the screenshots of each step taken
before handing the window over, and every friction filed as its own line in this block.
It is not a test run. A change of plan that the owner asks for mid-way ("undo, try the
other palette") is part of what is being proved, because a revision a person refines
several times is the case this block exists for.

## Block V — Parts every game repeats, installed already proved

### §PW368 Declared states and transitions

Menus, characters and the flow of a game are each a state machine written by hand, and
the failure is structural: a state no transition reaches, or one with no way out that
was not meant to be final, found only by a person who walks into it.

A kit could let the project declare its states and transitions, generate the skeleton
the code fills in, and check in the gate that every state is reachable from the start
and has an exit unless it is declared final. The check is the valuable half, since it
needs no run.

It is the most opinionated kit in this block: games structure their state very
differently, and a skeleton that suits one may fight the next. So it stays an idea until
Starship and Cottony both show code it would replace, at which point the shape it should
take is read off that code rather than invented here.

## Block W — A core that grows by layers

## Block X — The site on the shared design system
