"""What one paid call would cost, spending nothing (§PW308).

It prices any operation that spends, so it reads the picture layer's prices and the
sound layer's samples: the surface's, over the services' ledger.
"""

from __future__ import annotations

from typing import Annotated

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.services.purchase import CHEAPER, COUNTED, PRICED_BY, remaining


@operation("purchase.quote")
def quote(
    operation: Annotated[str, Param("the paid operation, as describe names it")],
    arguments: Annotated[dict, Param("the arguments the call would pass")] = None,
    *,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """What one paid call would cost, and what the ceiling leaves, spending nothing.

    Priced exactly as the operation prices itself: its service's `prices` row for the
    model it would buy. A window asks a person with this before such a call runs, one
    call at a time (§PW308); `cheaper` names a free path where there is one.
    """
    from polyweave.kernel import describe as D
    from polyweave.layers.picture import picture

    D.load()
    # As Claude Code names the tool, too: the window asks with the name it was given.
    if operation.startswith("mcp__polyweave__"):
        from polyweave.surface.server import tool_name

        named = {tool_name(name): name for name in D._REGISTRY}
        operation = named.get(operation.removeprefix("mcp__polyweave__"), operation)
    found = D._REGISTRY.get(operation)
    if found is None or not found.spends:
        paid = sorted(name for name, op in D._REGISTRY.items() if op.spends)
        raise PolyweaveError(
            "fetch.not-paid",
            f"{operation!r} draws on no paid service, so it has no price",
            f"quote one of {', '.join(paid)}",
            given=operation,
            allowed=paid,
        )
    given = dict(arguments or {})
    defaults = {p["name"]: p.get("default") for p in found.parameters}
    by = PRICED_BY.get(operation, "model")
    model = by if by not in defaults else str(given.get(by) or defaults.get(by) or "")
    config = load(root)
    service = config.service(given.get("service") or None, model=model or None)
    about = config.services()[service]
    counted = next((given[k] for k in COUNTED if isinstance(given.get(k), str)), None)
    if counted is None and operation == "voice.design" and given.get("entity"):
        # The line it speaks is its count: the one passed, or the entity's own (§PW482).
        from polyweave.layers.sound.sound_buy import _sample_of

        counted = _sample_of(str(given["entity"]), given.get("world"), root,
                             given.get("locale"), given.get("sample"))
    found_price = picture._priced(
        service, about.get("prices") or {}, model, given.get("rendering_speed"),
        None if counted is None else len(counted),
    )
    price = found_price["price"]
    left = remaining(root, service=service)
    return {
        "operation": operation,
        "service": service,
        "model": model,
        "price": price,
        **{k: v for k, v in found_price.items() if k != "price"},
        "unit": left["unit"],
        "left": left["left"],
        "after": round(float(left["left"]) - price, 4),
        "affordable": bool(left["spendable"]) and price <= float(left["left"]),
        **({"cheaper": CHEAPER[operation]} if operation in CHEAPER else {}),
    }
