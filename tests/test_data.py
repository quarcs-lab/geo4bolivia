"""Generic tests on the project's data: they hold for any project built from this template.

They read the scale registry, units and metadata instead of hard-coding values, so a
new project inherits them unchanged. They need the data repository (see conftest.py):
a checkout next to this one, ``<PREFIX>_DATA_DIR``, or the network. Project-specific
facts are tested in the data repository; the analyses are tested on synthetic data
in the other test files.
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
needs_checkout = pytest.mark.skipif(project.local_root() is None, reason="needs a checkout of the data repository")
pytestmark = pytest.mark.data


# --- project and geography -------------------------------------------------------------

def test_project_config_matches_the_package():
    cfg = geo.config()
    assert cfg["package"] == geo.PACKAGE
    assert store.raw_url("geo/units.csv").startswith("https://raw.githubusercontent.com/" + cfg["repository"])


def test_every_unit_matches_its_scale_pattern():
    from geo4bolivia.scales import scales_of
    for gid, scale in zip(geo.units()["geo_id"], geo.units()["scale"]):
        assert scale in scales_of(gid)
        if len(scales_of(gid)) == 1:                     # IDs shared only by maps of the same units
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
        geo.aggregate(df, to=geo.ancestors(finest)[0], map=finest)
    out = geo.aggregate(df, to="country", rules={"x": "sum"}, map=finest)
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
    folder = tmp_path / "data/mydata"
    assert (folder / f"{scale}/mydata.parquet").exists() and (folder / f"{scale}/mydata.csv").exists()
    saved = json.loads((folder / "datapackage.json").read_text())
    assert saved == pkg and saved["resources"][0]["geo:period"] == [2020, 2021]
    assert saved["resources"][0]["geo:path"] == f"data/mydata/{scale}/mydata.csv"
    readme = (folder / "README.md").read_text()
    assert "Population" in readme and f"{scale}/mydata.csv" in readme
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

@needs_checkout
def test_everything_validates():
    reports = validate.run()
    assert all(r.ok for r in reports), "\n".join(str(r) for r in reports if not r.ok)


@pytest.fixture
def repo_copy(tmp_path, monkeypatch):
    """A copy of geo/ and data/ that the package reads instead of the checkout."""
    root = store.repo_root()
    for part in ("geo", "data"):
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
@needs_checkout
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
@needs_checkout
def test_validator_catches_incomplete_metadata(repo_copy):
    dataset = DATASETS[0]
    path = repo_copy / metadata.package_path(dataset)
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


# --- understanding the data ---------------------------------------------------------------

@needs_data
def test_datasets_catalog_reports_years_and_units():
    cat = geo.datasets()
    for col in ("dataset", "scale", "years", "units", "variables", "license"):
        assert col in cat.columns
    for _, row in cat.iterrows():
        res = metadata.resource(row["dataset"], row["scale"])
        df = geo.load(row["dataset"], scale=row["scale"])
        assert row["units"] == df["geo_id"].nunique()
        assert metadata.resource_years(res) == sorted(int(y) for y in df["year"].unique())


@needs_data
def test_search_finds_a_variable_by_its_label_ignoring_case_and_accents():
    field = next(f for f in metadata.fields(DATASETS[0]) if f.get("geo:role", "variable") == "variable")
    word = field["title"].split()[0]
    hits = geo.search(word.upper())
    assert ((hits["dataset"] == DATASETS[0]) & (hits["variable"] == field["name"])).any()
    assert geo.search("zzzz no such words").empty
    with pytest.raises(ValueError):
        geo.search("  ")


@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_info_and_cite_describe_every_dataset(dataset):
    i = geo.info(dataset)
    text, page = repr(i), i._repr_html_()
    assert i.title in text and "Coverage" in text and "<h3>" in page
    apa, bib = geo.cite(dataset), geo.cite(dataset, style="bibtex")
    assert apa and "@misc{" in bib and bib.startswith("% Cite")
    cited = apa.split("\n\n")
    sources = metadata.package(dataset)["sources"]
    original = [s["title"] for s in sources if s.get("geo:role") == "original"]
    observatory = metadata.observatory_citation()
    # the original sources first, then the observatory that processes and maintains the data
    assert cited[:len(original) + 1] == [*original, observatory]
    assert set(cited) == {*original, observatory, *(s["title"] for s in sources)}
    with pytest.raises(ValueError):
        geo.cite(dataset, style="mla")


@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_reference_years_cover_every_variable_and_stored_year(dataset):
    ry = geo.reference_years(dataset)
    years = metadata.resource_years(metadata.resource(dataset))
    variables = metadata.variables(dataset)
    assert set(ry["variable"]) == set(variables)
    assert set(ry["year"]) <= set(years)


@needs_data
def test_labels_and_describe_use_the_metadata():
    dataset = DATASETS[0]
    variable = metadata.variables(dataset)[0]
    df = geo.load(dataset, variables=variable, names=True)
    names = geo.labels(df)
    assert names[variable] == geo.dictionary(dataset).set_index("variable").loc[variable, "label"]
    summary = geo.describe(df)
    assert set(summary["year"]) == set(df["year"]) and (summary["label"] == names[variable]).all()
    assert summary["count"].sum() == df[variable].notna().sum()


# --- working with panels ------------------------------------------------------------------

@needs_data
def test_load_adds_names_and_group_names():
    dataset = DATASETS[0]
    scale = metadata.resource(dataset)["geo:scale"]
    groups = [s for s in geo.ancestors(scale) if s in ACTIVE and s != "country"][:1]
    df = geo.load(dataset, groups=groups)
    assert list(df.columns[:3]) == ["geo_id", "name", "year"] and df["name"].notna().all()
    for g in groups:
        assert df[g].notna().all()
    with pytest.raises(ValueError, match="no rows"):
        geo.load(dataset, years=1800)


def test_change_compares_two_years_per_unit():
    df = pd.DataFrame({"geo_id": ["a", "a", "b", "b"], "year": [2000, 2010] * 2, "x": [1.0, 3.0, 4.0, 2.0],
                       "name": ["A", "A", "B", "B"]})
    out = geo.change(df, "x").set_index("geo_id")
    assert out.loc["a", "x_change"] == 2 and out.loc["a", "x_pct_change"] == 200
    assert out.loc["a", "x_annual_change"] == pytest.approx(0.2) and out.loc["b", "x_2010"] == 2
    assert out.loc["a", "x_rank_change"] == 1 and out.loc["b", "x_rank_change"] == -1   # a overtook b
    assert out.loc["a", "name"] == "A"
    with pytest.raises(ValueError):
        geo.change(df[df["year"] == 2000], "x")


# --- aggregation with weights from another dataset -------------------------------------------

def _borrowed_weight(dataset):
    """A variable whose weighted_mean weight lives in another dataset (via geo:weights), or None."""
    own = [f["name"] for f in metadata.fields(dataset)]
    return next((v for v, r in metadata.aggregation_rules(dataset).items()
                 if r.startswith("weighted_mean:") and r.split(":", 1)[1] not in own), None)


@needs_data
@pytest.mark.parametrize("dataset", [d for d in DATASETS if _borrowed_weight(d)] or [None])
def test_weighted_means_fetch_their_weights_from_the_metadata(dataset):
    if dataset is None:
        pytest.skip("no dataset borrows its weights")
    variable = _borrowed_weight(dataset)
    df = geo.load(dataset, variables=variable)            # without its weight
    scale = metadata.resource(dataset)["geo:scale"]
    target = next(t for t in geo.ancestors(scale) if t in ACTIVE)
    up = geo.aggregate(df, to=target, dataset=dataset)
    assert up[variable].notna().any() and up["coverage"].between(0, 1).all()
    lo, hi = df[variable].min(), df[variable].max()
    assert up[variable].dropna().between(lo - 1e-9, hi + 1e-9).all()       # means stay within the range


@needs_data
def test_aggregate_to_several_scales_reports_coverage():
    dataset = next(d for d in DATASETS if any(r == "sum" for r in metadata.aggregation_rules(d).values()))
    sums = [v for v, r in metadata.aggregation_rules(dataset).items() if r == "sum"]
    scale = metadata.resource(dataset)["geo:scale"]
    targets = [t for t in geo.ancestors(scale) if t in ACTIVE]
    out = geo.aggregate(geo.load(dataset, variables=sums), to=targets, dataset=dataset)
    assert set(out["scale"]) == set(targets)
    assert (out["coverage"] <= 1).all() and (out["n_units"] >= 1).all()


@needs_data
@needs_checkout
def test_validator_catches_files_outside_the_dataset_folder(repo_copy):
    dataset = DATASETS[0]
    path = repo_copy / metadata.package_path(dataset)
    pkg = json.loads(path.read_text())
    res = pkg["resources"][0]
    moved = f"data/{res['geo:scale']}/{dataset}"           # the layout before 0.9.0
    for key, ext in (("geo:path", "csv"), ("geo:parquet", "parquet")):
        (repo_copy / f"{moved}.{ext}").parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_copy / res[key], repo_copy / f"{moved}.{ext}")
        res[key] = f"{moved}.{ext}"
    res["path"] = store.raw_url(res["geo:path"], project.config().get("default_ref", "main"))
    path.write_text(json.dumps(pkg))
    (repo_copy / f"data/{dataset}/README.md").unlink()
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    assert f"data/{dataset}/{res['geo:scale']}/{dataset}.csv" in errors and "README.md" in errors


@needs_data
@needs_checkout
def test_validator_catches_stale_coverage_metadata(repo_copy):
    dataset = DATASETS[0]
    path = repo_copy / metadata.package_path(dataset)
    pkg = json.loads(path.read_text())
    pkg["resources"][0]["geo:units"] = 1
    pkg["resources"][0]["geo:years"] = [1900]
    path.write_text(json.dumps(pkg))
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    assert "geo:units" in errors and "geo:years" in errors


# --- maps ---------------------------------------------------------------------------------

@needs_data
def test_map_draws_a_variable():
    pytest.importorskip("plotly")
    dataset = DATASETS[0]
    variable = metadata.variables(dataset)[0]
    fig = geo.map(dataset, variable)
    assert fig.data and geo.labels(dataset)[variable] in fig.layout.title.text


# --- wide files ------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_wide_table_has_a_row_per_unit_and_a_column_per_variable_and_year(dataset):
    from geo4bolivia import io
    res = metadata.resource(dataset)
    wide = io.wide_table(dataset)
    years = metadata.resource_years(res)
    columns = [f"{v}_{y}" for v in metadata.variables(dataset) for y in years]
    assert len(wide) == len(geo.units(res["geo:scale"])) and wide["geo_id"].is_unique
    assert list(wide.columns[:2]) == ["geo_id", "name"] and list(wide.columns[-len(columns):]) == columns
    described = io.wide_dictionary(dataset)
    assert list(described["column"]) == columns and described["label"].astype(bool).all()


@needs_data
@needs_checkout
def test_validator_catches_a_stale_wide_file(repo_copy):
    import pyogrio
    dataset = DATASETS[0]
    res = metadata.resource(dataset)
    path = repo_copy / res["geo:geojson"]
    stale = pyogrio.read_dataframe(path)
    stale.iloc[0, stale.columns.get_loc(stale.columns[-2])] = -999.0      # a value the panel does not have
    path.unlink()
    pyogrio.write_dataframe(stale, path, driver="GeoJSON")
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    assert res["geo:geojson"] in errors and "differs" in errors


# --- Stata files -----------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("dataset", DATASETS)
def test_stata_contents_are_a_labelled_documented_panel(dataset):
    from geo4bolivia import io, stata
    res = metadata.resource(dataset)
    c = stata.contents(dataset)
    df = c["data"]
    panel = pd.read_parquet(store.open_binary(res["geo:parquet"]))
    variables = metadata.variables(dataset)
    groups = io.wide_id_columns(res["geo:scale"])
    assert len(df) == len(panel) and not df.duplicated(["geo_id", "year"]).any()
    assert list(df.columns[:4]) == ["unit_id", "geo_id", "year", "name"]
    assert list(df.columns[-len(variables):]) == variables
    assert all(f"{g}_code" in df.columns and f"{g}_code" in c["value_labels"] for g in groups)
    n = len(geo.units(res["geo:scale"]))
    assert df["unit_id"].between(1, n).all() and set(c["value_labels"]["unit_id"]) == set(range(1, n + 1))
    labels = c["variable_labels"]
    assert set(labels) == set(df.columns) and all(0 < len(v) <= 80 for v in labels.values())
    chars = {(v, k): t for v, k, t in c["characteristics"]}
    assert chars[("_dta", "_TSpanel")] == "unit_id" and chars[("_dta", "_TStvar")] == "year"
    assert int(chars[("_dta", "note0")]) >= 5
    for v in variables:
        assert int(chars[(v, "note0")]) >= 1 and chars[(v, "note1")]


@needs_data
def test_stata_file_round_trips(tmp_path):
    from geo4bolivia import stata
    dataset = DATASETS[0]
    res = metadata.resource(dataset)
    first, second = tmp_path / "a.dta", tmp_path / "b.dta"
    want = stata.write(dataset, res["geo:scale"], first)
    stata.write(dataset, res["geo:scale"], second)
    assert first.read_bytes() == second.read_bytes()            # reproducible: same data, same bytes
    got = stata.read(first)
    pd.testing.assert_frame_equal(want["data"], got["data"], check_dtype=False)
    for key in ("data_label", "variable_labels", "value_labels", "characteristics"):
        assert got[key] == want[key]
    # Unicode survives (format 118): every name reads back as written
    assert set(got["data"]["name"]) == set(want["data"]["name"])


@needs_data
@needs_checkout
def test_validator_catches_a_stale_stata_file(repo_copy):
    from geo4bolivia import stata
    dataset = DATASETS[0]
    res = metadata.resource(dataset)
    c = stata.contents(dataset)
    c["characteristics"] = [x for x in c["characteristics"] if x[0] != "_dta"]    # notes and xtset lost
    stata._Writer(repo_copy / res["geo:dta"], c["data"], write_index=False, version=118,
                  characteristics=c["characteristics"]).write_file()
    errors = " | ".join(validate.validate_dataset(dataset).errors)
    assert res["geo:dta"] in errors and "characteristics" in errors and "variable labels" in errors
