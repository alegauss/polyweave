# Artefacts somebody actually made

Copies from `D:\Git\viglet\cottony`, taken 2026-09-22. Copies and not a path into another
checkout, because a test needing a sibling repository on the same disk is one nobody else
runs (§PW48).

Every other input this suite has is built in code: a box of stated proportions, a
photograph of a rectangle on a plain ground, a figure whose limbs are where the plan puts
its bones. That is right for the arithmetic — a test states the numbers its assertion
depends on, which a committed PNG never does — so the builders stay. What they never show
is an artefact anybody made, and those are where every symptom in this backlog was
measured.

**One per failure worth reproducing, not one per asset Cottony has.** The 30 MB mascot
buys nothing the 8 MB hammer does not, so it is not here.

| File | Size | The failure it reproduces |
|---|---:|---|
| `booster_hammer.drawn.png` | 11 KB | §PW20: the drawing the hammer leans in |
| `booster_hammer.glb` | 8.0 MB | §PW20: what came back from the service standing upright |
| `friend_plush.glb` | 1.7 MB | §PW26: a real plush body to fit a skeleton to, and the cheapest mesh here |
| `meshy.lock.json` | 5 KB | §PW55: five purchases, 130 credits, and the hashes nothing ever compared |
| `friend_cloud.png` | 59 KB | §PW58: the standing frame of the only motion the game has |
| `friend_cloud_lean.png` | 57 KB | §PW58: the same mesh re-rendered at 93% of its height |

The settle pair is here because it is **the whole of Cottony's motion**, and because the
two frames carry a number rather than only a picture: the leaning silhouette is 186 px tall
against the standing one's 200, which recovers the `squash = 0.93` its constants declare
from the pixels that shipped. They also share a bottom row to the pixel, which is what makes
a crossfade read as a toy settling rather than as two toys. A built pair would have both
properties by construction and would prove neither.

`meshy.lock.json` is the whole file and not a trimmed one, because what it is here to
reproduce is a real ledger's **variance**: four purchases from a drawing and one from
words, one bought untextured so its texture prompt is empty and its reference is the whole
ask. A mapping written against a tidy sample would meet all three on the day it ran.

Two of the five meshes it names are in this directory and three are not. That is not a gap
to fill — an 8 MB mesh per entry buys nothing the two already here do not, and the replay
is asserted on both answers: the ones present adopt, the ones absent come back `missing`,
which is the right statement about this tree rather than a claim about Cottony's.

**No capture from a running game.** One was considered and left out: §PW25 is about the
settings a picture was taken under and not about its pixels, so a screenshot proves
nothing a declared environment does not already state.

## Why two of these are pointers and one is not

`*.glb` is routed to Git LFS by `.gitattributes` at the root; `*.png` deliberately is not.
Git keeps every version of a file whole, so an 8 MB mesh replaced three times is 24 MB in
every clone from then on and the only fix afterwards rewrites history. A drawing is 11 KB
and never rewritten, and reading one out of a pointer is a step nobody should have to take
to run the tests.

A clone needs `git lfs install` once per machine before the meshes arrive as meshes. The
tests that use them skip rather than fail where they have not, because a pointer file is a
thing that happened to the checkout and not a thing that is wrong with the plugin.
