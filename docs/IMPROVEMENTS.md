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

VM62 additionally needs longest motionless intervals inside selected screen recordings,
with source and cut timestamps. `reference.events` reports flashes rather than pause
budgets; its source needed inspection to establish that distinction. Expose sampled
frame-change thresholds, sampling resolution, cursor-only motion policy and reviewed
holds. Accept a continuous active drag; flag a frozen page inside an otherwise moving
clip. Never trim automatically. Marketing's temporary measurement lives in
video-maker/videomaker/pauses.py; retain hard duration limits for cards and photos.

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

### §PW712 Validate an authored cut before rendering

In viglet/marketing VM56, `python -m polyweave describe video.cut --json` offers source,
out and root, but no read-only validation result. The illustrated assembly draws all
cards before it discovers a missing spoken highlight anchor; one omitted article in the
WordPress outro wastes that render. The caller must validate narration provenance and
transcript hashes, word anchors, translation coverage, source references, media bounds
and required fonts in video-maker/preflight.py before drawing or encoding.

Offer a read-only cut preflight that returns all independent actionable findings with
source file, field, take and beat, using the same resolution as the production cut.
Probe existing media without rendering or buying anything. A stale transcript or missing
anchor must fail before any rendering subprocess, for both a dry plan and a real build.
Do not invent word alignment or regenerate voice. PW706 covers opening-proof estimates
before purchase; this gap covers a complete already-authored cut before rendering.

VM59 also needs declared repetition budgets before export: overlap between selected
source intervals, total screen time, adjacency and minimum reuse gap, plus optional
editorial category concentration across distinct files. Tie aliases to the same source
bytes, name affected beats, and allow explicit reasoned exceptions for continuous
tutorials or navigation. Warn or refuse according to declared limits, without replacing
footage or inferring activities from filenames. The marketing checker lives in
video-maker/repetition.py and shares the production beat timing.

### §PW713 Review a production interval with motion and audio

In viglet/marketing VM57, `python -m polyweave describe video.cut --json` offers a whole
cut but no selected production interval for motion review. Checking one WordPress
Gutenberg drag, portrait or opening otherwise requires a full export and separate
frame-extraction commands. PW708 provides labelled still sheets, which cannot show a
complete action or judder.

Allow a review interval, take, beat or spoken cue with before/after context, resolved
against the authored production timeline. Reuse production clips, source trims, frame
rate, fit, brand, timed callouts and the same audio mix; do not normalize a short
excerpt independently. Return the exact original interval and shifted cue mapping.
Render only the overlapping visual pieces and preserve subtitle placement. Verify
sampled preview frames and cue times against that interval of a full cut. The marketing
workaround belongs in video-maker/preview.py and uses the existing illustrated
compositor and stage cache, rather than recreating shots for a demonstration.

### §PW714 Reviewed media ranges carried into an authored cut

In viglet/marketing VM58, stock.fetch records downloads and reference.register protects
a source hash, while reference.frames produces previews. None holds an editorial
catalogue of accepted/rejected source ranges, reasons and explicitly confirmed
people/events that can feed a storyboard. WordPress footage was rediscovered despite
prior rejection for blur, unrelated text or a mistaken identity. A filename and public
availability cannot establish identity or reuse rights.

Keep candidates with source metadata, original provenance, media measurements, hash,
preview references and explicit rights status. Record human-authored range decisions,
reviewer/date/reason and identity/event tags. Selection must inherit the recorded
provenance and remain inside an accepted range with reviewed rights; changed media must
invalidate approval. Preserve rejected ranges so another search does not silently
rehabilitate them. Reuse stock.fetch, reference.register, reference.frames and
provenance.credits instead of duplicating acquisition or sampling. Marketing's adapter
will live in video-maker/library.py. PW701 separately owns YouTube ingestion. This
records declared human decisions and never accepts an image or invents a licence on an
agent's judgment.

### §PW715 Report video build stages as they run

