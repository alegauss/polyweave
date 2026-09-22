# The acceptance spec

Binds **PW12, PW13, PW15**. One file per asset, stating what makes a render of it correct.

Today that knowledge lives in commit messages and in somebody's memory, so no later change
can be checked against it and no search can aim at it. This file is what turns a judgement
into a gate.

`<asset>.accept.toml`, beside the asset or under a directory the project config names.

## Shape

```toml
asset = "mascot"
rung  = "final"          # the lowest preview rung a verdict may be taken at

[[predicate]]
id      = "face-reads-cream"
measure = "delta_e"
region  = [120, 80, 180, 140]
target  = "#E8D5C4"
max     = 2.0

[[predicate]]
id      = "silhouette-holds"
measure = "silhouette_iou"
against = "docs/design/art/ui/mascot.png"
min     = 0.97

[[predicate]]
id     = "has-a-saturated-tail"
measure = "saturation_p99"
region  = "subject"
min     = 0.85
weight  = 0.5

[search.light]
min = 0.5
max = 4.0

[search.form]
min  = 1.0
max  = 4.0
step = 0.1
```

## Rules

**`measure` is a name from [measurements.md](measurements.md).** An unknown name is refused
(`spec.unknown-measure`). The vocabulary is closed on purpose: a spec that accepts any string
is a spec that silently checks nothing, which is §PW19's lesson applied one layer up.

**Every predicate has an `id`.** The search reports a score per predicate and the trace
(§PW15) addresses them by name, so an anonymous predicate cannot be discussed.

**`min` and `max` are the only comparisons.** A predicate states a bound, not an expression.
Anything needing more than a bound is a measure that does not exist yet, and the honest
response is to add the measure rather than to widen this grammar. A predicate with neither
bound is refused: nothing could fail it.

**`target`, `against`, `display` and `delta` are arguments to the measure**, not
comparisons — the colour `delta_e` is measured to, the reference a silhouette is compared
with, the size `luma_bands` counts at. Every other key is refused where it is written, so a
misspelled field is never a claim that reads as checked while it is not.

**A measure whose answer is not a number cannot be bounded.** `region_colour` is a colour and
`saturation` is a set; a bound on either is refused and told to name a statistic instead.

**Bounds produce a margin, not only a verdict.** Each predicate yields pass/fail *and* a
value in `[0, 1]` for how comfortably it passed, normalised against the bound. A pure boolean
gives a search a cliff and nothing to climb; the margin is what makes PW13's parameter search
converge on something rather than wander. The overall score is the weighted mean of the
margins, with `weight` defaulting to 1.

The margin is **continuous on both sides of the bound**, so a failing predicate still reports
how close it came: against a `min` it is `value / min` below the bound and 1 at or above it,
and against a `max` it is `max / value` above the bound and 1 at or below it. A predicate
carrying both takes the worse of the two.

**`rung` is a floor.** It raises the rung a verdict on this asset may be taken at and never
lowers one the predicates themselves require, and a verdict offered from lower down is
refused (`spec.rung-too-low`) rather than quietly accepted.

**`[search.<param>]` is the whole permission.** A parameter not named there is not searched,
whatever the optimiser would like. This is what stops a search reaching a value that is wrong
for reasons the spec does not capture — it can tune the exposure and it cannot decide the
asset should be twice as large. Ranges come from the spec; where a project wants defaults for
a parameter it always searches, they live in `polyweave.toml`. A spec with predicates and no
ranges is not searchable, and a search over it is refused rather than run over nothing.

## How the search spends

**The budget is a number of renders, not a wall-clock.** It is the thing being managed, so it
has to be legible and it has to be obeyed exactly: the search evaluates no sample twice and
stops the moment it is spent.

A **coarse grid, then the window closes around the best** — the space is small and mostly
continuous, so this converges without anything cleverer. The grid is as fine as the remaining
budget affords and never coarser than the ends of the range. Each pass halves the window
rather than measuring a neighbourhood from the best value, because a best value sitting dead
centre of its range is the common case and its neighbourhood would be the range it started
as.

**A search that has its answer stops paying.** Once the spec passes with nothing left to
gain, the renders after it buy nothing, and the answer says which of those things ended it.

The winner is reported with its score **against every individual predicate**, so a spec that
was satisfied by an ugly render is visible as exactly that rather than as a success, along
with the whole trace of what was tried.

## The trace

A search that returns only its winner is one nobody can overrule, so it writes down what it
rejected: `<name>.json` holding every sample with its score against every predicate, and
`<name>.png` laying the best handful side by side, best first.

The sheet is what closes the loop. A person looks at it, sees that the top-scoring render is
not the one they would have chosen, and now knows **the spec is wrong rather than the
renderer**. The spec is the thing being debugged, and the search is the fastest way yet found
to discover that it is incomplete.

The sheet is assembled **from the cache**, which already holds every sample's picture under
its key, so no sample has to be rendered twice or kept anywhere else. Where the cache holds
none of them there is nothing to lay out, and the trace says so rather than writing a sheet
of the last render repeated.

The seed and the search's own configuration — the budget, the ranges, the rung, why it
stopped — sit beside the samples, because a result nobody can reproduce is one nobody can
check.

## What this file deliberately cannot say

Anything no measure can compute. "Reads as cloth rather than paper" is a real criterion and
not a predicate, and pretending otherwise by inventing a proxy for it is how a spec ends up
satisfied by a render a person rejects.

That case is expected, not designed away. It is exactly what PW15's contact sheet is for: the
search returns its best handful side by side, a person sees that the winner is not the one
they would have chosen, and now knows the **spec** is incomplete rather than the renderer.
The spec is the thing being debugged, and the search is the fastest way to find out it is
wrong.
