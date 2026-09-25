# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

### §PW36 Cottony adopts it without a fork

Cottony is the first consumer and the test of whether the configuration boundary in
Block A actually holds. Its pipeline uses everything this backlog proposes: a
script-built mesh, a fetched mesh re-dressed in drawn cloth, a cushion inflated from a
drawing, a fourteen-parameter rig, a paid service with a lock file, and four engine
captures. If all of that can move onto the plugin with a configuration file and no fork,
the boundary is real. If any of it needs a change inside the plugin that only Cottony
would ever want, that is the defect, and it is much cheaper to find here than via a
second adopter. The migration is also what keeps this from being a rewrite for its own
sake: each piece moves only once the plugin's version passes the same check the existing
one does, and the pieces that are better left alone stay where they are. What this line
delivers is the adoption plus a written list of everything that had to be configured,
which is the plugin's real interface, discovered rather than designed.

### §PW53 The rig is the thing being replaced, so it cannot be the thing still running

§PW36 moves one asset and stops there, which is the right size for a first port and the
wrong size for a claim. `tools/art/bake_model.py` is 1023 lines, and its `MODELS` table
holds twelve entries carrying up to fourteen rig parameters each — `fill`, `light`,
`turn`, `ambient`, `key`, `form`, `roughness`, `shadow`, `gloss`, `square`, `scrub`,
`roll`, `plate`, `dust` — every one of them found by hand at about two minutes a sample.
That table is the cost this plugin was written to remove.

One asset ported proves a picture can be made. Eleven left behind prove nobody chose the
plugin over the rig, and the rig is what still runs on a build.

The work is a translation rather than a move, which is why it is one line per asset.
§PW36's audit already found the sharp edge: `light` is a whole-rig multiplier and `form`
is the key's share of it, and neither is a parameter the renderer has. An axis with no
knob is refused before a render is spent, but the conversion stays a person's:
`exposure` is in stops, and a wrong one is a different picture rather than an error.

So each model's constants become an acceptance spec, the spec is what `search` aims at,
and the ledger `docs/specs/adoption.md` defines takes the before side for that asset
before it moves. A comparison with one side recorded is refused, and rightly.

Set aside: it needs a person three times over. The trap a hand conversion walks into is
in `docs/specs/adoption.md`.

### §PW56 Twelve runners, twelve ways to start Godot, and no check on what applied

`tools/capture_screens.py` drives four scripts under `tools/capture/`;
`tools/measure_frames.py` drives one. The other seven under `tools/perf/` have none —
started by hand, from a command line written in a docstring. Both drivers open a real
window, because `--headless` draws nothing; both distrust Godot's exit code; both bound
the run by a wall clock; and both fail a run whose line never came. That procedure is
written twice, and a third time in `run_tests.py`.

Block E is that, generalised and then taken further. `offscreen.py` probes which
offscreen route actually works on this machine instead of assuming one; `engine.py` and
`capture.py` run a script and compare the settings that were asked for against the ones
that applied; `units.py` checks a declared `pixels_per_unit` against the engine's own
number, which here is `const CELL := 112` in `scripts/board.gd`.

That comparison is the part Cottony has no equivalent of at all. `docs/specs/engine.md`
is about the settings a picture was taken under, and today a capture that ran at the
wrong resolution, the wrong locale or the wrong renderer prints its line, writes its
file and passes. The site publishes it.

**Replacing Blender, Godot or the generative service** is a non-goal, and this line
stays inside it: Godot still runs the scene. What changes is who starts it, and what is
checked once it has.

Godot 4.7.1 is installed and the probe answers the machine: `window-offscreen` and
`window-minimised` work, `virtual-display` cannot on Windows, and `headless` drew
nothing. The route exists, so what is left is Cottony's tree.

### §PW57 Five floors in five files, and not one of them is a target

`check_vivid.py`, `check_palette.py`, `check_markings.py`, `check_plush.py` and
`check_pieces.py` are about a thousand lines of measurement, each holding its own floor.
The best of them makes the argument this plugin adopted: `check_vivid.py` exists because
"washed out" was asserted, measured, and found true only at the tail — mean saturation
0.31 against the concept art's 0.32, and the 99th percentile 0.68 against 0.88. A look
is a distribution, and the interesting part is usually not its middle.

