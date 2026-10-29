"""Generic tests: they hold for any project built from this template, whatever its data.

They read the scale registry, units and metadata instead of hard-coding values,
so a new project inherits them unchanged. Project-specific facts belong in
tests/test_project.py.
"""

import json
import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

import geo4bolivia as geo
from geo4bolivia import metadata, project, store, validate
from geo4bolivia.aggregate import EQUAL_AREA_CRS

ACTIVE = list(geo.scales(active_only=True).index)
DATASETS = list(metadata.dataset_ids())
needs_data = pytest.mark.skipif(not DATASETS, reason="no datasets registered yet")


# --- project and geography -------------------------------------------------------------

def test_project_config_matches_the_package():
    cfg = geo.config()
    assert cfg["package"] == geo.PACKAGE
    assert store.raw_url("geo/units.csv").startswith("https://raw.githubusercontent.com/" + cfg["repository"])


def test_every_unit_matches_exactly_one_scale_pattern():
    for gid, scale in zip(geo.units()["geo_id"], geo.units()["scale"]):
        assert geo.scale_of(gid) == scale


def test_ids_start_with_the_country_code():
    assert geo.units()["geo_id"].str.startswith(project.country_code()).all()


@pytest.mark.parametrize("scale", ACTIVE)
def test_units_and_boundaries_agree(scale):
    u, b = geo.units(scale), geo.boundaries(scale)
    assert len(u) > 0 and u["geo_id"].is_unique
    assert set(u["geo_id"]) == set(b["geo_id"])
    assert b.geometry.is_valid.all()


@pytest.mark.parametrize("scale,target", [(s, t) for s in ACTIVE for t in geo.ancestors(s) if t in ACTIVE])
def test_crosswalks_cover_every_unit_and_sum_to_one(scale, target):
    xw = geo.crosswalk(scale, target)
    assert set(xw["geo_id_from"]) == set(geo.units(scale)["geo_id"])
    assert np.allclose(xw.groupby("geo_id_from")["weight_area"].sum(), 1)


def test_areas_add_up_to_the_country():
    u = geo.units()
    country = u.loc[u["scale"] == "country", "area_km2"].sum()
    for scale in ACTIVE:
        assert u.loc[u["scale"] == scale, "area_km2"].sum() == pytest.approx(country, rel=1e-3)


# --- datasets ------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_every_dataset_loads_as_a_panel(dataset):
    df = geo.load(dataset)
    assert list(df.columns[:2]) == ["geo_id", "year"]
    assert not df.duplicated(["geo_id", "year"]).any()
    assert set(geo.dictionary(dataset)["variable"]) == set(df.columns)
    first = int(df["year"].min())
    one = geo.load(dataset, years=first, geometry=True)
    assert isinstance(one, gpd.GeoDataFrame) and one.geometry.notna().all() and set(one["year"]) == {first}


@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_sum_variables_keep_their_totals_up_the_hierarchy(dataset):
    rules = metadata.aggregation_rules(dataset)
    sums = [v for v, r in rules.items() if r == "sum"]
    scale = metadata.resource(dataset)["geo:scale"]
    targets = [t for t in geo.ancestors(scale) if t in ACTIVE]
    if not sums or not targets:
        pytest.skip("no sum variables or no coarser scale")
    df = geo.load(dataset, variables=sums)
    for target in targets:
        up = geo.aggregate(df, to=target, dataset=dataset)
        assert up[sums].sum().to_numpy() == pytest.approx(df[sums].sum().to_numpy())


def test_aggregation_refuses_without_a_rule():
    finest = ACTIVE[-1] if geo.ancestors(ACTIVE[-1]) else next(s for s in ACTIVE if geo.ancestors(s))
    df = geo.units(finest)[["geo_id"]].assign(x=1.0)
    with pytest.raises(ValueError, match="No aggregation rule"):
        geo.aggregate(df, to=geo.ancestors(finest)[0])
    out = geo.aggregate(df, to="country", rules={"x": "sum"})
    assert out["x"].item() == len(df)


def _grid(cell_m=10_000):
    country = geo.boundaries("country").to_crs(EQUAL_AREA_CRS)
    x0, y0, x1, y1 = country.total_bounds
    cells = [box(x, y, x + cell_m, y + cell_m) for x in np.arange(x0, x1, cell_m) for y in np.arange(y0, y1, cell_m)]
    grid = gpd.GeoDataFrame({"cell": [f"c{i}" for i in range(len(cells))]}, geometry=cells, crs=EQUAL_AREA_CRS)
    return grid[grid.intersects(country.geometry.iloc[0])].to_crs("EPSG:4326")


