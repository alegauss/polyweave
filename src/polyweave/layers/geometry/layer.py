"""What the geometry layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Producer, Subject

LAYER = Layer(
    name="geometry",
    summary="Shapes declared as data, built to meshes or voxels, rendered, measured.",
    modules=(
        "polyweave.layers.geometry.cost",
        "polyweave.layers.geometry.mesh_buy",
        "polyweave.layers.geometry.normalise",
        "polyweave.layers.geometry.render",
        "polyweave.layers.geometry.review",
        "polyweave.layers.geometry.shape",
        "polyweave.layers.geometry.texture",
        "polyweave.layers.geometry.units",
    ),
    requires=("blender",),
    kinds=("render", "mesh"),
    subjects=(
        Subject(
            about="a model's cost, read off the file the game draws",
            measures="polyweave.layers.geometry.cost:COSTS",
            target="polyweave.layers.geometry.cost:predicate",
        ),
    ),
    producers=(
        Producer(
            name="render",
            about="a Blender render of a model on the project's rig",
            target="polyweave.layers.geometry.render:bake",
            plan="polyweave.layers.geometry.render:plan",
            described="polyweave.layers.geometry.render.rig:described",
        ),
    ),
)