`measure.py` closed that vocabulary and `accept.py` turns a bar into a file. The
difference is not tidiness and it is not line count. **A threshold inside a gate can
only answer after the render is spent.** The same number in an acceptance spec is what
`search` moves towards, so the bar stops being a verdict and becomes the target, which
is the whole loop this plugin is.

A second cost is being paid quietly. Five floors in five files are five numbers that
move independently, and `check_vivid.py` already records what that costs: for as long as
only one of the two boards was read, the mesh board sat at 0.776 with nothing saying so.

The end state is one spec per asset, the gates reduced to running them, and the
percentile argument surviving as a measurement name rather than as a paragraph in a
script.

### §PW59 Adopted is an opinion until something fails when it is not

Today the number is zero. A search for `polyweave` across `D:\Git\viglet\cottony`
returns nothing, against 8,839 lines under `tools/`. Every line in this block moves that
number and none of them defends it.

That matters because the failure mode is not a port that never happens; it is a port
that comes back. A helper reintroduced under deadline, a floor copied into a sixth check
script, a thirteenth GDScript runner written because twelve were there to copy from —
each is one commit, each looks reasonable in review, and nothing fails.

So this block closes with a gate in Cottony rather than a claim in this repository. It
names the surfaces the plugin owns — the rig, the geometry, the fetch, the engine run,
the measurement, the sheet — and fails when one of them is re-implemented beside a call
that already exists.

**The denominator has to be stated or the number is a slogan.**
`tools/art/make_assets.py` is 2,406 lines of drawn 2D generation and is not in it: this
plugin is geometry, surface and motion in three dimensions, and a flat PNG generator is
Cottony's own work. The palette and the fonts are the same. What counts is what the rest
of this block names, and the gate may report a fraction below one for as long as it says
what is left and why. Two of those are already answered in `docs/specs/adoption.md`: the
fetch ledger replays, and the motion Cottony has is two frames and no clip.

### §PW77 A bar that was measured and then left in a comment

The map's props are the family with the best-recorded target in the project and no way
to act on it. `scenery_mushroom` carries this, verbatim: tuned against the drawn sprite
on its cap and stem medians, 223,118,87 and 215,197,173 against 225,127,83 and
214,198,174. Somebody measured the thing the render had to match, wrote it down, and the
only reader is a person.

That makes them the right second family. The work is not finding a bar — it is moving
one that already exists into something a search can aim at, which is a smaller step than
inventing the bar and the port at once.

Four of the five are built from the outlines make_assets.py draws them with, so they
carry the stars' property of costing nothing to re-render. The fifth, the mushroom, is
fetched, and it is here rather than with the boosters because it shares the other four's
settings exactly: one exposure, one gloss, one shadow, differing only in how much of the
canvas each drawing spans. A port that holds across a built prop and a fetched one at
the same numbers is worth more than one that only holds across four siblings.

What it must not lose is the reason the numbers exist: each prop lands on a sheet beside
drawn siblings, and reading as the odd one out is the failure.

### §PW78 Framing that answers to a number the game already holds

The board tray and the booster tray are the two assets whose framing is not a matter of
taste. `board.gd` addresses a cell at `CELL := 112`, so the render has to put its wells
on that grid or the game draws pieces a few pixels off their homes. The bake answers
with `plate`: a world rectangle given outright, which replaces the fitting that `fill`
and `size` do and sets one unit to one pixel.

That is a different kind of hand-tuning from the stars' exposure, and it is why these
two come after the families where the only loose thing was light. An exposure that is
slightly wrong makes a picture somebody may accept. A plate that is slightly wrong makes
a board that does not line up, and the failure is structural rather than a matter of
looking right.

Both are built rather than fetched — the booster tray is a cushion inflated from the
lobed card drawn beside it, the board tray a grid that could not come from a service. So
the geometry is already a declaration and what has to move is the framing contract.

The thing to keep is that the number comes from the game, not from the render. A port
that lets the picture choose its own rectangle has lost the point.

### §PW79 The simplest rig with the hardest bar

