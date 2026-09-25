# Measurements

Binds **PW8–PW11**, and is the vocabulary [acceptance-spec.md](acceptance-spec.md) draws on.
This list is **closed**: a name not on it is a refusal (`spec.unknown-measure`), never a
warning. That is what makes an acceptance spec checkable rather than aspirational.

## Every measurement names its region and its rung

```json
{
  "measure": "saturation_p99",
  "region": "subject",
  "rung": "preview",
  "value": 0.68
}
```

**Region** is `frame`, `subject`, a rectangle `[x0, y0, x1, y1]`, or the name of a mask file.
`subject` means the pixels where alpha exceeds `[tolerance] alpha_floor`, and it is the
default wherever the image has an alpha channel. The masking is half the value of the whole
vocabulary: a prop measured over only its own pixels is not diluted by whatever background it
happens to sit on.

**Rung** is which preview level the render came from (§PW7). It is reported, never inferred,
so a verdict taken on a sphere is never mistaken for one taken on the final mesh.

## Distribution statistics

Reported as a set, never as a single number. §PW9 is the reason: Cottony's board matched the
concept art's mean saturation to within 0.01 while looking plainly wrong, and the entire
difference sat at the 99th percentile.

| Measure | Range | What it is |
|---|---|---|
| `saturation_{p1,p50,p99,mean,std}` | 0–1 | HSL saturation over the region |
| `luma_{p1,p50,p99,mean,std}` | 0–1 | Relative luminance, sRGB-weighted |
| `hue_spread` | 0–1 | Circular standard deviation of hue, weighted by saturation |
| `alpha_coverage` | 0–1 | Fraction of the region with alpha above the floor |

A call asking for `saturation` returns all five statistics. A predicate names one.

Two things the first implementation had to settle:

**`luma` is computed on linearised values**, because luminance is a linear quantity and the
bytes in a file are not. Mid grey stores as 128 and carries about 0.22 of the light, not
0.5; weighting the stored bytes would report a picture as half as bright as it is.

**`hue_spread` is the circular *variance*** — one minus the saturation-weighted resultant
length — rather than the circular standard deviation it is derived from. The standard
deviation is unbounded and this table declares a 0–1 range, and a measure that cannot hit
its own declared range is not usable in a bound. It is weighted by saturation because the
hue of a grey pixel is arbitrary, and an image of mostly grey would otherwise report a
spread it does not have.

A region holding no pixels is refused (`spec.empty-region`) rather than answered with zero:
a statistic over nothing is not a statistic.

## Silhouette

| Measure | Range | What it is |
|---|---|---|
| `silhouette_iou` | 0–1 | Intersection over union of the alpha mask against a reference |
| `silhouette_centroid_offset` | px | Distance between the two mask centroids |
| `silhouette_bbox_delta` | px | Largest per-edge difference between the two bounding boxes |

The reference is an image path. Both masks are normalised to the same dimensions before
comparison, so a render and a drawing of different sizes still compare.

**With no region named, these three take the whole frame** (§PW87), where every other
measure takes the subject. They compare two shapes, and cut to the render's own subject
the drawing outside the render was never counted: Cottony's mushroom read 0.916 against
its drawing that way and 0.856 over the frame, and a render missing half the drawn shape
scored close to one. A region that is named bounds both masks alike.

`silhouette_iou` is the measure that would have caught the tall dome returned for a wide low
cap, before the credits were spent (§PW16).

## Colour at a place

| Measure | Range | What it is |
|---|---|---|
| `region_colour` | Lab | Mean CIELAB colour over the region |
| `delta_e` | 0–100 | CIEDE2000 distance from `region_colour` to a target |
| `pixel_delta_e_{p1,p50,p99,mean,std}` | 0–100 | CIEDE2000 distance from each pixel to a target |

Perceptual, because the question being asked is always "does this read as the right colour",
and RGB distance answers a different question. A `delta_e` under 2 is a difference a person
has to look for; over 5 is a different colour.

**`delta_e` is taken at the mean, and `pixel_delta_e` is the one to bound** wherever the
region holds more than one colour (§PW86). Cottony's mushroom cap is covered in white spots,
so the bar recorded for it is a median, and over any rectangle on it the mean is pulled toward
white by however many spots it catches. `pixel_delta_e_p50` is the body colour through them,
and `_p99` is how far the worst of it strays. `delta_e` keeps its meaning so that no spec
already written changes under it.

## Comparing two renders

| Measure | Range | What it is |
|---|---|---|
| `distance` | 0–1 | Perceptual distance between two images |
| `changed_fraction` | 0–1 | Fraction of pixels differing by more than a stated amount |

A path-traced bake is not byte-reproducible (§PW11): two runs of one unchanged Cottony scene
differed in 29,696 pixels, none of them by more than 1/255. **That is the noise floor any
usable `distance` metric must sit above.** A metric that cannot separate sampler noise from a
real change is not fit for this purpose, and the first implementation has to demonstrate the
separation on that case rather than assert it.

Thresholds are per comparison and come from `[tolerance]` in the project config. The bar for
sampler noise is not the bar for a silhouette that has to land within three pixels.

