"""Motion as something with a name and a duration, rather than a second still.

The evidence is §PW27: motion in Cottony is **a second static render of the same mesh
squashed to 93 per cent of its height**, which the game crossfades to. That is a real
technique and the right answer for one beat — it keeps the face and the thread at the
size they were, where a scaled sprite would not — but it has no way to express anything
longer. A walk, a reaction, an idle, a hit: none of them are two frames.

A clip here has a **name**, a **duration**, a **frame rate** and **channels over time**.
A channel drives one property of one joint, and the three properties are the three glTF
animates: `rotation`, `scale`, `translation`. That vocabulary is not a coincidence — it
is what the engine will be handed, so nothing has to be translated on the way out.

The squash keeps its place as **what it honestly is, a clip of two poses**, rather than
being the only thing the pipeline can say:

    squash = clip("settle", 0.4, channels={"root": {"scale": [
        (0.0, [1, 1, 1]), (0.2, [1.06, 0.93, 1.06]), (0.4, [1, 1, 1])
    ]}})

**A frame of a clip is a still.** `frames` poses the mesh, writes it, and renders each
one through the same `render.bake` a still goes through — so the ladder, the cache, the
post-conditions and every measurement in Block B apply to a clip without any of them
knowing what a clip is. `across` is the one thing that is new: a measurement taken over
every frame and reported at its worst, because a silhouette that fits its budget at rest
and not mid-stride is a silhouette nobody measured.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from . import measure, skeleton
from .errors import PolyweaveError
from .post.mesh import as_mesh

#: What a channel may drive. The three glTF animates, and no others, because this is
#: what gets handed to the engine and a fourth would have nowhere to go.
PROPERTIES = ("rotation", "scale", "translation")

#: What a property means when nothing says otherwise.
RESTING = {
    "rotation": (0.0, 0.0, 0.0),
    "scale": (1.0, 1.0, 1.0),
    "translation": (0.0, 0.0, 0.0),
}

#: How a value gets from one key to the next.
EASINGS = ("linear", "step", "ease")

#: Frames a second, where the clip does not say.
FPS = 24


def clip(
    name: str,
    duration: float,
    *,
    fps: int = FPS,
    channels: dict | None = None,
    easing: str = "linear",
) -> dict:
    """One clip, checked for being motion at all."""
    if easing not in EASINGS:
        raise PolyweaveError(
            "clip.unknown-easing",
            f"there is no easing called {easing!r}",
            f"name one of {', '.join(EASINGS)}",
        )
    if float(duration) <= 0 or int(fps) <= 0:
        raise PolyweaveError(
            "clip.no-frames",
            f"a clip of {duration}s at {fps} fps has no frames in it",
            "give it a duration and a frame rate above zero",
        )

    kept: dict[str, dict[str, list]] = {}
    for joint, driven in (channels or {}).items():
        for prop, keys in driven.items():
            if prop not in PROPERTIES:
                raise PolyweaveError(
                    "clip.unknown-property",
                    f"{joint!r} has a channel for {prop!r}, which is not a property",
                    f"name one of {', '.join(PROPERTIES)}",
                )
            ordered = _keys(joint, prop, keys, float(duration))
            if ordered:
                kept.setdefault(joint, {})[prop] = ordered
    if not kept:
        raise PolyweaveError(
            "clip.empty",
            f"{name!r} has no channel with a key in it, so it moves nothing",
            "give it a channel with keys, or render it as a still; a clip that changes "
            "nothing over its duration is a still with a duration attached",
        )
    return {
        "name": str(name),
        "duration": float(duration),
        "fps": int(fps),
        "easing": easing,
        "channels": kept,
    }


def _keys(joint: str, prop: str, keys: Any, duration: float) -> list:
    out = []
    for key in keys or ():
        when, value = key[0], key[1]
        ease = key[2] if len(key) > 2 else ""
        if ease and ease not in EASINGS:
            raise PolyweaveError(
                "clip.unknown-easing",
                f"{joint}.{prop} at {when}s asks for {ease!r}",
                f"name one of {', '.join(EASINGS)}",
            )
        if not 0.0 <= float(when) <= duration:
            raise PolyweaveError(
                "clip.outside-duration",
                f"{joint}.{prop} has a key at {when}s, and the clip is {duration}s",
                "move the key inside the clip, or lengthen the clip; a key beyond the "
                "duration never plays",
            )
        out.append((float(when), tuple(float(v) for v in value), ease))
    return sorted(out, key=lambda key: key[0])


# -- what it looks like at a moment ----------------------------------------------------


def _eased(fraction: float, how: str) -> float:
    if how == "step":
        return 0.0
    if how == "ease":
        # Smoothstep. Not a spline: a spline is a curve somebody authored, and this is
        # what a key means when nobody said (§PW28 is where an authored one lives).
        return fraction * fraction * (3.0 - 2.0 * fraction)
    return fraction


def _between(keys: list, when: float, default: str) -> tuple:
    if when <= keys[0][0]:
        return keys[0][1]
    if when >= keys[-1][0]:
        return keys[-1][1]
    for before, after in zip(keys, keys[1:], strict=False):
        if before[0] <= when <= after[0]:
            span = after[0] - before[0]
            along = 0.0 if span <= 0 else (when - before[0]) / span
            mixed = _eased(along, before[2] or default)
            return tuple(
                a + (b - a) * mixed for a, b in zip(before[1], after[1], strict=True)
            )
    return keys[-1][1]  # pragma: no cover - the loop covers the whole span


def at(subject: dict, when: float) -> dict:
    """Every channel's value at one moment, as {joint: {property: value}}."""
    return {
        joint: {
            prop: _between(keys, float(when), subject["easing"])
            for prop, keys in driven.items()
        }
        for joint, driven in subject["channels"].items()
    }


