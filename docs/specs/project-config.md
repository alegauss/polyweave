# The project config

Binds **PW5**, and is read by every other spec here.

`polyweave.toml` at the project root. Everything the plugin would otherwise have to know
about a particular repository lives in this one file, and the plugin ships a default for all
of it. **A default that cannot be overridden is a defect.**

## Resolution order

Explicit call argument, then `polyweave.toml`, then the plugin default — evaluated **on every
call**, never cached at startup, so correcting this file does not need a session restart. The
file is read on each resolution rather than held; it is a few hundred bytes of TOML, and the
read is cheaper than the round trip a stale value costs.

**An unknown table or key is refused, never ignored**, with the near match named. A setting
that is silently dropped is one the caller believes is in effect and is not, which is the
same defect as a dropped argument (§3 of [tool-surface.md](tool-surface.md)). A value of the
wrong type is refused the same way.

**A table keyed by names the project chooses replaces the default rather than merging with
it.** `[render] samples` is keyed by `rungs`, so a project that renames its rungs would
otherwise inherit sample counts for rungs it does not have.

## The file

```toml
[project]
name = "cottony"
root = "."                      # everything below is relative to this

[paths]
blender  = "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
godot    = "${GODOT}"           # an env var reference, resolved per call
tesseract = "tesseract"         # reads lettering back off a picture; optional
meshes     = "tools/art/3d"
references = "docs/design/references"   # prepared references, committed with the tree
renders    = "docs/design/art"
specs      = "docs/design/accept"
work       = ".polyweave"
purchases  = "polyweave.purchases.json"
loop       = "polyweave.loop.json"      # what one asset cost, made each way

[render]
rungs        = ["sphere", "preview", "final"]
preview_size = 256
final_size   = 1024
samples      = { sphere = 32, preview = 64, final = 512 }
seed         = 20260922
max_parallel = 4

[tolerance]
alpha_floor        = 0.02      # what counts as a subject pixel
# below this, two renders are the same picture — keyed by rung, because the floor at
# thirty-two samples is not the floor at five hundred
render_noise       = { sphere = 0.025, preview = 0.020, final = 0.013 }
silhouette_iou     = 0.97
delta_e            = 2.0
background_delta_e = 12.0      # how far from the frame's edge colour is still ground
subject_coverage   = 0.12      # the least of the frame a photograph's subject may fill
subject_extent     = 0.05      # how far a rendered subject must reach across it

[cache]
max_bytes = 8_000_000_000

[provenance]
# what a person made, in a directory that otherwise holds produced work: matched against
# the path and against the bare name, so `*.png` excuses an extension everywhere
handmade = ["docs/design/art/brand/*"]

[engine]
fixed_fps = 60
frames    = 6000               # the frame budget a scene script is bounded by
timeout   = 180                # and the wall clock, for a run that never reaches a frame

[service]
base    = "https://api.meshy.ai"
key_env = "MESHY_API_KEY"      # the NAME of the variable, never the value
schema  = "polyweave.service.toml"
prices  = {}                   # a quoted price per output, for a service with no balance

[budget]
credits = 60
expires = "2026-12-31"

[sprites]
fps     = 12                   # the 2D half of a clip has its own rate
frames  = 0                    # or a count to hit, where zero means use the rate
trim    = true                 # one rectangle for the whole clip, never one per frame
columns = 0                    # frames across the sheet; zero lays them out square

[rig]
plan       = "plush"           # the body plan a fetched mesh is fitted with
influences = 4                 # one snaps every vertex to one bone, and tears
falloff    = 4.0               # both ends tear; four is the trough
pull       = 0.6               # how far a joint moves off the plan onto the mesh
tear_ratio = 2.0

[units]
pixels_per_unit = 0.0          # the weaker half; `source` is the stronger
source    = "scripts/board.gd:CELL"      # read the engine's scale where it keeps it
tolerance = 0.001

[capture]
declared   = ["locale", "resolution", "theme"]  # add your own; `theme` is this project's
locale     = "pt_BR"
resolution = [1920, 1080]
theme      = "dark"
reproducible = true            # a capture that stops reproducing is refused

[geometry]
outlines = "tools/art/outlines.py"   # where named shape generators come from

[style]
canon    = "docs/design/canon"     # pictures a person approved; only a verdict adds one
palette  = ["#f2c14e", "#3a2e39"]  # as values, never names
skeleton = { medium = "flat vector", lighting = "soft" }   # every structured prompt's start
cell     = [64, 64]                # the grid a picture is put on when it arrives
margin   = 2
anchor   = "centre"                # or "base", for what stands on the ground
filter   = "smooth"                # or "pixel": never smoothed, quantised to the palette

[words]
table    = "i18n/strings.csv"      # Godot's translation CSV, one column per locale
speaker  = "_speaker"              # the column naming who speaks, as a world entity id
ordinary = ["START", "OK"]         # capitalised words that are not names
canon    = "docs/design/lines.json"  # a person's verdicts on lines; only a verdict adds

[voxels]
budget        = 4000           # the most cells a model may have; zero is no ceiling
thread        = 3              # the longest run one cell thick before it is reported
extent        = []             # [x, y, z] a model should span; a document's own wins
near_symmetry = 0.9            # this symmetric in x and short of whole is reported
```