def test_overlay_to_a_grid_preserves_totals_and_bounds():
    scale = ACTIVE[1] if len(ACTIVE) > 1 else ACTIVE[0]
    u = geo.units(scale)
    df = u[["geo_id"]].assign(pop=u["area_km2"].astype(float) * 10, rate=np.linspace(0, 1, len(u)))
    out = geo.overlay(df, _grid(), extensive=["pop"], intensive=["rate"], id_col="cell")
    assert out["pop"].sum() == pytest.approx(df["pop"].sum(), rel=0.005)
    assert out["rate"].between(-1e-9, 1 + 1e-9).all()


def test_overlay_accepts_a_geodataframe_as_source():
    scale = ACTIVE[1] if len(ACTIVE) > 1 else ACTIVE[0]
    u = geo.units(scale)
    df = u[["geo_id"]].assign(pop=1.0)
    by_id = geo.overlay(df, "country", extensive=["pop"])
    by_gdf = geo.overlay(df, "country", extensive=["pop"], source=geo.boundaries(scale))
    assert by_gdf["pop"].sum() == pytest.approx(by_id["pop"].sum())


@needs_data
def test_load_accepts_numpy_years_and_rejects_unknown_variables():
    dataset = DATASETS[0]
    year = geo.load(dataset)["year"].max()            # a numpy integer
    assert set(geo.load(dataset, years=year)["year"]) == {year}
    with pytest.raises(ValueError, match="no variable"):
        geo.load(dataset, variables=["not_a_variable"])


# --- building your own data ----------------------------------------------------------------

def test_link_matches_names_ignoring_accents_case_and_spaces():
    scale = ACTIVE[1] if len(ACTIVE) > 1 else ACTIVE[0]
    u = geo.units(scale)
    mine = pd.DataFrame({"unit": u["name"].str.upper().str.replace(" ", ""), "year": 2020, "v": 1.0})
    linked = geo.link(mine, scale=scale, on="unit")
    assert (linked["geo_id"] == u["geo_id"]).all()
    assert geo.check(linked, scale=scale) == []
    with pytest.raises(ValueError, match="match no"):
        geo.link(pd.DataFrame({"unit": ["Atlantis"]}), scale=scale, on="unit", key="name")


def test_check_reports_problems():
    scale = ACTIVE[0]
    gid = geo.units(scale)["geo_id"].iloc[0]
    bad = pd.DataFrame({"geo_id": [gid, gid, "XX-99"], "year": [2020, 2020, 2020], "v": [1, 2, 3]})
    problems = " | ".join(geo.check(bad, scale=scale))
    assert "duplicate" in problems and "not found" in problems
    assert "no scale" in " | ".join(geo.check(pd.DataFrame({"geo_id": ["XX-99"], "year": [2020]})))


def test_save_writes_a_valid_dataset(tmp_path):
    scale = ACTIVE[1] if len(ACTIVE) > 1 else ACTIVE[0]
    u = geo.units(scale)
    df = pd.DataFrame({"geo_id": np.repeat(u["geo_id"], 2), "year": np.tile([2020, 2021], len(u)), "pop": 1.0})
    pkg = geo.save(df, "mydata", scale=scale, directory=tmp_path,
                   variables={"pop": {"description": "Population", "unit": "people", "aggregation": "sum"}})
    assert (tmp_path / f"data/{scale}/mydata.parquet").exists()
    saved = json.loads((tmp_path / "metadata/mydata.datapackage.json").read_text())
    assert saved == pkg and saved["resources"][0]["geo:period"] == [2020, 2021]
    field = saved["resources"][0]["schema"]["fields"][2]
    assert field["geo:aggregation"] == "sum" and field["title"] == "pop"


@needs_data
def test_combine_aggregates_datasets_to_one_scale():
    pairs = [(d, metadata.resource(d)["geo:scale"]) for d in DATASETS]
    d, s = pairs[0]
    out = geo.combine([d], scale=s)
    assert len(out) == len(geo.load(d))