The brand marks are the one family where the rig is nearly nothing and the criterion is
nearly everything. Two blends produce three sprites — the Cottony logo is baked twice,
large for the title and small for the board's corner, because a sprite for each beats
one scaled for both — and the whole of the hand-tuning is `light`, at 1.0 and 1.18.

They are deliberately not first. A family with one constant looks like the easy port,
and it is, right up to the point of saying what a correct render is. A wordmark is type:
it either reads or it does not, and the failure is not a median drifting but a letter
losing its edge. Every other family in this list can be stated as a colour and a
contrast against something drawn; this one cannot, and taking it early would mean
inventing an acceptance vocabulary under the pressure of the first port.

By the time the stars, the props and the trays have moved, three bars exist that were
written to be read rather than admired, and the question here is narrower: what does a
search aim at when the subject is a shape that must stay legible.

The marks also leave markings off — a rope round the silhouette of a word is not a thing
this style has.

### §PW80 What a fetched object arrives wearing

The boosters are the first family whose hand-tuning is not about light at all. The
hammer and the wand came back from the service, and each needed three separate
corrections that no exposure search would have found.

The service painted edges it saw: a dashed dark line round the hammer's head, a dark rim
on the wand's star, both of which rule 2 forbids on candy and neither of which a prompt
saying so prevented. `scrub` takes them back out of the texture before rendering. The
hammer also returned standing upright where the drawing leans it, so it carries a roll
of -22 degrees, and leaning it widens its box, so its fill had to go up to 0.72 to keep
the drawing's size. Each of those three is a consequence of the one before it.

The shuffle ball is here because it is the counter-example: it is built rather than
fetched, after the service returned a ring instead of a ball. Having both in one task is
the point — what a fetched object needs and what a built one does not is the comparison
this family exists to make.

The risk being carried is that a correction found for one object is a correction fitted
to one object. A port worth having states what the correction is for, not the number it
landed on.

### §PW81 The five that are looked at, and go last

The friends and the mascot carry more hand-found numbers than the other seventeen
sprites together, and they are also the ones a player looks at. Both facts point the
same way: last.

Nothing here is only an exposure. The mesh is dressed in cloth drawn in Python and
projected from the camera, because the service's own texture did not read as cotton. The
face is composited on afterwards, because a sculpted face comes back as dents that shade
and never read as eyes. The mascot needs its sculpted face taken back out first at 0.9,
where 1.0 flattens the cheek's own light; it arrives in 34,391 pieces, so a dust
threshold of 0.01 keeps the head and the lower body while dropping the tongue inside its
open mouth. Its face centre was solved rather than chosen: measured at 0.444 of the
height, then moved up by 0.09 so the mesh's cavity becomes the inside of the mouth we
draw.

The lean frames are the same mesh squashed to 0.93 and re-rendered rather than scaled,
so the light stays where the light is while the body moves under it.

Every earlier family in this list is a rehearsal for this one. If the search cannot hold
here, the honest outcome is that these five stay hand-tuned and the rig shrinks around
them rather than disappearing.

### §PW82 The rig has to actually go

This is the task PW53's objection was about. Setting it aside said that one asset moving
leaves bake_model.py standing for the rest, so the rig the plugin exists to remove is
still the thing that runs — and that stays true of two families, or five. It stops being
true only when the file is gone.

So the sequence needs an end that is checkable rather than assumed. After PW76 through
PW81 there should be no `tools/art/bake_model.py`, nothing importing it, and every
sprite under docs/design/art/ produced by the plugin. Until then Cottony has two routes
to the same picture, and the older one keeps working, which is exactly how a replaced
rig survives its replacement.

It is filed separately rather than folded into the last family because the failure it
guards against is not any one port going wrong. It is six ports going right and the file
remaining, with a handful of constants nobody moved and no reason left to look at them.

If a family turns out not to port — the friends and the mascot are the candidates — then
this is where that is recorded honestly: what still runs by hand, and why the rig shrank
instead of disappearing. An outcome worth having, stated, beats the same outcome
unstated.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW163 Buying a picture

The plugin prefers a drawing to a photograph (PW21), and today every drawing comes from
a person, because the agent cannot draw. Ideogram 4.0 generates an image, and its
transparent endpoint delivers a PNG with a real alpha channel — exactly the form
`reference.pick` recognises as a drawing. That makes the image service the cheap first
step in front of the dear one.

