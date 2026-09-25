# The acceptance spec

`<asset>.accept.toml` states what makes a picture of the asset correct.

```toml
asset    = "star_dim"
artefact = "sprites/star_dim.png"      # what accept.verify holds to this bar

[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"                   # measure.available lists the vocabulary
region  = "frame"
max     = { value = 0.37, origin = "person", date = "2026-09-24" }

[search.exposure]                      # the only parameters a search may turn
min = -1.0
max = 1.0
```

- `min` and `max` are the only comparisons. A bound may be a bare number or a table
  saying where it came from: `measured` (read off an artefact), `margin` (put by hand
  over a measured value) or `person` (a look a person accepted).
- A miss on a `margin` bound means the number may be wrong, not the look.
  `calibrate.run` sizes a bound from the render's own noise instead of by eye.
- A miss on a `person` bound means the look moved. Show a person; do not move the bound.
- `screen = { capture = "...", region = "..." }` checks the same bar where the engine
  drew the asset.