Marketing VM63 repeatedly polls a running `videomaker build` and file timestamps because
long card renders, clips, joins and audio stages have no live progress. `polyweave
describe video.cut --json` offers no progress option; the operation inventory offers no
job/progress status operation. The project needs a thin progress adapter until this is
available upstream.

Expose flushed human and structured JSON events for validation, rasterization, source
clips, joins, highlights, mix, mux and verification. Include stage, actionable take or
asset, completed/total planned units, cache hit/miss, elapsed time and last successful
stage on failure. Report active units while a subprocess runs, without process polling.
Never expose credentials, command arguments or large encoder logs. Distinguish known
planned counts from unknown future work; only show an ETA if supported by measured
history. Preserve failure records and completed cache stages for resume. Marketing's
adapter will live in video-maker/videomaker/progress.py.

### §PW716 Review narrated claims against declared evidence

Marketing VM64 has source URLs on storyboard beats but no evidence mapping for spoken
dates, versions, statistics or conclusions. The operation inventory exposes artefact
provenance and visual reviews, not narrated claim records or evidence review. A 2021
Gutenberg demonstration can illustrate a 2018 event without proving its date.

Support declared claims with stable IDs, language/take/word anchors, supporting URL and
excerpt or note, source/event/publication/retrieval dates, and human review records.
Distinguish historical facts, changing statistics, editorial conclusions and
illustrative footage dates. Produce a review view and reuse approved citations in
bounded publishing output, preserving all claim metadata separately. Detect edited
narration/evidence and expired reviews through input fingerprints and explicit review
deadlines. Never infer approval from a URL, automatically rewrite narration, or conflate
footage publication with the depicted event. Marketing's temporary checker and review
view will live in video-maker/videomaker/claims.py, integrated with existing preflight
and description formatting. Media range/rights review remains PW714; bounded credits
remain PW711.

### §PW717 A delivery setting the model ignores is recorded as applied

Where it happened: viglet/marketing, `japode/wordpress2`, on 2026-11-16. The call was
`python -m polyweave voice.lines --script narration/lines.json --keys intro --spend true
--root japode/wordpress2 --json`, with `"model": "eleven_v3"` and `"speed": 1.12` (then
`1.2`) at the top of the lines file.

What came back: `spent: true`, a take, and a provenance whose `details.delivery.speed`
records the value. Nothing said the model ignored it. Three takes of the same line
measured 14.28 s of talking with no speed, 13.30 s at 1.12 and 14.04 s at 1.2:
take-to-take variation only. eleven_v3 does not apply `voice_settings.speed`.

Expected: a delivery setting the model does not apply should be refused before any
spending, or at least come back as a warning in the plan (`ignored: ["speed"]`). It
should not be recorded in the take's provenance as if it shaped the take. The record
also makes every other take look stale for a change that alters nothing, which pushes a
re-purchase of the whole narration.

Workaround: viglet/marketing VM72 stretches the bought take with ffmpeg `atempo` inside
video-maker (`[narration] tempo`), and the `speed` key was dropped from the script.

### §PW718 Wikimedia Commons pictures are fetched by hand

Where it happened: viglet/marketing, the standalone Japode Short about the first
computer bug, on 2026-11-16. It needs three public-domain pictures from Wikimedia
Commons: the 1947 Harvard Mark II logbook page (File:First_Computer_Bug,_1945.jpg, Naval
Surface Warfare Center), Grace Hopper (James S. Davis, US Navy, 1984) and Thomas Edison
(Bachrach, about 1922).

What came back: `stock.fetch` takes only a Pixabay id. `describe` lists no operation
that brings a picture from Commons. The WordPress episode's historical portraits
(Mingus, Strayhorn, Armstrong, Gutenberg) had already been fetched and their
`.prov.json` written by hand.

Expected: one call that, given a Commons file title, downloads the original and records
in its provenance the page, the author, the licence short name and URL, the date and the
hash. These come from the API's `imageinfo` + `extmetadata`, which answers when given a
descriptive User-Agent. It should refuse a file whose licence is missing or non-free, as
`stock.fetch` would refuse an unknown id.