**The plugin speaks to the service itself**, which it has never done for meshes: until
now a consumer's own client fetched and the plugin captured. The client is small —
generate, generate transparent, and the poll for the async variants — and it goes
through the same doors a mesh does:

- the payload is validated against the learned `[service.ideogram] schema` before sending
  (PW19), which matters here because 3.0 and 4.0 spell the prompt field differently;
- `purchase.allow` is asked before the call, against that service's ceiling (PW18);
- the picture is captured before anything else happens, because the service's links expire
  and the order in PW17 is the only one that cannot leave a receipt without an asset.

**`bought` gains `image`.** The record carries the model, the speed and the resolution
the response reported, which may differ from the one asked for.

**The service's own refusals are codes, not tracebacks**: a prompt refused as unsafe
(422) and a rate limit (429) each name what to do next, and the client never holds more
calls in flight than the account allows, which by default is ten.

### §PW164 A price that says it was quoted

The ledger's proof of what something cost is two readings of the balance, one either
side of the spend (PW18). Ideogram publishes no balance endpoint, so an image entry
would be either unmeasured or invented, and a ledger that cannot tell those two apart
has stopped being evidence.

**The price is declared, and says it was declared.** `[service.ideogram] prices` maps a
model and speed to a price per output image — the service bills per picture returned, so
a request for four is four prices. The entry carries `credits` from that table and
`measured = false`, and every read that sums spend says how much of its total was quoted
rather than read.

**A quoted price is not trusted forever.** When a person supplies the service's own
usage export, `purchase.reconcile` matches its rows to ledger entries by time and count
and records the difference, the same `surprised` flag a measured entry carries. A table
that has gone stale is found on the first reconcile rather than on the invoice.

**The ceiling counts quoted spend in full.** Under-counting is the direction that lets a
session pass a ceiling a person set, so where the table has no row for a model, the call
is refused rather than priced at zero.

This is a deliberate exception to the fetching contract, which is why it is its own
line: the contract should say it, not a comment in the client.

### §PW165 A picture its record can make again

Ideogram 4.0 rewrites a text prompt before it draws — the response returns "a
potentially modified prompt" — so a record holding only what was sent describes a
picture nobody asked for. Regenerating from it gives a different picture, and refining
it means refining a prompt the service never used.

**The structured prompt is the default.** 4.0 accepts a `json_prompt` — a description, a
background, an ordered list of elements, and a style block of aesthetics, medium,
lighting and palette — in place of free text, and it is not rewritten. The plugin
composes that object from the asset's declaration and the project's style, and the
object is what goes in the record.

**The record holds everything a second call needs**: the prompt sent, the prompt
returned, the seed the response reported, the model, the speed, the resolution, and the
digest of every reference image. Whether a given model *accepts* a seed back is a fact
about the service, so it is learned by the schema probe rather than assumed.

**An approved picture can be turned back into a prompt.** The describe endpoint converts
an image to the same structured form, with element bounding boxes. A picture a person
approved is described once, and that description is committed beside it as a file —
which is what makes the next variation start from the approved picture's own terms
rather than from a paraphrase of it.

### §PW166 A style declared once, and a canon only a person grows

A generator asked for consistency in prose gives consistency by luck. Two pictures of
one character from one prompt differ in palette, line weight and proportion, and a
refinement drifts further from the picture it refines. Consistency has to be an **input
every call carries**, not an adjective in a prompt.

**A project declares its style once**, in `[style]`, and never in the plugin — Cottony
and Spinhole are two games with two looks, and a default that cannot be overridden is a
defect:

- `canon` — a directory of pictures a person approved, each with its described prompt
  (§PW165);
- `palette` — the colours a picture may use, as values, not names;
- `skeleton` — the style block every structured prompt starts from: medium, lighting,
  aesthetics, and what is always excluded;
- `references` — which canon pictures are sent as style references, where the model takes
  them, and one character reference per recurring character.

**The canon grows only by a person's verdict.** A picture joins it through
`verdict.judge`, and the canon's own record names the verdict that admitted it. An agent
that could add its own output to the canon would make its drift the standard, which is
the non-goal about an agent accepting its own look, written as a file permission.

