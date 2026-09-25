"""The escape hatch, which is a node and never a mode.

The evidence is §PW34: any format will eventually meet a shape it cannot state, and
**the framework that forces the shape into the format anyway produces worse geometry
than the script it replaced**. So the hatch is part of the design rather than an
admission of failure.

```toml
[[nodes]]
id     = "rope"
op     = "custom"
fn     = "tools/art/rope.py:build"
inputs = { along = "face" }
args   = { thickness = "bevel * 1.5", twist = 12 }
```

Three properties survive, and each is checked here rather than hoped for:

- **The parameters stay declared.** `args` are expressions over the document's own
  parameters, resolved before the call like every other field, so a search can still
  reach `thickness` by turning `bevel`.
- **The function's source is hashed into provenance**, so changing the code invalidates
  the cache. A custom node whose file changed and whose parameters did not would
  otherwise come back from the cache as the shape it used to be.
- **The rest of the shape stays data.** A declaration does not become a script because
  one operation in it is custom, which is the rule the whole design rests on: it is one
  node, not a mode the document enters.

Where the same custom node appears in three projects, that is the signal it should have
been vocabulary, and it gets filed as a roadmap line rather than copied a fourth time.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from ..jobs.worker import resolve_target
from ..post.mesh import as_mesh


def load(fn: str, *, root: str | Path = ".") -> Any:
    """The project's own function, by the same address a job's target uses."""
    try:
        return resolve_target(str(fn), Path(root).resolve())
    except PolyweaveError as refused:
        raise PolyweaveError(
            "geom.no-function",
            f"the custom node names {fn!r}, which did not load: {refused.message}",
            "write it as path/to/file.py:name, relative to the project root",
            detail=refused.detail,
        ) from refused


def source(fn: str, *, root: str | Path = ".") -> dict:
    """Where the function's code is and what it hashes to.

    The digest is what makes a custom node cacheable at all: the parameters say what
    was asked for and this says what would answer it, so either changing is a new key.
    """
    where, _, _name = str(fn).rpartition(":")
    path = Path(where)
    if not path.is_absolute():
        path = Path(root).resolve() / path
    if not path.is_file():
        # A module on the path rather than a file in the tree. It is still loadable and
        # still callable; what it is not is hashable, and saying so beats guessing.
        return {
            "fn": str(fn),
            "path": "",
            "sha256": "",
            "why": "not a file in the tree",
        }
    return {
        "fn": str(fn),
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "why": "",
    }


def build(node: dict, instance: dict, built: dict, *, root: str | Path = ".") -> dict:
    """Call the function with its resolved arguments and its named inputs.

    `built` holds the geometry of every node already made, which is how `inputs`
    reaches the graph: the function is handed meshes, not ids.
    """
    fn = node.get("fn")
    if not fn:
        raise PolyweaveError(
            "geom.no-function",
            f"{node['id']} is a custom node and names no function",
            'give it fn = "path/to/file.py:name"',
        )
    function = load(fn, root=root)

    inputs = {}
    for name, one in (node.get("inputs") or {}).items():
        if one not in built:
            raise PolyweaveError(
                "geom.unknown-node",
                f"{node['id']} takes {one!r} as {name}, and nothing built it",
                f"name a node built before this one: {', '.join(sorted(built))}",
                given=one,
                allowed=built,
                at=f"nodes.{node['id']}.inputs.{name}",
            )
        inputs[name] = built[one]

    args = dict(instance.get("args") or {})
    try:
        made = function(**inputs, **args)
    except PolyweaveError:
        raise
    except Exception as exc:
        raise PolyweaveError(
            "geom.no-function",
            f"{node['id']}: {fn} raised {type(exc).__name__}: {exc}",
            f"the function takes the inputs {sorted(inputs)} and the arguments "
            f"{sorted(args)}; check what it expects",
            detail=str(exc),
        ) from exc

    try:
        points, faces = as_mesh(made)
    except PolyweaveError as refused:
        raise PolyweaveError(
            "geom.not-geometry",
            f"{node['id']}: {fn} returned {type(made).__name__}, which is not geometry",
            "return a mesh, or a mapping of vertices and faces; the rest of the graph "
            "has nothing to compose with otherwise",
            detail=refused.message,
        ) from refused
    return {"vertices": points, "faces": faces}


def records(document: dict, *, root: str | Path = ".") -> list[dict]:
    """Every custom node's function and its digest, for the provenance record.

    Read off the document rather than off a build, so a cache key can be computed
    before anything is called — which is the same property every other key here has.
    """
    return [
        source(node["fn"], root=root)
        for node in document["nodes"]
        if node.get("op") == "custom" and node.get("fn")
    ]
