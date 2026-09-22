"""Giving a fetched mesh a skeleton, so it can be posed at all.

The evidence is §PW26: every generative mesh arrives as a **static surface with no
skeleton**, and rigging one by hand is the step that keeps character animation out of
reach entirely. Nothing else in Block F is reachable while every mesh is a rigid
surface.

For the shapes this pipeline actually produces — stuffed toys, props and rounded
characters rather than anatomically demanding figures — this is tractable:

- a **skeleton fitted to the mesh's own volume**, from a small library of the body
  plans that recur, each joint declared where it sits in a normalised mesh and then
  pulled onto the volume actually there;
- **weights solved from proximity** to the bone segments, kept to a few influences each;
- a **retarget by name**, so a clip authored against one skeleton plays on another.
  A joint name is the contract; a near miss is reported, never guessed at.

A plan is stated in the frame `normalise` leaves a mesh in — upright, one unit tall,
standing on the origin — which is what makes one declaration fit every mesh instead of
one mesh.

**Two guards, because a rig nobody can see is a rig nobody trusts.** It has to be
*inspectable*, and the cheapest possible check that the weights are not tearing the mesh
is one test pose and the edge lengths before and after it — a number rather than a
judgement about a picture. And it has to be *re-runnable*: the fit is a pure function of
the mesh, the plan and the settings, all of them recorded, so a mesh refetched at better
quality costs nothing but the refit and keeps every clip that names the same joints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .config import load
from .errors import PolyweaveError
from .post.mesh import as_mesh

#: How thick a slab of the mesh a joint is pulled onto, as a fraction of the height.
BAND = 0.09

#: Below this a distance is the same as zero, and a vertex is simply on the bone.
TOUCHING = 1e-6


def _mirror(joints: list[tuple[str, str, tuple]]) -> list[tuple[str, str, tuple]]:
    """Every `.L` joint again as `.R`, across x. A body plan is written once."""
    out = list(joints)
    for name, parent, at in joints:
        if name.endswith(".L"):
            other = parent[:-2] + ".R" if parent.endswith(".L") else parent
            out.append((name[:-2] + ".R", other, (-at[0], at[1], at[2])))
    return out


#: The body plans that recur. Positions are in the normalised frame: y from 0 at the
#: ground to 1 at the top, x and z as fractions of the width and depth about the centre.
PLANS: dict[str, list[tuple[str, str, tuple]]] = {
    # A thing that does not bend. One bone, so it can still be placed and animated.
    "prop": [("root", "", (0.0, 0.0, 0.0))],
    # Cottony's own shape: a soft body with stubby limbs and a big head.
    "plush": _mirror(
        [
            ("root", "", (0.0, 0.30, 0.0)),
            ("spine", "root", (0.0, 0.56, 0.0)),
            ("head", "spine", (0.0, 0.78, 0.0)),
            ("crown", "head", (0.0, 0.97, 0.0)),
            ("arm.L", "spine", (0.24, 0.60, 0.0)),
            ("hand.L", "arm.L", (0.32, 0.34, 0.0)),
            ("leg.L", "root", (0.14, 0.26, 0.0)),
            ("foot.L", "leg.L", (0.15, 0.02, 0.04)),
        ]
    ),
    "biped": _mirror(
        [
            ("root", "", (0.0, 0.52, 0.0)),
            ("spine", "root", (0.0, 0.66, 0.0)),
            ("chest", "spine", (0.0, 0.80, 0.0)),
            ("neck", "chest", (0.0, 0.88, 0.0)),
            ("head", "neck", (0.0, 0.95, 0.0)),
            ("shoulder.L", "chest", (0.10, 0.83, 0.0)),
            ("elbow.L", "shoulder.L", (0.22, 0.66, 0.0)),
            ("hand.L", "elbow.L", (0.26, 0.50, 0.0)),
            ("hip.L", "root", (0.09, 0.50, 0.0)),
            ("knee.L", "hip.L", (0.10, 0.27, 0.0)),
            ("foot.L", "knee.L", (0.10, 0.02, 0.04)),
        ]
    ),
    "quadruped": _mirror(
        [
            ("root", "", (0.0, 0.62, 0.0)),
            ("spine", "root", (0.0, 0.64, 0.18)),
            ("neck", "spine", (0.0, 0.72, 0.34)),
            ("head", "neck", (0.0, 0.82, 0.44)),
            ("tail", "root", (0.0, 0.60, -0.36)),
            ("shoulder.L", "spine", (0.13, 0.60, 0.24)),
            ("forefoot.L", "shoulder.L", (0.13, 0.02, 0.26)),
            ("hip.L", "root", (0.13, 0.58, -0.22)),
            ("hindfoot.L", "hip.L", (0.13, 0.02, -0.24)),
        ]
    ),
}


def plan(named: str) -> list[tuple[str, str, tuple]]:
    """One body plan, checked for being a skeleton at all."""
    if named not in PLANS:
        raise PolyweaveError(
            "rig.unknown-plan",
            f"there is no body plan called {named!r}",
            f"name one of {', '.join(sorted(PLANS))}",
        )
    return check_plan(PLANS[named])


def check_plan(joints: Any) -> list[tuple[str, str, tuple]]:
    """A plan is a tree, written parents first, with exactly one root."""
    out, seen, roots = [], set(), 0
    for name, parent, at in joints:
        if parent and parent not in seen:
            raise PolyweaveError(
                "rig.bad-plan",
                f"{name!r} hangs from {parent!r}, which is not above it in the plan",
                "give every joint a parent that comes before it",
            )
        roots += 0 if parent else 1
        seen.add(name)
        out.append((str(name), str(parent), tuple(float(v) for v in at)))
    if roots != 1:
        raise PolyweaveError(
            "rig.bad-plan",
            f"the plan has {roots} joints with no parent, and a skeleton has one",
            "give every joint but the root a parent",
        )
    return out


# -- fitting it to the mesh actually there ---------------------------------------------


def _onto(points: np.ndarray, at: np.ndarray, span: np.ndarray, pull: float):
    """Pull a joint from where the plan puts it onto the volume that is there.

    A slab of the mesh at the joint's own height, on the joint's own side, and the joint
    moves toward its centre. A plan placed in a box would put an arm bone in the air
    beside a mesh that is narrower than the box.
    """
    thick = max(float(span[1]) * BAND, TOUCHING)
    near = points[np.abs(points[:, 1] - at[1]) <= thick]
    if at[0] > 0:
        near = near[near[:, 0] > 0]
    elif at[0] < 0:
        near = near[near[:, 0] < 0]
    if not len(near):
        return at
    centre = near.mean(axis=0)
    return np.array(
        [
            at[0] + (centre[0] - at[0]) * pull,
            at[1],
            at[2] + (centre[2] - at[2]) * pull,
        ]
    )


def fit(subject: Any, *, named: str = "", root: str = ".", pull: float | None = None):
    """A skeleton on this mesh: every joint of the plan, where the mesh actually is.

    Pure in the mesh, the plan and the settings, so refitting a mesh fetched again at
    better quality gives the same skeleton and costs nothing else.
    """
    settings = load(root)
    which = named or str(settings.get("rig.plan"))
    toward = float(settings.get("rig.pull", pull))
    joints = plan(which)

    points, _ = as_mesh(subject)
    if len(points) < 3:
        raise PolyweaveError(
            "rig.unbound-vertices",
            f"{len(points)} vertices are not a mesh to fit a skeleton to",
            "check that the mesh imported",
        )
    low, high = points.min(axis=0), points.max(axis=0)
    span = np.maximum(high - low, TOUCHING)
    middle = (low + high) / 2.0

    placed = []
    for name, parent, at in joints:
        stated = np.array(
            [
                middle[0] + at[0] * span[0],
                low[1] + at[1] * span[1],
                middle[2] + at[2] * span[2],
            ]
        )
        placed.append(
            {
                "name": name,
                "parent": parent,
                "at": _onto(points, stated, span, toward).round(9).tolist(),
            }
        )
    return {"plan": which, "pull": toward, "joints": placed}


def bones(skeleton: dict) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Each joint as the segment from its parent to itself, which is what binds."""
    where = {joint["name"]: np.array(joint["at"], dtype=float) for joint in skeleton}
    out = []
    for joint in skeleton:
        head = where[joint["parent"]] if joint["parent"] else where[joint["name"]]
        out.append((joint["name"], head, where[joint["name"]]))
    return out


