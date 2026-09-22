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

## Still to come in this block

Pixels without a screen (PW23), the declared environment a capture is taken in (PW25), and
the unit contract between a baked sprite and the running game (PW24).