## A tolerance has one home

`[tolerance]` is the only table whose values also appear as arguments all through the code,
and that is where a second home for a number grows. It had one: `alpha_floor` was 0.02 here
and 0.0 in the signature of every function that used it, so an operation that resolved the
setting measured the subject the project asked for and one that forgot measured the whole
frame, background included, with nothing reporting that a choice had been made.

**A library function takes the number and never defaults it.** The functions that do the
measuring are pure — they read no files, which is what lets them run inside Blender — so a
default in one of them is a value nobody chose. They require it instead, and a call that
states none is refused (`post.tolerance-unstated`) rather than answered.

**An operation resolves, once.** Anything holding a `root` reads `Config.tolerances()` and
passes the numbers down: `measure`, `accept.check`, `normalise.ingest`, `render.bake`,
`outline.image`. The resolution order is the usual one — the explicit argument, then this
file, then the plugin default — so stating a floor for one call still works and is the only
way a second value ever enters.

All six resolve together, as one object, for two reasons: an operation cannot pick up a
stale sibling of the number it wanted, and a record written beside an artefact can carry the
values that were actually in force rather than whatever this file holds when it is read back.

**`render_noise` is keyed by rung**, like `[render] samples` and for the same reason: the
noise floor is not one number. Two seeds of one unchanged sphere measured 0.0234 apart at the
sphere rung, 0.0195 at preview and 0.0122 at final, against the single 0.004 this used to
hold — so every comparison at every rung read as a change (§PW44). `Config.tolerances(rung)`
resolves it to the one number the comparing code wants; naming no rung takes the strictest,
which is the safe way to be wrong **for comparing two renders**, since too tight costs a look
and too loose is a wrong answer.

**An operation that knows its rung names it, and the flatness check is why** (§PW62).
`render_noise` is also the bar below which one picture counts as flat, and there the strictest
number is the most permissive answer: a lower floor refuses less. `bake` resolved its
tolerances without naming the rung it had just chosen, so every render was judged at final's
0.013 — the sphere rung at four samples included, which has twice that much sampler noise in
it and is the rung §PW42's own evidence came from. One bar read two ways is the trap; the
door out is that the caller knows which rung it is on and says so.

**And a measured floor beats all of them.** Those defaults are what one machine measured,
which is still a guess about another. `measure.same` takes a `twin` — a second render of the
subject's own unchanged scene at another seed — and measures the floor from it, which costs
one render and is right at whatever sample count on whatever machine. The answer says which
of the three floors it used, because a verdict rests on its floor and one nobody can see is
a number nobody can argue with.

## Rules that are not defaults

**A secret is named, never stored.** `key_env` holds the name of an environment variable. A
config file carrying an API key is a config file that gets committed.

**Only a binary path may be absolute.** Everything else resolves under `[project] root`,
because a path pointing outside the tree is state a colleague cannot reproduce.

**Nothing is written outside the tree.** `[paths] work` is the only writable location the
plugin chooses for itself, and it belongs in `.gitignore`.

**`[budget]` is a person's decision, written down.** The plugin spends against it without
asking and refuses the call that would exceed it (§PW18). An expired or absent budget means
no spend at all, not an unlimited one — the absence of a ceiling is never read as permission.
**Credits without an expiry are not spendable either**, for the same reason: a ceiling with
no date is one nobody revisits, and an unbounded-in-time budget is not a decision anybody
made. Both halves are stated or nothing is spent.

## More than one paid service

A bare `[service]` and `[budget]` describe one service, which every call names as `default`.
A project buying from two writes each as a named table instead (§PW162):

```toml
[service.meshy]
base    = "https://api.meshy.ai"
key_env = "MESHY_API_KEY"
schema  = "polyweave.service.toml"     # a named service's default is polyweave.service.<name>.toml

[service.ideogram]
base    = "https://api.ideogram.ai"
key_env = "IDEOGRAM_API_KEY"
prices  = { "4.0" = 0.06, "4.0:TURBO" = 0.03 }   # per picture, in the ceiling's unit

[budget.meshy]
amount  = 60
unit    = "credits"
expires = "2026-12-31"

[budget.ideogram]
amount  = 20.0
unit    = "USD"
expires = "2026-12-31"
```