def _to_segment(points: np.ndarray, head: np.ndarray, tail: np.ndarray) -> np.ndarray:
    along = tail - head
    length = float(along @ along)
    if length <= TOUCHING:
        return np.linalg.norm(points - head, axis=1)
    where = np.clip(((points - head) @ along) / length, 0.0, 1.0)[:, None]
    return np.linalg.norm(points - (head + where * along), axis=1)


def weights(
    subject: Any,
    skeleton: dict,
    *,
    root: str = ".",
    influences: int | None = None,
    falloff: float | None = None,
) -> dict:
    """Which bones move which vertices, solved from proximity and nothing else.

    A vertex takes the nearest few bones, weighted by an inverse power of the distance
    to the bone's own segment.

    **Both knobs have a middle, and both ends of both are worse.** One influence per
    vertex snaps every vertex to exactly one bone, so every boundary between two bones
    is a tear — 5.4x on the test figure, by some distance the worst setting there is. A
    falloff too high snaps the same way; one too low spreads a vertex across bones
    that are nowhere near it, which pulls it in a direction nothing about it justifies.
    On the test figure, at four influences: falloff 1 gives 2.8x, falloff 4 gives 1.6x,
    and falloff 16 gives 2.6x. The defaults sit in that trough.
    """
    settings = load(root)
    most = int(settings.get("rig.influences", influences))
    power = float(settings.get("rig.falloff", falloff))
    points, _ = as_mesh(subject)
    segments = bones(skeleton.get("joints", skeleton))

    distances = np.stack(
        [_to_segment(points, head, tail) for _, head, tail in segments], axis=1
    )
    close = np.maximum(distances, TOUCHING) ** -power
    if len(segments) > most:
        # Exactly `most`, by index rather than by value: a symmetric mesh puts a vertex
        # the same distance from two bones, and a threshold would keep both of them.
        keep = np.argpartition(close, -most, axis=1)[:, -most:]
        only = np.zeros_like(close)
        np.put_along_axis(only, keep, np.take_along_axis(close, keep, axis=1), axis=1)
        close = only
    total = close.sum(axis=1, keepdims=True)
    bound = total[:, 0] > 0
    if not bound.all():
        raise PolyweaveError(
            "rig.unbound-vertices",
            f"{int((~bound).sum())} of {len(points)} vertices reach no bone at all",
            "fit a plan that covers this shape, or lower [rig] falloff so a bone "
            "reaches further into it",
        )
    return {
        "names": [name for name, _, _ in segments],
        "weights": (close / total).round(6),
        "influences": most,
        "falloff": power,
    }


