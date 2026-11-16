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
    assert u["scale"].value_counts().to_dict() == {"municipality": 343, "province": 113, "department": 9, "country": 1}
    m = geo.units("municipality")
    assert (m["geo_id"].str[:8] == m["parent_id"]).all()
    assert m["ine_code"].is_unique and m["mun_id"].is_unique
    assert m["gid"].dropna().is_unique and m["gid"].isna().sum() == 4           # four units created after GADM's map
    assert m["asdf_id"].dropna().is_unique and m["asdf_id"].isna().sum() == 10  # ten units whose polygon changed


def test_units_created_since_2015():
    u = geo.units().set_index("geo_id")
    new = {"BO-02-12-04": "031304", "BO-07-04-05": "050405", "BO-07-02-04": "051204", "BO-03-09-01": "080901"}
    for geo_id, ine in new.items():
        assert u.loc[geo_id, "ine_code"] == ine and pd.isna(u.loc[geo_id, "gid"])
    assert u.loc["BO-03-09", "name"] == "Territorio Indígena Multiétnico"   # its own Beni province
    assert u.loc["BO-03-09", "ine_code"] == "0809" and u.loc["BO-03-09-01", "parent_id"] == "BO-03-09"


def test_lakes_are_not_units():
    names = geo.units("municipality")["name_gadm"]
    assert not names.str.contains("Lago").any()


def test_boundaries_come_from_the_sdsn_map():
    m = geo.units("municipality")
    lk = pd.read_csv(store.repo_root() / "raw/lookups/municipalities343.csv", dtype={"ine_code": str})
    assert dict(zip(lk["geo_id"], lk["ine_code"])) == dict(zip(m["geo_id"], m["ine_code"]))
    assert set(geo.boundaries("municipality")["geo_id"]) == set(m["geo_id"])
    assert not (store.repo_root() / "raw/boundaries/gadm41_BOL_3.json").exists()   # no GADM geometry


def test_salt_flats_and_lakes_are_outside_every_unit():
    u = geo.units().set_index("geo_id")
    area = u.groupby("scale")["area_km2"].sum()
    # the scales are exact unions of the municipalities, holes included
    assert np.allclose(area[["country", "department", "province"]], area["municipality"], rtol=1e-6)
    assert 1.06e6 < area["country"] < 1.075e6       # ~13,000 km² of salt flats and lakes left out
    assert u.loc["BO-05-10-02", "area_km2"] < 400   # Coipasa: most of the Salar de Coipasa is a hole
    assert u.loc["BO-07-02-03", "area_km2"] < 9000  # Uyuni: the Salar de Uyuni (~9,500 km²) is a hole


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
    assert la_paz["name"] == "Nuestra Señora de La Paz" and la_paz["ine_code"] == "020101"   # the Atlas's spelling
    assert la_paz["name_ds4bolivia"] == "La Paz"
    assert la_paz["asdf_id"] == "176" and la_paz["mun_id"] == "20101"


def test_homonyms_follow_the_polygons():
    """DS4Bolivia's attribute rows are swapped for three homonym pairs; geo IDs follow the polygons."""
    m = geo.units("municipality").set_index("asdf_id")
    assert m.loc["57", "department_id"] == "BO-03"           # San Javier polygon 57 lies in Beni
    assert m.loc["57", "ine_code"] == "080102"
    assert m.loc["264", "department_id"] == "BO-08"          # ... and polygon 264 in Santa Cruz
    lk = pd.read_csv(store.repo_root() / "raw/lookups/municipalities339_gadm.csv")
    assert lk["swapped"].sum() == 6


def test_polygon_data_skip_the_changed_units():
    lk = pd.read_csv(store.repo_root() / "raw/lookups/municipalities343.csv")
    changed = set(lk.loc[lk["changed"], "geo_id"])
    assert len(changed) == 10 and "BO-07-04-01" in changed and "BO-02-12-04" in changed   # Colquechaca, Raqaypampa
    for dataset in ("pop", "ntl", "emb"):
        ids = set(geo.load(dataset)["geo_id"])
        assert len(ids) == 333 and not ids & changed


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
    assert len(xw) == 343 and xw["geo_id_to"].nunique() == 9
    assert np.allclose(xw["weight_area"], 1)


