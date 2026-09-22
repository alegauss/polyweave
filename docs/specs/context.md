# Judging an asset where it will be seen

Binds **PW10**, and is what §PW15's contact sheet is built on.

An asset that reads correctly on its own can be the one wrong thing in the frame it lands
in. Cottony's first modelled prop looked right in isolation and then sat on a sheet beside
five drawn siblings that each had a soft specular window and a shadow beneath them; it had
a pin-point highlight and it floated. **Nothing in a solo render shows that**, and no
measurement of a lone file can reach it.

## Two composites

**A contact sheet** places the asset among its siblings, so the one that does not belong is
visible at a glance. Every tile gets the same cell and is anchored on its footprint — a
prop that floats is exactly the failure this is for, and centring each tile in its cell
would hide it. A tile keeps its proportions; it is never stretched to fill.

**An in-place composite** puts the asset into a real capture of the screen it belongs to,
at the position and the width it will actually be drawn. Anchoring is `footprint` by
default, which is §6's origin — the base of the silhouette, not the centre of the box.

Both return **an image like any other**, so the measurement runs against the composite
rather than against the asset's own file. That is the whole point: the comparison has to
see what a person would see.

An asset placed entirely outside the capture is refused rather than silently clipped to
nothing, because a position given in the wrong coordinate space otherwise produces a
composite that looks like the capture and proves nothing.

## What survives at display size

`luma_bands` counts the distinct luminance levels left after downscaling to a stated size.
Cottony's fluff read at 1.2 and vanished at 1.0, at a third of the sprite's authored size.

**The display size is an argument and never a default.** A count taken at the authored size
answers a question nobody asked, so the measure refuses rather than guessing
(`spec.measure-needs`). The count is of distinct 8-bit luminance levels over the subject
after the downscale — a proxy for how much tonal structure a viewer actually receives, and
one that collapses exactly when detail is lost.

## Deliberately not here

**No labels on a contact sheet.** Text needs a font, a font is a file, and a file the
plugin ships is one more thing that differs between two machines. The order of the tiles is
the caller's and it already knows which one is new.
