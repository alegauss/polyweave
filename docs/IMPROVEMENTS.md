# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW692 video.buy through Scenario

Met in viglet/marketing (the Viglet Shio promo's opening, 2026-11-09): the project
wanted a short opening video generated from a prompt on Scenario, and polyweave has no
verb for it. `picture.buy` reaches Scenario's public models (PW688) through
`generate/custom/<model>` and takes the job's first asset, which is the same route a
Scenario video model answers on, but the picture layer opens the delivery with PIL and
measures it as an image, so a video model's mp4 cannot come through it. The project fell
back to a script of its own that calls Scenario's API directly
(`shio/promo/bin/intro-video.mjs`), outside the ledger, the budget and the provenance.

Add `video.buy`: a prompt (and optionally a still to start from), a model, a duration
and an aspect ratio, priced first with Scenario's quote as `picture.buy` is
(`creativeUnitsCost`), spent inside the project's budget, delivered to `--out` as a
video with its provenance beside it, and measured as a video (length, size, whether it
has sound). The service layer's submit, poll and deliver already do the Scenario part;
what is missing is a verb whose delivery is not a picture.

### §PW693 A remix keeps its parent's transparency

**Where.** marketing/shio/promo, the Viglet Shio promo's thumbnail (VM22), 2026-11-10.
The parent was another video's transparent presenter
(`demo/thumbnail/ana-wordpress.png`, bought with `picture.buy --transparent`).

```
python -m polyweave picture.vary --service ideogram --parent demo/thumbnail/ana-wordpress.png \
  --out demo/thumbnail/ana-agent.png --change remix --strength 40 --prompt "... transparent background ..."
```

**What came back.** `ok`, 0.08 credits, a 896x1120 **rgb24 picture on white**. The
parent was RGBA and the prompt asked for transparency; neither the answer nor the record
says the cut-out was lost, and `picture.vary` takes no `--transparent`.

**Also.** The first call refused `fetch.unpriced` (no `remix` row in `[service.ideogram]
prices`). The remedy was right, but nothing says what a remix costs, so the project
guessed 0.08.

**Workaround.** `shio/promo/bin/thumbnail.mjs`, `cutOut()`: a flood fill of near-white
from the edges, made transparent in a canvas, with a feathered ring. A guess per
picture; it fringes hair.

**What polyweave should do.** A remix of a cut-out parent comes back cut out the same
way, and `picture.vary` takes `--transparent` to ask either way. The answer and the
record say whether the result is transparent. The refusal for an unpriced remix names
the service's published price.

### §PW694 A copy's record stays out of the shipped folder and its credits resolve through its source

**Where it happened.** Viglet Shio, SH1431, 2026-11-10, three marketplace packages
(`marketplace/ervalume`, `orvalha`, `taipal` in D:\Git\viglet\shio\2026.3). Each cut its
shipped WebP files with `polyweave picture.copies` from a `*.copies.toml`, which writes
a `<name>.webp.prov.json` beside every copy in `assets/images/`, the directory the
package ships. Shio's packager zips that directory, so 24 provenance records would have
gone into the published packages; Shio added `.*\.prov\.json` to its exclusion list as
the workaround (`shio-site/scripts/marketplace.mjs`, `NOT_PACKAGED`).

Second, `provenance.credits` lists the copies with an empty prompt, model, seed and
licence: a copy does not inherit them from its source purchase. One agent wrote a
one-off Python script to read the source records and build `assets/CREDITS.json` in the
format the earlier showcase used. A third found no way to make copies without writing a
copies table first.

**What polyweave should do.** Let a copy's record live outside the shipped directory (a
records directory declared once, like the sources'), or name it so a packager can ignore
one pattern it documents. And make a copy's credits resolve through its source:
`provenance.credits` answers prompt, model, seed, service and licence for a copy from
the purchase it was cut from, so a credits file is one call.

**Done when.** A project cuts copies into a shipped folder that then holds only the
copies, and `provenance.credits` over that folder returns each copy's source prompt and
licence.

### §PW695 A re-bought path marks the purchase it replaced, with the reason

**Where it happened.** Viglet Shio, SH1431, 2026-11-10 (`marketplace/orvalha` and
`taipal` in D:\Git\viglet\shio\2026.3). After a rejected picture, the agent bought again
with `picture.buy --out` the same path. The PNG and its `.prov.json` were overwritten,
which is right, and `polyweave.purchases.json` kept every purchase, which is right for
the spend. But nothing in the ledger says which purchase a path now holds and which were
superseded and why: Taipal's `team-portrait` was bought three times, and a reader of the
ledger sees three equal entries for one file. The credits file had to take "the last
purchase for each path" by convention.

**What polyweave should do.** When a buy writes a path an earlier purchase wrote, record
the earlier one as superseded (by which purchase, when), and let the buy carry an
optional reason (`--replaces-because "malformed hands"`) that lands on the superseded
entry. The ledger then answers, per path, the purchase it holds and the rejected ones
with reasons, which is the history a reviewer and the next agent need.

**Done when.** Re-buying a path marks the earlier purchase superseded in the ledger with
the reason given, and `purchase.ledger` shows per path the held purchase and the
rejected ones.

### §PW696 A bought photo is checked for the faults generated photos have

**Where it happened.** Viglet Shio, SH1431, 2026-11-10: 24 photographs for three
marketplace packages (`marketplace/ervalume`, `orvalha`, `taipal` in
D:\Git\viglet\shio\2026.3), bought with `picture.buy --model 4.0` on Ideogram. Every buy
answered ok. The owner found by eye a physiotherapy photo whose patient's arm fuses into
the therapist's hands, and a chef portrait with no thumb. The agents then re-bought 10
more (0.60 USD): uncountable hands, a cat merging into an arm, pseudo-lettering, a table
merging into the floor. `picture.gate` only compares a silhouette to an outline.

**What it costs.** The only check on a bought photo is a person's eyes, and an agent
told to look missed it twice.

**What polyweave should do.** A check on a bought picture, at the buy or run over a set,
reporting the known faults of generated photos: malformed or fused hands and limbs,
extra heads, pseudo-text, objects merging. It can call a vision model through a declared
service, records its findings in the provenance, and answers per picture with the fault
and where in the frame. A failing purchase stays in the ledger marked not usable, with
prompt advice (frame hands out, avoid people touching).

**Done when.** The check over the 24 Shio photos flags the two the owner rejected and
the pseudo-text ones, naming each fault.

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

### §PW697 An acceptance spec on an encoded video

**Where.** marketing/japode/scion, the three YouTube Shorts cut from the Scion video by
`japode/scion/bin/short.py` (marketing VM31), 2026-11-12.

**What happened.** Every bar a Short is held to was checked by hand, after the encode,
with commands typed one by one:

    ffmpeg -hide_banner -i scion-short-2-pt-BR.mp4 -af ebur128=peak=true -f null -
    ffprobe -v error -show_entries stream=codec_type,duration -of csv=p=0 scion-short-2-pt-BR.mp4
    ffmpeg -ss 33.5 -i scion-short-2-pt-BR.mp4 -frames:v 1 f.png   (one still per moment, then hstack)

and read by eye: -14.9 LUFS, -1.3 dBTP, video and audio the same length, the end not
frozen. The first cut held a 3 s frozen end card that no measure caught; it took reading
other people's Shorts rules to learn it breaks the loop.

**What was expected.** An acceptance spec on an encoded video, as PW113 gave a WAV:

- length between bounds (a Short 20 to 55 s);
- integrated loudness and true peak (-14 LUFS within 1, under -1 dBTP);
- video and audio streams of the same length within a frame;
- no frozen stretch longer than N s, at the end above all (frame difference under a floor);
- cut cadence: the longest stretch without a visual change (scene score over a threshold) under N s;
- frame size and rate (1080x1920, 30).

Each predicate reports its measured value, so a failed Short says which bar and by how
much. video.cut's output could carry the same spec.

**Workaround.** The commands above, in the session; nothing kept.

### §PW698 Burned-in text held to a platform's safe area

**Where.** marketing/japode/scion, the Scion Shorts (`japode/scion/bin/short.py`,
marketing VM31), 2026-11-12.

**What happened.** A vertical video carries burned-in text (a hook at the top, keyword
callouts over the picture, word-timed captions below) and the platform draws its own
interface over the frame: on YouTube Shorts the right column of buttons (about the right
140 px from y 900 to 1700 at 1080x1920) and the title and channel at the bottom (about
the bottom 420 px). Whether any line of text reaches those zones was judged by looking
at four stills scaled to 360 px. The captions were moved left by hand (centre x 500) and
their font shrunk because a 22-character line at 70 px could reach x 960.

**What was expected.** A predicate that holds the text a video draws to a declared safe
area, per platform, over the whole length and not four stills:

- the safe area declared in the spec (a box, plus excluded boxes), with YouTube Shorts, Reels and TikTok as named presets a project can override;
- the text's extent measured, either from the subtitle file the cut burns in (an .ass, laid out by libass at the frame size) or from the rendered frames;
- the answer names the line, its time and how far it crossed, so the fix is a position or a size and not a guess.

**Workaround.** Stills by hand (`ffmpeg -ss <t> -frames:v 1`, then hstack) and
eyeballing; the safe-area numbers live only in comments in short.py.

### §PW699 A thumbnail held to its title and the feed size

**Where.** marketing/japode/scion, the Scion video's YouTube thumbnail
(`japode/scion/bin/thumbnail.py` through `japode/brand/brand.py`, marketing VM30),
2026-11-12.

**What happened.** The published thumbnail says "O Git não aguentou" and "30 mil merges
por dia", and the video's title is "30 mil merges por dia: o Git não aguentou e a
Anthropic...". Every channel guide read that day says a thumbnail must add what the
title leaves out; nothing checked it, and it was noticed only on reading the first
report (12.5% click-through on 48 impressions). Legibility at feed size was never
measured either: the thumbnail was looked at once, full size.

**What was expected.** A picture spec for a thumbnail, with its title as an input:

- legible at feed size: the picture scaled to about 168x94 and its text still readable (text height in px, contrast of text against what is behind it);
- at most N words of text on it (read from the layout that drew it, or by OCR);
- shares no meaningful word with the title (stop words per language, pt-BR included);
- and a sweep over the layout's choices (which words, which picture, which number) that brings two or three variants to the review page, so the Alexandre picks one for YouTube's own A/B test. The agent never picks.

**Workaround.** None; the check was a person reading the title and the picture side by
side, after publishing.

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
