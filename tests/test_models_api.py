"""Regression, panel and spatial models, on synthetic data with a known answer.

The frames built here have planted coefficients: an exact line (slope 3, R² 1), group
effects correlated with a regressor (least squares is biased until they are absorbed) and
a panel whose unit effects are correlated with the regressor (pooled and between
estimates are biased, fixed effects recover the slope and the Hausman test rejects).
``field`` is a spatial lag process with rho = 0.6 and coefficients 1.0 and -0.5. The
units (``u00``...) are not in the project, so nothing is read from it.
"""

import math
import sys

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import metadata
from geo4bolivia._engine.pedagogy._interpret._shared import _ASSOC_NOTE
from geo4bolivia.models import panel_model, regression, spatial_diagnostics, spatial_model

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []
TIDY = ["model", "term", "estimate", "std_error", "statistic", "p_value", "conf_low", "conf_high"]
SLOPE = 2.0                                   # the planted coefficient of x in `grouped` and the panels


def coefficient(result, model, term, column="estimate"):
    rows = result.df[(result.df["model"] == model) & (result.df["term"] == term)]
    assert len(rows) == 1
    return float(rows[column].iloc[0])


def reads_as_association(text):
    return text.endswith(_ASSOC_NOTE) and "effect of" not in text and "causes" not in text


@pytest.fixture(scope="module")
def line():
    """y = 2 + 3x exactly."""
    x = np.linspace(-2.0, 5.0, 30)
    return pd.DataFrame({"geo_id": [f"u{i:02d}" for i in range(30)], "x": x, "y": 2.0 + 3.0 * x})


