# Motion

Binds **PW26**, and is where the rest of Block F's contract will go.

## A mesh gets a skeleton, or nothing in this block is reachable

Every generative mesh arrives as a **static surface with no skeleton**, so it cannot be
posed at all, and rigging one by hand is the step that keeps character animation out of
reach. For the shapes this pipeline produces — stuffed toys, props and rounded characters
rather than anatomically demanding figures — fitting one is tractable.

**A body plan is a declaration, in the frame `normalise` leaves a mesh in.** Upright, one
unit tall, standing on the origin: that is what lets one plan fit every mesh rather than
one mesh. Each joint states its parent and where it sits as a fraction of the bounding box,
a plan is written for the left side only and mirrored across x, and the library is small on
purpose — `prop`, `plush`, `biped`, `quadruped` are the body plans that recur.

**The fit pulls each joint onto the volume that is actually there.** A plan placed in a
bounding box puts an arm bone in the air beside a mesh narrower than its box, so each joint
takes a slab of the mesh at its own height on its own side and moves toward the centre of
it, by `[rig] pull`. The fit is a pure function of the mesh, the plan and the settings — a
mesh refetched at better quality refits to the same skeleton and keeps every clip.

## Weights, and the knob that runs the way nobody expects

A vertex takes the nearest few bones, by an inverse power of its distance to each bone's
**segment** rather than to the joint, so a long bone carries what lies along it.

**Both knobs have a middle, and both ends of both are worse.** Measured on the test figure,
as the worst edge stretch in a test pose:

| influences | falloff 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| 1 | 5.35 | 5.35 | 5.35 | 5.35 | 5.35 |
| 2 | 3.01 | 3.05 | 3.11 | 3.25 | 3.52 |
| 4 | 2.78 | 1.87 | **1.57** | 2.16 | 2.56 |
| 8 | 1.51 | 1.37 | 1.56 | 2.15 | 2.56 |

One influence per vertex is the worst setting there is: every vertex snaps to exactly one
bone, so every boundary between two bones is a tear. A falloff too high snaps the same way;
one too low spreads a vertex across bones nowhere near it and pulls it in a direction
nothing about it justifies. The defaults — four influences, falloff four — sit in the
trough, and the refusal names both knobs because either can be the one at fault.

## The two guards

A rig nobody can see is a rig nobody trusts, so both of these are cheap on purpose.

**Inspectable.** One test pose, and the edge lengths before and after it. A tear is two
neighbouring vertices bound to bones that move apart, and it shows up as one very long
edge — so the check is a **number**, `[rig] tear_ratio`, and the refusal names the edge that
tore rather than asking anybody to look at a picture.

**Re-runnable.** Nothing in the fit depends on anything but the mesh, the plan and the
settings, and all three are in the record. A mesh fetched again at better quality costs the
refit and nothing else.

## One clip, more than one skeleton

A clip authored against one skeleton plays on another **by joint name**, which is the one
thing both sides can agree on without either knowing about the other. `plush` and `biped`
share `root`, `spine`, `head`, `hand.L`, `hand.R`, `foot.L`, `foot.R` — so a wave authored
on one plays on the other, and `shared` answers which joints two plans have in common
before anything is attempted.

**A name with no home is named, never dropped.** A silently ignored channel is a limb that
does not move and nobody knows why, so `rig.unmatched-joints` lists what the pose asked for
and what the skeleton has.

## Into the file the engine reads

Everything above is decided in numpy, and none of it reaches an engine until it is a
**glTF skin**. That last step is a write and nothing more: the joints become an armature,
the weights become vertex groups, and an armature modifier ties the two together.

Two details the write has to get right. A bone with no length is dropped by Blender, so a
**root and a leaf both need a tail beyond themselves** — a joint whose bone would start and
end in the same place gets a short stub up the height axis instead. And weights are
assigned **bucketed by value**, one call per distinct weight rather than one per vertex,
which on a fetched mesh is the difference between seconds and minutes.

**What proves it is playing a pose on the file, not inspecting it.** `plays` imports what
was written into a fresh scene, turns one joint by name, and reports how many vertices
moved and how far. A file whose bones survived but whose weights did not comes back with
every bone present and nothing moving, and that is a case only this check catches — so it
picks the mesh the armature actually drives rather than the first mesh in the scene, since
an import brings back whatever the file holds.

An import also re-splits vertices per face corner, so the count coming back is larger than
the count going in. That is glTF's own business and not a sign of anything; what is
checked is that **some** vertices move and not **all** of them, because a limb that carries
the whole mesh is not a limb.

## A clip, not a frame pair

Motion in Cottony is **a second static render of the same mesh squashed to 93 per cent of
its height**, which the game crossfades to. That is a real technique and the right answer
for one beat — it keeps the face and the thread at the size they were, where a scaled
sprite would not — but it has no way to express anything longer. A walk, a reaction, an
idle, a hit: none of them are two frames.