**Style is per asset family, not per project alone**: `[style.icons]` and
`[style.characters]` may differ, and an asset names the family it belongs to, so a
sprite sheet is never measured against the canon of a title screen.

### §PW167 Drift, measured against the canon

The agent's part in consistency is to **refuse drift by number before a person spends
attention on it**, and never to decide that a picture which passes looks right. Today
the only check is a person looking, after the picture was offered.

**Drift, against the canon of the asset's family (§PW166):**

- palette — each subject pixel's ΔE to the nearest declared colour, at the 95th percentile;
- value and saturation — the 5th and 95th percentiles of the subject;
- line weight — stroke width from a distance transform of the edges;
- edge — alpha fringe width and halo colour;
- light — the dominant shading direction;
- silhouette — IoU against a declared outline, where there is one.

**Percentiles, never means**: right on average and wrong in one hand is wrong.

**The bar is measured from the canon itself.** The spread among approved pictures is the
floor below which a difference means nothing, as a twin render sets the noise floor. A
family with one canon picture has no spread, and says so rather than inventing one.

**A refusal says which way** — palette ΔE 14 against a floor of 6, warmer; line weight
twice the canon's — because that is what the next prompt is corrected from. What these
measures cannot see, a face that became a different character, stays the person's
verdict, and the report says it was not checked.

### §PW168 The silhouette settled on the picture

Cottony asked for a wide low cap and got a tall dome, and learned it after thirty
credits (PW16). The shape check now runs before a mesh is accepted, but the drawing the
mesh is made from is still whatever a person supplied, and a drawing is where the
silhouette is decided, for cents rather than credits.

**The chain, each step refusing before the next is paid for:**

1. the geometry declaration gives the outline and the proportions;
2. a structured prompt is composed from it and from the family's style (§PW165, §PW166),
   and a transparent picture is generated;
3. `reference.pick` confirms it is a drawing — real alpha, clear border — and
   `reference.prepare` confirms the subject fills the frame and touches no edge;
4. its outline is compared to the declared one by IoU, against `[tolerance] silhouette_iou`,
   and its style against the canon (§PW167);
5. only a picture that passed all of it is handed to the mesh service.

**A picture that fails is a record, not a re-roll.** Its failure — centroid offset,
which edge is too long, which measure drifted — is written against its prompt, so the
next attempt is informed.

**No taste enters the choice.** Where several pictures pass, the highest IoU goes
forward, a rule and not an opinion. Where a person wants to choose, it is a verdict
sheet. How many pictures an attempt may buy is bounded by the ceiling, never by the
agent deciding one more is worth it.

### §PW169 Reading the letters back

Lettering is the thing this service does best, and it is the reason to use it for a
title, a sign, a label on a crate. It is also the one place a picture can be wrong in a
way no palette or silhouette measure sees: a letter missing, an accent dropped, a word
spelled the way the model preferred. A game in Portuguese loses its accents first.

**The text a picture was asked to carry is declared**, as an element of the structured
prompt (§PW165) — which is already where 4.0 wants it — so there is something to read
back against.

**The letters are read back mechanically**, by an OCR engine found the way Blender and
Godot are found: a binary on the machine, named in `[paths]`, reported by `capabilities`
as present or absent. The comparison is exact after case and whitespace folding, and
never after accent folding, because a dropped accent is precisely the defect.

**An absent engine is a stated gap, not a pass.** Where no OCR engine is installed, a
picture with declared text is reported as unchecked, by name, and a picture that failed
is refused with the word it read and the word it was asked for side by side.

This line is an idea rather than a plan because it adds a dependency no other line here
needs, and it should wait until a real title or sign has actually come back misspelt.

### §PW170 A variation measured against its parent

Refinement is where consistency is lost. A character is approved, asked for holding a
lantern, and comes back with longer legs and a warmer coat — and nothing compares the
new picture to the one it came from, because nothing records that it came from one.

**A variation has a parent.** Remix, edit-with-mask and reframe each take an approved
picture and return a new one; the record carries the parent's digest, the operation, its
strength (`image_weight` for a remix), and the mask where there was one. So a replaced
parent names every variation made from it.

