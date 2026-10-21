"""What the geometry layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Layer, Producer, Subject

LAYER = Layer(
    name="geometry",
    uses=("words",),
    summary="Shapes declared as data, built to meshes or voxels, rendered, measured.",
    modules=(
        "polyweave.layers.geometry.cost",
        "polyweave.layers.geometry.kit",
        "polyweave.layers.geometry.make",
        "polyweave.layers.geometry.mesh_buy",
        "polyweave.layers.geometry.normalise",
        "polyweave.layers.geometry.port",
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
    parts={
        "declaration.is": "polyweave.layers.geometry.make:is_declaration",
        "declaration.read": "polyweave.layers.geometry:read",
        "declaration.describe": "polyweave.layers.geometry.review:describe",
        "review:turntables": "polyweave.layers.geometry.page:turntables",
    },
    codes="polyweave.layers.geometry.codes",
    config="polyweave.layers.geometry.settings",
    # 18,030 with geometry.kit (§PW568).
    tools=18_200,
    census={
        "polyweave.layers.geometry.port:read": (
            "internal", "a family file checked, inside port.run"),
        "polyweave.layers.geometry.port:port": (
            "internal", "port.run with its renderer as a test hook"),
        "polyweave.layers.geometry.looks": (
            "internal", "the looks a material asks for, read by the bake and write"),
        "polyweave.layers.geometry.representations": (
            "internal", "which representation claims a declaration"),
        "polyweave.layers.geometry.representations.mesh": (
            "internal", "triangles, written by build.write"),
        "polyweave.layers.geometry.ops.primitive": (
            "internal", "the primitive op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.prism": (
            "internal", "the prism op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.plate": (
            "internal", "the plate op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.crowned": (
            "internal", "the crowned op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.annulus": (
            "internal", "the annulus op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.inflate": (
            "internal", "the inflate op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.union": (
            "internal", "the union op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.blend": (
            "internal", "the blend op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.transform": (
            "internal", "the transform op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.carve": (
            "internal", "the carve op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.bevel": (
            "internal", "the bevel op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.custom": (
            "internal", "the custom op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.cells": (
            "internal", "the cells op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.mirror": (
            "internal", "the mirror op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.mesh": (
            "internal", "the mesh op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.model": (
            "internal", "the model op, read by build, voxels and review"),
        "polyweave.layers.geometry.ops.paint": (
            "internal", "the paint op, read by build, voxels and review"),
        "polyweave.layers.geometry.units": (
            "internal", "a rectangle's arithmetic, inside units.check"),
        "polyweave.layers.geometry.cost": (
            "internal", "the readers under cost.read and a cost predicate"),
        "polyweave.layers.geometry.cost:bounds": (
            "internal", "a .glb's stored extent (§PW451)"),
        "polyweave.layers.geometry.page": ("internal", "the turntables; review.state"),
        "polyweave.layers.geometry.make:is_declaration": (
            "internal", "whether a TOML file is meant as a shape"),
        "polyweave.layers.geometry.make:made_from": (
            "internal", "what a build's outputs are made from"),
        "polyweave.layers.geometry.make:settings": (
            "internal", "`--set name=value`, read for the build"),
        "polyweave.layers.geometry.make:stamp": (
            "internal", "a build's stamp, its record's cache key"),
        "polyweave.layers.geometry": (
            "internal", "a declaration's machinery; geometry.build"),
        "polyweave.layers.geometry.build": ("internal", "the mesh a build writes"),
        "polyweave.layers.geometry.review": (
            "internal", "the words geometry.describe says"),
        "polyweave.layers.geometry.tuning": (
            "internal", "a shape search, with callable hooks"),
        "polyweave.layers.geometry.representations.voxels.model": (
            "internal", "the voxel model a build writes"),
        "polyweave.layers.geometry.shape": (
            "internal", "silhouette with its bake hook, and the gate"),
        "polyweave.layers.geometry.normalise": (
            "internal", "a mesh's maths, in memory, inside ingest"),
        "polyweave.layers.geometry.texture": (
            "internal", "the scrub on pixels in memory, in the bake"),
        "polyweave.layers.geometry.render.blender": (
            "internal", "bpy, behind the bake"),
        "polyweave.layers.geometry.render.rig": (
            "internal", "the rig's arithmetic, behind the bake"),
        "polyweave.layers.geometry.expr": ("internal", "a declaration's arithmetic"),
        "polyweave.layers.geometry.solver": ("internal", "a declaration's constraints"),
        "polyweave.layers.geometry.solid": ("internal", "the solid ops a build runs"),
        "polyweave.layers.geometry.outline": (
            "internal", "the outline ops a build runs"),
        "polyweave.layers.geometry.surface": (
            "internal", "the surface ops a build runs"),
        "polyweave.layers.geometry.finish": (
            "internal", "a material's finish, read by the bake"),
        "polyweave.layers.geometry.blend": (
            "internal", "the blend op's fields, built by build"),
        "polyweave.layers.geometry.fracture": ("internal", "an op a build runs"),
        "polyweave.layers.geometry.custom": (
            "internal", "the way back to code, called by build"),
        "polyweave.layers.geometry.representations.voxels.colour": (
            "internal", "a voxel build's palette"),
        "polyweave.layers.geometry.representations.voxels.fit": (
            "internal", "a voxel build's fitting"),
        "polyweave.layers.geometry.representations.voxels.compare": (
            "internal", "geometry.compare's two models"),
        "polyweave.layers.geometry.representations.voxels.sheet": (
            "internal", "a voxel build's contact sheet"),
    },
)
