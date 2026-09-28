# A store's capsules from one key art

Binds **PW268**.

A store page asks for one key art in many shapes, each with its own size and most with
the game's logo on it: Steam's is about ten. `store.capsules` cuts the whole set in one
call, so a project writes no crop script of its own.

## The store

A store is data: `src/polyweave/stores/<name>.toml` for one this plugin knows (`steam`),
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
rule, `stroke` and whether it is `legible`.
