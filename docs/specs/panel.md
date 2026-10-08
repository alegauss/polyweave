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
edge = { width = 2, colour = "#3fe0ff" }
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
margins, so a cut or a bracket that reaches past the smallest margin would be bent the
first time the panel is drawn larger than its texture. That is refused rather than drawn,
naming how far the corner reaches. A margin that leaves no middle is refused as well.
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
four arrows, `menu` (three bars) and `view`. A `dpad` with a `direction` lights that arm
and puts its arrow in it.

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
