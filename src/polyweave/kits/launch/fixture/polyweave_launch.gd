extends RefCounted
## The launch fixture's budgets: the first scene within three seconds of launch, and no
## frame of a change of scene over 100 ms at the 95th percentile.

const LAUNCH_MS := 3000
const FRAME_MS := 100.0