@pytest.fixture(scope="module")
def grouped():
    """y = 1 + 2x - z + a group effect that moves with x: least squares on x alone overstates the slope."""
    rng = np.random.default_rng(7)
    n = 120
    group = np.repeat(["a", "b", "c", "d", "e", "f"], n // 6)
    level = pd.Series(group).map(dict(zip("abcdef", [-6.0, -3.0, 0.0, 3.0, 6.0, 9.0], strict=True))).to_numpy()
    x, z = 0.5 * level + rng.normal(size=n), rng.normal(size=n)
    y = 1.0 + SLOPE * x - z + 2.0 * level + rng.normal(scale=0.3, size=n)
    return pd.DataFrame({"geo_id": [f"u{i:03d}" for i in range(n)], "g": group, "x": x, "z": z, "y": y})


def make_panel(seed, link, units=60, years=5, drift=0.0):
    """x = link * (unit effect) + drift * t + noise; y = 1 + 2x + 3 (unit effect) + drift * t + noise."""
    rng = np.random.default_rng(seed)
    effect = rng.normal(size=units)
    rows = []
    for i in range(units):
        for t in range(years):
            x = link * effect[i] + drift * t + rng.normal()
            rows.append((f"u{i:03d}", 2000 + t, x, 1.0 + SLOPE * x + 3.0 * effect[i] + drift * t + rng.normal(0, 0.5)))
    return pd.DataFrame(rows, columns=["geo_id", "year", "x", "y"])


@pytest.fixture(scope="module")
def correlated_panel():
    """Unit effects that move with x: only the within estimate recovers the slope."""
    return make_panel(1, link=1.0)


@pytest.fixture(scope="module")
def unrelated_panel():
    """Unit effects unrelated to x: every estimator is consistent and random effects are admissible."""
    return make_panel(2, link=0.0, units=200)


# --- regression ------------------------------------------------------------------------------

def test_regression_recovers_an_exact_line(line):
    res = regression(line, "y", "x")
    assert list(res.df.columns) == TIDY and list(res.df["term"]) == ["x", "Intercept"]
    assert coefficient(res, 1, "x") == pytest.approx(3.0) and coefficient(res, 1, "Intercept") == pytest.approx(2.0)
    assert coefficient(res, 1, "x", "conf_low") == pytest.approx(3.0)
    row = res.summary.iloc[0]
    assert row["n"] == 30 and row["r2"] == pytest.approx(1.0) and row["r2_adj"] == pytest.approx(1.0)
    assert row["fixed_effects"] == "none" and "robust" in row["std_errors"]
    assert res.models[0].params["x"] == pytest.approx(3.0) and res.y == "y" and res.x == (("x",),)
    assert res.years == () and res.year is None and res.notes == ()
    assert "3 higher" in res.interpret() and reads_as_association(res.interpret())
    named = regression(line, "y", ["x"], title="A straight line")
    assert "A straight line" in named.gt.as_raw_html() and named.fig.layout.title.text == "A straight line"


def test_regression_specifications_side_by_side(grouped):
    res = regression(grouped, "y", [["x"], ["x", "z"], ["x", "z"]], fixed_effects=[None, None, "g"])
    assert list(res.summary["model"]) == [1, 2, 3] and len(res.models) == 3
    assert list(res.summary["fixed_effects"]) == ["none", "none", "g"]
    assert coefficient(res, 1, "x") > SLOPE + 1.0 and coefficient(res, 2, "x") > SLOPE + 1.0     # biased
    assert coefficient(res, 3, "x") == pytest.approx(SLOPE, abs=0.1)                              # absorbed
    assert coefficient(res, 3, "z") == pytest.approx(-1.0, abs=0.1)
    assert coefficient(res, 3, "x", "conf_low") < coefficient(res, 3, "x") < coefficient(res, 3, "x", "conf_high")
    assert res.summary["r2"].is_monotonic_increasing and (res.summary["r2_adj"] <= res.summary["r2"]).all()
    # the dummies, and the intercept they absorb, are not coefficients
    assert set(res.df["term"]) == {"x", "z", "Intercept"}
    assert list(res.df.loc[res.df["model"] == 3, "term"]) == ["x", "z"]
    assert len(res.models[2].params) == 1 + 2 + 5
    html = res.gt.as_raw_html()
    assert all(text in html for text in ("(1)", "(3)", "g fixed effects", "Yes", "No", "Observations", "R²", "***"))
    assert f"({coefficient(res, 3, 'x', 'std_error'):.3f})" in html
    assert [trace.name for trace in res.fig.data] == ["(1)", "(2)", "(3)"]
    assert list(res.fig.layout.yaxis.ticktext) == ["x", "z"]                                      # no intercept
    reading = res.interpret()
    assert "3 specifications" in reading and "It shrinks" in reading and "within the same g" in reading
    assert reads_as_association(reading)


def test_fixed_effects_by_a_column_compare_within_groups(grouped):
    res = regression(grouped, "y", ["x", "z"], fixed_effects="g")
    centred = grouped[["y", "x", "z"]] - grouped.groupby("g")[["y", "x", "z"]].transform("mean")
    by_hand = np.linalg.lstsq(centred[["x", "z"]].to_numpy(), centred["y"].to_numpy(), rcond=None)[0]
    assert list(res.df["term"]) == ["x", "z"]
    assert res.df["estimate"].to_numpy() == pytest.approx(by_hand)
    assert res.fixed_effects == (("g",),) and "Fixed effects for *g*" in res.interpret()


def test_standard_errors_classical_robust_and_clustered(grouped):
    classical = regression(grouped, "y", "x", robust=False)
    robust = regression(grouped, "y", "x")
    clustered = regression(grouped, "y", "x", cluster="g")
    x, y = grouped["x"].to_numpy(), grouped["y"].to_numpy()
    slope = np.cov(x, y)[0, 1] / x.var(ddof=1)
    residuals = (y - y.mean()) - slope * (x - x.mean())
    by_hand = math.sqrt(residuals @ residuals / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
    for res in (classical, robust, clustered):
        assert coefficient(res, 1, "x") == pytest.approx(slope)
    assert coefficient(classical, 1, "x", "std_error") == pytest.approx(by_hand)
    assert coefficient(clustered, 1, "x", "std_error") > 1.2 * coefficient(robust, 1, "x", "std_error")
    assert classical.summary["std_errors"].iloc[0] == "classical"
    assert clustered.summary["std_errors"].iloc[0] == "clustered by g (6 clusters)" and clustered.cluster == "g"
    assert any("6 clusters" in note for note in clustered.notes) and "clustered by g" in clustered.gt.as_raw_html()


def test_regression_chooses_and_pools_years(correlated_panel):
    panel = correlated_panel.copy()
    last = regression(panel, "y", "x")
    assert last.years == (2004,) and last.year == 2004 and last.summary["n"].iloc[0] == 60
    assert regression(panel, "y", "x", year=2001).years == (2001,)
    panel.loc[panel["year"] == 2004, "x"] = float("nan")              # the last year with data for y and x
    assert regression(panel, "y", "x").years == (2003,)
    pooled = regression(panel, "y", "x", year="all")
    assert pooled.years == (2000, 2001, 2002, 2003) and pooled.year is None and pooled.summary["n"].iloc[0] == 240
    assert any("pooled" in note for note in pooled.notes) and "4 years pooled" in pooled.gt.as_raw_html()
    within = regression(panel, "y", "x", year="all", fixed_effects=["geo_id", "year"], cluster="geo_id")
    assert coefficient(within, 1, "x") == pytest.approx(SLOPE, abs=0.1) and coefficient(pooled, 1, "x") > SLOPE + 1.0
    assert within.summary["fixed_effects"].iloc[0] == "geo_id, year" and within.notes == ()
    assert "Unit fixed effects" in within.gt.as_raw_html() and "Year fixed effects" in within.gt.as_raw_html()
    assert regression(panel, "y", "x", year=[2000, 2001]).summary["n"].iloc[0] == 120


def test_regression_inputs_are_checked(grouped, correlated_panel):
    with pytest.raises(ValueError, match="No column"):
        regression(grouped, "y", ["x", "nothing"])
    with pytest.raises(TypeError, match="numeric"):
        regression(grouped, "g", "x")
    with pytest.raises(ValueError, match="cannot also be a regressor"):
        regression(grouped, "y", ["x", "y"])
    with pytest.raises(ValueError, match="at least one column"):
        regression(grouped, "y", [])
    with pytest.raises(ValueError, match="neither a column of the table nor a coarser scale"):
        regression(grouped, "y", "x", fixed_effects="nothing")
    with pytest.raises(ValueError, match="3 specifications but fixed_effects has 2"):
        regression(grouped, "y", [["x"], ["z"], ["x", "z"]], fixed_effects=[None, "g"])
    with pytest.raises(ValueError, match="cannot be told apart"):
        regression(grouped.assign(twice=2 * grouped["x"]), "y", ["x", "twice"])
    with pytest.raises(ValueError, match="cannot be told apart"):
        regression(grouped.assign(level=grouped["g"].map({"a": 1.0}).fillna(0.0)), "y", "level", fixed_effects="g")
    with pytest.raises(ValueError, match="no year column"):
        regression(grouped, "y", "x", year=2020)
    with pytest.raises(ValueError, match="No rows for 1999"):
        regression(correlated_panel, "y", "x", year=1999)
    with pytest.raises(ValueError, match="Pool the years"):
        regression(correlated_panel, "y", "x", fixed_effects="year")
    with pytest.raises(ValueError, match="geo_id"):
        regression(grouped.rename(columns={"geo_id": "id"}), "y", "x")


# --- panel_model -----------------------------------------------------------------------------

@pytest.mark.panel
def test_fixed_effects_recover_the_slope_and_hausman_rejects(correlated_panel):
    pytest.importorskip("linearmodels")
    res = panel_model(correlated_panel, "y", "x")
    assert list(res.df.columns) == TIDY and list(res.models) == ["pooled", "between", "fe", "re"]
    assert coefficient(res, "fe", "x") == pytest.approx(SLOPE, abs=0.1)
    assert coefficient(res, "fe", "x", "conf_low") < SLOPE < coefficient(res, "fe", "x", "conf_high")
    assert coefficient(res, "pooled", "x") > SLOPE + 1.0                 # the unit effects load on x
    assert coefficient(res, "between", "x") > coefficient(res, "pooled", "x")
    assert coefficient(res, "fe", "x") < coefficient(res, "re", "x") < coefficient(res, "pooled", "x")
    assert "Intercept" not in set(res.df.loc[res.df["model"] == "fe", "term"])
    assert res.hausman is not None and res.hausman.df == 1 and res.hausman.statistic > 20 and res.hausman.p_value < 0.001
    summary = res.summary.set_index("model")
    assert {"n", "units", "years", "r2", "r2_within", "r2_between", "r2_overall"} <= set(summary.columns)
    assert summary.loc["fe", "n"] == 300 and summary.loc["between", "n"] == 60
    assert (summary["units"] == 60).all() and (summary["years"] == 5).all()
    assert summary.loc["fe", "r2_within"] > summary.loc["pooled", "r2_within"]
    assert (res.n_obs, res.n_units, res.years) == (300, 60, (2000, 2001, 2002, 2003, 2004))
    html = res.gt.as_raw_html()
    assert all(text in html for text in ("Pooled OLS", "Between", "Fixed effects", "Random effects", "Hausman"))
    assert [trace.name for trace in res.fig.data] == ["Pooled OLS", "Between", "Fixed effects", "Random effects"]
    reading = res.interpret()
    assert "Hausman test" in reading and "**fixed effects** are the estimates to read" in reading
    assert "between units" in reading and "within units" in reading and reads_as_association(reading)


@pytest.mark.panel
def test_random_effects_are_admissible_when_unit_effects_are_unrelated(unrelated_panel):
    pytest.importorskip("linearmodels")
    res = panel_model(unrelated_panel, "y", "x")
    for kind in ("pooled", "fe", "re"):
        assert coefficient(res, kind, "x") == pytest.approx(SLOPE, abs=0.2)
    assert coefficient(res, "re", "x", "std_error") <= coefficient(res, "fe", "x", "std_error") * 1.05
    assert res.hausman.p_value > 0.05 and "**random effects**" in res.interpret()


@pytest.mark.panel
def test_panel_model_options(correlated_panel):
    pytest.importorskip("linearmodels")
    only = panel_model(correlated_panel, "y", "x", models="fe")
    assert list(only.models) == ["fe"] and only.hausman is None and any("Hausman" in n for n in only.notes)
    assert "Hausman" not in only.gt.as_raw_html()
    robust = panel_model(correlated_panel, "y", "x", models=["fe", "re"], cluster=False)
    assert coefficient(robust, "fe", "x") == pytest.approx(coefficient(only, "fe", "x"))
    assert coefficient(robust, "fe", "x", "std_error") != pytest.approx(coefficient(only, "fe", "x", "std_error"))
    assert set(robust.summary["std_errors"]) == {"heteroskedasticity-robust"} and robust.hausman.p_value < 0.001


@pytest.mark.panel
def test_time_effects_remove_what_all_units_share():
    pytest.importorskip("linearmodels")
    # x and y both drift upwards in every unit: two years, so the within estimate rests on one change per unit
    panel = make_panel(3, link=1.0, units=80, years=2, drift=2.0)
    plain = panel_model(panel, "y", "x")
    timed = panel_model(panel, "y", "x", time_effects=True)
    assert coefficient(plain, "fe", "x") > SLOPE + 0.5                  # the common drift counts as association
    assert coefficient(timed, "fe", "x") == pytest.approx(SLOPE, abs=0.2)
    assert list(timed.summary["time_effects"]) == [True, False, True, True]
    assert set(timed.df["term"]) == {"x", "Intercept"} and any("between" in note for note in timed.notes)
    assert "only two years" in plain.interpret() and "only two years" not in timed.interpret()
    assert "with year effects" in timed.interpret() and "Yes" in timed.gt.as_raw_html()


@pytest.mark.panel
def test_panel_model_needs_years_and_variation_within_units(correlated_panel, line):
    pytest.importorskip("linearmodels")
    with pytest.raises(ValueError, match="no year column"):
        panel_model(line, "y", "x")
    with pytest.raises(ValueError, match=r"at least two years.*\[2003\]"):
        panel_model(correlated_panel[correlated_panel["year"] == 2003], "y", "x")
    staggered = correlated_panel[correlated_panel["year"] == 2000 + correlated_panel["geo_id"].str[1:].astype(int) % 5]
    with pytest.raises(ValueError, match="more than one year"):
        panel_model(staggered, "y", "x")
    fixed = correlated_panel.assign(size=correlated_panel["geo_id"].str[1:].astype(float))
    with pytest.raises(ValueError, match=r"\['size'\] do\(es\) not change within units"):
        panel_model(fixed, "y", ["x", "size"])
    assert coefficient(panel_model(fixed, "y", ["x", "size"], models=["pooled", "re"]), "re", "size") is not None
    with pytest.raises(ValueError, match="Unknown model"):
        panel_model(correlated_panel, "y", "x", models=["fe", "first_difference"])
    with pytest.raises(ValueError, match="No column"):
        panel_model(correlated_panel, "y", "nothing")


def test_panel_model_says_how_to_install_linearmodels(correlated_panel, monkeypatch):
    monkeypatch.setitem(sys.modules, "linearmodels.panel", None)
    with pytest.raises(ImportError, match=rf'pip install "{geo.project.PACKAGE}\[panel\]"'):
        panel_model(correlated_panel, "y", "x")


# --- spatial models --------------------------------------------------------------------------

def test_spatial_lag_model_recovers_the_planted_process(field, units):
    res = spatial_model(field, "y", ["x1", "x2"], model="lag", gdf=units, n_draws=2000)
    assert res.model == "lag" and res.method == "ml" and res.n_obs == len(units) and res.year == 2020
    assert res.rho == pytest.approx(0.6, abs=0.12) and math.isnan(res.lam)
    betas = res.df.set_index("term")["estimate"]
    assert betas["x1"] == pytest.approx(1.0, abs=0.15) and betas["x2"] == pytest.approx(-0.5, abs=0.15)
    impacts = res.impacts.set_index("term")
    assert impacts.loc["x1", "total"] == pytest.approx(betas["x1"] / (1 - res.rho), rel=0.1)
    assert abs(impacts.loc["x1", "direct"]) < abs(impacts.loc["x1", "total"]) and impacts.loc["x2", "indirect"] < 0
    assert res.w_spec.startswith("queen") and "x1" in res.gt.as_raw_html()
    assert "ρ" in res.interpret() and reads_as_association(res.interpret())


def test_spatial_model_kinds_and_fixed_effects(field, units):
    ols = spatial_model(field, "y", ["x1", "x2"], model="ols", gdf=units)
    assert math.isnan(ols.rho) and ols.impacts is None
    error = spatial_model(field, "y", ["x1", "x2"], model="error", gdf=units)
    assert error.lam > 0.2 and math.isnan(error.rho) and error.impacts is None
    durbin = spatial_model(field, "y", "x1", gdf=units, n_draws=500)             # the default model
    assert durbin.model == "durbin" and durbin.rho > 0.2 and list(durbin.impacts["term"]) == ["x1"]
    assert any(term.startswith("W_x1") for term in durbin.df["term"])
    slx = spatial_model(field, "y", ["x1", "x2"], model="slx", gdf=units)
    assert len(slx.impacts) == 2 and math.isnan(slx.rho)
    halves = field.assign(half=np.where(field["geo_id"] < "u32", "south", "north"))
    fixed = spatial_model(halves, "y", ["x1", "x2"], model="lag", fixed_effects="half", gdf=units, n_draws=500)
    assert "half_south" in set(fixed.df["term"]) and len(fixed.impacts) == 2


def test_spatial_diagnostics_point_to_a_lag_model(field, units):
    res = spatial_diagnostics(field, "y", ["x1", "x2"], gdf=units)
    assert res.recommendation == "lag" and "lag" in res.reasoning
    tests = res.df.set_index("test")
    assert list(tests.index) == ["moran_residuals", "lm_lag", "lm_error", "robust_lm_lag", "robust_lm_error", "lm_sarma"]
    assert tests.loc["lm_lag", "p"] < 0.01 and tests.loc["robust_lm_lag", "p"] < 0.05
    assert tests.loc["robust_lm_lag", "statistic"] > tests.loc["robust_lm_error", "statistic"]
    assert res.moran_i_resid > 0.1 and res.alpha == 0.05 and res.w_spec.startswith("queen")
    assert "LM lag" in res.gt.as_raw_html() and "`lag`" in res.interpret() and reads_as_association(res.interpret())


def test_spatial_models_use_the_units_with_data_and_check_inputs(field, units):
    holes = field.copy()
    holes.loc[holes["geo_id"].isin(units["geo_id"].iloc[:4]), "x2"] = float("nan")
    assert spatial_model(holes, "y", ["x1", "x2"], model="lag", gdf=units, n_draws=200).n_obs == len(units) - 4
    assert f"n={len(units) - 4}" in spatial_diagnostics(holes, "y", ["x1", "x2"], gdf=units).w_spec
    with pytest.raises(ValueError, match="one year"):
        spatial_model(field, "y", "x1", year="all", gdf=units)
    with pytest.raises(ValueError, match="No rows for 1999"):
        spatial_diagnostics(field, "y", "x1", year=1999, gdf=units)
    with pytest.raises(ValueError, match="No column"):
        spatial_model(field, "y", ["x1", "nothing"], gdf=units)
    with pytest.raises(ValueError, match="one fixed_effects"):
        spatial_model(field, "y", "x1", fixed_effects=["x2", "year"], gdf=units)
    with pytest.raises(ValueError, match="unknown model"):
        spatial_model(field, "y", "x1", model="sarar", gdf=units)
    with pytest.raises(TypeError, match="numeric"):
        spatial_diagnostics(field.assign(x1=field["x1"].astype(str)), "y", "x1", gdf=units)


# --- the project's data ----------------------------------------------------------------------

def _two_variables():
    """The first dataset with two numeric variables that have data in a common year, and those variables."""
    for dataset in DATASETS:
        df = geo.load(dataset)
        numeric = [v for v in metadata.variables(dataset) if pd.api.types.is_numeric_dtype(df[v])]
        for year in sorted(df["year"].unique(), reverse=True):
            rows = df[df["year"] == year]
            usable = [v for v in numeric if rows[v].notna().sum() > 30 and rows[v].nunique() > 5]
            if len(usable) >= 2:
                return dataset, usable[0], usable[1]
    return None


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_without_boundaries_or_weights():
    found = _two_variables()
    if found is None:
        pytest.skip("needs a dataset with at least two numeric variables")
    dataset, y, x = found
    labels = geo.labels(dataset)
    res = regression(dataset, y, x)
    assert res.summary["n"].iloc[0] > 30 and len(res.years) == 1 and labels[y] in res.fig.layout.title.text
    assert labels[y] in res.gt.as_raw_html() and labels[x] in res.gt.as_raw_html() and labels[x] in res.interpret()
    # a coarser scale as fixed effects and as clusters: its units' names are added as a column
    scale = geo.scale_of(geo.load(dataset)["geo_id"].iloc[0])
    coarser = [s for s in geo.ancestors(scale) if 2 <= len(geo.units(s)) <= res.summary["n"].iloc[0] // 10]
    if coarser:
        grouped = regression(dataset, y, x, year=res.year, fixed_effects=coarser[-1], cluster=coarser[-1])
        assert grouped.summary["fixed_effects"].iloc[0] == coarser[-1] and list(grouped.df["term"]) == [x]
        assert f"{grouped.labels[coarser[-1]]} fixed effects" in grouped.gt.as_raw_html()
    tests = spatial_diagnostics(dataset, y, x)
    assert tests.w_spec.startswith("queen") and tests.recommendation in ("ols", "lag", "error")
    lag = spatial_model(dataset, y, x, model="lag", n_draws=200)
    assert lag.n_obs == res.summary["n"].iloc[0] and lag.year == res.year and -1 < lag.rho < 1
    assert list(lag.impacts["term"]) == [labels[x]]
