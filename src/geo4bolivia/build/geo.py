"""TEMPLATE geo builder for a new project (scripts/new_project.py installs it as build/geo.py).

It builds every administrative scale from one GADM file:

1. Download your country from https://gadm.org/download_country.html at the
   finest level you need (e.g. level 2, GeoJSON or GeoPackage) and save it, unedited,
   as raw/boundaries/<file> (set GADM_FILE below).
2. Make LEVELS match the admin scales in geo/scales.yaml (GADM level -> scale id).
3. Run ``uv run <package> build geo && uv run <package> validate``.

To add a grouping (regions made of whole units, like Global Data Lab regions),
register it in scales.yaml with ``children: <scale>``, add its units (scale,
name, parent_id) to ``units``, set ``<grouping>_id`` on the child units, and add
its dissolved layer, as geo4bolivia does in its build/geo.py.
"""

from .. import store
from .common import publish_geo
from .gadm import from_gadm

GADM_FILE = "raw/boundaries/gadm41_BOL_3.json"   # CHANGE: your GADM download
LEVELS = {1: "department", 2: "province", 3: "municipality"}           # CHANGE: GADM level -> scale id in geo/scales.yaml


def build() -> None:
    units, layers = from_gadm(store.repo_root() / GADM_FILE, LEVELS)
    publish_geo(units, layers)
