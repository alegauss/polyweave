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

**`min`, `max` and `target` are the only comparisons.** A predicate states a bound, not an
expression. Anything needing more than a bound is a measure that does not exist yet, and the
honest response is to add the measure rather than to widen this grammar.

**Bounds produce a margin, not only a verdict.** Each predicate yields pass/fail *and* a
value in `[0, 1]` for how comfortably it passed, normalised against the bound. A pure boolean
gives a search a cliff and nothing to climb; the margin is what makes PW13's parameter search
converge on something rather than wander. The overall score is the weighted mean of the
margins, with `weight` defaulting to 1.

**`[search.<param>]` is the whole permission.** A parameter not named there is not searched,
whatever the optimiser would like. This is what stops a search reaching a value that is wrong
for reasons the spec does not capture — it can tune the exposure and it cannot decide the
asset should be twice as large. Ranges come from the spec; where a project wants defaults for
a parameter it always searches, they live in `polyweave.toml`.

## What this file deliberately cannot say

Anything no measure can compute. "Reads as cloth rather than paper" is a real criterion and
not a predicate, and pretending otherwise by inventing a proxy for it is how a spec ends up
satisfied by a render a person rejects.

That case is expected, not designed away. It is exactly what PW15's contact sheet is for: the
search returns its best handful side by side, a person sees that the winner is not the one
they would have chosen, and now knows the **spec** is incomplete rather than the renderer.
The spec is the thing being debugged, and the search is the fastest way to find out it is
wrong.
