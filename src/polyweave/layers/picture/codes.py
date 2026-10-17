"""The picture layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "style": "what a project's pictures look like, and the canon a person grows",
}

CODES: dict[str, Code] = {
    "style.references-need-3": Code(
        means="a family with style references was asked for on a model that takes none",
        when="[style.<family>] names references and the call asked 4.0",
        doors=("ask model 3.0, the one that takes a reference picture",
               "empty references to draw on 4.0 from the words alone"),
    ),
    "style.references-take-text": Code(
        means="style references go with a text prompt, and the call gave structure",
        when="a family with references was asked for with json_prompt",
        doors=("pass prompt as text; the skeleton and palette are written into it",),
    ),
    "style.no-reference": Code(
        means="a style reference names a picture the family's canon does not hold",
        when="references lists a file name that is not in the canon directory",
        doors=("name a picture the canon holds", "admit it to the canon first"),
    ),
    "style.references-too-large": Code(
        means="the reference pictures are more than the service takes in one request",
        when="their bytes together pass the 50 MB the service allows",
        doors=("name fewer or smaller canon pictures in references",),
    ),
    # -- style: what a project's pictures look like ---------------------------
    "style.family-unnamed": Code(
        means="the project declares several styles and the call named no family",
        when="a picture bought with [style.<family>] tables and no family; a sprite "
        "held to a title screen's look is the mistake the families exist to prevent",
        doors=("pass the asset's family",),
    ),
    "style.unknown-family": Code(
        means="no style is declared for the family named",
        when="a misspelled family, or one whose [style.<family>] was never written",
        doors=("name a declared family", "declare [style.<family>]"),
    ),
    "style.needs-structure": Code(
        means="a style is carried by a structured prompt, and the call gave text",
        when="a picture asked for in a family with a text prompt, which the service "
        "would rewrite and which has no place for a palette or a style block",
        doors=("pass json_prompt",),
    ),
    "style.no-subject": Code(
        means="the picture has no pixel above the alpha floor, so there is no look "
        "to measure",
        when="an empty or fully transparent frame given to style.drift",
        doors=("check the picture is the asset",),
    ),
    "style.not-in-canon": Code(
        means="the picture named is not in the family's canon",
        when="a removal from the review page for a picture already withdrawn, or one "
        "in another family's canon",
        doors=("name a picture the board shows",),
    ),
    "style.not-a-candidate": Code(
        means="the picture is not one the family's candidates point at",
        when="an admission from the review page of a file no [style] candidates glob "
        "matches, or one the canon already holds",
        doors=("admit a candidate the board lists",
               "point [style.<family>] candidates at the pictures a person may admit"),
    ),
    "style.no-canon": Code(
        means="the family has no canon directory, so nothing can be admitted to it",
        when="a verdict naming a canon family whose [style] declares no canon",
        doors=("set canon under the family's [style]",),
    ),
    "style.too-few-to-train": Code(
        means="a family's canon holds fewer pictures than Scenario trains on",
        when="style.train on a canon of fewer than five approved pictures (§PW450)",
        doors=("admit more pictures to the canon by verdict",),
    ),
    "style.untrained": Code(
        means="a family's canon has trained no model to draw a picture from",
        when="picture.buy on a Scenario service before style.train (§PW450)",
        doors=("train one with style.train",),
    ),
    "style.bad-rig": Code(
        means="a family's rig names a setting the render does not take",
        when="style.drift or the canon board on a mesh, where [style] rig sets a key "
        "render.bake has no parameter for (§PW451)",
        doors=("set only render.bake's camera and light settings, rung and seen",),
    ),
}
