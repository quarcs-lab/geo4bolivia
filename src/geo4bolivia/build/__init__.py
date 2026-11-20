"""Building the published files from ``raw/``: generic helpers, and the entry point.

The helpers (``common``, ``gadm``, ``geoboundaries``) are generic. A project's own
builders live in its data repository, in a ``builders/`` package next to ``raw/``,
whose ``__init__.py`` defines:

- ``build_geo``: a function that writes ``geo/`` (units, boundaries, crosswalks);
- ``DATASETS``: ``{dataset id: function}``, one builder per dataset.

``<package> build`` runs them from a checkout of that repository: the geo builder
first (dataset builders take their geo IDs from ``geo/units``), then each dataset,
then the catalog. ``_template.py`` and ``_geo_template.py`` are starting points.
"""

from __future__ import annotations

import importlib.util
import sys

from .. import store
from .common import write_catalog

BUILDERS = "builders"


def load_builders():
    """Import the ``builders`` package of the local checkout of the data repository."""
    folder = store.repo_root() / BUILDERS
    init = folder / "__init__.py"
    if not init.exists():
        raise SystemExit(f"No {BUILDERS}/__init__.py in {folder.parent}: the builders live in the data repository")
    spec = importlib.util.spec_from_file_location(BUILDERS, init, submodule_search_locations=[str(folder)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[BUILDERS] = module
    spec.loader.exec_module(module)
    return module


def build(target: str = "all") -> None:
    """Run the geo builder, the dataset builders or one of them, then rewrite the catalog."""
    builders = load_builders()
    datasets = dict(builders.DATASETS)
    if target not in ("all", "geo", *datasets):
        raise SystemExit(f"Unknown build target {target!r}; use all, geo or one of {', '.join(datasets)}")
    if target in ("all", "geo"):
        print("geo")
        builders.build_geo()
    for name, builder in datasets.items():
        if target in ("all", name):
            print(name)
            builder()
    print("catalog")
    write_catalog()
