"""Build ``geo/``: units with geo IDs, boundaries and crosswalks for every active scale.

Inputs (in ``raw/``):
- ``boundaries/geoboundaries/geoBoundaries-BOL-ADM3.geojson``: geoBoundaries gbOpen ADM3 (commit
  9469f09), the 339 municipalities from GeoBolivia, in the public domain; the salt flats of
  Uyuni and Coipasa and lakes Poopó and Uru Uru lie outside every municipality, and Lake
  Titicaca outside the country
- ``lookups/municipalities339_geoboundaries.csv``: each geoBoundaries ``shapeID`` matched to a
  municipality by ``scripts/match_geoboundaries.py``
- ``lookups/municipalities339_gadm.csv``: the municipalities' GADM 4.1 codes and names, matched to
  DS4Bolivia (``asdf_id``, INE ``mun_id``) by ``scripts/match_municipalities.py``
- ``lookups/department_names.csv`` and ``lookups/province_names.csv``: GADM codes, hand-checked
  names (GADM writes them without spaces, e.g. ``JoséMaríaLinares``) and INE codes

The geo IDs follow GADM 4.1's numbering, built from the codes alone (no GADM geometry is used),
which differs from the INE codes (La Paz is ``BO-04`` here and ``02`` in INE); the INE codes are
kept in ``ine_code`` and the GADM codes in ``gid``. The municipalities are simplified as a coverage
(about 100 m), and provinces, departments and the country are their exact unions, so every scale
nests exactly.
"""

from __future__ import annotations

import pandas as pd

from .. import store
from .common import publish_geo
from .gadm import gadm_units
from .geoboundaries import from_geoboundaries

GEOBOUNDARIES_FILE = "raw/boundaries/geoboundaries/geoBoundaries-BOL-ADM3.geojson"
LEVELS = {1: "department", 2: "province", 3: "municipality"}
TOLERANCE_M = 100


def _check(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(f"raw lookups are inconsistent: {message}")


def _parent_code(gid: pd.Series) -> pd.Series:
    """'BOL.1.1.1_2' -> 'BOL.1.1' (the parent's GADM code, without its version suffix)."""
    return gid.str.replace(r"_\d+$", "", regex=True).str.rsplit(".", n=1).str[0]


def build() -> None:
    raw = store.repo_root() / "raw"
    municipalities = pd.read_csv(raw / "lookups/municipalities339_gadm.csv", dtype={"ine_code": str})
    departments = pd.read_csv(raw / "lookups/department_names.csv", dtype={"ine_code": str})
    provinces = pd.read_csv(raw / "lookups/province_names.csv", dtype={"ine_code": str})
    matched = pd.read_csv(raw / "lookups/municipalities339_geoboundaries.csv", dtype={"shapeID": str})
    _check(len(municipalities) == 339 and municipalities["GID_3"].is_unique, "339 distinct municipalities")
    _check(set(matched["GID_3"]) == set(municipalities["GID_3"]), "geoBoundaries lookup vs GADM codes")

    # one row per municipality with the GADM codes and names of every level
    unversioned = lambda gid: gid.str.replace(r"_\d+$", "", regex=True)  # noqa: E731
    prov = provinces.set_index(unversioned(provinces["GID_2"]))
    dep = departments.set_index(unversioned(departments["GID_1"]))
    codes = municipalities[["GID_3", "name_gadm"]].rename(columns={"name_gadm": "NAME_3"})
    p = _parent_code(codes["GID_3"])
    _check(p.isin(prov.index).all(), "every municipality's province is in province_names.csv")
    codes["GID_2"], codes["NAME_2"] = p.map(prov["GID_2"]), p.map(prov["name_gadm"])
    d = _parent_code(codes["GID_2"])
    _check(d.isin(dep.index).all(), "every province's department is in department_names.csv")
    codes["GID_1"], codes["NAME_1"] = d.map(dep["GID_1"]), d.map(dep["name_gadm"])
    _check(codes["GID_2"].nunique() == len(provinces) and codes["GID_1"].nunique() == len(departments),
           "every province and department has municipalities")

    units = gadm_units(codes, LEVELS)

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
    units["gb_id"] = units["gid"].map(matched.set_index("GID_3")["shapeID"])

    # the lookup's geo_ids must be the ones the GADM codes give
    gid_to_geo = units.set_index("gid")["geo_id"]
    _check((matched["GID_3"].map(gid_to_geo) == matched["geo_id"]).all(), "geoBoundaries lookup geo_id vs GADM codes")
    layers = from_geoboundaries(store.repo_root() / GEOBOUNDARIES_FILE, matched[["shapeID", "geo_id"]], units,
                                tolerance_m=TOLERANCE_M)
    units = units[["geo_id", "scale", "name", "parent_id", "gid", "ine_code", "asdf_id", "mun_id", "gb_id", "name_gadm"]]
    publish_geo(units, layers)