def times(subject: dict) -> list[float]:
    """Every frame's moment, from zero up to and including the last one."""
    count = max(1, int(round(subject["duration"] * subject["fps"])))
    return [round(index / subject["fps"], 6) for index in range(count + 1)]


def keys(subject: dict) -> list[float]:
    """The moments somebody actually stated, which is what a contact sheet shows."""
    found = {
        round(when, 6)
        for driven in subject["channels"].values()
        for channel in driven.values()
        for when, _, _ in channel
    }
    return sorted(found)


def joints(subject: dict) -> list[str]:
    return sorted(subject["channels"])


# -- what it does to a mesh ------------------------------------------------------------


def carried(rig: dict, bound: dict, joint: str) -> np.ndarray:
    """How much of each vertex a joint carries, counting everything below it.

    glTF propagates a node's transform down the tree, and this is that rule in weights:
    the root carries the whole mesh, an arm carries the arm and the hand. It is why the
    squash works — scaling the root scales everything, not the sliver of the mesh the
    root bone alone happens to be nearest.
    """
    joints = rig.get("joints", rig)
    parents = {one["name"]: one["parent"] for one in joints}
    below = {joint}
    # Parents come before children in a plan, so one pass down the list settles it.
    for one in joints:
        if parents[one["name"]] in below:
            below.add(one["name"])
    columns = [i for i, name in enumerate(bound["names"]) if name in below]
    if not columns:
        return np.ones((len(bound["weights"]), 1))
    return bound["weights"][:, columns].sum(axis=1, keepdims=True)


def apply(subject: Any, rig: dict, bound: dict, posed: dict) -> np.ndarray:
    """The mesh at one pose, blended by its weights.

    Rotation goes through the skeleton's own skinning. Scale and translation apply about
    the joint the channel names, to everything that joint carries — which is what makes
    the squash expressible as what it is: the root scaled about where it stands.
    """
    turns = {
        joint: driven["rotation"]
        for joint, driven in posed.items()
        if "rotation" in driven
    }
    points = skeleton.pose(subject, rig, bound, turns)
    where = {
        joint["name"]: np.array(joint["at"], dtype=float)
        for joint in rig.get("joints", rig)
    }

    for joint, driven in posed.items():
        if joint not in where:
            continue
        weight = carried(rig, bound, joint)
        pivot = where[joint]
        if "scale" in driven:
            moved = (points - pivot) * np.array(driven["scale"]) + pivot
            points = points + weight * (moved - points)
        if "translation" in driven:
            points = points + weight * np.array(driven["translation"])
    return points


def poses(subject: dict, rig: dict, bound: dict, mesh: Any) -> list[np.ndarray]:
    """The mesh at every frame, which is the clip as geometry."""
    return [apply(mesh, rig, bound, at(subject, when)) for when in times(subject)]


# -- a frame of a clip is a still ------------------------------------------------------


