# Visual effects as declarations

Binds **PW259**.

A game's trails and bursts are as visible as its models, and Starship wrote each as a
Resource of its own and tuned it by looking at captures. Here an effect is declared in a
`*.vfx.toml` the game owns, and `vfx.build` writes it as the scene the engine plays, so
the game instances what was built and holds no numbers of its own.

## The file

```toml
[effect.spark_trail]
kind             = "particles"   # particles; ribbon, a trail through each particle's
                                 # path; or path_ribbon, one through the emitter's
amount           = 64            # the particles alive at once; required
lifetime         = 0.8           # seconds; required
explosiveness    = 0.0           # 0 streams them, 1 starts them all at once
randomness       = 0.0           # how unevenly they start, 0 to 1
one_shot         = false         # a burst that plays once
emission         = "point"       # point, sphere of `radius`, or box of `extents`
radius           = 0.0
extents          = [0, 0, 0]     # box only: its three half-sizes, in metres
direction        = [0, 0, 1]
spread           = 15.0          # degrees, 0 to 180
speed            = [2.0, 3.0]    # metres a second, least and most
gravity          = [0, 0, 0]
damping          = [0, 0]        # speed lost a second, a number or least and most
angle            = [0, 0]        # a particle's turn at birth, degrees
angular_velocity = [0, 0]        # its spin, degrees a second
shape            = "square"      # square, dot, ring, flake, or a picture's path
size             = 0.2           # a quad's side, or a ribbon's width, in metres
size_over_life   = [1.0, 0.0]    # scales, evenly across the life
colour_over_life = ["#ffd24aff", "#ff4a1a00"]   # #rrggbb or #rrggbbaa, evenly
blend            = "add"         # add or mix
trail            = 0.3           # ribbon only: seconds of path each ribbon keeps
facing           = [0, 1, 0]     # path_ribbon only: the way its width lies
```

A key it does not have is refused with its nearest name, and so is a value outside what
the comment says (`vfx.bad-effect`); a missing file, one that is not TOML or one with no
`[effect.<name>]` is `vfx.no-source`.

The five keys after `gravity` are what Starship's accepted trails drew with (§PW281): its
sparks brake at 6 to 10 and stay by the engine, its confetti spins, its sun band throws
from a tall box. A `shape` other than `square` is a texture on each quad, drawn from a
white gradient as the trails drew theirs: `dot` a soft radial dot, `ring` a radial ring,
`flake` a strip that is opaque for 70% of its width. A path ending in a picture's suffix
names the project's own picture instead, refused where no file is there. `damping` is
never below 0, and a box needs at least one extent above 0.

## Building

`vfx.build(source, effect=, out=)` builds every effect in the file, or the one named, as
`<name>.tscn` beside the source or in `out`. The scene is a `GPUParticles3D` whose process
material, colour ramp, size curve, material and draw pass are all in the one file: a
billboarded quad for particles, a `RibbonTrailMesh` with particle trails for a ribbon.
Each is recorded (`vfx`, [provenance.md](provenance.md)).

A `path_ribbon` is the ribbon a moving emitter leaves, the tender's own trail (§PW281),
and is not particles at all: a `Node3D` the game puts where the engine is, carrying a
script inside the scene. Each frame it keeps the point its parent carried it to, drops
those older than `lifetime` and holds `amount` at most. It draws them in the world as one
triangle strip `size` wide across `facing`, each point's colour and width read off
`colour_over_life` and `size_over_life` at its age. So it narrows and fades behind the
emitter and stays where the emitter was, and the game still holds no code of its own.
Its `reach` is its half-width, since it travels nowhere by itself.

The answer gives each effect's `file` and `kind` and what it measures, worked out from the
declaration since each is arithmetic:

| Measure | What it is |
|---|---|
| `lifetime` | seconds a particle lives |
| `reach` | the furthest one can travel: the top speed over its life, braked by the least damping until it stops, the fall gravity adds, and the emission radius or the box's far corner |
| `alive` | the particles alive at once, the effect's budget |
| `rate` | how many start a second |
| `brightness` | the brightest stop of its gradient, as luminance times alpha |

## Watching

Whether its look is right is a person's call. `vfx.preview(source, out=, effect=,
stills=6)` builds each effect and plays it in the game's own project for one and a half
lifetimes against a neutral grey (`NEUTRAL`, 0.18), from across its direction with the
camera framing its reach. The emitter is carried round a circle in the camera's plane,
once in two lifetimes, since a trail reads only in motion; a `one_shot` burst is watched
standing still. The run goes through `capture.movie`, so it needs a display or the offscreen
route (`vfx.unwatched` where there is neither), asked at 320x180 (see engine.md). `stills`
frames, evenly spaced, are laid out on one sheet with their times and what it measures, and the sheets
are a sitting on the review page, one family an effect, with the choices `accept` and
`look`. The answer lands through `verdict.judge`.

## Held to a spec

An `*.accept.toml` bounds an effect's measures as it bounds a sound's, checked with
`accept.check` against the `.tscn` (see [measurements.md](measurements.md)):

```toml
asset = "spark_trail"

[[predicate]]
id = "budget"
measure = "alive"
max = 48

[[predicate]]
id = "reach"
measure = "reach"
min = 2.0
max = 4.0
```
