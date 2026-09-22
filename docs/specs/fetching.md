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

## Still to come in this block

The service client, the budget and its ledger, the lock that stops two sessions spending at
once, and what a fetch records — each is its own line, and `provenance.md` already pins the
fields a `fetch` record carries.