def test_zonal_sums_a_raster_over_units(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds
    shapes = geo.boundaries("country")
    x0, y0, x1, y1 = shapes.total_bounds
    path = tmp_path / "ones.tif"
    with rasterio.open(path, "w", driver="GTiff", width=400, height=400, count=1, dtype="float32",
                       crs="EPSG:4326", transform=from_bounds(x0, y0, x1, y1, 400, 400), nodata=-1) as dst:
        dst.write(np.ones((1, 400, 400), dtype="float32"))
    out = geo.zonal(path, scale=ACTIVE[1] if len(ACTIVE) > 1 else ACTIVE[0], stats=("sum", "mean", "count"),
                    name="ones", year=2020)
    assert (out["ones_mean"].dropna() == 1).all() and (out["ones_sum"] == out["ones_count"]).all()
    assert list(out.columns[:2]) == ["geo_id", "year"]


# --- validation ----------------------------------------------------------------------------

def test_everything_validates():
    reports = validate.run()
    assert all(r.ok for r in reports), "\n".join(str(r) for r in reports if not r.ok)


@pytest.fixture
def repo_copy(tmp_path, monkeypatch):
    """A copy of geo/, metadata/ and data/ that the package reads instead of the checkout."""
    root = store.repo_root()
    for part in ("geo", "metadata", "data"):
        shutil.copytree(root / part, tmp_path / part)
    shutil.copy(root / "project.yaml", tmp_path / "project.yaml")
    caches = (project.local_root, project.config, metadata.package, metadata.dataset_ids)
    monkeypatch.setenv(f"{project.ENV_PREFIX}_DATA_DIR", str(tmp_path))
    for f in caches:
        f.cache_clear()
    yield tmp_path
    monkeypatch.delenv(f"{project.ENV_PREFIX}_DATA_DIR")
    for f in caches:
        f.cache_clear()


@needs_data
def test_validator_catches_broken_data(repo_copy):
    dataset = DATASETS[0]
    res = metadata.resource(dataset)
    broken = pd.read_parquet(repo_copy / res["geo:parquet"])
    broken.loc[0, "geo_id"] = "XX-99"                      # unknown unit
    broken = pd.concat([broken, broken.iloc[[2]]])         # duplicate unit-year
    broken.to_parquet(repo_copy / res["geo:parquet"], index=False)
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    for expected in ("CSV and Parquet differ", "duplicate", "not in geo/units"):
        assert expected in errors


@needs_data
def test_validator_catches_incomplete_metadata(repo_copy):
    dataset = DATASETS[0]
    path = repo_copy / f"metadata/{dataset}.datapackage.json"
    pkg = json.loads(path.read_text())
    field = pkg["resources"][0]["schema"]["fields"][-1]
    del field["title"]                                     # no label
    pkg["licenses"] = [{"path": "https://example.org"}]    # license without a name
    pkg["geo:map"] = {"variable": "not_a_variable", "year": 2000}
    path.write_text(json.dumps(pkg))
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    for expected in (f"{field['name']} has no 'title'", "licenses", "geo:map"):
        assert expected in errors


@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_dictionary_has_a_label_for_every_column(dataset):
    d = geo.dictionary(dataset)
    assert list(d.columns[:3]) == ["variable", "label", "description"]
    assert d["label"].str.len().gt(0).all() and d["description"].str.len().gt(0).all()


@needs_data
def test_for_geometrics_returns_its_three_inputs():
    dataset = DATASETS[0]
    gdf, df, df_dict = geo.for_geometrics(dataset, years=int(geo.load(dataset)["year"].max()))
    assert list(df_dict["var_name"]) == list(df.columns)
    assert df_dict.set_index("var_name").loc[["geo_id", "year"], "type"].tolist() == ["entity", "time"]
    assert set(gdf["geo_id"]) == set(df["geo_id"]) and df["name"].notna().all()


@needs_data
def test_for_expdpy_returns_a_labelled_panel_with_groups():
    dataset = DATASETS[0]
    scale = metadata.resource(dataset)["geo:scale"]
    groups = [s for s in geo.ancestors(scale) if s in ACTIVE and s != "country"][:1]
    df, df_def = geo.for_expdpy(dataset, groups=groups)
    assert list(df_def["var_name"]) == list(df.columns)
    types = df_def.set_index("var_name")["type"]
    assert types["geo_id"] == "entity" and types["year"] == "time"
    for g in groups:
        assert df[g].notna().all() and types[g] == "factor"
    with pytest.raises(ValueError, match="do not nest"):
        geo.for_expdpy(dataset, groups=[scale])
