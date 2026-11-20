"""The registry of spatial scales (``geo/scales.yaml``)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from typing import TYPE_CHECKING

import yaml

from . import store

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class Scale:
    id: str
    label: str
    kind: str                     # admin | grouping | grid | custom
    id_pattern: str
    parent: str | None = None     # next coarser scale this one nests in exactly
    children: str | None = None   # for groupings: the scale they are unions of
    level: int | None = None
    status: str = "active"        # active | planned
    extra: dict = field(default_factory=dict, compare=False)

    def matches(self, geo_id: str) -> bool:
        return re.fullmatch(self.id_pattern, geo_id) is not None


@cache
def _registry(ref: str | None = None) -> dict[str, Scale]:
    raw = yaml.safe_load(store.open_binary("geo/scales.yaml", ref))
    known = {"label", "kind", "id_pattern", "parent", "children", "level", "status"}
    return {
        sid: Scale(id=sid, **{k: v for k, v in spec.items() if k in known},
                   extra={k: v for k, v in spec.items() if k not in known})
        for sid, spec in raw.items()
    }


def scales(active_only: bool = False, ref: str | None = None) -> dict[str, Scale]:
    """All registered scales, keyed by id."""
    reg = _registry(ref)
    return {k: v for k, v in reg.items() if v.status == "active" or not active_only}


def table(active_only: bool = False, ref: str | None = None) -> pd.DataFrame:
    """The registry of spatial scales as a table, one row per scale (``geo.scales()``).

    Columns: ``label``, ``kind`` (admin, grouping, grid, custom), ``parent`` (the
    coarser scale it nests in), ``children``, ``id_pattern``, ``example`` and
    ``status`` (active or planned). ``active_only=True`` hides planned scales.
    """
    import pandas as pd
    rows = [{"scale": s.id, "label": s.label, "kind": s.kind, "parent": s.parent, "children": s.children,
             "id_pattern": s.id_pattern, "example": s.extra.get("example"), "status": s.status}
            for s in scales(active_only, ref).values()]
    return pd.DataFrame(rows).set_index("scale")


def get(scale: str, ref: str | None = None) -> Scale:
    reg = _registry(ref)
    if scale not in reg:
        raise KeyError(f"Unknown scale {scale!r}; known scales: {', '.join(reg)}")
    return reg[scale]


def ancestors(scale: str, ref: str | None = None) -> list[str]:
    """Coarser scales a unit of ``scale`` nests in, in breadth-first order.

    Administrative scales follow ``parent``; a scale whose units are unions of
    ``scale`` units (a grouping, such as statistical regions) is also an ancestor. The parent
    chain of each level comes before the groupings of that level, e.g.
    ``municipality -> [province, department, country]``.
    """
    reg = _registry(ref)
    found: list[str] = []
    frontier = [scale]
    while frontier:
        current = frontier.pop(0)
        nxt = [reg[current].parent] if reg[current].parent else []
        nxt += [s.id for s in reg.values() if s.children == current]
        for s in nxt:
            if s not in found and s != scale:
                found.append(s)
                frontier.append(s)
    return found


def scale_of(geo_id: str, ref: str | None = None) -> str:
    """The scale a geo ID belongs to, from the ID patterns (e.g. a municipality ID -> ``"municipality"``)."""
    hits = [s.id for s in _registry(ref).values() if s.matches(geo_id)]
    if len(hits) != 1:
        raise ValueError(f"{geo_id!r} matches {len(hits)} scales")
    return hits[0]
