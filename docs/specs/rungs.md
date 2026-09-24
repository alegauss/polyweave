# The preview ladder

Binds **PW7**, and is the vocabulary [acceptance-spec.md](acceptance-spec.md) and
[measurements.md](measurements.md) already name without defining.

A material is read on a sphere, and a sphere renders in three seconds where a character
takes two minutes. That ratio is the whole argument: judging a surface on the final mesh
pays forty times over for an answer the cheap shape already gives, and the only reason it
keeps happening is that nothing makes the cheap path the default.

## Three rungs, and what each one is

| Rung | What stands in front of the rig |
|---|---|
| `sphere` | the material on a primitive, at the preview size and the sphere sample count |
| `preview` | the real mesh decimated, at the preview size and the preview sample count |
| `final` | the real mesh whole, at the final size and the final sample count |

**The meaning is the plugin's; the choice is the project's.** `[render] rungs` says which
are enabled and `[render] preview_size`, `final_size` and `samples` say how big each is. A
name outside these three is refused (`render.unknown-rung`) rather than treated as a fourth
rung nothing knows how to render.

## Two constraints, and they are the whole of it

**The rungs share the rig exactly.** The camera, the three lights and the film are computed
from one set of parameters, and a rung changes only the subject, the resolution and the
sample count. A cheap answer describing a different scene is worse than no answer, so this
is not a convention — the rig is one function and the rungs call it.

**The answer says which rung it came from.** In the result and in the `rung` field of the
record beside the picture, so a verdict taken at the sphere is never mistaken for one taken
at the top.

## Which rung answers which question

A caller names the measures it needs and gets the lowest rung that carries all of them.
A caller that names a rung gets that one.

| Measures | Lowest rung |
|---|---|
| `saturation_*`, `luma_*`, `hue_spread`, `region_colour`, `delta_e` | `sphere` |
| `silhouette_*`, `alpha_coverage` | `preview` |
| `distance`, `changed_fraction`, `luma_bands` | `final` |

A surface reads on a primitive. A silhouette is the shape itself and needs the real mesh,
but not the samples. A comparison between two renders, or a count of what survives a
downscale, is about the render and needs all of it.

An acceptance spec's own `rung` is a **floor**, not a choice: it raises the rung a verdict on
that asset may be taken at, and never lowers one the measures require.

A measure outside [measurements.md](measurements.md) is refused as `spec.unknown-measure`.
A question whose rung the project disabled is answered at the cheapest **higher** rung it
enables. That rung carries everything below it, and `why` names the rung that was skipped
(§PW117). It is never answered from a lower rung, and never quietly. Where no enabled rung
at or above it exists, it is refused as `render.rung-disabled`.

## Planning costs nothing

`plan` returns the rung, why it was chosen, the size, the sample count and the seed without
rendering anything. It is the read to make before spending: the cost of an answer is
knowable before the answer is.

## Colour

The renderer's view transform is set to the one that puts back what was put in, because
every predicate in an acceptance spec compares a measured colour against an authored one and
a filmic transform makes those two different numbers. An installation whose colour
configuration does not offer it keeps what it had, so **the transform actually in force is
recorded** beside the render rather than assumed — a render that moved because its colour
pipeline moved is otherwise indistinguishable from one whose scene moved.
