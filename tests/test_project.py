"""Project-specific tests: facts about Bolivia's units and datasets.

Generic behaviour is tested in tests/test_core.py.
"""

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import store


# --- scales and units -----------------------------------------------------------------

def test_ancestors_follow_the_hierarchy():
    assert geo.ancestors("municipality") == ["province", "department", "country"]
    assert geo.ancestors("province") == ["department", "country"]
    assert geo.ancestors("department") == ["country"]
    assert geo.ancestors("country") == []


def test_scale_of_recognises_every_id_pattern():
    assert geo.scale_of("BO") == "country"
    assert geo.scale_of("BO-04") == "department"
    assert geo.scale_of("BO-04-17") == "province"
    assert geo.scale_of("BO-04-17-04") == "municipality"
    assert geo.scale_of("BO-INE-020101") == "municipality_ine"
    assert geo.scale_of("BO-G10K-r012c034") == "grid10k"


def test_units_are_unique_and_nest_by_prefix():
    u = geo.units()
    assert u["geo_id"].is_unique
    assert u["scale"].value_counts().to_dict() == {"municipality": 339, "province": 112, "department": 9, "country": 1}
    m = geo.units("municipality")
    assert (m["geo_id"].str[:8] == m["parent_id"]).all()
    assert m["gid"].is_unique and m["asdf_id"].is_unique and m["mun_id"].is_unique


def test_lakes_are_not_units():
    names = geo.units("municipality")["name_gadm"]
    assert not names.str.contains("Lago").any()


def test_ine_codes_nest_like_the_gadm_hierarchy():
    u = geo.units().set_index("geo_id")
    m = u[u["scale"] == "municipality"]
    assert m["ine_code"].str.fullmatch(r"\d{6}").all()
    assert (m["ine_code"].str[:4] == m["province_id"].map(u["ine_code"])).all()
    assert (m["ine_code"].str[:2] == m["department_id"].map(u["ine_code"])).all()
    assert u.loc["BO-04", "ine_code"] == "02"            # GADM order differs from INE: La Paz


def test_known_names_and_keys():
    u = geo.units().set_index("geo_id")
    assert u.loc["BO-04", "name"] == "La Paz"
    assert u.loc["BO-07-09", "name"] == "José María Linares"   # "JoséMaríaLinares" in GADM
    la_paz = u.loc["BO-04-17-04"]
    assert la_paz["name"] == "La Paz" and la_paz["ine_code"] == "020101"
    assert la_paz["asdf_id"] == "176" and la_paz["mun_id"] == "20101"


def test_homonyms_follow_the_polygons():
    """DS4Bolivia's attribute rows are swapped for three homonym pairs; geo IDs follow the polygons."""
    m = geo.units("municipality").set_index("asdf_id")
    assert m.loc["57", "department_id"] == "BO-03"           # San Javier polygon 57 lies in Beni
    assert m.loc["57", "ine_code"] == "080102"
    assert m.loc["264", "department_id"] == "BO-08"          # ... and polygon 264 in Santa Cruz
    lk = pd.read_csv(store.repo_root() / "raw/lookups/municipalities339_gadm.csv")
    assert lk["swapped"].sum() == 6


def test_link_by_ds4bolivia_keys():
    table = pd.DataFrame({"asdf_id": [176, 57], "mun_id": [20101, 80102]})
    by_asdf = geo.link(table, scale="municipality", on="asdf_id", key="asdf_id")
    by_ine = geo.link(table, scale="municipality", on="mun_id", key="mun_id")
    assert by_asdf["geo_id"].tolist() == by_ine["geo_id"].tolist() == ["BO-04-17-04", "BO-03-01-01"]


def test_link_by_name_within_a_department():
    m = geo.units("municipality")
    potosi = m[m["department_id"] == "BO-07"]
    out = geo.link(pd.DataFrame({"mun": ["Potosí", "Uyuni"]}), scale="municipality", on="mun", key="name")
    assert out["geo_id"].isin(potosi["geo_id"]).all()


def test_crosswalks_are_nested():
    xw = geo.crosswalk("municipality", "department")
    assert len(xw) == 339 and xw["geo_id_to"].nunique() == 9
    assert np.allclose(xw["weight_area"], 1)
