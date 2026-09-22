# Driving the engine

Binds **PW22**, and is where the rest of Block E's contract will go.

## The exit code is not the verdict

Godot's exit code cannot be trusted. It exits **zero after a script error** and **non-zero
after a clean quit**, and a script that does not compile never reaches `quit()` at all, so
the engine sits in its main loop until something outside it intervenes. Every project that
drives the engine ends up writing the same wrapper around those three facts.

The honest verdict has three parts, and all three are needed:

1. **the line the script printed** — the one thing that only runs if the script got there;
2. **no error anywhere in the output** — an error inside one block can abort it quietly;
3. **the file it claims to have written exists** — a script can print its line before the
   write finishes, or write somewhere other than where it said.

A run reports `ok` only when all three hold. `exit_code` is recorded, because it is
evidence, and it is never the answer.

## The success line belongs to the caller

What the script prints when it worked is a project's own convention, so it is an argument:
a pattern whose **named groups come back in the result**, and whose names may be declared
as `produces` to mean "this group is a path that has to exist". That is what makes one
runner serve a capture, a test and a measurement run — they are the same problem with a
different line at the end.

**The error pattern is the engine's**, not the project's, and is the one thing compiled in:
`SCRIPT ERROR`, `Parse Error`, `Compile Error`, and `String formatting error`, which prints
without the word SCRIPT and still aborts the block it is in. A caller may widen it; nothing
requires it to.

Each error comes back with **the line of the script it came from**, as the engine printed
it, and the line of the output it was on. The first says where to fix it; the second says
where to look in the log.

## The bounds are part of the contract

Both are set on every run, because they catch different failures. The **frame budget**
(`--quit-after`, `[engine] frames`) ends a script the engine would otherwise loop in
forever. The **wall clock** (`[engine] timeout`) ends a run that never reaches a frame at
all. A capture settles in a few dozen frames, so a run still going after several thousand
is hung, and saying so is better than sitting there.

**Frames elapsed are reported only where the script printed them.** Inferring a frame count
from how the process ended is a guess, and a guess inside a verdict is the thing this
exists to remove. `bounded` is therefore true in exactly two cases that can be told apart:
the wall clock fired, or the script said how far it got and got all the way to the budget.

## What a run leaves behind

Everything the run printed is written under `[paths] work`, and the refusal names that
file. "The capture failed" is not actionable; a file somebody can open is. The result also
carries the command that was run, so a failure can be reproduced by hand without
reconstructing it.

`run` reports and never raises on a failed run — the verdict is the answer. `require` is
the same run as a gate, and each verdict has exactly one code it closes with, so a gate
never invents one.

## Real pixels with nobody watching

Godot's headless mode runs on a **dummy renderer that draws nothing**, so any capture
needing real pixels needs a real one — which is why every visual check lands on a
developer's desk and never in a gate, and why Block B's comparisons cannot be enforced.

**The engine states the problem itself.** `--help` on 4.7.1 lists the display drivers as
`"windows" ("vulkan", "d3d12", "opengl3", "opengl3_angle", "dummy")` and
`"headless" ("dummy")`. The headless display driver offers the dummy rendering driver and
nothing else; asking for `--display-driver headless --rendering-driver vulkan` does not
change it, and the read back comes out of `dummy/storage/texture_storage.h` with no image.
Measured, not assumed — `headless` is one of the routes here precisely so that it can be
shown not to draw.

**What works is a real display driver plus a viewport texture read back inside the
engine**, rather than a picture grabbed off a window. Nothing about the window's contents,
focus or visibility is involved, so the window can be minimised or moved off the desktop
and the capture is byte-identical. All four of the platform's rendering drivers produce
the same pixels; the rendering driver is therefore not the variable, and the display
driver is.

What that still needs is a **display server**: an interactive session on Windows, an X or
Wayland server elsewhere. On a machine with no screen at all that is what `xvfb-run`
supplies, which is why the virtual display is a route and not a footnote.

**A route is available only where it has been proved available.** `routes` writes a
throwaway Godot project of its own — so what is probed is the machine and not a project —
renders one known colour through each candidate, and reads the pixel back off disk. A
route that draws is a route whose picture was looked at. The answer is kept under
`[paths] work`, because a probe is a second or two per route and it changes only when the
machine does.

`capture` takes the caller's script and whichever route draws here, and records which one
it was, so a picture can be traced back to how it was taken. Where none draws, the refusal
(`engine.no-offscreen-route`) carries what each route was tried with and why it failed.

**Moving the window is the script's own line.** A route passes its wish as a user argument
after `--`; a capture script that honours it puts its window out of the way, and one that
ignores it still captures, with a window visible while it does. Nothing here reaches into
the running engine from outside to move it.

## Units are a contract, not a coincidence

Cottony's board tray renders at one unit per pixel because somebody set the render
rectangle to exactly the world rectangle the board covers, so its wells land on a cell
size the game holds separately as its own constant. **The two numbers agree because a
person made them agree.** Nothing fails if either moves; the sprite lands a few pixels off
the grid and someone notices later, on a screen, by eye.

Declared, it is arithmetic. The **asset** states the world rectangle it covers and the
pixels per unit it is baked at, which give the size in pixels it must be. The **engine**
states its own pixels per unit. A **check** compares them, and a disagreement is a refusal
**with both numbers in it** — `units.mismatch` when the two scales differ,
`units.wrong-size` when the picture is not the size the declaration asks for, and
`units.not-whole` when the rectangle and the scale land between two pixels, which is a
sprite that cannot sit on the grid whatever else is right.

**The engine's number is read from where the engine keeps it.** `[units] source` is
`path/to/file.gd:NAME`, read out of a GDScript constant, a JSON key or an ini-shaped one.
Stating the number in `polyweave.toml` instead (`[units] pixels_per_unit`) is the weaker
half of the same idea, because a copy that can drift is the coincidence this exists to
remove. Where the constant is renamed or moved, that is `units.unreadable` — the check
doing its job, not failing at it.

**The check happens before the render, not after.** A scale that disagrees costs nothing to
refuse, and the refusal is more useful than the same refusal with a render's worth of time
spent behind it. `render.bake` takes `covers` and `pixels_per_unit`, checks them against
the project's scale and against the size the rung will produce, and carries both into the
provenance record and the answer. A bake that declares nothing is not asked about scale,
because most renders are a preview of a thing rather than a sprite on somebody's grid.

What is not here is a bake whose size comes *from* the declaration rather than from the
rung: the renderer produces square pictures at a rung's size, and a rectangle needs both a
non-square render and the size in the cache key. That is PW47.

## Still to come in this block

The declared environment a capture is taken in (PW25).
