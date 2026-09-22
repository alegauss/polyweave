# Fetching from a paid service

Binds **PW16**, and is where the rest of Block D's contract will go.

## The shape is checked before the credits are

A generative service reinterprets silhouettes. Cottony sent a wide low cap on a short stem
and got back a tall dome on a long stem: thirty credits spent to learn that the shape was
not respected, discovered only once the money was gone.

The check is cheap and **nothing about it has to happen after payment**. Render the front
silhouette — azimuth zero, level, which §6 fixes as the front of a thing — and compare it
against the drawing that asked for it by intersection over union, against
`[tolerance] silhouette_iou`.

**Two doors, in order of preference.** Where the service offers any preview at all, however
low its resolution or however watermarked, take it and run the check there, because that is
the one place the answer arrives before the spend. Where it does not, the check still runs
on arrival, and its result is recorded against the prompt so the next attempt is informed
rather than a re-roll.

**A fetch that fails the check is a failure with a picture attached.** "It came back wrong"
is not actionable; the path of the render and the path of the drawing are. The refusal also
carries how the shape differs — the centroid offset and the largest edge of the bounding
box — because *which way* it is wrong is what a clearer prompt is written from.

Both masks are normalised to one size before comparing, so a 1024-pixel render and a
thumbnail drawing still compare. The render goes through the project's own rig rather than
a camera of its own: a silhouette taken through a different camera is a silhouette of
something else.

## A paid artefact is captured, not referenced

The service deletes a task's assets seventy-two hours after it completes. One Cottony run
recorded the settings it had proved and did not commit the mesh or its ledger entry, and the
mesh is now gone — thirty credits spent for a receipt.

That is a design problem, not a discipline one, so **the order is fixed**:

1. the bytes land on disk and are asserted against the length and digest the response
   declared;
2. they are hashed and the provenance record is written beside them, carrying the task id,
   the prompt or reference, and the credits consumed;
3. **only then** is the ledger entry appended.

The ledger is last so that it can never claim an asset that is not there. The reverse — a
file nothing recorded — is what `verify` finds. Between the two there is no window in which
a session can believe an asset is safe because a ledger mentions it, and a capture that
fails partway leaves no entry at all.

**Everything downstream keys off the local file and its hash**, never the remote id, because
the remote id is the identifier that stops existing.

The ledger is `[paths] purchases`, inside the tree and committed with it: a paid mesh and its
record are one artefact. `held()` answers the question that matters — is every artefact the
project paid for still present and still what it was — and names what each missing one cost.

## Still to come in this block

The service client, the budget ceiling and the lock that stops two sessions spending at once.
`provenance.md` already pins the fields a `fetch` record carries.
