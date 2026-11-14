# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

### §PW707 Measure an existing video with revision-bound evidence

Marketing VM39 needs a report bound to the exact exported MP4, without re-encoding it.
`polyweave describe video.cut` only accepts a cut source declaration; `sound.measure`
measures a sound and does not cover video streams, opening cadence or a decoded first
frame. PW702 separately covers reference.frames returning a false black opening.

Provide an operation accepting an existing MP4 that returns its SHA-256, size, duration,
streams, integrated audio loudness and true peak, first decoded video frame, and opening
presentation timestamps/frozen intervals. Bind every derived measurement and image to
that same output hash, and refuse if the input changes during measurement. Keep measured
cadence and repeated frames separate from any editorial verdict about shakiness or
quality. Marketing will use existing videomaker.media tools and direct ffprobe/ffmpeg in
videomaker/qa.py until this exists; scene counts remain project editorial metadata.

Done when a completed video can be checked in one declared operation without rebuilding
it, and its report cannot accidentally describe another revision.

### §PW708 Exact shot samples with editorial context

VM41 in D:/Git/viglet/marketing needs one still per declared beat before a full render,
labelled with the overlapping narration words, production captions and highlights,
source intervals and person/event/topic tags. `python -m polyweave describe
reference.frames` offers rate/ranges sampling of one existing video, but cannot accept
exact shot sample times with editorial labels or assemble an annotated review sheet
across unrendered source clips. video-maker will reuse its production composition for
single-frame previews and build a local HTML review sheet. Add a reusable exact-time
labelled contact-sheet operation, accepting source/time/label records and producing
images plus a portable HTML sheet; distinguish a source still from the composited
output. This complements PW700 for drawing cards.

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

### §PW700 Editorial cards before the cut

In viglet/marketing, the WordPress history uses original typographic cards, dates and
diagrams, rather than a recorded game. describe video.cut accepts still files and motion
but not an HTML card declaration; capture.web records HTTP visits rather than
deterministically rendering a local card to a PNG. The reusable video-maker cards
renderer uses Playwright to draw HTML and embed local fonts. The illustrated-history
assembly will reuse it, then encode gentle motion through the existing media runtime. No
paid image generation is needed. A reusable HTML-to-still operation should accept page
content or a local page, viewport and output, wait for fonts and images, return the file
and record its inputs. This is a narrower pre-cut rendering gap, not a claim that PW671
failed to implement motion or voice tracks.

The same gap applies to marketing/japode/brand/brand.py banner(): the 2048-by-1152
YouTube banner uses local Plus Jakarta fonts, the approved SVG J and a central
1235-by-338 safe area. Its existing Playwright renderer must still produce the final PNG
and a safe-area review image. Support self-contained branding pages as well as timeline
cards.

### §PW701 Creative Commons source clips from public video archives

For japode/wordpress, stock.find and stock.fetch support Pixabay and Pexels only. The
user requested real footage of Matt Mullenweg, Mike Little and other people named in the
history. The official WordPress YouTube channels mark FC9wfK1_F8c and CnYi-2Z92hw as
Creative Commons Attribution. Fetching a bounded excerpt requires yt-dlp metadata
inspection and section download outside polyweave. Preserve source URL, title, channel,
reported licence, retrieval date, original in and out points and content hash beside the
clip. Refuse missing or unapproved reuse licences rather than treating every public
video as stock. This is a source-ingestion gap; video.cut already accepts the resulting
local video.

### §PW702 First frame of a muxed narrated MP4

In marketing/japode/wordpress, reference.frames on video/wordpress.pt-BR.mp4 with rate
0.05 and ranges [[0,5,1]] writes a black t00000000.png, while t00001000.png is visible.
The opening scene and intro-0.mp4 both show Matt from zero. Independently decoding the
first video frame with videomaker.media.ffmpeg using -i video/wordpress.pt-BR.mp4
-frames:v 1 produces a visible title and Matt. ffprobe reports its first I frame at
0.000000. Evidence is .polyweave/final-reviewed, .polyweave/opening-check and
video/preview/first-decoded.png. The final MP4 has video, AAC and mov_text streams.
Ensure reference.frames samples the actual first decoded video frame at zero and does
not substitute a blank when a seek or timestamp boundary returns no frame.

### §PW704 A visit filmed the way a person moves

Found filming WordPress admin scenes for the Japode WordPress video (marketing
repository, `japode/wordpress/visits/wp-*.web.toml`, task VM38), with `python -m
polyweave capture.web --source visits/wp-plugins.web.toml`.

