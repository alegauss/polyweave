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

## Still to come in this block

Clips (PW27), curves as text (PW28), and one clip producing both outputs (PW29).
