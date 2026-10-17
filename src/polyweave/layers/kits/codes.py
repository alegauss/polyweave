"""The kits layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "kits": "a part every game repeats, made once in the plugin, proved and installed",
}

CODES: dict[str, Code] = {
    "kits.unknown": Code(
        means="a kit was named that the plugin does not carry",
        when="kit.install with a name kit.list does not answer (§PW341)",
        doors=("name a kit kit.list answers",),
    ),
    "kits.no-game": Code(
        means="a kit was to be installed where there is no Godot project",
        when="kit.install in a folder with no project.godot (§PW341)",
        doors=("install from the Godot project's own folder",),
    ),
    "kits.bad": Code(
        means="a kit's kit.toml does not keep the kit contract",
        when="a kit.toml missing, not TOML, with a key it does not know, a name that "
        "is not its folder's, a version not major.minor.patch, no core or proof, a "
        "file it names and does not hold, or kits that require each other (§PW340)",
        doors=("fix the kit.toml the refusal names, as docs/specs/kit.md says",),
    ),
}
