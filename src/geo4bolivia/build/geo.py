"""Build ``geo/``: units with geo IDs, boundaries and crosswalks for every active scale.

Inputs (in ``raw/``):
- ``boundaries/gadm41_BOL_3.json``: GADM 4.1 level 3, the 339 municipalities plus
  5 Lake Titicaca polygons (``TYPE_3 == "Lago"``), which are left out
- ``lookups/municipalities339_gadm.csv``: GADM municipalities matched to DS4Bolivia
  (``asdf_id``, INE ``mun_id``) by ``scripts/match_municipalities.py``
- ``lookups/department_names.csv`` and ``lookups/province_names.csv``: hand-checked
  names (GADM writes them without spaces, e.g. ``JoséMaríaLinares``) and INE codes

Provinces, departments and the country are dissolved from the municipalities, so
every scale nests exactly in the next one. IDs follow the GADM order, which
differs from the INE codes (La Paz is ``BO-04`` here and ``02`` in INE); the INE
codes are kept in the ``ine_code`` column.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import store
from .common import publish_geo
from .gadm import from_gadm

GADM_FILE = "raw/boundaries/gadm41_BOL_3.json"
LEVELS = {1: "department", 2: "province", 3: "municipality"}


def _check(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(f"raw lookups are inconsistent: {message}")


def build() -> None:
    raw = store.repo_root() / "raw"
    shapes = gpd.read_file(store.repo_root() / GADM_FILE)
    _check((shapes["TYPE_3"] == "Lago").sum() == 5, "expected 5 lake polygons in GADM level 3")
    shapes = shapes[shapes["TYPE_3"] != "Lago"].reset_index(drop=True)
    municipalities = pd.read_csv(raw / "lookups/municipalities339_gadm.csv", dtype={"ine_code": str})
    departments = pd.read_csv(raw / "lookups/department_names.csv", dtype={"ine_code": str})
    provinces = pd.read_csv(raw / "lookups/province_names.csv", dtype={"ine_code": str})
    _check(set(shapes["GID_3"]) == set(municipalities["GID_3"]), "municipalities vs GADM GID_3")
    _check(set(shapes["GID_2"]) == set(provinces["GID_2"]), "provinces vs GADM GID_2")
    _check(set(shapes["GID_1"]) == set(departments["GID_1"]), "departments vs GADM GID_1")

    units, layers = from_gadm(shapes, LEVELS)

    # harmonized names and source keys, by GADM code
    names = pd.concat([municipalities[["GID_3", "name", "ine_code"]].rename(columns={"GID_3": "gid"}),
                       provinces[["GID_2", "name", "ine_code"]].rename(columns={"GID_2": "gid"}),
                       departments[["GID_1", "name", "ine_code"]].rename(columns={"GID_1": "gid"})])
    by_gid = names.set_index("gid")
    has = units["gid"].isin(by_gid.index)
    _check(has.sum() == len(names), "every department, province and municipality has a name")
    units.loc[has, "name"] = units.loc[has, "gid"].map(by_gid["name"])
    units["ine_code"] = units["gid"].map(by_gid["ine_code"])
    keys = municipalities.set_index("GID_3")
    units["asdf_id"] = units["gid"].map(keys["asdf_id"]).astype("Int64")
    units["mun_id"] = units["gid"].map(keys["mun_id"]).astype("Int64")
    units = units[["geo_id", "scale", "name", "parent_id", "gid", "ine_code", "asdf_id", "mun_id", "name_gadm"]]
    publish_geo(units, layers)
