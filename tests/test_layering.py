"""The import direction the layout states, held by a test that fails (§PW506).

`kernel/` imports only itself; `loop/` the kernel; `services/` the loop and the kernel;
a layer those three; `surface/` anything. Every module is parsed with `ast`, the imports
inside functions included, which is where most reaches hide. Two imports point nowhere:
the package's own names (`__version__`, `readable`), and the bare `polyweave.layers`
namespace, which holds no code and is what the kernel walks to find the layers.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "polyweave"

#: Which areas each area may import, besides its own.
MAY = {
    "kernel": set(),
    "loop": {"kernel"},
    "services": {"kernel", "loop"},
    "layers": {"kernel", "loop", "services"},
    "surface": {"kernel", "loop", "services", "layers"},
    "root": {"kernel", "loop", "services", "layers", "surface"},
}

#: The package's own subpackages; any other name under `polyweave` is the package's.
AREAS = ("kernel", "loop", "services", "layers", "surface")


def area_of(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[1] in AREAS else "root"


def _named(module: str, is_package: bool, node: ast.AST) -> list[str]:
    """The polyweave modules (or package names) one import statement reaches."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names if a.name.split(".")[0] == "polyweave"]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level:
        base = module.split(".") if is_package else module.split(".")[:-1]
        base = base[: len(base) - (node.level - 1)]
        target = ".".join(base + ([node.module] if node.module else []))
    else:
        target = node.module or ""
    if target.split(".")[0] != "polyweave":
        return []
    if target == "polyweave":
        return [f"polyweave.{a.name}" for a in node.names]
    return [target]


def layer_name(module: str) -> str | None:
    parts = module.split(".")
    return parts[2] if len(parts) > 2 and parts[1] == "layers" else None


def _uses() -> dict[str, tuple[str, ...]]:
    from polyweave.kernel.layer import layers

    return {name: one.uses for name, one in layers().items()}


def wrong_way(source: str, module: str, is_package: bool = False,
              uses: dict | None = None) -> list[str]:
    """Each import in `source` against the layout, as `module:line -> target`.

    One layer reaching another is allowed only where its `layer.py` declares the edge
    in `uses` (§PW506).
    """
    mine = area_of(module)
    uses = _uses() if uses is None else uses
    out = []
    for node in ast.walk(ast.parse(source)):
        for target in _named(module, is_package, node):
            if target == "polyweave.layers":
                continue  # the namespace the kernel walks; it holds no code
            theirs = area_of(target)
            if mine == theirs == "layers":
                own, other = layer_name(module), layer_name(target)
                if other and own != other and other not in uses.get(own, ()):
                    out.append(f"{module}:{node.lineno} -> {target} (layer {own} does "
                               f"not declare it uses {other})")
                continue
            if theirs == "root" or theirs == mine or theirs in MAY[mine]:
                continue
            out.append(f"{module}:{node.lineno} -> {target} ({mine} may not reach "
                       f"{theirs})")
    return out


def _modules():
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
        is_package = parts[-1] == "__init__"
        if is_package:
            parts = parts[:-1]
        yield path, ".".join(parts), is_package


def test_every_import_in_the_package_points_the_way_the_layout_states():
    uses = _uses()
    found = [
        line
        for path, module, is_package in _modules()
        for line in wrong_way(path.read_text(encoding="utf-8"), module, is_package,
                              uses)
    ]
    assert found == []


def test_a_layer_reaching_one_it_does_not_declare_is_named():
    source = "from polyweave.layers.engine import capture\n"
    [said] = wrong_way(source, "polyweave.layers.words.fake", uses={"words": ()})
    assert "layer words does not declare it uses engine" in said
    declared = {"vfx": ("engine",)}
    assert wrong_way(source, "polyweave.layers.vfx.fake", uses=declared) == []


def test_layers_that_use_each_other_in_a_circle_are_refused():
    from polyweave.kernel.errors import PolyweaveError
    from polyweave.kernel.layer import Layer, _acyclic

    def one(name, uses):
        return Layer(name=name, summary="x", modules=(), uses=uses)

    with pytest.raises(PolyweaveError) as refused:
        _acyclic({"a": one("a", ("b",)), "b": one("b", ("c",)), "c": one("c", ("a",))})
    assert refused.value.code == "layer.cycle"
    assert "a -> b -> c -> a" in refused.value.message


@pytest.mark.parametrize(
    ("module", "source", "reached"),
    [
        ("polyweave.kernel.fake", "from polyweave.loop import accept\n", "loop"),
        ("polyweave.loop.fake",
         "def late():\n    from polyweave.layers.sound import sound\n", "layers"),
        ("polyweave.services.fake", "from ..surface import cli\n", "surface"),
        ("polyweave.layers.vfx.fake", "import polyweave.surface.server\n", "surface"),
    ],
)
def test_an_import_the_wrong_way_is_named_with_its_line(module, source, reached):
    [said] = wrong_way(source, module)
    assert said.startswith(f"{module}:")
    assert f"may not reach {reached}" in said


def test_the_namespace_and_the_packages_own_names_point_nowhere():
    source = "import polyweave.layers\nfrom polyweave import __version__, readable\n"
    assert wrong_way(source, "polyweave.kernel.layer") == []
