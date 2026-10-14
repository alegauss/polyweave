# A teaser cut from captures

Binds **PW429**.

A store page wants a short teaser: several stretches of play from different runs, cut
together at stated lengths, with the game's music under them, encoded at 1920 by 1080 as
H.264 in an MP4, and opening on play within a few seconds. `capture.movie` already keeps
every frame between two marks a script prints; `video.cut` takes those runs the rest of
the way, from a declared edit, so the project never drives ffmpeg itself.

## The file

```toml
[video]
out        = "store/teaser.mp4"   # where it is written; the call's `out` wins, and
                                  # beside the cut as <name>.mp4 where neither says
size       = [1920, 1080]         # two even numbers; each clip fitted inside, centred
                                  # on black
fps        = 30
music      = "audio/theme.ogg"    # the sound beneath, optional
music_from = 0.0                  # seconds into it the teaser starts
music_gain = 0.0                  # dB
clip_audio = false                # each run's own audio.wav mixed in under the music
fade_out   = 1.0                  # seconds the end fades to black and silence

[[clip]]
from    = ".polyweave/teaser/fight"   # a folder capture.movie wrote, or its sequence.json
start   = 1.0                         # seconds into that run
length  = 4.0                         # seconds held
fade_in = 0.0                         # seconds it crossfades from the clip before; 0 cuts
```

A run is read at the rate its `sequence.json` gives, so `start` and `length` are seconds
of play whatever the capture's rate. A key the file does not have, a size that is not two
even numbers, a cut with no `[[clip]]`, a clip with no `from` or `length`, a first clip
that fades in, a `fade_in` as long as either clip it joins, a `fade_out` as long as the
teaser, or music that is not there is `video.bad-cut`. A `from` holding no
`sequence.json` is `video.no-sequence`, and a clip asking past the end of its run is
`video.short-sequence`, both before anything is encoded. A missing or unparseable file is
`video.no-source`.

## Building

`video.cut(source, out=, root=)` makes one ffmpeg call: each clip trimmed from its run,
brought to `fps`, scaled to fit `size` and padded on black; joined in order by a cut, or by
`xfade` over `fade_in`, which overlaps the two by that much, so the teaser is the sum of the
lengths less the sum of the fades. The music is trimmed to that length at `music_gain`;
with `clip_audio`, each run's `audio.wav` is cut to the same stretch and laid at its
clip's place on the timeline, mixed under the music without normalising. `fade_out` fades
the picture and the sound together. It is encoded with libx264 at CRF 18, yuv420p, AAC at
192 kb/s and 48 kHz stereo, with the index at the front (`+faststart`) so a store's player
starts it before it has all arrived. No ffmpeg or ffprobe on PATH is `video.no-ffmpeg`;
ffmpeg failing is `video.encode-failed`, its own words in the detail.

The answer gives the `file`, what it measures (below), `audio` (whether it carries
sound), and a `sheet`: eight stills evenly over its length, four to a row, each with its
time, written beside it as `<name>.sheet.png`, which is what a sitting lays out for a
person while the file itself is watched. Its record (kind `capture`, engine `video.cut`)
names every run's `sequence.json` and the music as inputs, the cut file in its params,
and the measures.

## Measures

Read off the file written, not the declaration, so a spec holds what a viewer gets:

| Measure | What it is |
|---|---|
| `video_seconds` | its length |
| `video_width`, `video_height` | its size in pixels |
| `video_fps` | its frames a second |
| `first_motion` | seconds before one frame first differs from the one before it |

`first_motion` reads every frame in grey at 160 across, and a frame moves where more than
0.2% of its pixels changed by more than 6% of full scale from the frame before: the
encoder's noise on a still title or a held black stays under both, and one small thing
crossing the screen does not. A teaser that never moves answers its whole length. A spec
bounds them as it bounds a picture's, with the MP4 as its subject or `of`; a path with no
video there, or a file ffprobe cannot read, is `video.unreadable`:

```toml
asset = "teaser"

[[predicate]]
id = "store-length"
measure = "video_seconds"
min = 25
max = 30

[[predicate]]
id = "plays-at-once"
measure = "first_motion"
max = 3
```

Whether it is a good teaser is a person's call, made at a sitting on its sheet with the
file beside it.
