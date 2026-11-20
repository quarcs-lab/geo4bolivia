"""Multiscale geographically weighted regression, on synthetic data with a known answer."""

import pandas as pd
import pytest

from geo4bolivia import io, metadata, project
from geo4bolivia._engine.pedagogy._interpret._shared import _ASSOC_NOTE
from geo4bolivia.local import mgwr

pytest.importorskip("mgwr")
pytestmark = pytest.mark.mgwr

DATASETS = list(metadata.dataset_ids()) if project.local_root() is not None else []


@pytest.fixture(scope="module")
def fit(field, units):
    """One fit on the lattice: ``y`` depends on ``x1`` (1.0) and ``x2`` (-0.5) through a spatial lag."""
    return mgwr(field, "y", ["x1", "x2"], gdf=units, max_iter=20)


def test_mgwr_fits_one_regression_per_unit(fit, units):
    assert list(fit.df.columns[:2]) == ["geo_id", "name"] and len(fit.df) == len(units)
    assert set(fit.df["geo_id"]) == set(units["geo_id"])
    for term in ("const", "x1", "x2"):
        assert {f"{term}_coef", f"{term}_se", f"{term}_t", f"{term}_significant"} <= set(fit.df.columns)
    assert fit.df["residual"].notna().all() and 0 < fit.r2 <= 1


def test_mgwr_finds_the_planted_associations(fit):
    assert fit.df["x1_coef"].mean() > 0 > fit.df["x2_coef"].mean()
    assert fit.df["x1_coef"].abs().mean() > fit.df["x2_coef"].abs().mean()      # betas 1.0 and -0.5
    assert fit.df["x1_significant"].mean() > 0.5


def test_mgwr_gives_each_term_its_bandwidth(fit, units):
    assert set(fit.bw) == {"const", "x1", "x2"}
    assert all(2 <= bw <= len(units) for bw in fit.bw.values())
    for term, (low, high) in fit.bw_interval.items():
        assert low <= fit.bw[term] <= high
    assert set(fit.adj_alpha) == set(fit.critical_t) == set(fit.bw)
    assert "Bandwidth" in fit.gt_bw.as_raw_html() and fit.gt.as_raw_html()


def test_mgwr_checks_local_collinearity(fit):
    assert (fit.df["local_cn"] >= 1).all()            # a condition number is at least one
    assert fit.df["local_cn"].max() < 30              # independent regressors: no local collinearity


def test_mgwr_maps_every_coefficient(fit):
    assert set(fit.figs) == {"const", "x1", "x2"} and all(f.data for f in fit.figs.values())
    assert fit.fig.data
    text = fit.interpret()
    assert "bandwidth" in text.lower() and text.rstrip().endswith(_ASSOC_NOTE)
    assert fit.year == 2020


def test_mgwr_uses_the_units_with_data(field, units):
    holes = field.copy()
    holes.loc[holes["geo_id"].isin(units["geo_id"].iloc[:4]), "x1"] = float("nan")
    res = mgwr(holes, "y", "x1", gdf=units, max_iter=5, tiles=None)
    assert len(res.df) == len(units) - 4


def test_inputs_are_checked(field, units):
    with pytest.raises(ValueError, match="No column"):
        mgwr(field, "y", ["x1", "nothing"], gdf=units)
    with pytest.raises(ValueError, match="at least one"):
        mgwr(field, "y", [], gdf=units)
    with pytest.raises(ValueError, match="cannot also be in x"):
        mgwr(field, "y", ["x1", "y"], gdf=units)
    with pytest.raises(ValueError, match="No rows for 1999"):
        mgwr(field, "y", "x1", year=1999, gdf=units)
    with pytest.raises(TypeError, match="numeric"):
        mgwr(field.assign(x1=field["x1"].astype(str)), "y", "x1", gdf=units)


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_without_boundaries():
    for dataset in DATASETS:
        panel = io.load(dataset)
        numeric = [c for c in metadata.variables(dataset) if pd.api.types.is_numeric_dtype(panel[c])]
        last = panel[panel["year"] == panel["year"].max()]
        usable = [c for c in numeric if last[c].notna().sum() > 30 and last[c].nunique() > 10]
        if len(usable) >= 2:
            break
    else:
        pytest.skip("no dataset with two numeric variables")
    y, x = usable[0], usable[1]
    res = mgwr(dataset, y, x, max_iter=3)
    assert res.df["geo_id"].str.startswith(project.country_code()).all()
    assert set(res.bw) == {"const", x} and res.figs[x].data
