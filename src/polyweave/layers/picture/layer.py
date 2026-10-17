"""What the picture layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer

LAYER = Layer(
    name="picture",
    summary="Pictures bought, fitted, varied and drawn, held to the project's style.",
    modules=(
        "polyweave.layers.picture.fitting",
        "polyweave.layers.picture.panel",
        "polyweave.layers.picture.picture",
        "polyweave.layers.picture.scenario",
        "polyweave.layers.picture.style",
        "polyweave.layers.picture.variation",
        "polyweave.layers.picture.vector",
    ),
    judges=(
        Judge(
            name="canon",
            about="an accepted look joins the style family its member names as canon",
            claims=lambda member: bool(member.get("canon")),
            target="polyweave.layers.picture.style:judged",
        ),
    ),
    kinds=("picture",),
    parts={
        "brief:gate": "polyweave.layers.picture.page:gate",
        "brief.read:picture": "polyweave.layers.picture.page:read",
        "report:gate": "polyweave.layers.picture.page:report_gate",
        "review:gates": "polyweave.layers.picture.page:gates",
        "page.admit": "polyweave.layers.picture.page:admitted",
        "page.overrule": "polyweave.layers.picture.page:overruled",
        "page.withdraw": "polyweave.layers.picture.page:withdraw",
        "page.boards": "polyweave.layers.picture.page:boards",
    },
    codes="polyweave.layers.picture.codes",
)
