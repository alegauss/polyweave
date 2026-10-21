"""The motion layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "rig": "fitting a skeleton to a mesh, and moving a pose between skeletons",
    "clip": "motion over time, as something with a name and a duration",
}

CODES: dict[str, Code] = {
    # -- clip: motion over time ------------------------------------------------
    "clip.empty": Code(
        means="the clip moves nothing",
        when="a clip with no channels, or channels with no keys in them; a clip that "
        "changes nothing over its duration is a still with a duration attached",
        doors=("give it a channel with keys", "render it as a still instead"),
    ),
    "clip.camera-absent": Code(
        means="the game clip.shots opened never made the camera it was to frame",
        when="clip.shots opening the game itself, with args, and the camera node not "
        "existing within the wait (§PW553)",
        doors=("pass the args that open the game where the clip plays",
               "open the game with game.open, drive it there, and pass session"),
    ),
    "clip.anchor-absent": Code(
        means="a clip stood up by clip.shots names anchors the game has no node for",
        when="clip.shots given clip, with the game where none of the shots' anchors "
        "is a Node3D by that name or by the path anchors gives (§PW591)",
        doors=("pass anchors mapping each name to its node's path",
               "pass the args that build the world the anchors are in"),
    ),
    "clip.no-timeline": Code(
        means="the timeline named is not there, or is not TOML",
        when="clip.timeline on a path with no *.timeline.toml, or one that does not "
        "parse (§PW554)",
        doors=("name a *.timeline.toml relative to the project root",),
    ),
    "clip.bad-timeline": Code(
        means="a timeline declares something no Animation can play",
        when="an unknown key, a target with no property, keys out of order or of two "
        "kinds, a value no property holds, or an easing outside the set (§PW554)",
        doors=("correct the key the message names",),
    ),
    "clip.unknown-property": Code(
        means="a channel drives something a joint does not have",
        when="a property outside the three glTF animates: rotation, scale, translation",
        doors=("name rotation, scale or translation",),
    ),
    "clip.unknown-easing": Code(
        means="the keyframe asks for an interpolation nothing implements",
        when="an easing named outside the declared set",
        doors=("name a declared easing",),
    ),
    "clip.outside-duration": Code(
        means="a keyframe sits outside the clip it belongs to",
        when="a key at a negative time, or past the duration; the duration is the clip "
        "and a key beyond it never plays",
        doors=("move the key inside", "lengthen the clip"),
    ),
    "clip.frames-differ": Code(
        means="the frames of one clip are not all the same size",
        when="frames rendered at different rungs, or gathered from two runs; a sheet "
        "of cells that are not one size is a sheet nothing can index",
        doors=("render every frame at one rung",),
    ),
    "clip.nothing-drawn": Code(
        means="no frame of the clip has anything in it to trim to",
        when="a clip rendered with the subject out of frame, or on a rung that drew "
        "nothing at all",
        doors=("check the rig and the rung", "look at the frames the run wrote"),
    ),
    "clip.unreadable": Code(
        means="the clip file is not readable as the format it claims",
        when="a hand edit that left invalid TOML behind; the format is text so that a "
        "person can change it, which is also how it gets broken",
        doors=("fix the syntax the detail points at",),
    ),
    "clip.malformed": Code(
        means="the file is TOML and is not a clip",
        when="a file missing a name, a duration, or any channel at all",
        doors=("give it a name, a duration and a channel with keys",),
    ),
    "clip.no-camera": Code(
        means="there is no camera clip file, or it is not TOML",
        when="a path to no file, or a hand edit that left invalid TOML behind",
        doors=("name a *.camera.toml under the project",
               "fix the syntax the detail points at"),
    ),
    "clip.bad-camera": Code(
        means="a camera clip's key or value means nothing",
        when="a misspelled key, a shot with no from, look or hold, a place not three "
        "numbers, a field of view outside 1 to 179 degrees, an easing nothing "
        "implements, or a camera looking at the place it stands",
        doors=("correct the key or value the refusal names, at the shot it names",),
    ),
    "clip.unshipped": Code(
        means="the camera scene would land beside a declaration the export leaves out",
        when="no out, with the declaration under a .gdignore or a preset's "
        "exclude_filter; the editor would load it and the shipped game not",
        doors=("pass out, a folder the game ships",),
    ),
    "clip.no-frames": Code(
        means="the clip is too short or too slow to have a single frame in it",
        when="a duration or a frame rate at or below zero",
        doors=("give it a duration above zero", "give it a frame rate"),
    ),
    # -- rig: fitting a skeleton to a mesh ------------------------------------
    "rig.no-mesh": Code(
        means="a clip was asked to move a mesh that is not there",
        when="motion.bake naming a .glb that was never built or has moved",
        doors=("name the mesh the clip is for, as a path under the project",),
    ),
    "rig.unknown-plan": Code(
        means="there is no body plan by that name",
        when="a plan named outside the small library of the body plans that recur",
        doors=("name a declared plan", "state the joints"),
    ),
    "rig.bad-plan": Code(
        means="the body plan does not describe a skeleton",
        when="a joint whose parent is not in the plan, a cycle, or no root at all",
        doors=("give every joint a parent that comes before it",),
    ),
    "rig.unbound-vertices": Code(
        means="some vertices are attached to no bone, so posing leaves them behind",
        when="a mesh with a part no bone reaches, usually a plan that does not match "
        "the shape",
        doors=("fit a plan that covers the shape", "widen the falloff"),
    ),
    "rig.tearing": Code(
        means="a test pose stretches the mesh past what the weights should allow",
        when="two neighbouring vertices bound to bones that move apart; one influence "
        "per vertex is the worst case, and either end of the falloff is the next",
        doors=(
            "give a vertex more influences",
            "move the falloff off its extreme",
            "fit a plan that matches",
        ),
    ),
    "rig.unmatched-joints": Code(
        means="the pose names joints the skeleton does not have",
        when="a clip authored against one plan played on another that spells its "
        "joints differently; a name is the contract and a near miss is not a match",
        doors=(
            "name the joints the skeleton has",
            "retarget through a plan that shares them",
        ),
    ),
}