def frames(
    subject: dict,
    mesh: Any,
    rig: dict,
    bound: dict,
    *,
    out: str | Path,
    root: str | Path = ".",
    when: Any = None,
    bake: Any = None,
    **how: Any,
) -> list[dict]:
    """Render the clip, one frame at a time, through the same call a still goes through.

    Every frame is written as its own mesh and baked, so the ladder, the cache, the
    post-conditions and Block B's measurements all apply without any of them having to
    know what a clip is.
    """
    from . import normalise
    from .config import load
    from .render import bake as bake_still

    draw = bake or bake_still
    settings = load(root)
    where = Path(out)
    if not where.is_absolute():
        where = settings.root / where
    work = settings.path("paths.work") / "clip" / subject["name"]
    moments = list(when) if when is not None else times(subject)

    out_frames = []
    for number, moment in enumerate(moments):
        posed = {
            "vertices": apply(mesh, rig, bound, at(subject, moment)),
            "faces": as_mesh(mesh)[1],
        }
        model = normalise.write_mesh(posed, work / f"{number:04d}.glb")
        picture = where / f"{subject['name']}.{number:04d}.png"
        found = draw(
            _Quiet(),
            out=str(picture.relative_to(settings.root))
            if picture.is_relative_to(settings.root)
            else str(picture),
            model=str(model),
            root=str(settings.root),
            inline=False,
            **how,
        )
        out_frames.append({**found, "frame": number, "at": moment})
    return out_frames


class _Quiet:
    """Nothing to report to: a frame is one render inside a clip."""

    def stage(self, stage, *, progress=None, note=None):
        pass

    def progress(self, value, *, note=None):
        pass

    def note(self, text):
        pass


def sheet(rendered: list[dict], *, out: str | Path, **how: Any):
    """A contact sheet of the frames, so a clip can be looked at in one picture."""
    from . import compose

    return compose.sheet([found["artefact"] for found in rendered], out=out, **how)


def across(rendered: list[dict], named: str, *, worst: str = "max") -> dict:
    """One measurement over every frame, reported at its worst.

    The thing a still cannot answer: a silhouette that fits its budget at rest and not
    mid-stride is a silhouette nobody measured.
    """
    taken = []
    for found in rendered:
        value = measure.summarise(found["measurements"]).get(named)
        if value is None:
            raise PolyweaveError(
                "spec.unknown-measure",
                f"no frame of this clip carries {named!r}",
                f"ask for it when the frames are rendered; they carry "
                f"{', '.join(sorted(measure.summarise(found['measurements'])))}",
            )
        taken.append(float(value))
    if not taken:
        raise PolyweaveError(
            "clip.no-frames",
            "there are no frames to measure",
            "render the clip before measuring across it",
        )
    at_worst = int(np.argmax(taken) if worst == "max" else np.argmin(taken))
    return {
        "measure": named,
        "frames": len(taken),
        "values": [round(v, 6) for v in taken],
        "worst": round(taken[at_worst], 6),
        "at": rendered[at_worst]["at"],
        "frame": rendered[at_worst]["frame"],
        "rest": round(taken[0], 6),
    }


def as_record(subject: dict) -> dict:
    """The clip as something to read, without every key in it."""
    return {
        "name": subject["name"],
        "duration": subject["duration"],
        "fps": subject["fps"],
        "easing": subject["easing"],
        "frames": len(times(subject)),
        "joints": joints(subject),
        "channels": sorted(
            f"{joint}.{prop}"
            for joint, driven in subject["channels"].items()
            for prop in driven
        ),
        "keys": keys(subject),
    }


# -- the authored form is text -------------------------------------------------------


def _number(value: float) -> str:
    """A number as a person would write it: no trailing zeros, no exponents."""
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text or "0"


def as_toml(subject: dict) -> str:
    """The clip as the file somebody authors, **one key per line**.

    One per line is the contract and not a preference. A diff that says an ease changed
    is the difference between an animation that can be collaborated on and one that can
    only be replaced wholesale, and a key sharing a line with three others says nothing.
    """
    out = [
        f'name = "{subject["name"]}"',
        f"duration = {_number(subject['duration'])}",
        f"fps = {subject['fps']}",
        f'easing = "{subject["easing"]}"',
    ]
    for joint in sorted(subject["channels"]):
        for prop in sorted(subject["channels"][joint]):
            out += ["", "[[channel]]", f'joint = "{joint}"', f'property = "{prop}"']
            out.append("keys = [")
            for when, value, ease in subject["channels"][joint][prop]:
                stated = ", ".join(_number(v) for v in value)
                easing = f', ease = "{ease}"' if ease else ""
                out.append(f"  {{ at = {_number(when)}, value = [{stated}]{easing} }},")
            out.append("]")
    return "\n".join(out) + "\n"


