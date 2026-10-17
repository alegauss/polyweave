"""The geometry layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "render": "producing a picture from a scene",
    "mesh": "building or transforming geometry",
    "geom": "a shape declared as data",
    "units": "the scale an asset is baked at, against the one the engine draws it at",
    "texture": "the pixels a service painted, and what has to come back out of them",
}

CODES: dict[str, Code] = {
    # -- mesh: building or transforming geometry ------------------------------
    "mesh.too-few-vertices": Code(
        means="there are not enough vertices to determine a frame",
        when="a normalisation of an empty or nearly empty mesh",
        doors=("check that the file imported",),
    ),
    "mesh.not-ready": Code(
        means="a mesh misses its engine-ready bar on a bound only a person can fix",
        when="normalise.ingest with ready= whose spec bounds holes, non-manifold "
        "edges, materials or texture bytes the written mesh exceeds, after its seams "
        "were welded and its triangles reduced to the ceiling (§PW447)",
        doors=("repair the mesh by hand", "buy it again",
               "move the bound if a person accepts the mesh as it is"),
    ),
    "mesh.bad-frame": Code(
        means="a mesh was asked to be sized on an axis or held from an origin that "
        "does not exist",
        when="size_on other than height, length or longest, or origin other than base "
        "or centre",
        doors=("name one of the axes", "name one of the origins"),
    ),
    "mesh.degenerate": Code(
        means="the mesh is flat or collinear, so its own axes say nothing about which "
        "way it faces",
        when="a normalisation of a plane, a line, or a mesh with no height",
        doors=("orient it against a reference drawing", "state the rotation"),
    ),
    "mesh.ambiguous-forward": Code(
        means="every orientation matches the reference equally well",
        when="a symmetric mesh, or a reference that does not distinguish its front; "
        "guessing which way is forward is a judgement this does not make",
        doors=("give a reference that shows the front", "state the rotation"),
    ),
    "texture.not-pixels": Code(
        means="what was handed over is not a texture",
        when="an array that is not height x width x channels, where a scrub or a mark "
        "count was asked for",
        doors=("pass the texture as floats in 0..1, with at least three channels",),
    ),
    # -- render: producing a picture from a scene -----------------------------
    "render.no-renderer": Code(
        means="Blender is not importable here, so nothing can render",
        when="the bpy module is not installed in the interpreter running the work",
        doors=("install bpy", "point [paths] blender at one that runs the worker"),
    ),
    "render.unknown-rung": Code(
        means="the rung named is not one of the three the ladder renders",
        when="a project renames a rung, or a caller misspells one",
        doors=("name sphere, preview or final",),
    ),
    "render.rung-disabled": Code(
        means="the question needs a rung this project does not enable",
        when="a measure that needs the real mesh on a project that enables only sphere",
        doors=("add the rung to [render] rungs", "ask a cheaper question"),
    ),
    "render.no-rungs": Code(
        means="the project enables no rungs at all",
        when="[render] rungs is empty",
        doors=("name some of sphere, preview and final",),
    ),
    "render.no-samples": Code(
        means="no sample count is declared for the rung being rendered",
        when="a project names a rung in [render] rungs and omits it from samples",
        doors=("set samples for that rung",),
    ),
    "render.placed-off-front": Code(
        means="a rectangle with a place was asked for from a camera not in front",
        when="covers given as [x0, y0, x1, y1] with a non-zero azimuth or elevation, "
        "where the corners would land wherever the turn put them",
        doors=("look straight on", "give covers as [width, height]"),
    ),
    "render.size-with-covers": Code(
        means="a size was asked for where a world rectangle already decides it",
        when="size given beside covers; the rectangle and its scale fix both axes",
        doors=("leave size out", "change pixels_per_unit instead"),
    ),
    "render.no-mesh": Code(
        means="the rung renders the real mesh and there is none to render",
        when="no model was named, the file is not there, or it imported empty",
        doors=("pass the model", "ask a question the sphere rung carries"),
    ),
    "render.no-pass": Code(
        means="a pass named in `after` is not a function in a file under the project",
        when="the path is wrong, outside the project, or the function is not in it",
        doors=("name it as path/to/file.py:function, under the project",),
    ),
    "render.pass-failed": Code(
        means="a project's own pass raised while painting the render",
        when="the pass's code assumed a picture, an argument or a module it lacks",
        doors=("read the detail for where it raised, and fix the pass",
               "drop it from after to see the render without it"),
    ),
    "render.unknown-format": Code(
        means="the mesh file is not in a format this reads",
        when="an .obj or another format where a .blend, glTF or FBX was expected",
        doors=("give it a .blend", "export as .glb, .gltf or .fbx"),
    ),
    "render.unknown-primitive": Code(
        means="the primitive named does not exist",
        when="a rung asks for a shape other than the sphere a surface is read on",
        doors=("use the sphere",),
    ),
    "render.bad-ratio": Code(
        means="a decimation ratio is not a fraction of one",
        when="a preview rung is given a ratio at or below zero, or above one",
        doors=("pass a ratio above 0 and at most 1",),
    ),
    "render.no-material": Code(
        means="this Blender has no standard shader to build a material on",
        when="a build without the Principled BSDF node",
        doors=("render with a Blender that ships the standard shader nodes",),
    ),
    "render.unknown-material-field": Code(
        means="a material names an input the shader does not have",
        when="a misspelled Principled BSDF socket, refused rather than dropped",
        doors=("name a socket the shader declares",),
    ),
    "render.no-scale": Code(
        means="a picture off the game's grid was given a rectangle and no scale",
        when="render.bake with on_grid=false and covers, without pixels_per_unit",
        doors=("pass pixels_per_unit, the scale the picture is drawn at",),
    ),
    "render.missing-picture": Code(
        means="a material wears a picture that is not on disk",
        when="a declared material's `image` names a path nothing is at",
        doors=("name the picture as a path under the project",),
    ),
    # -- geom: a shape declared as data ----------------------------------------
    "geom.unreadable": Code(
        means="the declaration is not readable as the format it claims",
        when="a hand edit that left invalid TOML behind",
        doors=("fix the syntax the detail points at",),
    ),
    "geom.malformed": Code(
        means="the file is TOML and is not a shape",
        when="a document with no name, no nodes, or no output named",
        doors=("give it a name, a node and an output",),
    ),
    "geom.bad-expression": Code(
        means="the expression is not one this evaluates",
        when="a call, an attribute, a comparison or a name outside the parameters and "
        "the repeat variables; nothing here evaluates arbitrary code, because a value "
        "that can depend on anything but its parameters breaks the cache key",
        doors=("write it with the operators and functions the grammar names",),
    ),
    "geom.unknown-field": Code(
        means="a declaration or a node carries a key nothing reads",
        when="`sizee = 9` beside `size` on a primitive, or `materails` at the top",
        doors=("spell it as one of the fields the refusal lists",),
    ),
    "geom.unknown-name": Code(
        means="the expression names something the document does not declare",
        when="a parameter spelled differently here than in [params], or a repeat "
        "variable used on a node that does not repeat",
        doors=("declare it in [params]", "name a variable this node repeats over"),
    ),
    "geom.duplicate-id": Code(
        means="two nodes claim the same id",
        when="a node copied and not renamed; ids are how every other node refers to "
        "one, so two of them makes every reference ambiguous",
        doors=("give each node an id of its own",),
    ),
    "geom.unknown-node": Code(
        means="a node refers to an id no node has",
        when="a typo in an input, or a node deleted while something still points at it",
        doors=("name a node the document declares",),
    ),
    "geom.cycle": Code(
        means="the nodes refer to each other in a circle, so none can be built first",
        when="a node taking its own output as an input, directly or through others",
        doors=("break the circle; a graph of shapes has to have a beginning",),
    ),
    "geom.bad-outline": Code(
        means="what was given is not an outline",
        when="fewer than three points, a mapping naming no shape, or a star of one "
        "point",
        doors=("give it a shape, an image, or at least three points",),
    ),
    "geom.no-function": Code(
        means="the custom node names a function nothing here can load",
        when="a path that does not resolve, or a function the file does not have",
        doors=("write it as path/to/file.py:name", "check the name"),
    ),
    "geom.not-geometry": Code(
        means="a custom node returned something that is not geometry",
        when="a project function returning None, or a value with no vertices and faces "
        "on it; the rest of the graph has nothing to compose with",
        doors=("return a mesh, or a mapping of vertices and faces",),
    ),
    "geom.bad-solid": Code(
        means="the solid's own numbers do not describe a shape",
        when="an annulus whose inner radius is not inside its outer one, or a union of "
        "nothing at all",
        doors=("check the numbers the node states",),
    ),
    "geom.unknown-op": Code(
        means="a node names an operation nothing here builds",
        when="a typo in an `op`, or a shape reaching for a vocabulary this does not "
        "have; the declaration parses either way, because what an op means is the "
        "vocabulary's question and not the document's",
        doors=("name a declared op", "write it as a `custom` node of your own"),
    ),
    "geom.bad-surface": Code(
        means="the surface stated on a material is not one this can build",
        when="a fuzz with no depth or no coarseness, a depth at or below zero, a "
        "coarseness outside nought to one, or one of the shell constants named as "
        "though it were the way to ask; those are derived from the two that are",
        doors=(
            "state a depth and a coarseness",
            "read the derived constants back with `construction`",
        ),
    ),
    "geom.unknown-shape": Code(
        means="there is no outline generator by that name",
        when="a shape named outside the small library the scripts were read off",
        doors=("name a declared generator", "trace a drawing instead"),
    ),
    "geom.nothing-to-trace": Code(
        means="the drawing has no subject in it to trace an outline from",
        when="an image that is entirely background",
        doors=("point it at a drawing with a subject in it",),
    ),
    "geom.bad-repeat": Code(
        means="the repeat does not describe a range",
        when="a range with no variable, or a step of zero, which is a loop that never "
        "ends rather than one that repeats nothing",
        doors=("give each range a var, a from and a to", "use a step above zero"),
    ),
    "geom.bad-voxels": Code(
        means="the document asks for cells and does not say how big one is",
        when="a [voxels] table with neither `cell` nor `across`, or with both, or a "
        "size that is not above zero; two ways of saying one number would disagree",
        doors=("give [voxels] a `cell` size", "give [voxels] an `across` count"),
    ),
    "geom.bad-fracture": Code(
        means="the fracture plan does not describe fragments that can exist",
        when="a size that is not two whole numbers, a smallest fragment under one "
        "cell, or a smallest above the largest",
        doors=(
            "write size = [smallest, largest] in cells, with 1 <= smallest <= largest",
        ),
    ),
    "geom.bad-fit": Code(
        means="a voxel fit was asked for something it cannot compare",
        when="no parameter to move, a view that is not front, side or top, or a "
        "drawing asked to stand for a view it does not show",
        doors=(
            "give ranges, or a [search.<param>] table in the document",
            "name views among front, side and top",
            "fit a drawing on the front view, or give a mesh for more",
        ),
    ),
    "geom.bad-cells": Code(
        means="a `cells` node's text does not describe a block of cells",
        when="layers or rows of different lengths, a character the legend does not "
        "name, or no size for a cell because [voxels] states only `across`",
        doors=(
            "make every row and every layer the same size",
            "add the character to `legend`, or use `.` for an empty cell",
            "give the node or [voxels] a `cell` size",
        ),
    ),
    # -- units: the scale an asset is baked at --------------------------------
    "units.undeclared": Code(
        means="nothing says what scale this asset is baked at",
        when="a check with no world rectangle, or a project that names no scale of its "
        "own and no file to read one from",
        doors=("state the rectangle the asset covers", "set [units] pixels_per_unit"),
    ),
    "units.unreadable": Code(
        means="the file the project points at holds no such number",
        when="a constant renamed or moved in the engine's own source; the point of "
        "reading it there is that this is what happens when it moves",
        doors=("check the name [units] source addresses", "state the number here"),
    ),
    "units.mismatch": Code(
        means="the asset is baked at one scale and the engine draws at another",
        when="a render rectangle tuned by hand to match a cell size held separately, "
        "after either of the two moved",
        doors=("bake at the engine's scale", "change the engine's, deliberately"),
    ),
    "units.not-whole": Code(
        means="the rectangle and the scale do not come to a whole number of pixels",
        when="a rectangle whose width times the scale lands between two pixels, which "
        "is a sprite that cannot sit on the grid whatever else is right",
        doors=("round the rectangle", "use a scale the rectangle divides by"),
    ),
    "units.wrong-size": Code(
        means="the picture is not the size the declaration asks for",
        when="a bake whose size came from the rung rather than from the rectangle",
        doors=("render at the size the declaration gives",),
    ),
}
