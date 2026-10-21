# A store's capsules from one key art

Binds **PW268**.

A store page asks for one key art in many shapes, each with its own size and most with
the game's logo on it: Steam's is about ten. `store.capsules` cuts the whole set in one
call, so a project writes no crop script of its own.

## The store

A store is data: `src/polyweave/layers/store/stores/<name>.toml` for one this plugin knows (`steam`),
or a project's own file of the same shape, passed by path.

```toml
name = "steam"
min_stroke = 2.0            # the logo's thinnest stroke, in pixels, for it to read

[shape.small_capsule]
size = [462, 174]           # pixels
logo = "centre"             # centre, lower, only or none
logo_width = 0.8            # of the shape's width
logo_at = 0.72              # lower only: where the logo's middle sits, of the height
```

`centre` puts the logo across the middle, `lower` the same with its middle at `logo_at`,
`only` draws the logo alone on a transparent canvas fitted inside the shape (Steam's
library logo), and `none` leaves it off where the store asks for no text (the library
hero) or the shape is art alone. A shape without a size in whole pixels or with another
rule is `store.bad-shape`.

## Cutting

`store.capsules(key_art, logo, out=, store="steam", focus=[0.5, 0.5], shapes=)` writes
`<out>/<shape>.png` for each shape, or for those `shapes` names. Each is the key art
scaled to cover the shape and cropped there around `focus`, a point given as fractions of
the key art (`store.bad-focus` otherwise), which moves only as far as the art allows: a
square cut from a wide picture spans its full height and moves across it only. The logo
is resized to its rule's size and placed on it. Each capsule gets a record (`picture`)
naming both pictures as inputs, the store, the shape and the focus.

**Nothing is upscaled.** Before anything is written, a key art smaller than any shape it
covers, or a logo drawn larger than it is, is refused (`store.too-small`) naming each
shape and the size it needs, with the shapes that can be cut now in `allowed`, so a
project whose key art is too small for Steam's 3840x1240 hero cuts the rest with
`shapes=` while it makes a larger one.

**The logo is held to reading at its size.** Its thinnest stroke is measured on its alpha
at the scale each shape draws it: over its opaque pixels, the 10th percentile of the
shorter of each one's horizontal and vertical run. A capsule where that falls under the
store's `min_stroke` is written, since a person should see it, and named in `failed`; the
answer is `ok` only when none is. Each capsule's answer gives its `file`, `size`, `logo`
rule, `stroke` and whether it is `legible`. A logo whose alpha fills its box is a plate
with the letters on it, and a stroke read off its alpha is the plate's: the answer says
so in `logo_plate` and `why_plate`, since the number would pass every time.

**A vector logo is drawn at each capsule's size** (§PW275). A logo given as `.svg` is
rasterised by the engine's own SVG renderer, ThorVG, in one short headless run: once at
its own size to learn its shape, then once per capsule at the scale that capsule draws
it, so its stroke is measured on the letters as the capsule shows them rather than on a
scaled-down export. A vector has no size to be too small at, so the logo half of
`store.too-small` does not apply to it. Without the engine it is `store.no-rasteriser`,
and a PNG with alpha is the other way in.

## The same logo in the game

**The game draws the logo the store shows, from the same file** (§PW315). Starship's
title wanted the logo accepted for its store page, an SVG with a blurred halo, a dashed
ring and the letters, and the store's PNG came from a rasterisation nothing recorded.
`picture.vector(source, out, width, layers=)` draws the SVG at `width` pixels through the
same ThorVG run, blur filters and masks included, and writes a record whose `vector`
input is the SVG. So `provenance.outdated` names the PNG once the SVG changes.

**A layer that moves is one source and one sweep** (§PW476). Spinhold turns its logo's
dashed orbit by drawing it at several `stroke-dashoffset` values, and had grown eight SVGs
and eight records that never said they were one loop. `sweep = {element, attribute,
from, to, frames}` sets that attribute on each named element (an `#id` anywhere in the
drawing, or a list of them) at `frames` even steps from `from` towards `to`, the end left
out so the last frame steps back into the first, and draws every layer, and the whole
unless `whole = false`, once a frame as `<out>[.<layer>].<frame>.png`. Each frame's record
names the one SVG, the sweep, the frame and its value; the answer lists the frames in
order and the values. `strip = true` also packs each layer's frames left to right into
`<out>[.<layer>].strip.png`, whose record lists the frames it holds. `whole = false`
leaves out the whole picture a game never draws, with or without a sweep, and needs a
layer. A sweep naming an id the drawing lacks, a key it does not take, a bound that is
not a number or frames outside 2 to 256 is `compose.bad-sweep`, listing the ids there
are.

