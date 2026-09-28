# Driving a running game

An agent's turn takes seconds and a game runs at sixty frames a second, so a game left
running between two calls has moved on before the second one arrives, and no sequence of
calls could be replayed. The driver holds a game still and moves it only when told to,
by a counted number of frames, and answers what an agent asks about it (§PW212). The
session tools (PW213), a kept flow (PW214) and the release check (PW215) all read this
contract, which is why it is written before them.

## What it is, and how it starts

The driver is `addons/polyweave_driver/driver.gd`. It is a `SceneTree` script, not an
autoload: the engine runner launches it with `--script`, and it loads the project's own
main scene (`application/run/main_scene`) under the root itself. **A project need install
nothing** (§PW216): the engine runs a script from outside the project, so where a game
has no `addons/polyweave_driver/`, the copy polyweave carries is launched by its own path,
and driving the game writes nothing into its tree beyond `.polyweave/`. A project that
wants its own pinned copy installs it with `godot.install(project,
addon="polyweave_driver")`, and that copy is the one that runs. Either way no autoload
and no feature tag is involved, and a normal launch of the game never loads the driver.
The project's autoloads still load, as they do for any `--script` run.

User arguments after `--`:

| Argument | Meaning |
|---|---|
| `--port=N` | the loopback port to listen on; `0`, the default, lets the system choose |
| `--seed=N` | `seed(N)` before the main scene loads, so the global random functions repeat |
| `--scene=res://…` | load this scene instead of the main one |
| `--idle=N` | quit after N seconds with no request; `0`, the default, waits for ever |
| `--flow=<path>` | replay a kept flow instead of listening; see "A flow kept as a test" |
| `offscreen`, `minimized` | the offscreen route's wish for a real window: moved off the desktop, or minimised |

It prints one line once it listens, and nothing is sent before it:

    polyweave_driver: port=53817 token=9f2c…e1

The port is the one actually bound and the token is sixteen random bytes in hex. The
driver binds `127.0.0.1` only.

## How the game is held

**The main loop blocks between commands; the tree is never paused to hold it.** The
driver reads its socket from its own `_process`, which the engine calls before any node
processes that frame, and it does not return until a command asks for frames. While it
waits, no frame passes, so nothing in the game moves — a tween, a timer, a coroutine
awaiting `process_frame`, the physics. Pausing the tree is not the same: a paused tree
still emits `process_frame`, and Cottony's board, which awaits it after every fall, ended
each move a frame early while a spike held it paused (§PW211). The game's own
`SceneTree.paused` is left to the game.

**A headless run is sized as the project says.** Headless, the root window is 64 by 64
whatever `project.godot` declares, and a pointer outside it hovers nothing, so a Button
takes a click and never fires. On its first frame the driver gives the root the declared
`display/window/size/viewport_width` and `viewport_height` (Godot's 1152 by 648 where
none is declared), and a click beyond them is refused as `driver.off-screen` rather than
sent into nothing.

**A real-time game holds too** (§PW216). Starship, a shooter whose enemies spawn on
timers and whose ship moves under `_physics_process`, was driven into its first phase
with fire and a direction held for 720 frames, and kept as a flow of 24 steps expecting
its score, its ship's lives and shields and its wave at three points. The session, with
seconds of wall clock between calls, and ten replays with none, all agreed: every replay
ended on frame 732 with the same values. At `--fixed-fps` the physics ticks once a frame,
and a game drawing from its own seeded generators repeats as long as its seed does.

**A driven game has a user folder of its own** (§PW217). Godot puts `user://` under the
platform's per-user data folder, so a game driven there would read the person's own save
— which level they reached, which settings they chose — and write over it. `game.open`
and `game.replay` launch it with `APPDATA` and `XDG_DATA_HOME` pointed at an empty folder
under `.polyweave/driving/`, so every session and every replay starts from a fresh save
and never touches the person's.

A frame only passes inside `step` and `wait`, so the same commands give the same game:
PW211 drove Cottony from its splash to a won level ten times and every run ended on the
same frame and the same board. Randomness the game draws from its own generator is the
game's to seed, through `call`; `--seed` covers the global functions only.

## The protocol

One TCP connection, one JSON object per line each way. A request carries the token, an
`id` it chooses and a `cmd`; the answer carries the same `id`:

    {"token": "9f2c…e1", "id": 1, "cmd": "query", "path": "/root/Game/Title"}
    {"id": 1, "ok": true, "frame": 0, "result": {…}}

