"""The geometry layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "render": {
        "rungs": ["sphere", "preview", "final"],
        "preview_size": 256,
        "final_size": 1024,
        "samples": {"sphere": 32, "preview": 64, "final": 512},
        "seed": 0,
        "max_parallel": 4,
    },
    "geometry": {"outlines": ""},
    # How a finish reaches the engine (§PW569). Left as it is, a finish is the closed
    # material the bake used. A project that draws its pieces on a MultiMesh and holds
    # its background under the play opens it: `hue = "instance"` turns each instance's
    # colour by INSTANCE_CUSTOM.x turns of the wheel, and `include` with `hold` passes
    # the colour through a function of the project's, `hold(colour, amount)`, where
    # `amount` is an instance uniform of that name, 1 unless the instance says.
    "finish": {"hue": "", "include": "", "hold": "", "amount": "backdrop"},
    "voxels": {
        # What a voxel build is checked against (§PW97). A game decides how many cubes
        # it can draw and how thin a part may be before it vanishes, so these are the
        # project's. A budget of zero is no ceiling and an empty extent no target.
        "budget": 0,
        # The longest run one cell thick before it is reported.
        "thread": 3,
        # [x, y, z] in the declaration's units; a document's own [voxels] extent wins.
        "extent": [],
        # One cell for every voxel declaration in the project (§PW229), so the debris of
        # a drone and of a boss are the same cubes. A document giving neither `cell` nor
        # `across` takes it; its own wins, reported where it differs. Zero is none.
        "cell": 0.0,
        # A model at least this symmetric in x and short of whole is reported, because
        # that is what two halves drifting apart looks like.
        "near_symmetry": 0.9,
    },
    "units": {
        # The scale the engine draws at. Stating it here is the weaker half; `source`
        # is the stronger one — `path/to.gd:NAME` reads it from wherever the game
        # already holds it, so the two numbers cannot drift apart (§PW24).
        "pixels_per_unit": 0.0,
        "source": "",
        "tolerance": 0.001,
    },
}

#: Tables whose keys a project names itself.
OPEN = ("render.samples",)
