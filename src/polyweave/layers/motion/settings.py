"""The motion layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "sprites": {
        # What the 2D half of a clip is baked at. Configuration rather than decisions
        # taken inside code: a sheet's rate, its count and its trim are a project's
        # (§PW29). `frames` of zero takes every frame the clip has.
        "fps": 12,
        "frames": 0,
        "trim": True,
        "columns": 0,
    },
    "rig": {
        # Which body plan a mesh gets fitted with, and how the weights fall off. The
        # plan is the only one of these a project usually changes (§PW26).
        "plan": "plush",
        # One influence snaps every vertex to one bone and tears at every boundary.
        "influences": 4,
        # Both ends tear: high snaps a vertex to one bone, low spreads it onto bones
        # nowhere near it. Four sits in the trough, at 1.6x on the test figure.
        "falloff": 4.0,
        # How far a joint is pulled from the plan's own position onto the mesh's volume.
        "pull": 0.6,
        # How far an edge may stretch in a test pose before the rig is called wrong.
        "tear_ratio": 2.0,
    },
}
