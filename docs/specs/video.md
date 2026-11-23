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

**A clip may be a file instead of a run** (§PW671). Dumont's narrated product video held
its title cards and cut its B-roll with some 600 lines of ffmpeg arguments of its own.
A `[[clip]]` names exactly one of `from`, `still` or `video`:

```toml
[[clip]]
still  = "art/card.png"                         # a picture, held for length
length = 3.0
motion = { zoom = [1.0, 1.15], pan = "left" }  # optional; pan none, left, right, up, down

[[clip]]
video  = "footage/broll.mp4"                    # a stretch of a video file
start  = 2.0
length = 3.0
```

A still is fitted to `size` and held, or, with `motion`, zoomed from the first factor to
the second (each 1 to 4) over its length while the frame pans across the room the zoom
leaves. A video file is cut from `start` for `length`, and one shorter than that is
`video.short-sequence`, read with ffprobe. A clip naming none or several of the three,
or a `motion` outside those words, is `video.bad-cut`; a file that is not there is
`video.no-source`. A file clip carries no sound into `clip_audio`. The record names each
file as an input, with the role `still` or `video`.

**A clip may name a stock file by its id** (§PW675), so a cut is rebuilt from its
declaration alone: `stock = { service = "pixabay", id = 123456, rendition = "medium" }`
in place of `video` (`height` instead of `rendition`, and `kind = "picture"` for a held
or moving still). Its copy lives under `[stock] dir` (`stock` by default) as
`<service>-<id>-<rendition>.mp4`, or `<service>-<id>.jpg` for a picture; `video.cut`
fetches it with `stock.fetch` where no copy is there and reuses the copy where it is, so
a rebuild downloads nothing it holds. A clip the service no longer has, with no copy on
disk, is `stock.gone`, never skipped, since a cut one shot short still renders and looks
finished; a `stock` that is not such a table is `video.bad-cut`. The cut's record names
each stock copy as an input with the role `stock`, so `provenance.credits all=true`
follows it to the service's licence and `provenance.dependents` on a copy finds the cuts
that carry it.

**A web page is filmed into a clip by `capture.web`** (§PW690), so a product video's
browser scenes come with the record of what was visited, and no project writes its own
recorder. The visit is a `*.web.toml`:

```toml
[web]
url      = "http://localhost:2710/"     # where it starts; a step's path joins it
viewport = [1920, 1080]                 # the clip's size, two whole numbers
out      = "video/scenes/install.webm"  # beside the visit as <name>.webm otherwise
timeout  = 15                           # seconds one step may take
allow    = ["/api/session"]             # what may fail: part of a URL or console text

[[step]]
go = "/console"                         # a path under url, or a whole URL
[[step]]
type = "#password"                      # with text, or secret naming an env variable
secret = "SHIO_PASSWORD"
[[step]]
click = "text=Install"
name  = "install"                       # the step's mark, answered under marks
[[step]]
wait  = "#review-queue"                 # a selector reaching a state, never seconds
state = "visible"                       # visible, hidden, attached or detached
[[step]]
scroll = 600                            # pixels; negative is up
[[step]]
hold = 2.0                              # seconds the camera stays, for the viewer
[[step]]
find = "The block editor is here."      # a sentence the page prints, brought mid-screen
within = "p, li, blockquote"            # where it is looked for (§PW721)
[[step]]
highlight = "The block editor is here." # one overlay box drawn over each of its lines
color = "rgba(255,200,40,.45)"          # seconds = 0.5, each line in turn
```

**A quoted sentence is found by its words** (§PW721). `find` looks for the sentence in
the first block of `within` (`p, li, blockquote, h1` to `h4`, `td, figcaption, dd` if
unset) whose text holds it, across its text nodes and links with whitespace folded, and
scrolls it to the middle of the viewport with the eased scroll below (`seconds`, or 200
px a second). `highlight` finds it the same way and draws one box per client rect of
its range, absolutely placed over the page with `pointer-events: none`, each growing
left to right over `seconds` in turn; the page's text is never changed. The camera waits
while the lines are drawn, so the step's `done` mark is when the highlight has landed.
A sentence the page does not print is `web.text-missing`, naming it, and the film stops
with nothing recorded.

