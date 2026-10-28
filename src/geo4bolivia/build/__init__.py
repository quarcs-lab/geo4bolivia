"""Builders that regenerate every published file from ``raw/``.

``geo`` must run first: dataset builders take their geo IDs from geo/units.
Register each new dataset builder in DATASETS (see CONTRIBUTING_DATA.md).
"""

from . import emb, geo, ntl, pop, sdg
from .common import write_catalog

DATASETS = {"pop": pop.build, "ntl": ntl.build, "sdg": sdg.build, "emb": emb.build, "embpw": emb.build_pw}


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