The clips come back correct but unwatchable as product scenes. A headless Chromium draws
no pointer, so a click on "Instalar agora" or "Ativar" happens with nothing moving on
screen; `scroll` is a single `page.mouse.wheel`, so the page jumps 450 px in one frame;
`type` is `page.fill`, so a search term or a post body appears whole. The editor has to
cut around each jump, and the viewer never sees what was clicked.

The marketing repository already solved this for a Playwright script:
`video-maker/story-moves.mjs` injects a pointer before the page's own scripts, moves it
to a target along a minimum-jerk arc, rings it on a click, scrolls with an eased curve
at about 200 px/s and types at a hand's pace. A declared visit cannot reach it, so VM38
held on each mark and cut there.

What capture.web should offer, as visit options rather than new steps:
- `[web] pointer = true`: draw the pointer and move it to every click and type target before
  acting, with the click ring.
- `scroll` eased over a duration (a `speed` or `seconds` key on the step, defaulting to the
  story-moves pace), so the record's step marks still say when it started and ended.
- `type` at a hand's pace (`pace` in characters per second) instead of fill, keeping `secret`
  values out of the record as today.

### §PW705 Music from stock, with its licence

Found replacing the music bed of the Japode WordPress video (marketing repository,
`japode/wordpress/video.toml`, VM38). The bed was a 30-second generated clip looped over
six minutes, and the owner heard a held note in it twelve times; he asked for an open,
licensed track instead.

`stock.find` and `stock.fetch` take `kind = picture | video` only, so no music can be
searched, fetched or recorded with its licence. The track ("Inspired", Kevin MacLeod,
incompetech.com, CC BY 4.0) was downloaded with curl into
`japode/wordpress/music/inspired.mp3`; its source, licence and credit line live only in
`storyboard.json` and the README, with no provenance record beside the file.

What polyweave should offer: `kind = "music"` on `stock.find` / `stock.fetch`, from at
least one source whose licence is machine-readable (Pixabay Music, Free Music Archive,
incompetech), with search by mood, genre and minimum length, and a `.prov.json` that
carries the page, the licence, its URL and the exact attribution text the licence
requires.

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

### §PW709 Timed editorial-label conflicts

In marketing VM43, a caption and a spoken highlight can overlap in time with conflicting
versions or duplicate labels, and a named-person/event highlight can imply that
unrelated stock footage depicts that entity. The describe catalogue has game.text_fit
but no timed editorial-label check. PW698 concerns platform safe areas, a separate
spatial check. video-maker will compare beat caption visibility intervals with resolved
highlight intervals and warn on declared person/event metadata mismatches across source
assets. Add a read-only check over labelled time intervals and optional declared entity
tags, returning every overlap and unverified entity with source/take/beat identifiers.
Do not infer a real person's identity from an image or automatically accept semantic
correspondence.

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

### §PW703 Word times from the speech check

In marketing/japode/wordpress the user requested the keyword treatment already used in
Docker and Scion. describe sound.speech exposes take and text, and its answer for
narration/pt-BR/intro.mp3 includes said.heard but no timestamped words. Existing
japode/scion/bin/check-takes.py calls ElevenLabs Scribe directly with
timestamps_granularity word and saves text, start and end with the audio hash. The
reusable video-maker transcription helper will carry that workaround for WordPress,
refusing stale times before placing callouts. sound.speech should expose and persist
service word timings as part of its own answer or artifact, together with the take hash,
so clients do not pay for or maintain a second transcription path.

### §PW706 Declared narration preflight before purchase

While implementing marketing VM29 in D:/Git/viglet/marketing, `python -m polyweave
describe voice.lines --json` exposes purchase selection and spending but no preflight
for an opening's first proof. The caller now checks before voice.lines in
video-maker/narration/opening.mjs and buy.mjs.

Allow a caller to declare a first-proof take and word offset, per-language narrator
words per minute, and a maximum estimated time. Count spoken words without delivery
tags, validate anchors and translations, and refuse before any purchase if the estimate
exceeds the declared limit. A configurable list of preamble phrases can also reject a
script before spending. These are mechanical checks against the editor's declared proof,
not an assessment of visual truth or an editorial verdict. Keep project-specific
thresholds and phrases in configuration.

Done when the same declared constraints can gate both dry plans and voice purchases
without a custom video pipeline checker. Existing scripts without this declaration
retain their purchase behavior.

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