# -- posing it, which is how the rig gets looked at ------------------------------------


def _chain(skeleton: list[dict]) -> dict[str, list[str]]:
    """Each joint and every joint above it, root last."""
    parents = {joint["name"]: joint["parent"] for joint in skeleton}
    out = {}
    for name in parents:
        chain, walk = [], parents[name]
        while walk:
            chain.append(walk)
            walk = parents[walk]
        out[name] = chain
    return out


def _turn(degrees: Any) -> np.ndarray:
    """A rotation from x, y, z degrees, applied in that order."""
    x, y, z = (np.radians(float(v)) for v in degrees)
    about_x = np.array(
        [[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]]
    )
    about_y = np.array(
        [[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]]
    )
    about_z = np.array(
        [[np.cos(z), -np.sin(z), 0], [np.sin(z), np.cos(z), 0], [0, 0, 1]]
    )
    return about_z @ about_y @ about_x


def pose(
    subject: Any, skeleton: dict, bound: dict, turns: dict[str, Any] | None = None
) -> np.ndarray:
    """The mesh with each joint turned as asked, blended by its weights.

    Linear blend skinning: every bone carries the whole mesh to where it would put it,
    and each vertex takes the weighted average. It is the simplest thing that is
    actually a pose, and it is what makes a rig something to look at.
    """
    points, _ = as_mesh(subject)
    joints = skeleton.get("joints", skeleton)
    where = {joint["name"]: np.array(joint["at"], dtype=float) for joint in joints}
    above = _chain(joints)
    asked = {str(k): v for k, v in (turns or {}).items()}

    out = np.zeros_like(points)
    for index, name in enumerate(bound["names"]):
        moved = points
        # Every joint from this one up to the root, so a shoulder carries the hand.
        for joint in [name, *above[name]]:
            if joint not in asked:
                continue
            pivot = where[joint]
            moved = (moved - pivot) @ _turn(asked[joint]).T + pivot
        out += bound["weights"][:, index : index + 1] * moved
    return out