Workaround: the marketing session queried the Commons API with curl and wrote each
`.prov.json` by hand in `japode/primeiro-bug/footage/`.

### §PW719 Voices cannot be searched or compared

Where it happened: viglet/marketing, the standalone Japode Short about the first
computer bug, on 2026-11-16. The owner asked for a voice in the audience's own age (21
to 31) in place of the channel's narrator.

What was missing: `describe` lists `voice.design`, `voice.choose` and `voice.lines`, but
nothing that searches ElevenLabs' shared voice library by language, locale, age, gender
and use. The session called `GET
/v1/shared-voices?language=pt&locale=pt-BR&age=young&gender=...` with curl to shortlist
candidates. It then wrote one lines file per voice in
`japode/primeiro-bug/narration/samples/` to hear the same sentence in each, because a
lines file holds a single voice.

Expected:
- a `voice.find` that answers the library's matches (id, name, accent, age, use, description,
  usage), kept in the project like `stock.find`;
- a way to speak one line in several voices as one sitting to compare, priced before spending.

### §PW720 A current take cannot be bought again

Where it happened: urdido (the video framework extracted from marketing's video-maker),
task UR7. In marketing's `japode/wordpress2` the chapter-1 take bought with eleven_v3 on
2026-11-16 drifted into European Portuguese between 0:28 and 0:35. The words were right,
so the owner wanted the same line spoken again.

The call: `python -m polyweave voice.lines --script lines.json --locale pt-BR --spend
true` (urdido's `prepare` builds the lines file). The take's words, voice, model and
delivery are unchanged, so the plan lists it under `current` and buys nothing. No
parameter says "buy this key again even though it is current".

The workaround (urdido UR7): before the quote, `urdido prepare --retake <take>
--retake-reason "..."` moves the take, its `.prov.json` and its `.words.json` aside as
`<take>.retake-<time>.*` and records the reason in the narration's `retakes.json`. With
the file gone, voice.lines plans and prices the line again. A dry plan or a failed
purchase puts the old take back.

What polyweave should do: a `retake` (or `again`) list of keys on voice.lines (and
sound.speak) that plans those keys as not current, keeps the replaced take beside the
new one, and records the reason in the take's provenance. Then a voice or model that
keeps drifting shows up in the ledger across projects.

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

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

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

### §PW710 A product fixture behind a web visit

Marketing VM44 films WordPress and Viglet Shio on clean instances, but capture.web
exposes only source/out/root and its web declaration names only the URL and actions. No
instance or container operation appears in describe. Video-maker will declare Docker
Compose files, service readiness and visit-to-instance references, expose explicit
up/reset/down/plan commands, and record the container/image inspection beside the
capture. Add a reusable instance fixture that capture.web can resolve before visiting,
with explicit reset, bounded readiness, seed/setup steps, and identity evidence.
Preserve human control over reset and never touch an existing unowned container, volume
or network. The local wrapper is videomaker.instances; the recording remains
capture.web.

The real integration refused web.instance with web.bad-visit: '[web] has instance, which
it does not take'; the remedy allows only allow/out/timeout/url/viewport. The wrapper
must retain the original visit and forward a hash-addressed compatible copy with
instance metadata removed, recording both declaration hashes. This compatibility step
should disappear when capture.web accepts the fixture reference.

### §PW711 Bounded publishing copy from credit records

Marketing VM52 found a 15791-character WordPress description and a 5288-character Scion
description. provenance.credits accepts root/out/check/all and exports JSON for a game's
credits screen; it has no declared summary, chapter times, used-media subset or platform
text budget. video-maker now formats declared publishing copy, shortens YouTube watch
URLs, groups shared licence notices and stock service credits, keeps mandatory
title/author/source/licence/change fields, archives full provenance, and refuses text
that cannot fit without dropping required fields. Scion retains all 33 source credits.
Add a bounded publishing-text export over declared credit records, with protected fields
and explicit grouping policy. Do not infer a licence version, invent missing rights
metadata or silently truncate mandatory credits. The reusable adapter currently lives in
videomaker/publish/description.py.

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
