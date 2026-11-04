"""What the picture layer adds, read by the kernel (§PW500)."""

from polyweave.kernel.layer import Judge, Layer

LAYER = Layer(
    name="picture",
    uses=("engine", "geometry", "reference", "words",),
    summary="Pictures bought, fitted, varied and drawn, held to the project's style.",
    modules=(
        "polyweave.layers.picture.copies",
        "polyweave.layers.picture.fitting",
        "polyweave.layers.picture.panel",
        "polyweave.layers.picture.picture",
        "polyweave.layers.picture.scenario",
        "polyweave.layers.picture.stock",
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
        # A bought picture a person accepted is kept through a reworded prompt (§PW679).
        Judge(
            name="bought",
            about="a bought picture's verdict is kept in its own record, so it is not "
            "bought again",
            claims=lambda member: (bool(member.get("bought"))
                                   and not member.get("canon")),
            target="polyweave.layers.picture.picture:judged",
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
    config="polyweave.layers.picture.settings",
    #: 12,925 with stock.find and stock.fetch (§PW673, 2026-10-31).
    #: 13,616 with their kind, service and video renditions (§PW674, §PW672).
    #: 14,138 with picture.batch, a batch planned before it spends (§PW680).
    tools=14_600,
    census={
        "polyweave.layers.picture.picture:kept": (
            "internal", "a bought picture's accept on its bytes, inside picture.buy"),
        "polyweave.layers.picture.picture:judged": (
            "internal", "a bought picture's verdict, kept in its record"),
        "polyweave.layers.picture.panel:declared": (
            "internal", "a panel's states, checked; panel.build"),
        "polyweave.layers.picture.panel:wipe": (
            "internal", "a wipe's kind and uniforms, for panel.build"),
        "polyweave.layers.picture.page": (
            "internal", "the picture layer's parts of the brief, page and report"),
        "polyweave.layers.picture.style": (
            "internal", "compose and admit; verdict.judge is admit's door"),
        "polyweave.layers.picture.variation:person_marked": (
            "internal", "a person's mark, inside vary"),
        "polyweave.layers.picture.picture:gates": (
            "internal", "the gate's log, read by the review page"),
        "polyweave.layers.picture.scenario:serves": (
            "internal", "whether a service is Scenario (§PW450)"),
        "polyweave.layers.picture.scenario:trained_model": (
            "internal", "the model a family's canon trained (§PW450)"),
        "polyweave.layers.picture.scenario:bought": (
            "internal", "picture.buy on Scenario, from the trained model (§PW450)"),
    },
)