def edges(faces: Any) -> np.ndarray:
    """Every edge of the mesh, once, as the pair of vertices it joins."""
    pairs = set()
    for face in faces:
        corners = list(face)
        for a, b in zip(corners, corners[1:] + corners[:1], strict=True):
            pairs.add((a, b) if a <= b else (b, a))
    return np.array(sorted(pairs), dtype=int) if pairs else np.zeros((0, 2), dtype=int)


#: A pose that bends everything a little, which is all a tearing check needs.
TEST_POSE = {
    "spine": (0, 0, 12),
    "head": (14, 0, 0),
    "arm.L": (0, 0, -25),
    "arm.R": (0, 0, 25),
    "leg.L": (18, 0, 0),
    "leg.R": (-18, 0, 0),
    "shoulder.L": (0, 0, -25),
    "shoulder.R": (0, 0, 25),
    "hip.L": (18, 0, 0),
    "hip.R": (-18, 0, 0),
    "neck": (10, 0, 0),
}


def stretch(subject: Any, skeleton: dict, bound: dict, turns: Any = None) -> dict:
    """How far the worst edge stretches in a test pose.

    The cheapest possible check that the weights are not tearing the mesh, and a number
    rather than a judgement about a picture. Two neighbouring vertices bound to bones
    that move apart is what a torn rig is, and it shows up here as one very long edge.
    """
    points, faces = as_mesh(subject)
    joined = edges(faces)
    if not len(joined):
        return {"worst": 1.0, "edges": 0, "at": []}
    moved = pose(subject, skeleton, bound, TEST_POSE if turns is None else turns)
    before = np.linalg.norm(points[joined[:, 0]] - points[joined[:, 1]], axis=1)
    after = np.linalg.norm(moved[joined[:, 0]] - moved[joined[:, 1]], axis=1)
    ratio = after / np.maximum(before, TOUCHING)
    worst = int(np.argmax(ratio))
    return {
        "worst": round(float(ratio[worst]), 4),
        "edges": int(len(joined)),
        "at": joined[worst].tolist(),
    }


def check(
    subject: Any, skeleton: dict, bound: dict, *, root: str = ".", ratio=None
) -> dict:
    """The two guards: every vertex is carried, and nothing tears when it moves."""
    bar = float(load(root).get("rig.tear_ratio", ratio))
    sums = bound["weights"].sum(axis=1)
    if not np.allclose(sums, 1.0, atol=1e-4):
        raise PolyweaveError(
            "rig.unbound-vertices",
            f"{int((~np.isclose(sums, 1.0, atol=1e-4)).sum())} vertices carry weights "
            f"that do not come to one",
            "solve the weights again; a vertex that is partly bound is partly left "
            "behind when the bone moves",
        )
    found = stretch(subject, skeleton, bound)
    if found["worst"] > bar:
        raise PolyweaveError(
            "rig.tearing",
            f"a test pose stretches an edge to {found['worst']}x its length, and "
            f"{bar}x was the most; the edge is between vertices {found['at']}",
            "give a vertex more than one influence, move [rig] falloff off whichever "
            "end it is at (both extremes tear, and the middle is around four), or fit "
            "a plan whose joints match this shape",
        )
    return {
        "holds": True,
        "vertices": int(len(sums)),
        "bones": len(bound["names"]),
        "stretch": found,
        "tear_ratio": bar,
    }


