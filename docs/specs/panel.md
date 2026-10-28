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

**A holo frame's details** (§PW479), as Spinhold's accepted holo shader drew them:

```toml
edge = { width = 3, colour = "#baa6ff", lit = [1.15, 0.55] }
hairline = { inset = 9, width = 1, colour = "#baa6ff", strength = 0.35 }
brackets = { length = 12, width = 3, colour = "#40e8ff", inset = 12 }
tick = { from = 30, to = 102, width = 3, colour = "#ff3dcc" }
```

`edge.lit = [top, foot]` multiplies the edge's colour by `top` at the panel's top and
`foot` at its foot, so a bevel is lit from above and falls to shadow in its own hue;
`[1, 1]`, the default, is one colour. A `hairline` is a line `width` pixels thick
`inset` pixels inside the outline, its colour laid over the glass at `strength`, 0 to 1.
`brackets.inset` sets the brackets in from the corner, starting at the inset on both
axes rather than on the outer edge past the cut; the inset counts towards the corner's
reach. `tick.from` and `tick.to` place the accent along the top edge, in pixels from the
left, in place of a centred `length`. All four are drawn the same on the nine-patch and
on the shader, but for the tick, which only the shader draws.

A line's thickness — the `width` of the edge, hairline, piping, brackets and tick — is
any number of pixels from 0.5 (§PW638), so a 1.2-pixel hairline a person accepted is
declared as it was drawn; an edge or piping may also be 0, for none. The shader draws the
fraction exactly and the nine-patch to the nearest quarter pixel, being drawn four times
larger. Sizes, margins, insets, cuts and lengths stay whole, since the nine-patch cuts on
them, and a corner whose parts reach a fraction of a pixel needs the whole pixel past it
in the margin.

**States change by amounts, not only colours.** Three keys of a panel, which a state
overrides like any other: `glow` (0 to 4, default 1) multiplies the edge, the brackets
and the tick, after the edge's `lit`, so a glowing bevel keeps its hue; `glass_lift` (0
to 2) brightens the glass by that share; `drain` (0 to 1) mixes the whole towards a dim
grey and fades it by up to 30%. Spinhold's focus is `glow = 1.9`, pressed
`glass_lift = 0.35` and disabled `drain = 1`. A `sweep = { colour, strength, speed,
width, slant }` is a faint diagonal light crossing the glass on `TIME`, which only the
shader draws, so the nine-patch says `not_drawn: ["sweep"]`. `tint` multiplies the
brackets' colour and nothing else: the edge, the tick and the fill ignore it, on the
shader and the nine-patch alike, so a gold tint over cyan brackets comes out green. To
replace the brackets' colour, set `bracket_colour` itself.

A `seam` sews the panel, where a flat dashed stroke only paints a line on it:

```toml
[panel.play.seam]
inset = 7          # pixels in from the outline
dash = 5           # a stitch, in pixels
gap = 3            # between stitches, in pixels
width = 1.6        # the thread, in pixels
thread = "#fff4f0" # its colour, which a seam must name
seed = 2           # which hand sewed it
# shading, shadow, holes, jitter: each 0 (off) to 1 (default)
```

The stitches follow the outline at `inset`, whether cut, rounded, a pill or an outline of
its own, spaced by arc length so whole stitches close the loop. `shading` lights the
thread along the side the light comes from and shades the other, with a faint twist of
plies; `shadow` lays a soft shadow down and right of each stitch, darkened from the fill
so it never goes grey; `holes` punches a needle hole past either end, where the thread
goes under, and shortens each stitch to show it; `jitter` sets each stitch a seeded
fraction off its angle and its line. A seam with all four at 0 is the plain dash that
read as a road marking. It is clipped to the panel and drawn over the fill and the
piping, under the edge.

A built seam is drawn at the size the panel is built. A nine-patch grows the stitches in
its middle, so a stretchable state says `stretched: ["seam"]`. The shader sews by arc
length along the inset path at the Control's own size, so a panel grown to fit a longer
translation keeps its stitch pitch, with the same four effects drawn by the same rules,
though not to the pixel: the build lays its stitches with a seeded random draw, the
shader with a hash of each stitch's index.

`picture.sew(source, out=, seam=)` lays the same seam along a picture's silhouette, so
a baked prop and a drawn panel are sewn by one needle. `seam` takes a panel seam's keys.
The silhouette is the picture's alpha at the project's `[tolerance] alpha_floor`, worn
`inset` pixels in, nearly round, rather than offset, so a star's tips never cross into
loops. The stitches follow that inner edge by arc length, and every effect is clipped
to the body, the shadow and the holes darkened from the picture under them pixel by
pixel. The sewn picture lands at `out` with a record whose `picture` input is the source,
and the answer says how many stitches it laid. A seam with no thread, a key no seam
takes, or a silhouette that wears away before the inset is `compose.bad-seam`.

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

A material loaded with `preload` is shared by every Control that loads it, so setting a
uniform on one state's material changes every panel drawn in that state. The build
therefore also writes `<name>.panel.gd`, named in the answer's `switches` (§PW639): a
`ColorRect` that keeps a `ShaderMaterial` of its own and, whenever its state changes,
copies every uniform from that state's material onto it. A game preloads it and calls
`.new()`, or extends it. It has a flag for each state the panel declares (`disabled`,
`pressed`, `focused`, `hovered`), and the first one set in that order wins, with
`normal` when none is set. Its `overrides`, uniforms by name such as `cut`,
`bracket_length` or `bracket_colour`, are applied after every switch, so they hold on
that one panel through every state. It has no `class_name`, so it cannot collide with a
game's own. It is written again with the materials, and nobody edits it by hand.

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
needs a display or the offscreen route, and without one it is `compose.unfilmed`. So is
a film whose shader would not compile (§PW489).

