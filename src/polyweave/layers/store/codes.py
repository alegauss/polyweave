"""The store layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "compose": "putting an asset where it will actually be seen",
    "store": "a store's capsule set, cut from one key art and a logo",
    "video": "a teaser cut together from captured runs, scored and encoded",
}

CODES: dict[str, Code] = {
    # -- compose: an asset where it will be seen ------------------------------
    "compose.no-tiles": Code(
        means="a contact sheet was asked for with nothing to put on it",
        when="an empty list of assets",
        doors=("pass the asset and the siblings it is seen beside",),
    ),
    "compose.unknown-anchor": Code(
        means="the anchor named is not one an asset can be placed by",
        when="a placement asking for something other than footprint or centre",
        doors=("anchor on the footprint, or on the centre",),
    ),
    "compose.outside": Code(
        means="the asset lands entirely outside the capture it was placed into",
        when="a position in the coordinates of a different capture, or of the asset",
        doors=("place it within the capture's own pixels",),
    ),
    # -- video: a teaser cut from captured runs (§PW429) -------------------------
    "video.no-source": Code(
        means="the cut named is not there, or is not TOML",
        when="video.cut given a path with no file, or a file that does not parse",
        doors=("name a *.cut.toml under the project", "fix the line the detail names"),
    ),
    "video.bad-cut": Code(
        means="a cut declares something it cannot hold",
        when="a key the cut does not take, a size not two even numbers, no clip, a "
        "clip with no run or length, a first clip fading in, a fade as long as a clip "
        "it joins, a fade_out the whole teaser, music not there, or an out not an .mp4",
        doors=("fix the key the refusal names",),
    ),
    "video.no-sequence": Code(
        means="a clip names a folder capture.movie did not write",
        when="a clip's from holds no sequence.json",
        doors=("capture the run with capture.movie and name the folder it wrote",),
    ),
    "video.short-sequence": Code(
        means="a clip asks more of a run than it holds",
        when="start plus length past the run's frames at its rate",
        doors=("shorten the clip", "start it earlier", "capture a longer run"),
    ),
    "video.no-ffmpeg": Code(
        means="ffmpeg or ffprobe is not on PATH",
        when="video.cut, or a video bound in a spec, on a machine without ffmpeg",
        doors=("install ffmpeg and put it on PATH",),
    ),
    "video.encode-failed": Code(
        means="ffmpeg did not write the teaser",
        when="ffmpeg exits with an error; the detail is what it said",
        doors=("read the detail",),
    ),
    "video.unreadable": Code(
        means="a video is not there, or is not one ffprobe reads",
        when="a video bound in a spec on a path with no file, or a file that is not a "
        "video",
        doors=("cut it again with video.cut",),
    ),
    # -- store: a store's capsules from one key art -------------------------------
    "store.unknown": Code(
        means="no store by that name, and no store file at that path",
        when="a misspelled store, or a project's store file that is not there",
        doors=("name a store this plugin knows", "pass a store file's path"),
    ),
    "store.bad-shape": Code(
        means="a store file's shape has no size in pixels or an unknown logo rule",
        when="a size that is not two whole numbers, or a logo other than centre, "
        "lower, only or none",
        doors=("write the shape as the remedy says",),
    ),
    "store.bad-focus": Code(
        means="the focus is not a point inside the key art",
        when="a focus that is not two fractions from 0 to 1",
        doors=("pass focus as [x, y], fractions of the key art",),
    ),
    "store.no-picture": Code(
        means="the key art or the logo is not there",
        when="a path to no file",
        doors=("name the picture as a path under the project",),
    ),
    "store.no-rasteriser": Code(
        means="a vector logo needs the engine to draw it, which is missing or failed",
        when="an .svg logo with no Godot binary, or an SVG the engine cannot read",
        doors=("set $GODOT or [paths] godot", "give the logo as a PNG with alpha"),
    ),
    "store.too-small": Code(
        means="the key art or logo is smaller than a shape needs, and nothing upscales",
        when="a key art narrower than a store's widest capsule, or a logo drawn larger "
        "than it is",
        doors=("give a larger key art or logo",),
    ),
    "store.internal-input": Code(
        means="a store page would be cut from a picture derived from internal footage",
        when="a key art or logo whose record, or an input's, says internal: frames "
        "of another game's video, or anything made from them",
        doors=("cut the capsules from the game's own key art and logo",),
    ),
    "compose.bad-icons": Code(
        means="an icon set's declaration cannot be drawn",
        when="a *.icons.toml missing or not TOML, a shape or key it does not know, a "
        "size out of range, or no icon at all (§PW331)",
        doors=("declare each icon with a shape the refusal lists",),
    ),
    "compose.empty-layer": Code(
        means="a vector's layer, or the whole picture, drew no pixel at all",
        when="picture.vector where every pixel of a layer came out transparent in "
        "every frame: the element is invisible, empty, or leans on a filter or mask "
        "that is not one (§PW478)",
        doors=(
            "check the element draws on its own",
            "check what it points at is the element meant",
        ),
    ),
    "compose.ambiguous-id": Code(
        means="an id in a vector means more than one element, or the wrong kind",
        when="picture.vector where a selector, a sweep or a url(#id) reference names "
        "an id two elements share, or a filter, mask or clip-path resolves to an "
        "element of another kind (§PW478)",
        doors=("give each element its own id", "point the reference at the one meant"),
    ),
    "compose.bad-sweep": Code(
        means="a vector's sweep cannot be drawn",
        when="picture.vector given a sweep naming an element no id in the SVG has, a "
        "key it does not take, a from or to that is not a number, or frames outside 2 "
        "to 256 (§PW476)",
        doors=(
            "name each element by an id the drawing holds; the refusal lists them",
            "write exactly element, attribute, from, to and frames",
        ),
    ),
    "compose.bad-seam": Code(
        means="a picture cannot be sewn with the seam asked for",
        when="picture.sew given a seam with no thread, a key nothing reads, a number "
        "out of its range, or a silhouette too small to lay a stitch inside (§PW474)",
        doors=(
            "name the thread's colour, and only the keys a panel's seam takes",
            "sew a larger picture, or a smaller inset",
        ),
    ),
    "compose.bad-panel": Code(
        means="a menu panel's declaration cannot be drawn",
        when="a *.panel.toml missing or not TOML, a key nothing reads, a colour or "
        "number that is not one, or a corner (cut, bracket) reaching past the "
        "nine-patch margin, which the stretch would bend (§PW316)",
        doors=(
            "name a declared key; the refusal says the nearest",
            "make the margin at least as wide as the cut plus the bracket",
        ),
    ),
    "compose.unfilmed": Code(
        means="a built panel or wipe could not be filmed by the engine",
        when="panel.capture where no display or offscreen route draws real pixels, or "
        "the run never reached its marks (§PW316)",
        doors=("run it where a display is, or through the offscreen route",),
    ),
    "compose.no-vector": Code(
        means="the vector picture named cannot be drawn",
        when="picture.vector given a path with no SVG, one that does not parse, or one "
        "stating neither a pixel width nor a viewBox (§PW315)",
        doors=("name an .svg under the project", "give its svg element a viewBox"),
    ),
    "compose.text-unoutlined": Code(
        means="an SVG's live text cannot be outlined, and the engine draws it blank",
        when="picture.vector or store.capsules on an SVG with text along a path, a "
        "font-family no declared or installed font has, a character its font lacks, "
        "or no fontTools (§PW453)",
        doors=("add the font to [words] fonts", "pip install fonttools",
               "convert the text to outlines in the editor"),
    ),
    "compose.no-layer": Code(
        means="a layer names an element the SVG does not have",
        when="picture.vector given a layer whose #id or place matches no top-level "
        "drawing element",
        doors=("name it by #id, or by its place counted from 1",),
    ),
}
