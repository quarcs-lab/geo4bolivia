"""Spatial dependence: weights, connectivity, Moran's I and LISA, on synthetic data with a known answer."""

import pytest

import geo4bolivia as geo
from geo4bolivia import metadata

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []


def test_weights_are_keyed_by_geo_id(units):
    w = geo.weights(units)
    assert set(w.id_order) == set(units["geo_id"]) and w.n == len(units)
    assert pytest.approx(1.0) == sum(w.weights[w.id_order[0]])
    assert geo.weights(units, method="knn", k=4).cardinalities[w.id_order[0]] == 4


def test_connectivity_counts_neighbours(units):
    res = geo.connectivity(units)
    assert list(res.df.columns[:2]) == ["geo_id", "name"]
    assert res.n_units == len(units) and res.max_neighbors == 8 and len(res.df) == len(units)
    assert res.fig.data and "neighbor" in res.interpret().lower()


def test_moran_finds_the_planted_clustering(field, units):
    res = geo.moran(field, "y", gdf=units)
    assert res.moran_i > 0.2 and res.p_sim < 0.01
    assert res.variable == "y" and res.year == 2020
    assert list(res.df.columns[:2]) == ["geo_id", "name"] and len(res.df) == len(units)
    assert "positive" in res.interpret()
    noise = geo.moran(field, "x1", gdf=units)            # an independent draw: no clustering
    assert noise.moran_i < res.moran_i / 2 and noise.p_sim > 0.01


def test_moran_in_every_year(growth_panel, units):
    res = geo.moran(growth_panel, "gdppc", year="all", gdf=units)
    assert list(res.df["year"]) == sorted(growth_panel["year"].unique())
    assert {"moran_i", "p_sim"} <= set(res.df.columns)


def test_moran_uses_the_units_with_data(field, units):
    holes = field.copy()
    holes.loc[holes["geo_id"].isin(units["geo_id"].iloc[:5]), "y"] = float("nan")
    res = geo.moran(holes, "y", gdf=units)
    assert len(res.df) == len(units) - 5 and f"n={len(units) - 5}" in res.w_spec


def test_lisa_labels_every_unit(field, units):
    res = geo.lisa(field, "y", gdf=units)
    assert len(res.df) == len(units) and {"geo_id", "name", "cluster", "p_sim"} <= set(res.df.columns)
    assert res.n_hh + res.n_ll + res.n_hl + res.n_lh + res.n_ns == len(units)
    assert res.n_hh + res.n_ll > res.n_hl + res.n_lh        # positive dependence: clusters, not outliers
    assert res.fig.data and res.fig_scatter.data and res.interpret()


def test_inputs_are_checked(field, units):
    with pytest.raises(ValueError, match="No column"):
        geo.moran(field, "nothing", gdf=units)
    with pytest.raises(ValueError, match="No rows for 1999"):
        geo.moran(field, "y", year=1999, gdf=units)
    with pytest.raises(ValueError, match="geo_id"):
        geo.moran(field.rename(columns={"geo_id": "id"}), "y", gdf=units)
    with pytest.raises(TypeError, match="numeric"):
        geo.moran(field.assign(y=field["y"].astype(str)), "y", gdf=units)


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_without_boundaries_or_weights():
    dataset = DATASETS[0]
    variable = metadata.variables(dataset)[0]
    res = geo.moran(dataset, variable)
    assert res.w_spec.startswith("queen") and len(res.df) > 3
    assert geo.labels(dataset)[variable] in res.fig.layout.title.text
    assert geo.lisa(dataset, variable).df["geo_id"].str.startswith(geo.project.country_code()).all()