**A variation is measured against its parent, and against the canon.** Against the canon
with the drift measures (§PW167); against the parent with one more, which only a lineage
makes possible: **outside the mask, nothing should have changed.** The unmasked region
is compared pixel for pixel after alignment, and a change there beyond the noise floor
is the remix redrawing what it was not asked to.

**The mask comes from the request, not from a person drawing one.** Where the change is
named by region — "the left hand", "the background" — the region is taken from the
parent's described element boxes (§PW165), so an edit an agent asks for is an edit
bounded where the approved picture already said that element was.

What a variation *should* look like is still the person's verdict; what it must not have
changed is a number.

### §PW171 A picture put on the project's grid on arrival

A picture service returns an image at a size it chose, with a margin it chose, centred
where it chose. An icon, a UI piece or a flat sprite needs the project's pixel size, the
project's padding and an alpha edge that sits cleanly on the game's own background.
Fixing that by hand is the same kind of work as turning a mesh round until it faces
forward, and it gets the same answer: it is mechanical, so it happens on arrival (PW20).

**On ingest, once, recorded as one transform:**

- trim to the alpha's bounding box, then fit to the family's declared cell — `[sprites]` and
  `[units] pixels_per_unit` already say what a cell is;
- pad by the declared margin, anchored where the family says: centre for an icon, the base
  for anything that stands on the ground, the convention a mesh's origin already follows;
- downscale with a filter chosen by the family, never by the picture — a pixel-art family
  quantises to its palette with no smoothing, a painted one resamples;
- check the fringe: a halo of the generator's background colour around the alpha is the
  commonest defect a cut-out has, and it is measured and removed rather than noticed in the
  engine.

**The ingested file is what the engine loads**, and `compose.sheet` takes it like any
other frame. The original stays on file with its digest, so a change to the family's
cell size is one re-ingest and never one more purchase.

## Block O — A person sees and answers

### §PW172 One local page to look at

A verdict is the one step the loop cannot automate, and today it is the slowest. The
person sees a render or a picture only by opening files by hand, so in practice they see
the agent's description of it — which is the agent's judgement arriving where the
person's was asked for. `verdict.sheet` and `sitting` (PW109, PW110) made one picture
per family; nothing puts it in front of anybody.

**`polyweave review` serves one local page**, bound to 127.0.0.1 and nothing else, and
prints its address. It opens in any browser, including the one inside the editor beside
the conversation. No build, no packaging, no account: the page ships with the plugin as
static files, and the server is the standard library's.

**The page is a reader.** Everything it shows is already on disk — `loop.pending`, the
sheets, the provenance records, the ledger — and it keeps no state of its own, so it can
never disagree with the files. Closing it loses nothing; a second one open shows the
same.

**It has one write**: `verdict.judge` with the person's choice and sentence, the call an
agent makes from a reply in chat. There is no second path into the ledger or the spec
for a bug to live on.

That is why this is not the graphical editor the non-goal excludes: it edits nothing,
and the agent loses no door by it — every answer it records is one the agent could have
carried.

### §PW173 An answer the agent can wait on

A person answering on the page (§PW172) has answered; the agent does not know it.
Without a way back, the person switches to the chat to say "done", and the agent reads
the files to find out what was said — a round trip the page existed to remove.

**Every answer is an event on disk.** `verdict.judge` already writes the ledger; the
page's call also appends one line to `[paths] work`/`answers.jsonl` — who answered which
family, with what choice and sentence, at what time. An append-only file is the simplest
thing to wait on, and nothing needs a socket.

**`verdict.answers` is the read**: the answers since a given time, each with the
members, the choice and the sentence, so the agent resumes from what was said without
re-reading the ledger. An answer the agent has acted on is not marked or moved — the
next read simply passes a later time — because a file the agent edits is a file two
sessions can race on.

**The agent can be woken, not polled.** The same file is what a Monitor or a background
wait watches, so a session that offered five families can stop, and continue at the
moment the first answer lands.

**The page shows what the agent did with it.** An answer followed by a new candidate for
the same family shows the two together, so the person sees their sentence acted on
rather than trusting that it was.

### §PW174 A mark says where

