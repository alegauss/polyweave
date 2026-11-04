# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW659 The aspect ratio a 4.0 buy asked for

Met in the Shio repository, `marketplace/quilhara/` (Shio SH1254), buying ten
photographs on Ideogram 4.0 through `picture.buy`.

```
python -m polyweave picture.buy --root . --out assets/source/home-coast.png \
  --transparent false --aspect_ratio 16x9 --prompt "..."
python -m polyweave picture.buy --root . --out assets/source/about-map.png \
  --transparent false --aspect_ratio 3x2 --prompt "..."
```

The answers were `credits: 0.06` and no warning. The files are 2496x1664 (3:2) for the
16x9 request and 1792x2240 (4:5) for the 3x2 one; the record says `details.aspect_ratio:
"3x2"` beside `details.resolution: "1792x2240"`, two fields that contradict each other
with nothing saying so. The same 16x9 request sent straight to the 3.0 endpoint earlier
in the session came back 1312x736, so either 4.0 spells the parameter differently (or
takes `resolution` instead), or it treats the ratio as a hint and the prompt overrides
it.

What polyweave should do: send the ratio in whatever form 4.0 honours (schema.read for
the service would settle which), and compare the returned resolution with the ratio
asked. A mismatch is a named finding on the answer (`picture.aspect-differs`, asked and
got), not a silent record, because the caller has already paid and a crop is a decision
about the picture.

Workaround in the project: the bought pictures are centre-cropped to the asked ratio
with Pillow in the same one-off re-encode that PW658 covers.

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

### §PW450 Buying a picture from Scenario

Block N holds pictures to a canon: a family's approved members, its palette and its
style block. The services behind it today are FLUX and Ideogram, which take the style as
words, and PW180 sends one canon picture as a style reference on Ideogram 3.0. Scenario
takes a different route: a model trained on a team's own art, which reviews in 2026 name
as the strongest answer to style consistency for game art.

A canon is exactly the training set such a model wants, already chosen by a person's
verdicts. This line is an adapter behind the existing `picture.buy` surface: the same
ceiling, quote, ledger and provenance, and a record naming the trained model and which
canon members trained it, so a model trained before a member joined reads as outdated.

Training spends money, so it is a purchase like any other, quoted and bounded by the
ceiling, and never started on the agent's own judgement. The pictures it returns are
held to the canon and the gate like any service's; being trained on the style earns no
pass.

Evidence that it landed: one family's canon trains a Scenario model within the ceiling,
a picture bought from it passes or fails the family's gate, and its record names the
model and the members.

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

## Block Q — Words held to the world

## Block R — Levels measured before a person plays them

### §PW206 Cottony's levels made through polyweave

Cottony is where the level loop pays for itself first. Its 20 shipped levels are JSON
files generated from curve constants that `make_levels.py` reads out of `level_set.gd`
with a regular expression. Any level without a file falls back to that same curve at
runtime, so level 900 is only as good as a curve nobody has measured.

Adoption is done when:
- Each of the 20 levels is a `*.level.toml` under a schema Cottony declares, and `level.compile` writes the JSON the game already loads.
- The match-3 probe from PW201 is Cottony's declared `[levels] probe`, and every level carries a probe record.
- A set spec holds the 20 levels to the curve a person agreed on the verdict page, and `accept.check` passes on all of them.
- `make_levels.py` is deleted, and the runtime fallback curve is fitted from the accepted levels rather than typed.

The census from Block H counts which of Cottony's levels are made this way. The fallback
curve is the part to watch: it is still a formula for levels nobody declared, and the
probe can at least sample it. Probing levels 21 to 200 from the curve and reporting
where they leave the set spec's bounds says whether the endless tail keeps the promise
the first twenty make. Cottony's RK150 (2026-10-16) set that bar by hand: the careless
spike bot, swept with engine.sweep, put level 20 at 64 to 66% wins, against the owner's
60%.

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

### §PW685 A picture fitted beside what is asked of it

Met by the owner on 2026-11-04 (PW311). The item view draws a picture at its real size
(the README's "a picture at its real size"), so a tall capture such as Spinhold's
`art/renders/ring.png` runs far below the fold with a sideways scroll bar, and asking
for a change means scrolling away from the picture to reach the box.

What to build: the picture fits the panel by default, the whole of it visible beside the
item's facts and the request box, with a toggle to its real size (and back) and a click
to see it alone at full size. Its real width and height are said beside it, so fitting
it hides nothing a person judges by.

Done when every picture in Spinhold's inventory shows whole beside its request box
without scrolling, and real size is one click.

### §PW686 The project screen across the window's width

Met by the owner on 2026-11-04 (PW311), on a 3840-pixel-wide screen: the project screen
is a narrow centred column with wide empty margins on both sides, so the list and the
item are cramped side by side while most of the window is blank.

What to build: the project screen uses the window's width. The list takes a fixed,
resizable share on the left and the item fills the rest, with a sensible maximum line
length kept for prose only. On a narrow window the two stack, as now. The layout is
`ui`'s alone; nothing in `core` or the payloads changes.

Done when, at 3840 wide, the item panel shows a picture, its facts and the request box
without the side margins taking more than a small share of the window.

### §PW687 Marks drawn where the change is asked

Met by the owner on 2026-11-04 (PW311): asking for a change to a picture from its item
view, they looked for the box to draw where it is wrong and found none. PW401 put "mark
where it is wrong" on the Decide screen only, on a sitting's card, so a request made
from the item where a person is looking at the picture carries words alone.

What to build: the item view's picture takes the same drawn boxes as Decide's, kept in
the picture's own pixels whatever size it is shown at (the code PW401 wrote is reused,
not copied), and "Ask for a change" sends them with the words: `revision.ask` keeps them
as a mask tied to the picture's digest, as `review.answer` does, and the session's first
message names them, so the agent knows where before it reads the words.

Done when a box drawn on a picture in the item view reaches the revision and the
session's opening as a mask on that picture.

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