def write(subject: dict, path: str | Path, *, root: str | Path = ".") -> Path:
    """Write the authored clip, which is the source and not an export."""
    from .files import write_atomic

    where = Path(path)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    write_atomic(where, as_toml(subject))
    return where


def read(path: str | Path, *, root: str | Path = ".") -> dict:
    """Read one back, refusing a file that is TOML and is not a clip."""
    import tomllib

    where = Path(path)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    if not where.is_file():
        raise PolyweaveError(
            "clip.unreadable",
            f"there is no clip at {where}",
            "check the path, or write the clip before reading it",
        )
    try:
        stated = tomllib.loads(where.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "clip.unreadable",
            f"{where.name} is not readable as TOML",
            "fix the syntax the detail below points at; the format is text so a person "
            "can change it, which is also how it gets broken",
            detail=str(exc),
        ) from exc

    channels: dict[str, dict[str, list]] = {}
    for stated_channel in stated.get("channel", ()):
        joint = stated_channel.get("joint")
        prop = stated_channel.get("property")
        if not joint or not prop:
            raise PolyweaveError(
                "clip.malformed",
                f"{where.name} has a channel with no joint or no property",
                "give every channel a joint and a property",
            )
        channels.setdefault(joint, {})[prop] = [
            (key["at"], key["value"], key.get("ease", ""))
            for key in stated_channel.get("keys", ())
        ]
    if not stated.get("name") or not stated.get("duration"):
        raise PolyweaveError(
            "clip.malformed",
            f"{where.name} is TOML and is not a clip: it has no "
            f"{'name' if not stated.get('name') else 'duration'}",
            "give it a name, a duration and a channel with keys",
        )
    return clip(
        stated["name"],
        stated["duration"],
        fps=int(stated.get("fps", FPS)),
        easing=str(stated.get("easing", "linear")),
        channels=channels,
    )


# -- changing a curve, which is the most iterated part ---------------------------------


def set_key(
    subject: dict, joint: str, prop: str, when: float, value: Any, ease: str = ""
) -> dict:
    """A key set or replaced, as a new clip. The change an agent makes directly.

    Directly, rather than describing it to a tool and hoping — which is the whole reason
    this is text in the first place.
    """
    channels = {
        j: {p: list(k) for p, k in d.items()} for j, d in subject["channels"].items()
    }
    keys = channels.setdefault(joint, {}).setdefault(prop, [])
    channels[joint][prop] = [key for key in keys if key[0] != float(when)] + [
        (float(when), tuple(float(v) for v in value), ease)
    ]
    return clip(
        subject["name"],
        subject["duration"],
        fps=subject["fps"],
        easing=subject["easing"],
        channels=channels,
    )


def retime(subject: dict, duration: float) -> dict:
    """The same shape over a different span — the change that gets made most."""
    scale = float(duration) / subject["duration"]
    channels = {
        joint: {
            prop: [(when * scale, value, ease) for when, value, ease in keys]
            for prop, keys in driven.items()
        }
        for joint, driven in subject["channels"].items()
    }
    return clip(
        subject["name"],
        float(duration),
        fps=subject["fps"],
        easing=subject["easing"],
        channels=channels,
    )


# -- the export, which is a compile step with a cache ----------------------------------


def _radians(value: Any) -> list[float]:
    return [float(np.radians(v)) for v in value]


def _action(bpy: Any, rig: Any, subject: dict) -> Any:
    """The clip as keyframes on the armature's own pose bones."""
    rig.animation_data_create()
    action = bpy.data.actions.new(subject["name"])
    rig.animation_data.action = action
    for joint, driven in subject["channels"].items():
        if joint not in rig.pose.bones:
            raise PolyweaveError(
                "rig.unmatched-joints",
                f"the clip drives {joint!r}, which this skeleton does not have",
                f"this skeleton has "
                f"{', '.join(sorted(b.name for b in rig.pose.bones))}; a joint name is "
                f"the contract between a clip and a skeleton",
            )
        bone = rig.pose.bones[joint]
        bone.rotation_mode = "XYZ"
        for prop, channel in driven.items():
            for when, value, _ in channel:
                frame = when * subject["fps"]
                if prop == "rotation":
                    bone.rotation_euler = _radians(value)
                    bone.keyframe_insert("rotation_euler", frame=frame)
                elif prop == "scale":
                    bone.scale = [float(v) for v in value]
                    bone.keyframe_insert("scale", frame=frame)
                else:
                    bone.location = [float(v) for v in value]
                    bone.keyframe_insert("location", frame=frame)
    return action


