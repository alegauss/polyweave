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

[budget]
credits = 60
expires = "2026-12-31"

[sprites]
fps     = 12                   # the 2D half of a clip has its own rate
frames  = 0                    # or a count to hit, where zero means use the rate
trim    = true                 # one rectangle for the whole clip, never one per frame

[rig]
plan       = "plush"           # the body plan a fetched mesh is fitted with
influences = 4                 # one snaps every vertex to one bone, and tears
falloff    = 4.0               # both ends tear; four is the trough
tear_ratio = 2.0

[units]
source    = "scripts/board.gd:CELL"      # read the engine's scale where it keeps it
tolerance = 0.001

[capture]
declared   = ["locale", "resolution", "theme"]  # add your own; `theme` is this project's
locale     = "pt_BR"
resolution = [1920, 1080]
theme      = "dark"

[geometry]
outlines = "tools/art/outlines.py"   # where named shape generators come from
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
which is the safe way to be wrong, since too tight costs a look and too loose is a wrong
answer.

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
