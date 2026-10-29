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


def test_boundaries_come_from_geoboundaries():
    m = geo.units("municipality")
    assert m["gb_id"].notna().all() and m["gb_id"].is_unique       # one geoBoundaries shapeID each
    lk = pd.read_csv(store.repo_root() / "raw/lookups/municipalities339_geoboundaries.csv", dtype={"shapeID": str})
    assert dict(zip(lk["geo_id"], lk["shapeID"])) == dict(zip(m["geo_id"], m["gb_id"]))
    assert not (store.repo_root() / "raw/boundaries/gadm41_BOL_3.json").exists()   # no GADM geometry


def test_salt_flats_and_lakes_are_outside_every_unit():
    u = geo.units().set_index("geo_id")
    area = u.groupby("scale")["area_km2"].sum()
    # the scales are exact unions of the municipalities, holes included
    assert np.allclose(area[["country", "department", "province"]], area["municipality"], rtol=1e-6)
    assert 1.06e6 < area["country"] < 1.075e6       # ~13,000 km² of salt flats and lakes left out
    assert u.loc["BO-05-10-02", "area_km2"] < 400   # Coipasa: most of the Salar de Coipasa is a hole


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


def test_link_refuses_names_shared_by_several_municipalities():
    table = pd.DataFrame({"mun": ["San Javier", "Uyuni"]})
    with pytest.raises(ValueError, match="BO-03-01-01, BO-08-10-04"):
        geo.link(table, scale="municipality", on="mun", key="name")
    with pytest.warns(UserWarning, match="name several"):
        out = geo.link(table, scale="municipality", on="mun", key="name", errors="warn")
    assert out["geo_id"].isna().tolist() == [True, False]


def test_crosswalks_are_nested():
    xw = geo.crosswalk("municipality", "department")
    assert len(xw) == 339 and xw["geo_id_to"].nunique() == 9
    assert np.allclose(xw["weight_area"], 1)


# --- datasets ---------------------------------------------------------------------------

def test_population_panel_and_aggregation():
    df = geo.load("pop")
    assert len(df) == 339 * 20 and df["year"].agg(["min", "max"]).tolist() == [2001, 2020]
    dep = geo.aggregate(df, to="department", dataset="pop")
    assert len(dep) == 9 * 20 and (dep["n_units"].groupby(dep["year"]).sum() == 339).all()
    assert np.isclose(dep.loc[dep["year"] == 2020, "pop"].sum(), df.loc[df["year"] == 2020, "pop"].sum())


def test_ntl_logs_are_not_aggregable():
    df = geo.load("ntl")
    assert df["year"].agg(["min", "max"]).tolist() == [2012, 2020]
    with pytest.raises(ValueError, match="No aggregation rule"):
        geo.aggregate(df, to="department", dataset="ntl", variables="ln_NTLpc")


SDG_GOALS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17]


def test_sdg_goal_datasets_hold_index_components_and_context():
    names = set()
    for g in SDG_GOALS:
        fields = [f["name"] for f in geo.metadata.fields(f"sdg{g:02d}") if not f.get("geo:role")]
        assert fields[0] == f"index_sdg{g}" and fields[-2:] == ["population_2020", "urbano_2012"]
        assert all(f.startswith(f"sdg{g}_") for f in fields[1:-2])
        names |= set(fields)
    assert len(names) == 62 + 15 + 2


def test_sdg_indicators_are_stored_at_their_reference_years():
    mpi = geo.load("sdg01", variables="sdg1_2_mpi").dropna()
    assert len(mpi) == 339 and set(mpi["year"]) == {2012}
    malaria = geo.load("sdg03", variables="sdg3_3_imr").dropna()         # average 2014-17 -> 2015
    assert set(malaria["year"]) == {2015}
    index = geo.load("sdg03", variables="index_sdg3").dropna()           # latest component: dengue 2018
    assert len(index) == 339 and set(index["year"]) == {2018}


def test_sdg_rows_follow_ine_codes_for_homonyms():
    pop = geo.load("sdg01", variables="population_2020", years=2020).set_index("geo_id")["population_2020"]
    assert pop["BO-08-10-04"] == 16027          # San Javier, Santa Cruz
    assert pop["BO-03-01-01"] == 5906           # San Javier, Beni


def test_population_weighted_sdg_by_department():
    df = geo.load("sdg01", variables="sdg1_2_mpi", years=2012)
    out = geo.aggregate(df, to="department", rules={"sdg1_2_mpi": "weighted_mean:pop"}, weights=geo.load("pop"))
    assert len(out) == 9 and out["sdg1_2_mpi"].between(0, 1).all()


@pytest.mark.parametrize("dataset", ["emb", "embpw"])
def test_embeddings(dataset):
    df = geo.load(dataset)
    assert len(df) == 339 and set(df["year"]) == {2017}
    assert len(geo.metadata.variables(dataset)) == 64 and df.filter(regex=r"^A\d{2}$").notna().all().all()
