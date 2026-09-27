# Driving a running game

An agent's turn takes seconds and a game runs at sixty frames a second, so a game left
running between two calls has moved on before the second one arrives, and no sequence of
calls could be replayed. The driver holds a game still and moves it only when told to,
by a counted number of frames, and answers what an agent asks about it (§PW212). The
session tools (PW213), a kept flow (PW214) and the release check (PW215) all read this
contract, which is why it is written before them.

## What it is, and how it starts

The driver is `addons/polyweave_driver/driver.gd`, installed by `godot.install(project,
addon="polyweave_driver")`. It is a `SceneTree` script, not an autoload: the engine runner
launches it with `--script res://addons/polyweave_driver/driver.gd`, and it loads the
project's own main scene (`application/run/main_scene`) under the root itself. So a
project installs a folder and edits nothing — no autoload, no feature tag in
`project.godot` — and a normal launch of the game never loads the driver at all. The
project's autoloads still load, as they do for any `--script` run.

User arguments after `--`:

| Argument | Meaning |
|---|---|
| `--port=N` | the loopback port to listen on; `0`, the default, lets the system choose |
| `--seed=N` | `seed(N)` before the main scene loads, so the global random functions repeat |
| `--scene=res://…` | load this scene instead of the main one |
| `--idle=N` | quit after N seconds with no request; `0`, the default, waits for ever |
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
| `input` | `action`; or `key`; or `click` with `path` or `at` | Queues a press then a release, delivered through `Viewport.push_input` when the next frame passes — so a signal the input causes fires inside the `step` or `wait` that follows, where a wait armed for it sees it. A click moves the pointer there first, since a Button fires only while hovered. `click` at a node aims at its centre on screen (a Control's rect, a Node2D's position, through its canvas transform); `at` is a point in the viewport. `result` says where a click lands |
| `step` | `frames` (default 1) | Lets that many frames pass, then holds |
| `wait` | `frames` budget, and one of `signal` + `path`, `node` (a path or group that must exist), or `path` + `property` + `equals` | Lets frames pass until the condition holds or the budget is spent; `result` is `{met, frames}`. An unmet wait is `ok` with `met: false` — the budget ran out, which is an answer and not an error |
| `call` | `path`, `method`, optional `args` | Calls a method the game exposes for setup, and returns its value. An awaited coroutine is not waited on; a caller that needs it done follows with `wait` |
| `shot` | `out` | Saves the viewport as a PNG at that path and returns it with its size. A headless run draws nothing, so a shot there is refused (`driver.no-picture`) rather than saved blank |
| `close` | — | Answers, then quits |

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
- `game.close` ends the game and says whether it ended.

Every answer carries `frame` and `errors`: the lines the engine printed since the last
call that match the runner's error pattern, so a script error mid-flow is reported by the
call that caused it. A driver refusal is raised under its own `driver.*` code. The game
quits by itself after `[driving] idle` seconds with no call (600 by default), so a session
an agent forgot never outlives the conversation; a call to it after that is `game.gone`.

    python -m polyweave game.open --root . --seed 7
    python -m polyweave game.input --session g1a2b3c4d --click UI/Play
    python -m polyweave game.wait --session g1a2b3c4d --path . --prop level --equals 1 --frames 120

A number arrives as JSON gives it, a float, so `wait … equals` compares numbers as
numbers: a node's int 42 equals the 42 a caller sent.