A clip has a **name**, a **duration**, a **frame rate** and **channels over time**. A
channel drives one property of one joint, and the three properties are the three glTF
animates: `rotation`, `scale`, `translation`. That vocabulary is not a coincidence — it is
what the engine gets handed, so nothing has to be translated on the way out. The squash
keeps its place as **what it honestly is, a clip of three poses**, rather than being the
only thing the pipeline can say.

**A node's transform propagates down the tree, and here that is a sum of weights.** A
scale or a translation on a joint applies to everything that joint carries: the root
carries the whole mesh, an arm carries the arm and the hand. Without that rule a scale on
the root moves only the sliver of mesh the root bone happens to be nearest, and the squash
does not squash. Rotation goes through the skeleton's own skinning, which already walks
the hierarchy.

Between two keys a value is **linear** by default, **step** where a key holds until the
next one, or **ease** for a smoothstep. Not a spline: a spline is a curve somebody
authored, and an authored one is PW28's.

**A frame of a clip is a still.** Each frame is posed, written as its own mesh, and
rendered through the same `render.bake` a still goes through — so the ladder, the cache,
the post-conditions and every measurement in Block B apply to a clip without any of them
having to know what a clip is. A contact sheet of the *key* moments, rather than every
frame, is what a clip looks like in one picture.

**`across` is the one thing that is new.** A measurement over every frame, reported at its
worst and beside what it was at rest — because a silhouette that fits its budget at rest
and not mid-stride is a silhouette nobody measured, and that is the question a still
cannot be asked.

## Curves are data

An animation inside a binary mesh file is a binary track. A timing change to it is
**invisible in a diff, unreachable by an edit**, and only makeable by re-exporting from a
tool nobody has scripted — which puts the most iterated part of animation behind the
highest-friction door in the pipeline.

So the authored form is **TOML**, by this repository's own rule: a person writes it, and
the binary is an export rather than the source.

```toml
name = "settle"
duration = 0.4
fps = 24
easing = "linear"

[[channel]]
joint = "root"
property = "scale"
keys = [
  { at = 0, value = [1, 1, 1] },
  { at = 0.2, value = [1.06, 0.93, 1.06], ease = "ease" },
  { at = 0.4, value = [1, 1, 1] },
]
```

**One key per line is the contract and not a preference.** A review that can see an ease
changed is the difference between an animation that can be collaborated on and one that
can only be replaced wholesale, and a key sharing a line with three others says nothing. A
timing change is one changed line, and the tests hold it to exactly that.

`set_key` and `retime` are the same changes made **directly** rather than described to a
tool and hoped at, which is the whole reason this is text. Both return a new clip, so the
one being edited is never quietly changed underneath.

## The export is a compile step with a cache

Exactly like the renders in Block C. The clip becomes keyframes on the armature's pose
bones and leaves as a glTF animation, and the result is kept under a key so an unchanged
clip is a copy rather than an export.

**The key is over the authored text, not over a summary of it.** The first version keyed
on the clip's record, which carries the key *times* and not their *values* — so two clips
with the same timings and different values keyed identically, and the cache would have
handed back the wrong animation. A digest of the text is the whole of what was asked for,
which is the advantage of having a source that is text in the first place. The mesh and
the weights are in the key too, because the same clip on a differently weighted mesh is a
different file.

**The written file carries curves for every bone, not only the driven ones.** glTF has no
sparse animation, so the exporter samples the whole armature. That is the format's
business and not a defect, and it is why reading a compiled file reports the joints
separately from the raw channel list.

A clip driving a joint the skeleton does not have is `rig.unmatched-joints` — the same
refusal a retarget gives, for the same reason.

## One clip, two outputs

The same motion is needed in two shapes. A **2D screen needs frames**, as a sprite sheet
the interface crossfades or plays. A **3D scene needs a clip** the engine plays on a
skeleton. Cottony has the first and will want the second, and authoring them separately
means keeping two things in step by hand.

Both come out of the one clip: `compile` is the 3D half, and the sheet is the 2D one,
**rendered through the same rig** so the two genuinely match rather than merely resemble
each other. An atlas sits beside the sheet in JSON — a machine writes it and a machine
reads it — saying where each cell is, which moment of the clip it is, and how the sheet
was trimmed out of the rendered frame.

**The trim is one rectangle for the whole clip, not one per frame.** A frame trimmed to
its own silhouette is a frame whose subject sits somewhere slightly different from the
last, and a sprite that jitters on its own axis is the opposite of what a settle is for.
The union of every frame's outline, and every cell cut from it, so every cell is the same
size and the sheet can be indexed by arithmetic.

**The rate, the count, the trim and the column count are `[sprites]`**, because they are a
project's decisions rather than ones taken inside code. The sheet's rate is its own: a clip
authored at 24 may be sampled at 12 for a screen that plays it small, and a count can be
asked for instead where a sheet has a shape to hit.

**The value is not the saved authoring pass.** It is that a change to the timing lands in
both outputs. Both carry the **digest of the authored clip text**, so `matched` turns
"keeping them in step" from a discipline into a check: equal digests are a screen and a
scene playing the same motion, and a difference says so rather than waiting to be noticed.