A refused command answers `"ok": false` with `"error"` (a code) and `"message"`, and the
game is still held. A request whose token is wrong is answered with `driver.bad-token`
and the driver quits. A connection may close and another open, the game held between
them; the driver quits on `close`, or after `--idle=N` seconds with no request.

`frame` in every answer is the number of frames the driver has let pass since start.

### The commands

| `cmd` | Fields | What it does, and what `result` is |
|---|---|---|
| `query` | `path`, or `group`, or `class`; optional `properties` | The nodes found, each `{path, class, properties}`. A path is absolute from `/root` or relative to the main scene. Without `properties`: `name`, `visible`, `position`, `text` and `disabled` where the node has them |
| `input` | `action` or `key`, with `hold` or `release`; or `click` with `path` or `at` | Queued, and delivered when the next frames pass — so a signal the input causes fires inside the `step` or `wait` that follows, where a wait armed for it sees it. An action or a key goes through `Input.parse_input_event`, which is what a game polling `Input.is_action_pressed` reads; a tap presses on one frame and releases on the next, so `is_action_just_pressed` sees it once; `hold` sends only the press, kept down across frames until a `release` (§PW216). A click goes through `Viewport.push_input`, moving the pointer there first, since a Button fires only while hovered; `click` at a node aims at its centre on screen (a Control's rect, a Node2D's position, through its canvas transform), and `at` is a point in the viewport. `result` says where a click lands |
| `step` | `frames` (default 1) | Lets that many frames pass, then holds |
| `wait` | `frames` budget, and one of `signal` + `path`, `node` (a path or group that must exist), or `path` + `property` + `equals` | Lets frames pass until the condition holds or the budget is spent; `result` is `{met, frames}`. An unmet wait is `ok` with `met: false` — the budget ran out, which is an answer and not an error |
| `call` | `path`, `method`, optional `args` | Calls a method the game exposes for setup, and returns its value. An awaited coroutine is not waited on; a caller that needs it done follows with `wait` |
| `shot` | `out` | Saves the viewport as a PNG at that path and returns it with its size. A headless run draws nothing, so a shot there is refused (`driver.no-picture`) rather than saved blank |
| `expect` | `path`, `property`, `equals` | Whether the property holds the value now, no frame passing: `{held, value}` |
| `set` | `path`, `property`, `value` | Sets a property for setup, a nested one written `rng:seed` (Godot's `set_indexed`), and answers `{was, now}`; an int stays an int though JSON sends a float. How a flow seeds a generator the game made itself, which `--seed` does not reach (§PW217) |
| `selector` | `path`, or any target | The selector that picks this one node out now, `{select}`, or `select: null` where none does |
| `close` | — | Answers, then quits |

**A node may be named by what it is** (§PW270). Wherever a command takes `path` it also
takes `select`, as `click` does inside it: `{"class": <engine class or script
class_name>, <property>: <value>, ...}`, every node of the class whose properties hold
those values. A generated name such as `@Node2D@14` is renumbered by any node added ahead
of it; what a node is holds. `selector` finds one: the class alone where it is unique,
then `name`, `text`, `title`, `tooltip_text` and `placeholder_text` added in that order
until it is.

Values cross as JSON: a `Vector2` is `[x, y]`, a `Color` `[r, g, b, a]`, a node its path,
and any other object its class name. A property a node lacks is left out of its answer
rather than answered as null.

### Codes

| Code | When |
|---|---|
| `driver.bad-token` | the token does not match the one printed |
| `driver.bad-command` | an unknown `cmd`, or a field it needs is missing |
| `driver.no-node` | a path, group or class that finds nothing |
| `driver.no-method` | a `call` to a method the node does not have |
| `driver.no-picture` | a `shot` in a run that renders nothing |
| `driver.off-screen` | a click outside the viewport, where nothing can be hovered |

## The session tools

An agent reaches the driver through the `game.*` operations (§PW213), over MCP or from a
terminal, where every call is a process of its own. So a session is a file,
`.polyweave/driving/<session>.json`, naming the game's process, port and token, and each
call connects, sends one command and reads one answer; the driver keeps the game held
between connections.

- `game.open` launches the project headless (or through the offscreen route with
  `display`, so `game.shot` has pixels), waits for the driver's line, and answers the
  `session`.
- `game.query`, `game.input`, `game.step`, `game.wait`, `game.call` and `game.shot` each
  forward one command. `game.query` takes one of `path`, `group` and `of_class`;
  `game.wait` takes `prop` and `equals` (a JSON value), a `signal`, or a `node`.
- `game.batch` sends a list of commands in one call, each as the driver takes it
  (`{"cmd": "input", "click": {"path": "UI/Play"}}`), answering each with its `step`
  (§PW271). From a terminal every call is a process, and a match-3 level's loop of
  query, tap and wait cost hundreds of them; a batch costs one. Each command is
  journalled as its own tool's would be, so `game.keep` keeps it the same way. The first
  refusal stops the batch and is answered in its place (`stopped` is its index), unless
  `keep_going`. A flow that starts deep in a game reaches it with a `call` to a method
  the game exposes for setup, such as starting a level, rather than winning the ones
  before it; where a game has none, `driver.no-method` says so, and adding one is the
  game's change.
- `game.close` ends the game and says whether it ended.

Every answer carries `frame` and `errors`: the lines the engine printed since the last
call that match the runner's error pattern, so a script error mid-flow is reported by the
call that caused it. A driver refusal is raised under its own `driver.*` code. The game
quits by itself after `[driving] idle` seconds with no call (600 by default), so a session
an agent forgot never outlives the conversation; a call to it after that is `game.gone`.

    python -m polyweave game.open --root . --seed 7
    python -m polyweave game.input --session g1a2b3c4d --click UI/Play
    python -m polyweave game.wait --session g1a2b3c4d --path . --prop level --equals 1 --frames 120

## A release checked for the driver

A listener that runs any method it is asked to is a way into a game, so its absence from
a player's build is checked, not assumed (§PW215). `game.release_check` reads and spends
nothing and never edits a preset; each finding names where it is and what to change:

| Code | What it finds |
|---|---|
| `game.driver-exported` | a preset in `export_presets.cfg` that would ship `addons/polyweave_driver/`: `all_resources` with no `exclude_filter` covering it, or an `include_filter` pulling it in |
| `game.driver-autoloaded` | an autoload in `project.godot` naming the driver, which would load it in every run |
| `game.driver-in-pack` | an exported `.pck`, given as `pack`, holding the addon's paths |
| `game.pack-unread` | a pack whose directory is encrypted, so it cannot be looked into — named, not passed |

With `strict` it is a gate: the first finding is refused under its own code, the rest in
the detail, so a project puts it in its own release script. The fix is always the same
one line, `"addons/polyweave_driver/*"` in the preset's `exclude_filter`, and the person
who owns the release makes it.

## A flow kept as a test

A session is exploring; a flow is the part of it worth running again, with no agent
(§PW214). Every answered command is journalled in the session, and each answer's `step`
is its place in that journal. `game.keep` writes the journal as a flow file — JSON, since
the driver reads it inside the game — and nothing goes in on its own, because a session
includes wrong turns:

- inputs, steps and calls are kept in order, and those named in `drop` left out;
- a query is kept only where `expect` names its step, as one `expect` per property it
  answered: that node's property must hold that value again at that point;
- a wait is kept as a wait that must be met, where it was met in the session;
- a shot is left out, since a replay draws nothing;
- a generated path, one holding an `@`, is written as the selector the driver found for
  it when the command ran, while the node was there, so the flow survives a node added
  ahead of it; one no selector picked out stays a path and is named in `fragile`.

```json
{"format": 1, "proves": "a click on PRESS counts one press", "seed": 3, "scene": "",
 "engine": "4.7.stable.official", "driver": "<sha256 of driver.gd>",
 "steps": [{"cmd": "input", "click": {"path": "UI/Press"}}, {"cmd": "step", "frames": 3},
           {"cmd": "expect", "path": "/root/Main", "property": "presses", "equals": 1}]}
```

`game.replay` runs a flow in one launch through the engine runner, the driver reading it
with `--flow=<path>` rather than a socket, as fast as the engine goes. It ends on one line,
`polyweave_flow: passed steps=N frame=F`, or `polyweave_flow: failed step=S frame=F
why=…` at the first refusal, unmet wait or expectation that did not hold. Its answer
carries `ok`, the failed step, the frame and the reason, and `differs` where the engine
version or the driver changed since the flow was kept — reported, not failed, since a
different engine is a reason to look and not a verdict. `expect` is a command of its own
too, answering `{held, value}` with no frame passing.

A number arrives as JSON gives it, a float, so `wait … equals` compares numbers as
numbers: a node's int 42 equals the 42 a caller sent.