# --- datasets ---------------------------------------------------------------------------

def test_population_panel_and_aggregation():
    df = geo.load("pop")
    assert len(df) == 333 * 20 and df["year"].agg(["min", "max"]).tolist() == [2001, 2020]
    dep = geo.aggregate(df, to="department", dataset="pop")
    assert len(dep) == 9 * 20 and (dep["n_units"].groupby(dep["year"]).sum() == 333).all()
    assert np.isclose(dep.loc[dep["year"] == 2020, "pop"].sum(), df.loc[df["year"] == 2020, "pop"].sum())


def test_ntl_logs_are_not_aggregable():
    df = geo.load("ntl")
    assert df["year"].agg(["min", "max"]).tolist() == [2012, 2020]
    with pytest.raises(ValueError, match="No aggregation rule"):
        geo.aggregate(df, to="department", dataset="ntl", variables="ln_NTLpc")


SDG_GOALS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17]


def test_sdg_goal_datasets_hold_index_and_indicators():
    names = set()
    for g in SDG_GOALS:
        fields = [f["name"] for f in geo.metadata.fields(f"sdg{g:02d}") if not f.get("geo:role")]
        assert fields[0] == f"index_sdg{g}"
        assert all(f.startswith(f"sdg{g}_") for f in fields[1:])
        names |= set(fields)
    assert len(names) == 81 + 15
    assert [f["name"] for f in geo.metadata.fields("sdg") if not f.get("geo:role")] == \
        ["index_sdg", "rank_sdg", "population", "urbanization"]


def test_sdg_panels_hold_both_periods():
    mpi = geo.load("sdg01", variables="sdg1_2_mpi")
    assert len(mpi) == 343 * 2 and set(mpi["year"]) == {2012, 2024}
    sucre = mpi[mpi["geo_id"] == "BO-01-06-02"].set_index("year")["sdg1_2_mpi"]   # values of the Atlas workbook
    assert sucre.to_dict() == {2012: 0.071, 2024: 0.014}
    field = {f["name"]: f for f in geo.metadata.fields("sdg02")}["sdg2_2_dcn"]
    assert field["geo:reference_years"] == {"2012": "2008", "2024": "2023"}       # EDSA survey years


def test_sdg_index_and_ranking():
    ids = geo.load("sdg").set_index(["geo_id", "year"])
    assert ids.loc[("BO-04-17-04", 2024), "rank_sdg"] == 1                       # Nuestra Señora de La Paz
    assert ids.loc[("BO-02-12-04", 2024), "rank_sdg"] == 343                     # TIOC-Raqaypampa
    assert ids.xs(2024, level="year")["rank_sdg"].sort_values().tolist() == list(range(1, 344))
    assert ids.xs(2024, level="year")["population"].sum() == 11_365_333 - 400    # census; Huarina differs by 400
    goals = pd.concat([geo.load(f"sdg{g:02d}", variables=f"index_sdg{g}").set_index(["geo_id", "year"])
                       for g in SDG_GOALS], axis=1)
    assert np.allclose(goals.mean(axis=1), ids["index_sdg"].reindex(goals.index), atol=0.1)


def test_population_weighted_sdg_by_department():
    df = geo.load("sdg01", variables="sdg1_2_mpi")
    out = geo.aggregate(df, to="department", rules={"sdg1_2_mpi": "weighted_mean:population"},
                        weights=geo.load("sdg", variables="population"))
    assert len(out) == 9 * 2 and out["sdg1_2_mpi"].between(0, 1).all()


@pytest.mark.parametrize("dataset", ["emb", "embpw"])
def test_embeddings(dataset):
    df = geo.load(dataset)
    assert len(df) == 333 and set(df["year"]) == {2017}
    assert len(geo.metadata.variables(dataset)) == 64 and df.filter(regex=r"^A\d{2}$").notna().all().all()