**A layer that draws nothing is refused** (§PW478). Spinhold's halo group shared the id
`halo` with its own blur filter, and the layer came back fully transparent with an
answer like any other's. Before drawing, every id a layer selector, a sweep or a
`url(#id)` or `href="#id"` reference leans on has to name one element, and a `filter`,
`mask` or `clip-path` has to land on an element of that kind; either failing is
`compose.ambiguous-id`, naming the elements. A duplicate id nothing leans on is said in
`duplicate_ids` instead. After drawing, a layer (or the whole) whose every pixel is
transparent in every frame is `compose.empty-layer`, naming its selector; a sweep's
frames that drew nothing while others drew are listed in `empty_frames`.

**Live text is outlined before ThorVG draws it** (§PW453). ThorVG, as Godot builds it,
draws no `<text>`, so a banner came out with every letter missing and the call answered
a success. Before any drawing, in `picture.vector` and in `store.capsules` alike, each
`<text>` and its `<tspan>`s are replaced by their glyph outlines, set by the glyphs'
advances, with `text-anchor` and `letter-spacing` applied and no kerning. The font is
the one the run's `font-family` (inherited from the groups around it), `font-weight` and
`font-style` resolve to, looked for first among `[words] fonts` and then among the
system's fonts. A generic family such as `sans-serif` stands for the usual faces
(Arial, DejaVu Sans and the like). A span keeps its own fill and stroke. Each font file
used is a `font` input of the picture's record. Text along a `<textPath>`, a family no
font has, a character the font lacks, or fontTools not installed (`pip install
polyweave[text]`) is refused as `compose.text-unoutlined` by name, never drawn blank.
An SVG with no text never imports fontTools.

**A part that moves is drawn as its own layer.** `layers` maps a name to one top-level
element of the drawing: `#id`, or its place counted from 1, because exported SVGs often
leave their groups without ids. Each layer is written beside `out` as
`<out>.<name>.png`, drawn with every other element hidden and the `<defs>` kept, on the
whole picture's canvas and origin, so a ring can turn and a glow pulse while the letters
hold still, and the layers stack back into the whole. A selector naming no element is
`compose.no-layer`, and its `allowed` lists the places and ids there are. An SVG that
does not parse, or states neither a pixel width nor a viewBox, is `compose.no-vector`.
Each layer is a picture like any other, so a spec can hold its alpha edge.

## A site's copies of the art

**A resized copy is declared, and its record says what it was cut from** (§PW585). A
promo site ships its own copies of the art, because a page cannot carry the originals.
Cottony cut 28 of them with a script whose check re-cut each in memory and called it
stale past a mean of 0.75 levels and a 99th percentile of 12, floors tuned by hand after
twelve copies showed older art than the game for weeks. A `*.copies.toml` declares them:

    into = "site/assets"         # where each `out` is written; the project if unset
    quality = 88                 # WebP and JPEG, unless a row says; 90 if unset

    [[copy]]
    source = "docs/design/promo3.jpg"
    out = "hero.webp"            # .webp, .jpg or .png picks the format
    side = 820                   # the largest side in px; the size kept if unset
    box = [30, 402, 850, 1024]   # left, top, right, bottom, cropped before the resize

`picture.copies(source)` crops each row by `box`, fits it within `side` by Lanczos and
encodes it by its extension, a WebP at method 6. Every copy's record names the source
(`picture`) and the table (`table`) as inputs with the side, box and quality as params,
so `provenance.outdated` names a copy once its source or its table moves, and a newer
Pillow encoding a level differently changes nothing. A source that is not there is
`copies.missing-source`, naming every one, before anything is written. A key the table
does not take, a row with no source or out, an extension no format is picked by, or a
side, box or quality that is not a whole number in range is `copies.bad-table`. A JPEG
of a source with transparent pixels is `copies.no-alpha`, never filled.
