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

## Silhouette

| Measure | Range | What it is |
|---|---|---|
| `silhouette_iou` | 0–1 | Intersection over union of the alpha mask against a reference |
| `silhouette_centroid_offset` | px | Distance between the two mask centroids |
| `silhouette_bbox_delta` | px | Largest per-edge difference between the two bounding boxes |

The reference is an image path. Both masks are normalised to the same dimensions before
comparison, so a render and a drawing of different sizes still compare.

`silhouette_iou` is the measure that would have caught the tall dome returned for a wide low
cap, before the credits were spent (§PW16).

## Colour at a place

| Measure | Range | What it is |
|---|---|---|
| `region_colour` | Lab | Mean CIELAB colour over the region |
| `delta_e` | 0–100 | CIEDE2000 distance from `region_colour` to a target |

Perceptual, because the question being asked is always "does this read as the right colour",
and RGB distance answers a different question. A `delta_e` under 2 is a difference a person
has to look for; over 5 is a different colour.

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
