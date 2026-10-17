"""The vfx layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "vfx": "a particle or ribbon effect declared as data and built for the engine",
}

CODES: dict[str, Code] = {
    # -- vfx: an effect declared as data and built for the engine -----------------
    "vfx.no-source": Code(
        means="there is no effects file, or it holds no [effect.<name>] tables",
        when="a path to no file, a file that is not TOML, or one of stray tables",
        doors=("name a *.vfx.toml under the project",
               "write each effect as [effect.<name>] with its amount and lifetime"),
    ),
    "vfx.unshipped": Code(
        means="the scenes would land beside a declaration the game's export leaves out",
        when="no out and no [paths] vfx, with the declaration under a .gdignore or a "
        "preset's exclude_filter; the editor would load them and the shipped game not",
        doors=("pass out, a folder the game ships",
               "set [paths] vfx in polyweave.toml"),
    ),
    "vfx.bad-effect": Code(
        means="an effect's key or value means nothing, or the named one is not there",
        when="a misspelled key, an amount of 0, a colour not written #rrggbb, a kind "
        "other than particles or ribbon",
        doors=("write the value the remedy describes",),
    ),
    "vfx.unwatched": Code(
        means="the engine could not play the effect where its frames could be kept",
        when="no display and no offscreen route, or a run that failed; the log says",
        doors=("run it where a display is", "read the log the detail names"),
    ),
}