`capture.web(source, out=, root=)` plays the steps in Playwright's Chromium while it
records, and writes the WebM, which a `[[clip]]` takes as `video = "<file>"`. Its record
(kind `capture`, engine `capture.web` with the browser's version) names the visit as an
input with the role `visit`, and keeps the URL, viewport, allow-list and every step with
the second it started (`at`) and ended (`done`) since the recording began. A browser
records in real time, so there is no `sequence.json`. A secret is kept by its variable's
name; its value is read only to type it, and reaches neither the record nor the answer.

**It is filmed the way a person moves** (§PW704). A headless browser draws no pointer,
jumps a scroll in one frame and fills a field at once, so a product scene never showed
what was clicked. `[web] pointer = true` adds a script before the page's own that draws
a pointer following the mouse, with a ring where a button goes down, and carries it to
the middle of each click and type target over 0.6 s along a minimum-jerk path
(`10t³ − 15t⁴ + 6t⁵`) at 30 frames a second, from wherever it last was. A `scroll` eases
over the step's `seconds` (its pixels at 200 a second, at least 0.2 s, where unset) in
thirty wheel turns a second along the same curve. A `type` clears the field and types at
the step's `pace` characters a second (12 where unset). `seconds` on any step but a
scroll, `pace` on any but a type, or either not above 0, is `web.bad-visit`; both are
kept on the step in the record.

A console error, an uncaught page error, a failed request, a response of 400 or above,
or an image that loaded no pixels (checked after every step) is `web.broken-page`, unless
an `allow` entry is part of its URL or message; nothing is kept. A step that does not
finish within `timeout` is `web.step-failed`, naming the step and what the browser said.
A key it does not take, a `url` not `http(s)`, no step, a step doing none or two things,
a `wait` given seconds, a secret the environment lacks or an `out` not `.webm` is
`web.bad-visit`, before a browser opens; a missing file is `web.no-source`. No
`playwright` package, or no Chromium for it, is `web.no-playwright`, whose remedy is
`pip install playwright` and `python -m playwright install chromium`.

**Each language is a sound track of its own** (§PW671). A narrated cut declares its
languages and lays each take where it is said:

```toml
[video]
music_loop = true                 # the bed loops under a cut longer than it

[[track]]
language = "eng"                  # one audio stream, tagged; title optional
[[voice]]
file  = "vo/en/intro.mp3"
at    = 0.5                       # seconds into the cut it starts
track = "eng"                     # the [[track]] it is laid on
gain  = 0.0                       # dB, optional

[[subtitles]]
file     = "subs/en.srt"
language = "eng"
```

With no `[[track]]` the cut has one sound, as above. With them, the bed (the music and,
with `clip_audio`, the runs' own sound) is laid under each track's voices, each track is
trimmed and faded with the picture and written as its own AAC stream tagged with its
language, and each subtitle file is carried as a `mov_text` stream. A voice on a
language no `[[track]]` declares, one starting past the cut's end, two tracks of one
language or a row with a key it does not take is `video.bad-cut`; a voice or subtitle
file that is not there is `video.no-source`. The answer names the `tracks`, the measures
add `audio_tracks` and `subtitle_tracks`, and the record names every voice and subtitle
file as an input.

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
| `video_loudness` | its sound's integrated loudness, LUFS |
| `video_true_peak` | its sound's true peak, dBTP |
| `video_audio_gap` | seconds between the picture stream's length and the sound's |
| `video_longest_frozen` | the longest stretch, in seconds, where no frame moves |
| `video_frozen_end` | seconds the picture holds still at its end |
| `video_longest_shot` | the longest stretch, in seconds, without a cut |

The last six hold an encoded video to a platform's bars (§PW697): a Short is 20 to 55 s,
-14 LUFS within 1, under -1 dBTP, its streams the same length within a frame, and a
frozen end card breaks its loop. Loudness and true peak are ffmpeg's EBU R128 meter
(`ebur128=peak=true`), read on every sound stream: `audio_streams` lists each with its
`stream` index, its `language` tag and its three sound measures, and the top-level
values are the first stream's. A spec bounding a sound measure on a video with several
streams reads the stream furthest past its bounds, and its `of` names that stream and
its language, so a failed multi-language cut says which track missed and by how much.
A silent video answers them as `null`, and a spec that bounds one is `video.no-audio`. A frame holds still where it moves no
more than `first_motion`'s threshold; a cut is a frame where more than 35% of the
picture changed by more than 6% at once, and a shot runs from one cut, or the start, to
the next, or the end.

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

## Burned-in text and a platform's controls

A vertical video's captions compete with the platform's buttons and title (§PW698).
`video.safe_area(subtitles, size=, preset=, safe=, exclude=, fonts=)` reads the `.ass`
file burned into the video: its `PlayResX`/`PlayResY`, its styles and every `Dialogue`
line. Each line is placed at `size` (the play size where none is given) from its
style's alignment and margins, or its `\pos` and `\an` overrides, sized by its style's
or `\fs` font size, `ScaleX` and `ScaleY`, and widened by outline and shadow; its width
is measured with the style's font as Pillow finds it, in `fonts` first, and the answer
names the fonts used, so Pillow's default font reads as an estimate.

The bounds are a preset's, as fractions of the frame scaled to `size`: `youtube-shorts`
excludes `buttons` (x 940..1080, y 900..1700 of 1080x1920) and `title` (the bottom
420 px), observed on 2026-11-12 and not a platform's specification; `none` excludes
nothing. `safe` (a box in px) and `exclude` (boxes in px by name) replace the preset's.
Each line that reaches past the safe box or into an excluded one is in `crossed` with
its number, `start`, `end`, text, `box` and each area it `crosses` with `by_px`;
`passed` is true where none does. A missing file, one with no `Dialogue`, or a bad
`size` is `video.bad-subtitles`.

## A thumbnail against its title and a feed

`store.thumbnail(picture, title, texts=, language=, max_words=6)` holds a video's
thumbnail to what a person checked by eye on the Scion video (§PW699). Its text is
`texts`, each a string or `{text, box: [l, t, r, b]}` from the layout that drew it, or,
where none is given, what tesseract reads (its TSV, words of confidence 60 and up,
grouped into lines with their boxes); with neither, the answer is unchecked, never
passed. `words` is counted against `max_words`. `shared` lists the meaningful words it
shares with the title: case and accents folded, punctuation dropped, numbers kept, the
language's stop words (en and pt) aside. At feed size (168x94, the picture scaled to fit)
each line with a box answers `height_px`, at least 8, and `contrast`, the ratio between
the mean relative luminance of the box's lighter and darker parts (split at the box's
mean), at least 3; a line without a box is `unmeasured`. `failed` says each miss in
words and `passed` is true where there is none. A missing picture is
`store.no-thumbnail`. Which thumbnail is better stays a person's choice.

`store.thumbnails(variants, title, keep=3, out=)` takes the variants the project's own
layout drew from its choices (which words, which picture, which number), each a path or
`{picture, texts}`, holds each to `store.thumbnail`, and lays the first `keep` that pass,
in the order given, as the family `thumbnail` of a sitting in `out` (else `[paths]
sittings`/thumbnails, else the work area's), where a person picks the ones to put to the
platform's A/B test. `rest` names each variant not laid and why: its failures, or that it
passed past the `keep` laid out. Where none passes, nothing is laid. polyweave draws no
thumbnail layout itself; the choices are the project's layout's, and the agent never picks.

## An HTML card as a still

A narrated video's editorial cards (dates, timelines, diagrams) are HTML a project
writes with its own fonts, and `video.cut` takes stills (§PW700).
`capture.card(html, out, viewport=[1920, 1080], scale=1, bounds=, safe=, exclude=,
allow=)` loads one local `.html` file in Chromium (Playwright, as `capture.web`) at the
viewport and device scale given, waits for `load` and for `document.fonts.ready`, and
writes the viewport as a PNG to `out`. A console error, a page error, a failed request or
a broken picture refuses it as `web.broken-page`, and nothing is written, unless
`allow` names it. The record (kind `capture`, engine `capture.card` with the browser's
version) has the page as its `card` input and each local file the page loaded (fonts,
pictures, styles under the project) as a `loaded` input. Each CSS selector in `bounds`
answers every element it matches with its `box` in CSS px and whether it is `visible`
(a size, not `display: none`, not hidden, opacity above 0); one that matches nothing is
in `missing`. Where `safe` or `exclude` is given, each element is held to them by the
check `video.safe_area` uses, and those that cross are in `crossed`. A missing card, an
`out` that is not `.png`, or a bad viewport is `web.bad-card`.

**A card is guarded and not rendered twice.** Each element `guard` (CSS selectors)
matches has its text checked as a viewer meets it: a letter lost to U+FFFD or a `?`
between two letters (`hist?ria`), text past its own box (scroll size over client size),
glyphs no loaded font has (`document.fonts.check` on its computed font, an
approximation), and any of `names` whose characters land on more than one line
(`WordPre`/`ss`). Elements with a fault are in `faults` with their selector, index,
text, box and faults; `guarded` counts what was checked, and a fault fails `passed`. A
render's key is the page's digest, every argument and the Playwright release (which
pins its Chromium); the record keeps the key and the answer. A call whose key matches
the record of the PNG already at `out`, where that PNG and every recorded input still
hash as recorded, starts no browser and answers the recorded answer with `cached` true.

## One report on an exported video

A finished video is checked without rebuilding it, in one report bound to its bytes
(§PW707). `video.measure(video, opening=3, out=)` answers the file's `sha256` and
`bytes`; every stream's `index`, `kind`, `codec`, `seconds` and `language`; everything
`video.measured` reads (the measures above, `audio_streams`, and `frozen`, each stretch
held still for 0.5 s or more as `[start, end]` seconds); the first decoded frame,
written as `<stem>.<first 12 of the hash>.first.png` in `out` (the work area's
`measured/` if unset) and named as `first_frame`; and `opening.frame_times`, the
presentation time of every video frame in the first `opening` seconds, as ffprobe reads
them. Nothing is re-encoded. The file is hashed again at the end, and one whose hash
moved while it was read is `video.changed`, so a report never describes two revisions.
Cadence and stillness are measured; whether they are wrong is the editor's call.

**A recording's pauses are held to a budget** (§PW707). `video.pauses(video, clips,
max_seconds=2, threshold=, side=160, cursor="moves", cursor_px=48)` decodes the video
once in grey `side` px across. Each clip is `{name, start, end, source_start, holds}`:
a stretch of the video from a screen recording that began `source_start` seconds into
its source, with reviewed `holds` in cut seconds. A frame is still where no more than
`threshold` of its pixels (`first_motion`'s 0.2% unless set) changed past the 6% step;
with `cursor = "still"`, one whose change fits a `cursor_px` box (scaled to `side`) is
still too, so a pointer alone does not hide a frozen page, while a drag across the page
moves. Each clip answers its `longest` still stretch with its `cut` and `source`
seconds and `within`, against `max_seconds`; a stretch wholly inside a hold is exempt.
The answer names the video's `sha256`, the threshold, the side and the cursor policy.
Nothing is trimmed. A clip without a `start` before its `end` is `video.bad-cut`.

## A review sheet, one still per beat

Before a full render a video is reviewed beat by beat, each shot beside what is said
over it (§PW708). `video.sheet(samples, out, title=)` takes records `{source, at,
label, words, captions, interval, tags, kind}`: `source` a video under the project,
sampled at exactly `at` seconds (`-i <video> -ss <at> -frames:v 1`), or a picture
(`.png`, `.jpg`, `.webp`), taken as it is; `words` the narration over the beat,
`captions` its production captions and highlights, `interval` the source stretch it came
from, `tags` its people, events and topics; `kind` `source` for a source's still or
`output` for the composited output's. It writes the stills numbered in order
(`001.png`, …) to `out`, an `index.html` that shows each with its labels, escaped, and
opens with no server (an output's card is outlined apart), and `sheet.json` listing the
same, recorded with every source as an input. A time a video has no frame at is shown
as missing and named in `missing`, never filled with another frame. A sample with no
source, an unknown key, an `at` below 0, or a `kind` not `source` or `output` is
`video.bad-sheet`.

## Editorial labels against each other and the footage

A caption and a spoken highlight can be on screen together with two versions of one
fact, and a highlight naming a person can sit over stock footage of someone else
(§PW709). `video.labels(labels, footage=)` is read-only over what the cut declares:
`labels`, each `{id, kind, text, start, end, entities, source, take, beat}`, and
`footage`, each stretch `{id, start, end, source, entities}`. Every two labels whose
times overlap are in `overlaps` with both labels, the overlap's `from` and `to`, and
`same`: `duplicate` where their words agree with case, accents and punctuation folded,
`versions` where they differ. A label naming `entities` is held to each stretch of
footage it overlaps, and one the stretch does not declare is in `unverified` with the
label and the stretch (`footage` null where no stretch is under it). Nothing is
inferred from a picture: the report compares declarations and accepts no semantic
correspondence. A record that is not a table, an unknown key, a `start` not before its
`end`, or `entities` not a list is `video.bad-labels`.

## The product instance a visit films

A product scene is filmed on a clean instance, and every retake repeated Docker and
seed commands by hand (§PW710). A `*.instance.toml` declares it: `[instance]` with
`compose` (the Compose file, under the project), `project` (the Compose project, in
letters, digits, `-` and `_`, the only one ever touched), `ready` (a URL that answers
below 500 once the product is up) and `ready_seconds` (120 unless set), and `[[seed]]`
steps, each a `service` of that project and a `run` argv executed in it in order.
`capture.instance(fixture, action=)` is the only thing that changes an instance, and
only when called: `plan` answers the docker calls of `up`, `reset` and `down` and runs
none; `up` is `compose -p <project> -f <file> up --detach --wait` then the seeds as
`exec -T`; `reset` is `down --volumes --remove-orphans` of that project first; both wait
for `ready`; `down` stops it; `status` reads its containers. Every call names the
project and its file, so a container, volume or network it does not own is never
touched. A visit with `[web] instance = "<fixture>"` waits for the instance to be
ready, refuses one that is not (`web.instance-not-ready`), never resets it, and records
`params.instance`: the fixture, the project and each running container's service, id,
image and state, with the fixture and the Compose file as inputs. A bad fixture is
`web.bad-instance`, no docker is `web.no-docker`, and a failed docker call is
`web.instance-failed` with what docker said.

## A description from the credits

A platform bounds a video's description (YouTube at 5,000 characters), and listing
every credit whole ran one to 15,791 (§PW711). `store.description(files, summary=,
chapters=, limit=5000, out=)` writes it from the records of the files the video uses:
the summary, then the chapters as `M:SS Title` (`H:MM:SS` past an hour; the first at 0
and each later one later, else `store.bad-chapters`), then `Credits:`. A file whose
record carries a `credit`, an attribution its licence requires, has it kept whole; the
others are grouped as `<service> (<licence>): <authors>`, each author once, the licence
the record's or the one `provenance.credits` resolves through what the file was made
from. YouTube watch URLs become `youtu.be` links. A file whose licence nothing states is
named in `unstated` and left out, never given one, and a file with no record is in
`unrecorded`. A text past `limit` is `store.description-long`, saying how much of it is
required credit; nothing is cut. With `out` the text is written there.

## Every finding of a cut, before it renders

A missing anchor or a bad source found mid-build wasted a whole render (§PW712).
`video.check(source)` reads a `*.cut.toml` as `video.cut` does, each part on its own,
and answers every finding at once: the `[video]` table (unknown keys, size, `fps`,
`fade_out`, music), each `[[clip]]` (its source, and its stretch against what the run
or file holds, as ffprobe reads it), whether `fade_out` covers the whole cut, and the
voices and subtitles. Each finding has its `code`, `message`, `remedy` and `at`
(`video`, `clip[n]`, `voice`); a failing part never stops the next from being read.
Nothing renders, is fetched or is bought: a stock clip with no copy under `[stock] dir`
is `video.unfetched`, where a build would fetch it. `passed` is true with no finding.

**A source's reuse is held to declared limits** (§PW712). A cut may declare
`[repetition]`: `max_overlap` (seconds two uses of one source may share), `max_screen`
(seconds one source may hold the screen), `min_gap` (the least seconds between its
uses in the cut), `adjacent = false` (no two of its clips back to back), and
`exceptions`, each `{source, why}`, a why required, for a continuous tutorial or
navigation. Clips are one source where their files hash alike, so a copy under another
name is the same footage; a clip's place in the cut follows the ones before it, less
their fades. `video.check` reports each limit passed as `video.repeated`, naming the
clips and the file, and never replaces footage or reads an activity from a filename.
Every limit is off where unset.

## One interval of a cut, for a review

Checking one action of a finished cut meant exporting it whole (§PW713).
`video.cut(source, interval=[start, end], context=)` renders only those seconds of the
cut, `context` wider each side and held inside it, through the very graph a whole cut
uses: the same clips, fit, fades, voices, music and mix, so a short excerpt is never
mixed or normalised on its own, and a voice or subtitle keeps its time relative to the
picture. The output seeks to the window after the graph (`-ss <start> -to <end>`),
written to `<name>.preview-<start>-<end>.mp4` unless `out` says otherwise. The answer's
`interval` gives the seconds `asked`, those `rendered`, and the `offset` a time in the
preview adds to be the cut's; the record keeps the window. An interval that is not two
seconds inside the cut, start before end, is `video.bad-cut`. Every clip before the
window is still decoded on the way to it. `around` names the window by what is in it in
place of seconds: `clip[n]` is the n-th clip's seconds in the cut (from where its fade
begins), `voice[n]` the n-th voice line's, from its `at` for as long as its file runs; a
place the cut does not have is `video.bad-cut`.

## Fetched media and the ranges a person accepted (§PW714)

A `*.library.toml` holds one `[[source]]` per fetched file: `file`, its `sha256`,
`seconds`, and the `licence`, `page` and `author` its provenance record names, all
written by `video.library add=<file>`, which adds a file as `rights = "unreviewed"` and
decides nothing. A person sets `rights` to `cleared` or `refused` with `rights_by`, may
add `tags` (people and events they confirmed), and records each decision as a
`[[source.range]]`: `start` and `end` in seconds (both left out: the whole file),
`verdict` `accepted` or `rejected`, `reason`, `by` and `on`. A range missing any of
verdict, reason, by or on is `video.bad-library`. Adding a file already held answers its
entry as `held`, rejected ranges included, and appends nothing.

A cut naming `[video] library` shows a `video` or `still` clip (a stock clip by its
copy) only where the source's rights are `cleared`, its stretch lies inside one accepted
range (a still's needs a whole-file range) and touches no rejected one; otherwise
`video.unapproved`. A file gone or whose SHA-256 moved since is
`video.library-changed`. Captured runs are not catalogued. The cut's record carries
`library` and `approved`, one entry per file clip with the range, `by`, `on`, `reason`
and the source's tags. `video.check` reports each clip's refusal as its own finding.
## A narration's claims and their evidence (§PW716)

A `*.claims.toml` beside a cut holds one `[[claim]]` per thing the narration asserts:
`id`, `says`, `kind` (`fact`, `statistic`, `conclusion` or `footage`), its anchor
(`voice = n`, the cut's n-th voice line, with `words` it rests on; footage `clip = n`),
`source` with `excerpt` and `retrieved_on`, or a `note`, and dates: a fact's
`happened_on`; a statistic's `published_on` and `review_by`; footage's `happened_on`
(what it depicts) and `published_on` (the footage's own date), kept apart so a later
demonstration never dates an earlier event. Anything missing is `video.bad-claims`.

A `[claim.review]` is a person's: `by`, `on`, `verdict` (`approved` or `rejected`) and
the `fingerprint` they reviewed. `video.claims path cut` answers each claim in the cut's
order with `at` (the voice line's `at` plus the words' start in its `<file>.words.json`,
when that file's SHA-256 matches; the clip's start for footage), its fingerprint (its
own fields and the SHA-256 of the line or clip it is anchored in) and `status`:
`approved`, `unreviewed`, `rejected`, `stale` (fingerprint moved since the review),
`expired` (`review_by` past) or `unanchored` (its place or words not found). `out`
writes a Markdown page for the review. `citations` lists the approved claims' URL
sources, which `store.description cited` keeps whole under Sources, inside its limit.