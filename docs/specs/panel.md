# A menu panel from a declaration

Binds **PW316**. A game's UI kit is panels, frames and buttons, each in a few states. When
a project draws them in its own shader, their look is numbers chosen in code and held by
nothing but a verdict on a screenshot. A `*.panel.toml` declares the parts of a frame
instead, and `panel.build` draws them.

## The file

```toml
[panel.holo]
size = [96, 64]                 # the texture, in pixels
margin = 16                     # the nine-patch margin, or [left, top, right, bottom]
fill = "#0a1a2acc"              # #rrggbb, or #rrggbbaa with its alpha
cut = 4                         # each corner cut off at 45 degrees, in pixels
# radius = 4                    # or each corner rounded, in pixels; never both
edge = { width = 2, colour = "#3fe0ff" }
# piping = { width = 4, colour = "#ffffff", raise = 0.3 }   # a raised rim, see below
brackets = { length = 10, width = 3, colour = "#ff4fd8" }
scan = { pitch = 3, colour = "#3fe0ff26" }

[panel.holo.states.focus]
edge = { colour = "#ffffff" }

[panel.holo.states.disabled]
fill = "#10101080"
```

A panel is drawn in its `normal` state, and once per state under `states`: `hover`,
`focus`, `pressed` and `disabled`, the names Godot's controls use. A state replaces only
what it names, key by key within a part, so a focused edge keeps its width and changes
its colour.

**A corner has to fit inside the margin.** A nine-patch stretches everything between the
margins, so a cut, a radius or a bracket that reaches past the smallest margin would be
bent the first time the panel is drawn larger than its texture. That is refused rather
than drawn, naming how far the corner reaches. A corner is cut or rounded, and a panel
declaring both is refused; brackets start where either ends. On the shader route a
radius is clamped to half the Control's smaller side, so a Control no taller than twice
the radius is drawn as a pill.

`radius = "pill"` rounds each end whole, at half the smaller side. A pill's ends survive
a nine-patch only along its length, so it is built with `stretch: "width"` (or
`"height"`, for a tall one), its corner held against that axis's margins alone; on the
shader route its radius is past any size, so it is a pill whatever the Control is.

A panel that is no box at all takes an `outline` from the geometry vocabulary
(`docs/specs/geometry.md`): a generator (`{ shape = "lobed", lobes = 6, radius = 10,
depth = 2 }`, `star`, `circle`, `rounded_square`), `points`, or an `image` to trace, with
`offset` and `radial` as there. The outline is stretched over the panel's box. It cannot
be a nine-patch, so it is drawn at its declared size with no stylebox and says
`stretch: "none"`; on the shader route it is a distance field over the Control's own
size, up to 128 points. Cut, radius and outline are one choice each, brackets sit on a
box's corners and are refused beside an outline, and an outline the geometry refuses is
refused here with its reason.

A `material` lights the fill as a body instead of one flat colour: the felt or candy a
soft style is made of. Every number defaults to 0, which is the flat fill, so a material
names no finish of its own and a project's felt is its own declaration:

```toml
material = { lift = 0.18, shade = 0.34, core = 0.3, grain = 0.6, grain_size = 2, seed = 3 }
```

`light` is where the light falls, `[x, y]` in shares of the panel's box (default
`[0.36, 0.30]`, upper left). From the top down the body runs from the fill lightened by
`lift` to the fill darkened by `shade`, channel by channel so the foot keeps its hue and
never goes grey. `core` glows a spot at the light, and `gloss` lays a soft white
highlight there. `vivid` turns what is lit from paler (0, felt) to more saturated (1,
candy). `grain` is a fibre grain of `grain_size` pixels drawn from `seed`, and `weave` a
cross-hatch of `weave_pitch` pixels. Each is 0 to 1 but the two sizes, which are pixels
from 1. The build and the shader do the same sum, the grain from the same integer hash,
so the engine draws the felt the built picture shows; on a nine-patch the grain in the
middle stretches with it, and on the shader it holds its size. A piping is lit by its
own `raise`, not by the material.

A `piping` is the raised rim stuffed fabric is finished with: a band `width` pixels in
from the outline, in its own `colour`, shaded across its width like a tube. `raise`, from
0 (flat) to 1, is how far its crown is lit towards white and its flanks darkened in their
own hue, never mixed towards grey; it defaults to 0.3. It is drawn over the fill and the
scan lines and under the edge, follows a cut or a rounded corner, and its width counts
towards the corner's reach like the edge's. A margin that leaves no middle is refused as well.
Every key is checked, and one nothing reads is refused with the nearest one that exists.
All of these are `compose.bad-panel`.

## What it builds

