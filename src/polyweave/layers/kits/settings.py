"""The kits layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    # Each installed kit's declaration, `[kit.<name>]` (§PW341): its keys are the kit's
    # own, so the kit checks them and this table does not.
    "kit": {},
}
