"""What the geometry layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer

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
)