**Ceilings never pool.** Credits and dollars are not one number, so a spend is judged only
against its own service's ceiling, in that ceiling's unit. A named service with no
`[budget.<name>]` may spend nothing, like a project with no `[budget]`.

**A call names its service wherever there is more than one.** `purchase.allow`,
`remaining`, `spent`, `schema.read` and `schema.validate` take `service`. Naming none is
refused with `fetch.service-unnamed` when several are declared, and a name nothing declares
with `fetch.unknown-service`. Guessing which balance to draw on is the one mistake a ceiling
exists to prevent.

**Declaring one two ways is refused** (`config.services-mixed`): bare `[service]` keys beside
named tables, a bare `[budget]` beside named services, or a `[budget.<name>]` for no declared
service. A bare `[budget]` is always in credits, so a single service that bills in anything
else is declared as a named one.

**The ledger entry names its service.** An entry from before it did is charged to the only
service a project declares. Once there are several, `spent` refuses such an entry with
`fetch.ledger-unattributed` rather than charging it to a ceiling it may not have drawn on, and
`held` names it under `unattributed`. `held` reports `against_ceiling` as one number for one
service and per service for several. `capabilities` reports each key under `services`, by the
variable's name and never its value, with each ceiling under `budgets`. The single-service
`service` and `budget` fields are null once there are several.

## A style declared once

What a project's pictures look like is declared in `[style]`, and never in the plugin: two
games have two looks (§PW166). A bare `[style]` is one family, `default`; a project with
several writes `[style.<family>]` tables, and a call names its family the way it names a
service. It is refused when several are declared and none is named (`style.family-unnamed`),
so a sprite sheet is never held to a title screen's canon.

- `canon`: a directory under the project holding pictures a person approved, each with its
  described prompt beside it where there is one, and `canon.json` saying which verdict
  admitted each;
- `palette`: the colours a picture may use, as `#rrggbb` values, refused as names;
- `skeleton`: the style block every structured prompt starts from, as the service spells it.

**Every picture carries it.** Where a project declares a style, `picture.buy` composes the
structured prompt over the family's skeleton. The skeleton's keys win over the prompt's, and
the family's palette is the palette. A text prompt is refused (`style.needs-structure`),
because it has nowhere to carry either. `style.read` returns a family's style and its canon.

**The canon grows only by a person's verdict.** A `verdict.judge` member carrying `canon`, the
family's name, joins that family's canon when the verdict accepts the look. The picture and
its `<name>.prompt.json` are copied in, and the verdict's choice, sentence and date are
written to `canon.json`. Admission is not an operation, so no other call can add to a canon.
An agent that could admit its own output would make its drift the standard.

**Drift is refused by number before a person looks** (§PW167). `style.drift` measures a
picture and every canon picture of its family, always at a percentile of the subject, never
a mean: the palette distance (each pixel's ΔE to the nearest declared colour, at the 95th),
value and saturation (5th and 95th), line weight (stroke width from repeated erosion of the
ink, the subject's darker half where its tones span at least 20 L*), the edge (fringe width
and halo ΔE) and the direction light falls from. **The floor is the canon's own spread**:
how far its approved pictures sit from their median. A family with fewer than two canon
pictures has no spread, so its report is `judged: false` and says so, rather than inventing a
floor. A refusal says which way each measure went (warmer, thicker lines, light turned 40
degrees), because the next prompt is corrected from that. `not_checked` names what a number
cannot see, such as whether it is still the same character, and that stays the person's.

**`[capture] declared` is the list that matters.** Every name in it is an environment setting
a capture must state explicitly, and a capture leaving one to chance is refused. §PW25 is why:
the same script on two machines produced two different images because the game read its
language from the machine and nothing said which language the picture was in.

**`[capture]` is the one table a project may add its own keys to**, because the settings a
picture depends on are per project and a project that cannot name its own is back to
leaving them to the machine. A name in `declared` takes its value from a key of the same
name here, or from the call. Everywhere else, an unknown key is still a typo and is
refused.

## Adding a key

A new key here is the cheap answer to "Cottony needs X and no other project would". The
expensive answer is a change inside the plugin, and PW36 is the line that measures how often
the cheap one was enough. The list of keys that had to be added during that adoption is the
plugin's real interface, discovered rather than designed.