"The left hand is too big" says what and not where. The agent then guesses the region,
and an edit bounded by a guess is one that redraws what the person liked.

**A person may mark where.** On the page, a rectangle or a loose outline drawn over the
picture is kept with the sentence it belongs to. It is stored as a mask image beside the
answer, at the picture's own pixel size, with the digest of the picture it was drawn on,
so a mask can never be applied to a different picture than the one it was drawn over.

**The mask is what an edit is bounded by.** A variation (§PW170) takes the region from
the person's mask where one exists, and from the described element boxes only where none
does — a person's mark outranks the agent's reading. The check that nothing outside the
mask changed then runs on the region the person actually drew.

**A mark is also a named predicate.** `judge` already takes `named`, the predicates a
person blamed for a look. A region with a sentence is the same thing with a place
attached, so a look verdict carries both and a later search can aim at the part that
failed .

For a mesh, the mark is drawn on the render, and the answer carries the camera it was
drawn from, so the region can be traced back onto the surface rather than applied to
pixels.

### §PW175 The refused beside the kept

The agent refuses drift before a person looks (§PW167), which is right — and makes the
agent the one filter nobody checks. A picture wrongly refused is never seen, so a bar
set too tight costs good work silently, and the person has no way to find out.

**The page shows the refused beside the kept.** Each family has two lanes: the
candidates offered, and the ones the agent set aside, each with the measure that refused
it, the value, and the floor — palette ΔE 14 against 6, warmer. The refused lane is
collapsed by default and never absent.

**A person may overrule a refusal.** Promoting a refused picture is a verdict like any
other, through `judge`, and it records that the bar was wrong for this one — the
evidence a tolerance is loosened from, where today the only evidence is a person
noticing.

**Every picture carries its numbers.** Beside each candidate: the drift report, the
silhouette IoU where there is one, what it cost, and what is left of that service's
ceiling. A decision is made with the same facts the agent used, never with fewer.

**What was not checked is shown as unchecked.** A measure a family cannot compute — no
spread in a one-picture canon, no OCR engine — appears as a gap by name, so a clean
report is never mistaken for a complete one.

### §PW176 Comparing in one place

Two versions of an asset side by side hide exactly what the drift measures find: a
palette a few ΔE warmer, a line a pixel thicker, a silhouette that grew. Eyes compare a
difference well only when the two are in the same place.

**Pictures, four ways:**

- side by side, at the size the game shows them and at full size;
- a slider across one picture, the old on one side and the new on the other;
- onion skin, one over the other at an opacity the person sets;
- a difference map, computed by `measure.same` against the noise floor, so what lights up is
  what is above noise and not every resampled pixel.

**Meshes, turned.** A glTF is shown as a turntable at the project's own rig angles,
never at a camera of the viewer's choosing — a mesh seen through a different camera is a
mesh seen differently. The reference drawing's silhouette can be laid over the front
view, which is the picture the shape check already scored, now visible.

**The comparison is chosen by what is compared**: a variation against its parent
(§PW170) opens as a slider with the mask outlined, a refused picture against the canon
as a difference map. The person can switch.

The viewer loads its 3D library from the plugin's own static files, never from a
network, so the page works offline like everything else here.

### §PW177 The canon on one board

The canon (§PW166) is a folder of files and a table in the config. What a family is
meant to look like is therefore never seen whole, and a canon that has quietly become
two styles — the early pictures and the late ones — is found only by somebody opening
every file.

**The page has a board per family**: every canon picture, the palette as swatches, the
prompt skeleton as text, and the spread the drift floor is measured from (§PW167), so a
person sees what the canon looks like and how tolerant it made the agent.

**A picture joins the canon by a click, and only by one.** "Add to canon" is a `judge`
with its own choice, recorded with the person's sentence; the canon's record names that
verdict. There is no other route in, so the rule that only a person grows the canon is a
property of the page and not a promise.

**Removing is the same.** A picture taken out of the canon is a verdict too, and the
board shows what its removal did to the floor before the person confirms — a canon
picture that was the outlier widening every tolerance is visible as exactly that.

**Two canons, one page.** A project with several families shows them side by side, so
the icons and the characters of one game can be seen to belong to it, which is the
question Cottony and Spinhole will each ask of their own.