# -- one clip, more than one skeleton --------------------------------------------------


def retarget(turns: dict, skeleton: dict) -> dict:
    """Move a pose onto another skeleton, by the one thing both sides agree on.

    Joint names. A clip authored against one plan plays on another that spells its
    joints the same way, and a name with no home is **named** rather than dropped — a
    silently ignored channel is a limb that does not move and nobody knows why.
    """
    joints = skeleton.get("joints", skeleton)
    have = {joint["name"] for joint in joints}
    unmatched = sorted(name for name in turns if name not in have)
    if unmatched:
        raise PolyweaveError(
            "rig.unmatched-joints",
            f"the pose names {', '.join(unmatched)}, which this skeleton does not have",
            f"this skeleton has {', '.join(sorted(have))}; a joint name is the "
            f"contract between a clip and a skeleton, and a near miss is not a match",
        )
    return {name: tuple(float(v) for v in turn) for name, turn in turns.items()}


def shared(one: str, other: str) -> list[str]:
    """Which joints two plans have in common, which is what can be retargeted."""
    here = {name for name, _, _ in plan(one)}
    there = {name for name, _, _ in plan(other)}
    return sorted(here & there)


# -- writing it into the file the engine reads -----------------------------------------

#: The shortest a bone may be before Blender drops it for having no length. A leaf joint
#: and a root both need a tail beyond themselves, and two joints pulled onto one spot do
#: too.
STUB = 1e-3


def _tail_for(head: np.ndarray, at: np.ndarray, up: float):
    """Where a bone ends. Its own joint, unless that is where it started."""
    if float(np.linalg.norm(at - head)) > STUB:
        return at
    return head + np.array([0.0, max(up, STUB), 0.0])