**And the noise floor is measurable, which beats configuring it.** It is not one number: two
seeds of one unchanged sphere measured 0.0234 apart at the sphere rung, 0.0195 at preview and
0.0122 at final (§PW44), so `[tolerance] render_noise` is keyed by rung. Even so those are
one machine's numbers. The better route is a **twin** — a second render of the subject's own
unchanged scene at another seed — whose distance from the subject *is* the floor, right at
whatever sample count on whatever machine, for one render. The controls are what make it
trustworthy: the same seed rendered twice measures 0.0 exactly, so what a twin measures is
sampler noise and not the pipeline wobbling, and a changed material measures 0.63 against a
floor of 0.02, so nothing real is hidden under a bar that size.

`distance` is **the worst patch, not the average pixel**. The difference is pooled over 8×8
blocks and the largest block is reported. Pooling is the whole separation: a path tracer's
error is uncorrelated between neighbours and averages away inside a patch however many
pixels carry it, while a real change is contiguous and survives the average at full
strength. Counting differing pixels cannot tell those apart; averaging over a neighbourhood
can. The worst block rather than the mean block, because §PW9's lesson applies here too — a
highlight that moved is small, and an average over the frame dilutes it away.

**Alpha is applied before the comparison.** The colour beneath a fully transparent pixel is
undefined: a renderer writes whatever it had there, and two runs of one unchanged scene
disagree about it entirely. Comparing raw channels over a transparent background measures
the renderer's scratch memory and nothing else — measured here as the difference between a
useless metric and one that separates noise from change by a factor of fifty.

## At display size

| Measure | Range | What it is |
|---|---|---|
| `luma_bands` | count | Distinct luminance bands surviving after downscale to a stated size |

Some detail exists in the file and is gone on the screen. Cottony's fluff read at 1.2 and
vanished at 1.0, at a third of the sprite's authored size. This measure takes the display
size as an argument and downscales before counting, which is the only way to ask that
question honestly.

## What comes back with a render

Per §PW8, a render call returns the image alongside its measurements in one answer, so a
verdict costs one turn rather than three. The default set is `saturation`, `luma`,
`alpha_coverage` and the dimensions; anything else is asked for by name.

The image comes back **base64-encoded at the size it was rendered**, never a thumbnail: an
image worth looking at is the other half of the answer, and a caller that has to open the
file to see it is back to paying two calls for one question. A sweep that wants only the
numbers turns it off, because the answer rides home inside a job record.

**A measure this plugin does not compute yet is refused by name**, saying which roadmap line
builds it (`spec.unmeasured`). An answer that is quietly missing the field that was asked
for is the same defect as a dropped argument, one layer up.

`alpha_coverage` is a fraction **of its region**, not of the frame — a measurement taken
over a rectangle answers about that rectangle, or a region would only ever report its own
size.

## Sound

A sound is measured off its own samples, never a picture (§PW113), and the two seam
measures are Cottony's own, from `tools/audio/loop_music.py`. Each is a ratio against
the track itself, so one bar serves every track: a seam may sound like any ordinary
moment of that music, and nothing more.

- `seam_step`: the jump from the last sample to the first, over the track's
  99th-percentile step between samples. Above one, the wrap clicks.
- `seam_flux`: the largest spectral change across the wrap, over the track's
  90th-percentile spectral change. Above one, the seam sounds like a cut.
- `loudness` (RMS, dBFS), `peak` (dBFS) and `duration` (seconds).

A 16-bit or 24-bit PCM WAV is read with the standard library, and anything else is
decoded by ffmpeg or refused (`spec.unreadable-sound`), as is a clip too short to hold
a seam. `sound.measure` returns all five. A pure tone is a poor fixture for the
spectral ratio, since every moment of it is the same: the tests use noise made
periodic by an inverse FFT, which is a loop by construction.

## Two digests: did the outline move, or only the look

**A bake leaves two 16-character hashes** in its answer and in its record (§PW141):
`shape_digest` over the outline and `look_digest` over the look, split where Shio's render
digest splits, so "I restyled it" and "I broke the outline" are different answers a later
session reads without the pictures. A cache hit returns the ones it was recorded with.

- The outline: the subject's box and its footprint anchor (the middle of its lowest row),
  as fractions of the frame, its coverage, and the triangle count the renderer drew.
- The look: luma at the 5th, 50th and 95th percentile, by the percentile rule above, and
  the palette: the mean Lab colour of each material slot, keyed by the slot's name.

Each figure is **quantised at the rung's `render_noise`** before it is hashed, a Lab colour
at a hundred times that, so a render that moved only by sampler noise keeps both. A figure
sitting on a step's edge can still cross it, which is why the answer also carries
`quantum`, and `measure.digest` returns the figures themselves. `measure.digest` reads the
same two off any picture by path, at the rung its record names.

**A palette per slot comes off one flat pass** (§PW161). The picture keeps only the
blended result, so a mean over the whole subject let a recoloured wrapper or rim sit
inside one quantisation step. After the render, the bake paints every slot an emission
of its own colour, turns the lights and world off and renders one sample at the same
rig, and gives each subject pixel to the nearest of those colours. The masks are not
kept. The palette is recorded beside the two hashes, so a moved `look_digest` says which
slot moved. A subject wearing one slot, and a picture read by path with
`measure.digest`, have no masks and keep the subject's mean.