`panel.build(source, panel=, out=)` draws each state four times larger and brings it
down, so its diagonals are smooth. Each lands as `<name>.<state>.png`, beside the file or
under `out`, with a record whose `declaration` input is the `*.panel.toml`. Beside it,
`<name>.<state>.tres` is a Godot `StyleBoxTexture` with the declared margins, which a
theme takes as it is. Where the panel has scan lines, the stylebox tiles its middle
vertically (`axis_stretch_vertical`), so the lines keep their pitch at any height.

A built state is a picture like any other. A spec holds it to text contrast over the fill
(`measure.contrast`), its edge and its palette, and a capture of the menu holds it where
the game draws it.

## As a shader

`panel.build(shader=true)` also writes `<name>.gdshader`, a canvas shader that draws the
same parts at whatever size the Control is, and `<name>.<state>.material.tres` per state,
a `ShaderMaterial` holding that state's look as uniforms. Sizes stay in the panel's
pixels, and `pixel_scale` says how many screen pixels one of them takes. The shader also
draws what a nine-patch cannot:

```toml
[panel.holo.tick]                 # an accent mark centred on the top edge
length = 20
width = 2
colour = "#ff4fd8"
```

Built without the shader, a panel with a `tick` says `not_drawn: ["tick"]` for each state
rather than dropping it unannounced. Every number is written to the material with a
point, because Godot reads `4` as an integer and a float uniform given one keeps its
default.

## Screen wipes

The same file declares the wipes the menus move between:

```toml
[wipe.sweep]
kind = "sweep"          # or "iris"
colour = "#05070c"
angle = 0               # the direction it sweeps, in degrees (sweep)
bow = 0.2               # how far its front bows (sweep)
softness = 0.02         # the width of its edge, as a share of the screen
# centre = [0.5, 0.5]   # where an iris closes to (iris)
```

`panel.build` writes each one as `<name>.gdshader` and `<name>.material.tres`. Its
`progress` uniform covers the screen from 0, nothing, to 1, all of it, so the game tweens
one number. A kind other than these two is `compose.bad-panel`, naming both.

## Seen as the engine draws them

`panel.capture(source, out=, steps=, scale=)` builds the shaders and films them through
`capture.movie`. The stills are each panel state as `<name>.<state>.capture.png`, drawn
`scale` times larger on a grey screen, and each wipe at `steps` even points of its
progress as `<name>.<step>.capture.png`. Each still has a record naming the declaration
and the material it shows, so a spec can hold the edge's colour in a state or what a
wipe covers halfway, and a person can judge them on a sitting. Like every capture it
needs a display or the offscreen route, and without one it is `compose.unfilmed`.

## An icon set

A game's prompts draw each button as the pad shows it (§PW331), and the project does not
draw them by hand, so a set of small icons is a declaration, `*.icons.toml`: `name`,
`sizes` (8 to 1024 pixels), `atlas`, a `[style]` every icon inherits, and one
`[icon.<name>]` each. An icon is a `shape` (`circle`, `rounded`, `pill`, `trigger`,
`keycap`, `dpad`, `stick`), a `fill`, a `symbol` with its `symbol_colour`, and the
style's `outline`, `outline_width` (a share of the size), `rim` and `shade`, any of which
it may override. A symbol is text, or a glyph: `cross`, `ring`, `square`, `triangle`, the
four arrows, `menu` (three bars) and `view`, or a compass point, `north`, `south`,
`east` or `west`: four dots in a diamond, that one filled, drawn wider than a letter so
the dots read at 64 pixels (§PW431). A `dpad` with a `direction` lights that arm and puts
its arrow in it.

`icons.build(source)` draws each icon four times over and brings it down, so a 32-pixel
icon keeps smooth edges: the dark outline that reads over a bright scene, the fill
lighter at its top than its foot, a lit rim inside the outline, and the symbol in its
colour. Each lands as `<set>/<icon>_<size>.png`, or with `atlas = true` each size as
`<set>/<set>_<size>.png` and a JSON map of names to `[x, y, w, h]`; every file's record
(`picture`) has the declaration as an input. `out` sets the folder.

`[accept]` holds every icon at the smallest size: `symbol_contrast_min`, the WCAG ratio
of the symbol against its face; `background_contrast_min`, the worse of the outline
against white and the face against black; `symbol_share_min`, the symbol's share of the
face. `measured` gives each icon's three, and `failed` names each one under a bound.
With `sitting`, on by default, the set waits on the review page at its largest size,
since whether it reads as the pad's own button is a person's to say. A declaration that
cannot be drawn (an unknown shape or key, a size out of range, no icon) is
`compose.bad-icons`.