def _digest(text: str | bytes) -> str:
    import hashlib

    return hashlib.sha256(
        text.encode("utf-8") if isinstance(text, str) else text
    ).hexdigest()


def _key_params(subject: dict, mesh: Any, rig: dict, bound: dict) -> dict:
    """What the compiled file depends on, in full rather than in summary.

    The clip goes in as a digest of its **authored text**, not of `as_record`: a record
    leaves the key values out, so two clips with the same timings and different values
    would key the same and the cache would hand back the wrong animation. The text is
    the source, so a digest of it is the whole of what was asked for.

    The mesh and the weights are in it too, because the same clip on a differently
    weighted mesh is a different file.
    """
    points = np.ascontiguousarray(as_mesh(mesh)[0], dtype=np.float64)
    return {
        "clip": subject["name"],
        "clip_sha256": _digest(as_toml(subject)),
        "mesh_sha256": _digest(points.tobytes()),
        "weights_sha256": _digest(
            np.ascontiguousarray(bound["weights"], dtype=np.float64).tobytes()
        ),
        "bones": list(bound["names"]),
        "joints": [
            [joint["name"], joint["parent"], list(joint["at"])]
            for joint in rig.get("joints", rig)
        ],
    }


def compile(
    subject: dict,
    mesh: Any,
    rig: dict,
    bound: dict,
    *,
    out: str | Path,
    root: str | Path = ".",
    cached: bool = True,
) -> dict:
    """Export the clip onto the rigged mesh, and keep the result under its own key.

    A compile step with a cache, exactly like the renders in Block C: the key is over
    the clip, the skeleton and the weights, so an unchanged clip is a copy rather than
    an export.
    """
    from . import cache as store
    from . import provenance
    from .config import load
    from .render import blender

    settings = load(root)
    where = Path(out)
    if not where.is_absolute():
        where = settings.root / where
    work = settings.path("paths.work")

    params = _key_params(subject, mesh, rig, bound)
    signature = provenance.cache_key(provenance.planned("mesh", params=params))
    if cached:
        hit = store.look(signature, work=work, suffix=".glb")
        if hit is not None:
            return {
                "artefact": str(store.take(hit, where)),
                "clip": subject["name"],
                "cached": True,
                "cache_key": signature,
            }

    bpy = blender.require()
    blender.reset()
    obj, armature = skeleton.build(mesh, rig, bound, name=subject["name"])
    _action(bpy, armature, subject)
    where.parent.mkdir(parents=True, exist_ok=True)
    for other in bpy.context.scene.objects:
        other.select_set(other in (obj, armature))
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(where),
        use_selection=True,
        export_format="GLB" if where.suffix.lower() == ".glb" else "GLTF_SEPARATE",
        export_skins=True,
        export_animations=True,
    )
    record = provenance.build("mesh", where, params=params, root=settings.root)
    provenance.write(record, root=settings.root)
    if cached:
        store.put(signature, where, record, work=work)
    return {
        "artefact": str(where),
        "clip": subject["name"],
        "cached": False,
        "cache_key": signature,
    }


#: How a bone's name appears in an f-curve's address.
ADDRESSED = re.compile(r'pose\.bones\["([^"]+)"\]')


def compiled(path: str | Path) -> dict:
    """What a written file actually carries, read back off the file itself.

    The channel list is longer than the clip's own. glTF has no sparse animation, so the
    exporter samples **every** bone whether the clip drives it or not — that is the
    format's business and not a defect, and it is why `joints` is here beside it.
    """
    from .render import blender

    bpy = blender.require()
    blender.reset()
    bpy.ops.import_scene.gltf(filepath=str(Path(path)))
    found = []
    for action in bpy.data.actions:
        start, end = action.frame_range
        addressed = sorted({curve.data_path for curve in _curves(action)})
        found.append(
            {
                "name": action.name,
                "frames": [round(float(start), 3), round(float(end), 3)],
                "channels": addressed,
                "joints": sorted(
                    {
                        match.group(1)
                        for path in addressed
                        if (match := ADDRESSED.match(path))
                    }
                ),
            }
        )
    return {"clips": sorted(found, key=lambda one: one["name"])}


def _curves(action: Any):
    """Every f-curve of an action, whichever shape this Blender keeps them in.

    Slotted actions landed in 4.4 and moved the curves down into layers and strips.
    Reading both is two lines and saves the whole read breaking on a version bump.
    """
    if hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                yield from bag.fcurves
