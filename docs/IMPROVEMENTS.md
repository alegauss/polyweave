# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

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

### §PW728 A level search's best kept, not played again

Split from PW723 (2026-11-23). A search ends by making its best sample again, so the
file at `out` is the answer and not whichever sample came last. A render serves that
from its cache at no cost. A level has no cache: `levels.sample` writes the candidate
and probes it, so a level search whose best was not its last sample plays its best level
again, 50 seeded games in Godot for a figure already in the trace.

The level producer should keep each candidate it probed, by the digest of the level it
wrote, with its `.probe.json`, so making a sample again whose level is byte for byte one
already probed copies the kept candidate and its probe record to `out` and plays
nothing. Done when a level search whose best is an earlier sample ends with `out`
holding that level and its probe, and the probe ran once per distinct candidate.

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
