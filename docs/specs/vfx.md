# Visual effects as declarations

Binds **PW259**.

A game's trails and bursts are as visible as its models, and Starship wrote each as a
Resource of its own and tuned it by looking at captures. Here an effect is declared in a
`*.vfx.toml` the game owns, and `vfx.build` writes it as the scene the engine plays, so
the game instances what was built and holds no numbers of its own.

## The file

```toml
[effect.spark_trail]
kind             = "particles"   # particles, or ribbon: a trail through each path
amount           = 64            # the particles alive at once; required
lifetime         = 0.8           # seconds; required
explosiveness    = 0.0           # 0 streams them, 1 starts them all at once
one_shot         = false         # a burst that plays once
emission         = "point"       # point, or sphere of `radius` metres
radius           = 0.0
direction        = [0, 0, 1]
spread           = 15.0          # degrees, 0 to 180
speed            = [2.0, 3.0]    # metres a second, least and most
gravity          = [0, 0, 0]
size             = 0.2           # a quad's side, or a ribbon's width, in metres
size_over_life   = [1.0, 0.0]    # scales, evenly across the life
colour_over_life = ["#ffd24aff", "#ff4a1a00"]   # #rrggbb or #rrggbbaa, evenly
blend            = "add"         # add or mix
trail            = 0.3           # ribbon only: seconds of path each ribbon keeps
```

A key it does not have is refused with its nearest name, and so is a value outside what
the comment says (`vfx.bad-effect`); a missing file, one that is not TOML or one with no
`[effect.<name>]` is `vfx.no-source`.

## Building

`vfx.build(source, effect=, out=)` builds every effect in the file, or the one named, as
`<name>.tscn` beside the source or in `out`. The scene is a `GPUParticles3D` whose process
material, colour ramp, size curve, material and draw pass are all in the one file: a
billboarded quad for particles, a `RibbonTrailMesh` with particle trails for a ribbon.
Each is recorded (`vfx`, [provenance.md](provenance.md)).

The answer gives each effect's `file` and `kind` and what it measures, worked out from the
declaration since each is arithmetic:

| Measure | What it is |
|---|---|
| `lifetime` | seconds a particle lives |
| `reach` | the furthest one can travel: the top speed over its life, the fall gravity adds, and the emission radius |
| `alive` | the particles alive at once, the effect's budget |
| `rate` | how many start a second |
| `brightness` | the brightest stop of its gradient, as luminance times alpha |

Whether its look is right is a person's call. Showing it to them over a few frames, and
holding these measures to an acceptance spec, are still open on PW259.