def build(subject: Any, skeleton: dict, bound: dict, *, name: str = "rigged"):
    """The mesh, an armature of the fitted joints, and the weights between them.

    Built in Blender because glTF's skin is what an engine reads, and Blender is what
    writes one. Everything decided here was decided already, in numpy; this is the
    write.
    """
    from .render import blender

    bpy = blender.require()
    points, faces = as_mesh(subject)
    joints = skeleton.get("joints", skeleton)
    where = {joint["name"]: np.array(joint["at"], dtype=float) for joint in joints}
    parents = {joint["name"]: joint["parent"] for joint in joints}
    up = float(points[:, 1].max() - points[:, 1].min()) * 0.05

    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata(
        [blender.to_blender(p) for p in points], [], [list(face) for face in faces]
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    rig = bpy.data.objects.new(
        f"{name}-armature", bpy.data.armatures.new(f"{name}-armature")
    )
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for joint in joints:
        this = joint["name"]
        head = where[parents[this]] if parents[this] else where[this]
        bone = rig.data.edit_bones.new(this)
        bone.head = blender.to_blender(head)
        bone.tail = blender.to_blender(_tail_for(head, where[this], up))
        made[this] = bone
    for joint in joints:
        if joint["parent"]:
            made[joint["name"]].parent = made[joint["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")

    _bind(obj, rig, bound)
    return obj, rig


def _bind(obj: Any, rig: Any, bound: dict) -> None:
    """Weights onto vertex groups, and the modifier that makes them mean anything."""
    weights = np.asarray(bound["weights"], dtype=float)
    for index, name in enumerate(bound["names"]):
        column = weights[:, index]
        carried = np.flatnonzero(column > 0.0)
        if not len(carried):
            continue
        group = obj.vertex_groups.new(name=name)
        # Bucketed by value: one call per distinct weight rather than one per vertex,
        # which on a fetched mesh is the difference between seconds and minutes.
        rounded = np.round(column[carried], 5)
        for value in np.unique(rounded):
            group.add(
                [int(v) for v in carried[rounded == value]], float(value), "REPLACE"
            )
    obj.parent = rig
    obj.modifiers.new(name="Armature", type="ARMATURE").object = rig


def write(subject: Any, skeleton: dict, bound: dict, out: str | Path) -> Path:
    """Export the rigged mesh, so the engine has a skin to play a pose on."""
    from .render import blender

    bpy = blender.require()
    blender.reset()
    where = Path(out)
    where.parent.mkdir(parents=True, exist_ok=True)
    obj, rig = build(subject, skeleton, bound)
    for other in bpy.context.scene.objects:
        other.select_set(other in (obj, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(where),
        use_selection=True,
        export_format="GLB" if where.suffix.lower() == ".glb" else "GLTF_SEPARATE",
        export_skins=True,
    )
    return where


def joints_in(path: str | Path) -> list[str]:
    """The bone names a written file carries, read back off the file itself."""
    from .render import blender

    bpy = blender.require()
    blender.reset()
    bpy.ops.import_scene.gltf(filepath=str(Path(path)))
    return sorted(
        bone.name
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
        for bone in obj.data.bones
    )


def plays(path: str | Path, joint: str, turn: Any = (0.0, 0.0, 30.0)) -> dict:
    """Import what was written, turn one joint by name, and see if the mesh moved.

    The whole claim of this half: the joints and the weights exist as data and are
    checked there, and what is unproven is that they survive the write into a file.
    """
    from mathutils import Euler

    from .render import blender

    bpy = blender.require()
    blender.reset()
    bpy.ops.import_scene.gltf(filepath=str(Path(path)))
    rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    # The mesh this armature drives, not the first mesh in the scene: an import brings
    # back whatever the file holds, and only one of them is the one that was skinned.
    mesh = next(
        (
            o
            for o in bpy.data.objects
            if o.type == "MESH"
            and any(m.type == "ARMATURE" and m.object is rig for m in o.modifiers)
        ),
        None,
    )
    if rig is None or mesh is None:
        raise PolyweaveError(
            "rig.unbound-vertices",
            f"{Path(path).name} came back with "
            f"{'no armature' if rig is None else 'no mesh'} in it",
            "export with skins, and with both the mesh and the armature selected",
        )
    if joint not in rig.pose.bones:
        raise PolyweaveError(
            "rig.unmatched-joints",
            f"the written file has no joint called {joint!r}",
            f"it carries {', '.join(sorted(b.name for b in rig.pose.bones))}",
        )

    before = _evaluated(bpy, mesh)
    posed = rig.pose.bones[joint]
    posed.rotation_mode = "XYZ"
    posed.rotation_euler = Euler([np.radians(float(v)) for v in turn], "XYZ")
    bpy.context.view_layer.update()
    after = _evaluated(bpy, mesh)

    moved = np.linalg.norm(after - before, axis=1)
    return {
        "joint": joint,
        "moved": int((moved > 1e-5).sum()),
        "vertices": int(len(moved)),
        "furthest": round(float(moved.max()), 6),
        "bones": sorted(bone.name for bone in rig.pose.bones),
    }


def _evaluated(bpy: Any, obj: Any) -> np.ndarray:
    """Where the vertices actually are, with the armature modifier applied."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points = np.array([tuple(v.co) for v in mesh.vertices], dtype=float)
    evaluated.to_mesh_clear()
    return points


def as_record(skeleton: dict, bound: dict, checked: dict) -> dict:
    """The rig as something to read: what it was fitted from, and what held.

    Weights are left out on purpose — they are one number per vertex per bone, and a
    record nobody can read is a record nobody reads. What is here is enough to refit.
    """
    return {
        "plan": skeleton["plan"],
        "pull": skeleton["pull"],
        "influences": bound["influences"],
        "falloff": bound["falloff"],
        "joints": [
            {"name": joint["name"], "parent": joint["parent"], "at": joint["at"]}
            for joint in skeleton["joints"]
        ],
        "checked": {
            "vertices": checked["vertices"],
            "bones": checked["bones"],
            "worst_stretch": checked["stretch"]["worst"],
            "tear_ratio": checked["tear_ratio"],
        },
    }
