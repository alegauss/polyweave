# Shipped Ledger

## Block A — What a tool call costs the turn

- ✅ **PW1** **an operation that takes minutes holds the turn, and nothing reports progress until it ends** — Long work returns a handle at once; poll names the stage it reached, result the artefact or the typed failure, cancel the whole process tree (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW2** **a tool reports success on an empty result, so the failure is found a render later** — Every operation asserts its own output before returning, and an empty boolean, a blank render or a short download is an error naming what failed (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW3** **a tool's parameters are learned by reading the source that implements them** — One call returns an operation's parameters with type, range, default and a sentence, read from the signature; another says what this machine can do (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW4** **a failure arrives as a stack trace, so the fix is guessed from the frame that raised it** — Every code is declared with what it means and what produces it, explain answers any of them, and a code the table lacks cannot be raised (design recorded in `docs/specs/tool-surface.md`).

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

