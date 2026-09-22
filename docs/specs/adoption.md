# Adoption

Binds **PW35**, and is where the rest of Block H's contract will go.

## What one asset cost, each way

Every line in this backlog is a claim that something will be faster or more certain, and
**not one of them is measured**. The risk is specific: the work gets rearranged rather than
reduced, and the plugin becomes a different way to spend the same afternoon.

So the loop is instrumented against a real asset made both ways. Five numbers, from brief to
accepted render:

| What | Why it is here |
|---|---|
| wall-clock seconds | the number the claim is actually about |
| renders spent | a faster loop that renders ten times as much is not faster |
| tool calls | a turn is what an agent pays |
| credits | some of this is real money |
| results a person rejected after the tool passed them | the honest measure of assertiveness |

**A tool that approves renders a person then rejects has made things worse however fast it
was**, and nothing else recorded here would show it. So every result carries **both**
verdicts — the tool's and a person's — and the gap between them is counted. The tool's own
verdict alone is worth nothing at this level.

## A baseline cannot be written afterwards

The baseline is what the existing pipeline costs today, recorded **before anything is
ported**, so that it cannot be reconstructed favourably once the answer is known.

That is enforced rather than asked for: starting the *before* side for an asset the plugin
has already made is refused (`loop.baseline-too-late`). Each run also carries the commit it
was taken at, so its place in the order is checkable by somebody who was not there, and the
ledger is append-only and committed with the tree.

A comparison with only one side recorded is refused too. A claim measured on one side is not
measured.

## The comparison is allowed to say it got worse

The verdict is one sentence, and the order it checks in is the order that matters:

1. **more overruling than before** — "faster or not, it is approving work that gets
   rejected";
2. **no faster** — "the work was not reduced by this measure";
3. **faster, but renders, calls or credits went up** — "the cost may have moved rather than
   gone", which is the specific failure this line exists to catch;
4. **faster with nothing else higher** — the only case that is unambiguously a win.

Nothing here can report a success that the numbers do not support, which is the whole
reason the line sits late in the file and is deliberately not optional: the alternative is a
backlog whose central claim cannot be falsified.

## Still to come in this block

Adopting the plugin onto a real project without carrying that project's paths and palette
into it (PW36), and testing against artefacts somebody actually made (PW48).
