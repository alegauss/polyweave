# Improvements

## Block A — What a tool call costs the turn

### §PW51 A measurement without the tolerance it was taken against is a number, and the file cannot be read back for it

A record says which mesh, which seed, which sample count and which view transform made
an artefact, and nothing about the numbers the verdict beside it was taken against. Two
records can therefore carry the same measurement and mean different things, because the
alpha floor that decided what counted as the subject sat in a file that has since been
edited. Reading the config back does not recover it: the record is the artefact's, and
the file is the project's as it is now.

`Config.tolerances()` resolves all six together for exactly this reason, and
`Tolerances.as_dict()` exists to be written down. What is missing is the field and the
decision about where it goes.

The decision is whether they belong in the cache key. They should not, on the argument
that they do not change the artefact: a render made at one alpha floor is byte-identical
to the same render at another, because the floor is read after the pixels exist. That
argument has a hole worth checking first — a search that accepts on a predicate measured
at one floor and is re-run at another reuses a hit whose verdict no longer holds, which
is a stale acceptance rather than a stale picture. Whether that is the key's problem or
the spec's is the thing to settle.

Measure how often a project actually changes a tolerance, because a field nobody varies
is a field nobody needs.

### §PW52 How little of a frame a subject may fill is a number nothing has measured, and the nearest one means something else

The line that made flatness a tolerance expected the transparency check beside it to be
`max(alpha) == 0`, with the same equality problem. Measured on 2026-09-22, it is not:
the check is `not mask.any()` over `alpha > round(alpha_floor * 255)`, so it already
asks whether anything clears the floor. The equality was gone before the line was
written.

The gap it pointed at is real all the same, and different. A 64x64 render whose only two
opaque pixels sit in one corner passes both checks today: coverage 0.000488, above the
floor because those pixels are fully opaque, and not flat because the two differ. It is
empty for every purpose and nothing says so.

What is missing is a floor on how much of a frame a subject must fill to be worth
judging, and the reason it was not folded into that fix is that no number for it has
been measured. `[tolerance] subject_coverage` is 0.12 and looks like the answer. It is
not: it means the least of the frame a photograph's subject may fill before the cut is
worth spending on, and a correctly framed render of a thin asset — Cottony's
booster_wand, a rope — is well under 12% by area while being exactly right. Borrowing it
here would refuse real work.

So the number has to come from measuring real renders of the thinnest assets rather than
from picking one. Until then a two-pixel render passes, which is a smaller failure than
refusing a wand.

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW49 Painted shading is a shadow that cannot move, and removing it needs a measured threshold rather than a found one

A generative service returns a mesh whose texture has shading painted into it — a dark
line where a seam was drawn, a smudge where the model thought a shadow belonged. Under
the plugin's lighting those marks are wrong twice over: they are shadows that do not
move when the light does, and they are darker than anything the rig would produce.
Cottony found this on every fetched prop and wrote `scrub()`, with three constants found
by eye: the widest mark to remove, how much darker a texel must be, and the size those
are measured at.

Nothing here can do it. `post` is post-conditions and `material` sets shader inputs, and
neither reaches a texture's pixels. So a project that buys meshes keeps its own pass —
the fork the audit was testing for.

What this has to settle is where the threshold comes from. Cottony's is a fixed number
found by hand, which is the cost the search exists to remove, so the answer is likely a
measurement rather than a constant: a mark is darker than its surroundings by more than
the texture's own local variation, and that variation is readable. Whether it belongs at
fetch time, beside the normalise, or as an operation a declaration asks for, depends on
whether an unfetched texture ever needs it — and on this evidence it does not.

Measure first whether removing the marks changes the accepted render. A repair nobody
can see is not worth a pass over every texel.

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

### §PW50 A fuzzy surface is an intent, and eight shell-texturing constants are the answer to it rather than the way to ask

The geometry vocabulary can carve, bevel and inflate a shape, and a material can be
given shader inputs. Neither can make a surface fuzzy. Cottony's friends are plush toys
and its answer is shell texturing — the same surface drawn twenty times, each copy a
little further out and keeping only the tufts tall enough to reach it, so the silhouette
breaks into tufts rather than single hairs. Eight constants describe it: the shell
count, the depth, the cut sharpness, a finer fibre field multiplied into the first, how
much strand length wanders, how far the body pushes out under the clumps, and how far
the tips lean towards their clump's crown.

Every one was found by eye, and the readings that drove them are in the user's own
words: clumps alone gave hard beads, and fibres grown straight off a smooth ball read as
velvet rather than as sherpa.

The reason this has nowhere to go is that it is a **technique**, not a number. Eight
keys would not help a project wanting fur instead of cotton, and a `[fluff]` table would
be the first thing here that is one project's look compiled in — the non-goal exactly.
What a declaration should carry is the intent: a named surface with a depth and a
coarseness, with the shell construction underneath it.

So this is a vocabulary question before it is an implementation. The test is whether a
second surface, unlike cotton, can be asked for in the same words.

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

### §PW48 Test against what Cottony actually has

Every input the suite has is built in code: a box of stated proportions, a photograph of
a rectangle on a plain ground, a figure whose limbs are where the plan puts its bones.
That is right for the arithmetic — the test states the numbers its assertion depends on,
which a committed PNG never does — so the builders stay.

What it never sees is an artefact anybody made. No mesh from the service, no photograph
of a real object on a real table, no capture from a running game — and those are where
every symptom here was measured.

Cottony has them. `booster_hammer.drawn.png` is the drawing the hammer leans in and
`booster_hammer.glb` is what came back standing upright, which is the case PW20 was
written about. Copies, not a path into another checkout: a test needing a sibling
repository on the same disk is one nobody else runs.

Size is what LFS answers. Drawings are 10–21 KB and stay plain blobs; meshes are 1.7–30
MB and become pointers, by the reasoning Cottony's own `.gitattributes` gives: git keeps
every version whole, and the only fix afterwards rewrites history.

The GDScript in the engine tests belongs in files either way: real code living as Python
string literals full of escaped tabs, where nothing highlights it and nothing lints it.

Which assets earn a place is open. One per failure worth reproducing, not one per asset
Cottony has: the 30 MB mascot buys nothing the 8 MB hammer does not.