`sizes=[[w, h], …]`, in the panel's pixels, films each state once per size instead of at
the declared one, as `<name>.<state>.<w>x<h>.capture.png` with the size in the record's
params (§PW490). That is the shader route's own case: a button grown to fit a longer
translation keeps its stitch pitch, its pill ends and its grain, where a nine-patch
would stretch them. The screen grows to hold the largest at `scale`, up to 3840×2160; a
size past that, or one under 8 pixels, is `compose.bad-panel` before the engine starts.

## An icon set

A game's prompts draw each button as the pad shows it (§PW331), and the project does not
draw them by hand, so a set of small icons is a declaration, `*.icons.toml`: `name`,
`sizes` (8 to 1024 pixels), `atlas`, a `[style]` every icon inherits, and one
`[icon.<name>]` each. An icon is a `shape` (`circle`, `rounded`, `pill`, `trigger`,
`keycap`, `dpad`, `stick`, `hexagon`), a `fill`, a `symbol` with its `symbol_colour`, and the
style's `outline`, `outline_width` (a share of the size), `rim` and `shade`, any of which
it may override. A symbol is text, or a glyph: `cross`, `ring`, `square`, `triangle`, the
four arrows, `menu` (three bars), `view`, `plus`, `minus`, `star`, `figure` (a head
over shoulders) and `shield`, or a compass point,
`north`, `south`, `east` or `west`: four dots in a diamond, that one filled, drawn wider
than a letter so the dots read at 64 pixels (§PW431). A `dpad` with a `direction` lights
that arm and puts its arrow in it.

Text is fitted by its ink, not its font size (§PW642). It is measured at one size, then
scaled until its ink meets the symbol's box on its longer side and centred on that ink,
as a glyph fills the same box. Before this, a "+" drawn at half the icon inked 0.024 of
the face and a "-" 0.004, where the glyphs beside them reached 0.11 to 0.18. Fitted, a
font's "+" is still a hairline beside the set's strokes (0.046 against a ring's 0.12), so
the text "+" and "-" are drawn as the `plus` and `minus` glyphs.
`symbol_scale`, from 0.2 to 2 and 1 by default, a style key an icon may override, grows
or shrinks that box for text and glyphs alike.

**States and tints** (§PW644). Spinhold's world map shows each world's three marks as a
hexagonal pip, filled in the world's colour once earned and a dark socket before, in five
world colours. It had to draw them at run time, outside every check. An icon now declares
both:

```toml
[icon.star]
shape = "hexagon"
symbol = "star"
tints = ["#e85d4a", "#4ab0e8", "#f2c14e"]   # the colours the game tints it with

[icon.star.states.empty]                    # what the empty state changes
fill = "#1c1f27"
symbol_colour = "#3a3f4c"
tints = []
```

A state is the icon with what it changes, built and measured as an icon of its own,
`<icon>_<state>_<size>.png`. A state key no icon takes is refused. An icon with `tints`
is built as two pictures. `<icon>_<size>.png` is its face in white, with its shading
kept as light and dark, which the game modulates by its colour. Over it,
`<icon>_over_<size>.png` holds the outline and the symbol in their own colours, which no
tint touches. Its legibility is measured at every declared tint: `measured` keeps the
worst of each figure and names the colour in `worst_tint`. The sitting shows it once in
each tint, not as the white face. A tint that is not `#rrggbb` is `compose.bad-icons`.

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
Bound or no bound, an icon whose symbol fills under a third of the set's median share
says so in its `measured` as `speck`, where the set has three symbols or more: a speck is
never what was meant.
With `sitting`, on by default, the set waits on the review page at its largest size,
since whether it reads as the pad's own button is a person's to say. A declaration that
cannot be drawn (an unknown shape or key, a size out of range, no icon) is
`compose.bad-icons`.

### An icon rendered from a model

A palette tile, an inventory slot, a bestiary entry or a map marker is a small picture of
a model the project built (§PW610), and cropping a render by hand leaves it stale the day
the model changes. So an icon may name a `model` instead of a `shape`: a `.glb`, `.gltf`
or `.fbx` under the project, a geometry build's output or a mesh ingested. Beside it:

- `view`: `three_quarter` (the rig's own camera, azimuth 35, elevation 20, the default),
  `front` or `side`; `azimuth` and `elevation`, in degrees, override it, which is how an
  icon takes the game's own camera; `focal_mm` too;
- `margin`, the room around the subject, as `render.bake` takes it (1.15 by default);
- `light`, a table of any of `render.bake`'s `key`, `fill`, `rim`, `ambient`,
  `ambient_colour`, `exposure` and `light_distance`;
- `background`, `"#RRGGBB"` laid behind it, or `"transparent"`, the default;
- `rung`, the render rung, `final` unless named.

Shape keys (`fill`, `symbol`, the style) are refused on a model's icon, since it is
rendered and not drawn. The model is rendered once through `render.bake`, transparent, at
twice the largest size, into `paths.work/icons/<set>/renders/`, and brought down to each
size. Each file's record has the mesh as an input (`mesh`) beside the declaration, so
`provenance.outdated` names every icon a model edit left behind, and `icons.build` again
makes them anew; an atlas holding one has every model of the set as inputs.

`[accept]` holds a model's icon at the smallest size to `coverage_min`, the share of the
square the subject fills; `silhouette_kept_min`, the overlap of its outline at that size,
grown back, with the render's own, which is how much of the shape that tells one actor
from another survives; and `background_contrast_min`, the subject's median luminance
against its background, or the worse of white and black where it has none. A model that
is not there is `compose.bad-icons` before anything renders, and a machine without
Blender refuses as `render.no-renderer`, where a set of shapes alone needs none.
