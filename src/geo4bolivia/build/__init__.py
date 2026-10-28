"""Builders that regenerate every published file from ``raw/``.

``geo`` must run first: dataset builders take their geo IDs from geo/units.
Register each new dataset builder in DATASETS (see CONTRIBUTING_DATA.md).
"""

from . import geo
from .common import write_catalog

DATASETS = {}   # e.g. {"gdppc": gdppc.build} after `from . import gdppc`


def build(target: str = "all") -> None:
    if target in ("all", "geo"):
        print("geo")
        geo.build()
    for name, builder in DATASETS.items():
        if target in ("all", name):
            print(name)
            builder()
    if target not in ("all", "geo", *DATASETS):
        raise SystemExit(f"Unknown build target {target!r}; use all, geo or one of {', '.join(DATASETS)}")
    print("catalog")
    write_catalog()
