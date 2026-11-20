"""Convergence: beta, sigma and clubs, on synthetic panels with a known answer.

``growth_panel`` has planted beta-convergence (growth = a - 0.02 log y0, so the slope is
-0.02 per year) and a dispersion of logs that shrinks every year. Its units (``u00``...)
are not in the project, so a call without ``gdf=`` also proves that no boundaries are read.
"""

import math

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import metadata
from geo4bolivia.convergence import beta_convergence, convergence_clubs, sigma_convergence

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []
B = 0.02                                      # the planted rate of convergence (tests/conftest.py)


@pytest.fixture(scope="module")
def holes(growth_panel, units):
    """The growth panel without the last year of five units."""
    out = growth_panel.copy()
    out.loc[out["geo_id"].isin(units["geo_id"].iloc[:5]) & (out["year"] == out["year"].max()), "gdppc"] = float("nan")
    return out


@pytest.fixture(scope="module")
def two_clubs(units):
    """Twenty years of two planted clubs: each half of the units settles on its own level."""
    rng = np.random.default_rng(1)
    ids = list(units["geo_id"])
    rows = []
    for j, unit in enumerate(ids):
        level, gap = (10.0 if j < len(ids) // 2 else 8.6), rng.uniform(-0.4, 0.4)
        rows += [(unit, 2000 + t, level + gap * 0.8 ** t + rng.normal(0, 0.002)) for t in range(20)]
    return pd.DataFrame(rows, columns=["geo_id", "year", "log_y"]), dict(zip(ids, [1] * 32 + [2] * 32, strict=True))


# --- beta ------------------------------------------------------------------------------------

def test_beta_recovers_the_planted_rate(growth_panel):
    res = beta_convergence(growth_panel, "gdppc")                 # OLS: no boundaries, no weights
    assert res.beta_total == pytest.approx(-B, abs=1e-3) and res.se_total < 1e-3
    assert res.model == "ols" and res.variable == "gdppc" and res.n_obs == 64 and res.horizon == 5
    assert res.speed == pytest.approx(-math.log(1 - 5 * B) / 5, abs=2e-3)
    assert res.half_life == pytest.approx(math.log(2) / res.speed)
    assert res.fig_map is None and res.w_spec is None and math.isnan(res.beta_indirect)
    assert list(res.df.columns) == ["geo_id", "name", "initial", "final", "growth"] and len(res.df) == 64
    assert list(res.summary.columns) == ["metric", "ols"] and res.fig.data
    assert "growth between 2000 and 2005" in res.notes


def test_beta_interpret_reads_the_slope(growth_panel):
    text = beta_convergence(growth_panel, "gdppc").interpret()
    assert "negative" in text and "half-life" in text and "64 units" in text
    assert text.rstrip().endswith("_") and "causal" in text       # associations only


@pytest.mark.parametrize("model", ["sar", "sem", "slx", "sdm"])
def test_beta_spatial_models_run_on_the_boundaries(growth_panel, units, model):
    res = beta_convergence(growth_panel, "gdppc", model=model, gdf=units, draws=300)
    assert res.model == model and res.n_obs == 64 and res.w_spec.startswith("queen")
    assert res.beta_total == pytest.approx(-B, abs=2e-3)          # no planted spillover: the total stays at -b
    assert list(res.summary.columns) == ["metric", "ols", model] and len(res.impacts) == 1
    assert res.fig_map is not None and res.df["name"].str.startswith("Unit ").all()
    assert math.isfinite(res.lam if model == "sem" else res.beta_direct)


def test_beta_ols_draws_the_map_when_boundaries_are_given(growth_panel, units):
    res = beta_convergence(growth_panel, "gdppc", gdf=units)
    assert res.fig_map is not None and res.w_spec is None and res.beta_total == pytest.approx(-B, abs=1e-3)


def test_beta_first_and_last_choose_the_years(growth_panel):
    res = beta_convergence(growth_panel, "gdppc", first=2001, last=2003)
    start = growth_panel[growth_panel["year"] == 2001].set_index("geo_id")["gdppc"]
    assert res.horizon == 2 and "growth between 2001 and 2003" in res.notes
    assert np.allclose(res.df["initial"], start.loc[res.df["geo_id"]])
    assert res.beta_total == pytest.approx(-B, abs=3e-3)
    full = beta_convergence(growth_panel, "gdppc")
    assert beta_convergence(growth_panel, "gdppc", first=2000, last=2005).beta_total == full.beta_total
    with pytest.raises(ValueError, match="No rows for 1999"):
        beta_convergence(growth_panel, "gdppc", first=1999)
    with pytest.raises(ValueError, match="first and last are both 2003"):
        beta_convergence(growth_panel, "gdppc", first=2003, last=2003)
    with pytest.raises(ValueError, match="must not be before"):
        beta_convergence(growth_panel, "gdppc", first=2004, last=2001)
    with pytest.raises(ValueError, match="has data for 2000 only"):
        beta_convergence(growth_panel[growth_panel["year"] == 2000], "gdppc")


def test_beta_uses_the_units_with_data_in_both_years(holes, units):
    res = beta_convergence(holes, "gdppc")
    assert res.n_obs == 59 and any("5 of 64 units were left out" in note for note in res.notes)
    spatial = beta_convergence(holes, "gdppc", model="sar", gdf=units, draws=300)
    assert spatial.n_obs == 59 and "n=59" in spatial.w_spec      # weights built on the units with data
    assert beta_convergence(holes, "gdppc", last=2004).n_obs == 64


def test_beta_controls_and_fixed_effects(growth_panel, units):
    rng = np.random.default_rng(3)
    data = growth_panel.assign(x=rng.normal(size=len(growth_panel)), half=growth_panel["geo_id"].str[1].map(
        lambda digit: "south" if digit < "4" else "north"))
    res = beta_convergence(data, "gdppc", "x", fixed_effects="half")
    assert res.controls == ("x",) and res.fig_conditional is not None
    assert {"x", "half"} <= set(res.df.columns) and res.beta_total == pytest.approx(-B, abs=1e-3)
    spatial = beta_convergence(data, "gdppc", ["x"], model="sdm", gdf=units, draws=300)
    assert list(spatial.impacts["term"]) == ["log_initial", "x"]
    with pytest.raises(ValueError, match="no such column"):
        beta_convergence(data, "gdppc", fixed_effects="nothing")
    with pytest.raises(TypeError, match="numeric"):
        beta_convergence(data, "gdppc", "half")


def test_beta_checks_its_inputs(growth_panel, units):
    with pytest.raises(ValueError, match="Unknown model"):
        beta_convergence(growth_panel, "gdppc", model="gwr")
    with pytest.raises(ValueError, match="No column"):
        beta_convergence(growth_panel, "nothing")
    with pytest.raises(ValueError, match="needs a 'year' column"):
        beta_convergence(growth_panel.drop(columns="year"), "gdppc")
    with pytest.raises(ValueError, match="vcov"):
        beta_convergence(growth_panel, "gdppc", vcov="robust")
    with pytest.raises(ValueError, match="at least 100"):
        beta_convergence(growth_panel, "gdppc", min_obs=100)


# --- sigma -----------------------------------------------------------------------------------

def test_sigma_finds_the_falling_dispersion(growth_panel):
    res = sigma_convergence(growth_panel, "gdppc")
    assert res.std_slope == pytest.approx(-B, abs=5e-3) and res.std_pvalue < 0.01     # ln(1 - b t) falls by ~b a year
    assert res.gini_slope < 0 and res.cv_slope < 0
    assert res.n_units == 64 and res.n_periods == 6 and res.variable == "gdppc"
    assert list(res.df.columns) == ["year", "n_units", "mean", "std", "gini", "cv"]
    assert list(res.df["year"]) == [2000, 2001, 2002, 2003, 2004, 2005]       # whole years, not floats
    assert res.df["std"].is_monotonic_decreasing and res.summary["converging"].all()
    assert res.fig.data and "narrowed" in res.interpret() and "σ-convergence" in res.interpret()


def test_sigma_first_and_last_choose_the_window(growth_panel):
    res = sigma_convergence(growth_panel, "gdppc", first=2001, last=2004)
    assert list(res.df["year"]) == [2001, 2002, 2003, 2004] and res.std_slope < 0


def test_sigma_keeps_the_units_observed_every_year(holes):
    res = sigma_convergence(holes, "gdppc")
    assert res.n_units == 59 and (res.df["n_units"] == 59).all()
    assert res.notes == ("5 of 64 units were left out: no data for 'gdppc' in every year from 2000 to 2005",)


def test_sigma_says_what_a_short_panel_lacks(growth_panel):
    two = growth_panel[growth_panel["year"].isin([2000, 2005])]
    with pytest.raises(ValueError) as error:
        sigma_convergence(two, "gdppc")
    message = str(error.value)
    assert "at least 3 years" in message and "'gdppc' has 2 (2000, 2005)" in message and "inequality" in message
    if DATASETS:                                # with the project's catalog, the datasets that are long enough
        assert ("Datasets with at least 3 years" in message) == any(
            len(metadata.resource_years(metadata.resource(d))) >= 3 for d in DATASETS)
    with pytest.raises(ValueError, match="at least 3 years"):
        sigma_convergence(growth_panel, "gdppc", first=2003, last=2004)


# --- clubs -----------------------------------------------------------------------------------

def test_clubs_recover_the_planted_clubs(two_clubs, units):
    data, truth = two_clubs
    res = convergence_clubs(data, "log_y", gdf=units)
    assert res.n_clubs == 2 and not res.converged and res.global_tstat < res.tcrit
    assert res.n_units == 64 and res.n_periods == 20 and res.variable == "log_y"
    found = res.membership.set_index("geo_id")["club"]
    assert (found.groupby(found.index.map(truth)).nunique() == 1).all()        # each planted club in one club
    assert found[found.index.map(truth) == 1].iloc[0] != found[found.index.map(truth) == 2].iloc[0]
    assert list(res.membership.columns[:3]) == ["geo_id", "name", "club"]
    assert list(res.df.columns) == ["geo_id", "name", "year", "value", "relative", "club"]
    assert res.df["year"].dtype.kind == "i" and len(res.df) == 64 * 20
    assert res.fig.data and res.fig_paths.data and res.fig_clubs.data and res.fig_map is not None
    assert "2 convergence clubs" in res.interpret()


def test_clubs_map_and_log_options(growth_panel, units):
    res = convergence_clubs(growth_panel, "gdppc", log=True, map=False)
    assert res.fig_map is None and res.notes == () and res.n_periods == 6
    levels = growth_panel[growth_panel["year"] == 2000].set_index("geo_id")["gdppc"]
    raw = convergence_clubs(growth_panel, "gdppc", log=True, hp_filter=False, gdf=units)
    start = raw.df[raw.df["year"] == 2000].set_index("geo_id")["value"]
    assert np.allclose(start, np.log(levels.loc[start.index])) and "log gdppc" in raw.fig.layout.title.text
    unknown = convergence_clubs(growth_panel, "gdppc")           # units outside the project: no boundaries
    assert unknown.fig_map is None and "no map" in unknown.notes[0]


def test_clubs_say_what_a_short_panel_lacks(growth_panel, units):
    five = growth_panel[growth_panel["year"] <= 2004]
    with pytest.raises(ValueError) as error:
        convergence_clubs(five, "gdppc", gdf=units)
    message = str(error.value)
    assert "at least 6 years" in message and "'gdppc' has 5 (2000–2004)" in message and "smaller trim" in message
    assert convergence_clubs(five, "gdppc", trim=0.1, gdf=units).n_periods == 5      # the engine's rule: 4 left
    with pytest.raises(ValueError, match="at least 6 years"):
        convergence_clubs(growth_panel, "gdppc", first=2000, last=2001, gdf=units)
    with pytest.raises(ValueError, match="trim must be between 0 and 1"):
        convergence_clubs(growth_panel, "gdppc", trim=1.5, gdf=units)


# --- shared checks ---------------------------------------------------------------------------

def test_a_variable_that_is_not_positive_is_refused(growth_panel):
    logs = growth_panel.assign(gdppc=np.log(growth_panel["gdppc"]) - 9)       # centred logs: many below zero
    for run in (lambda: beta_convergence(logs, "gdppc"), lambda: sigma_convergence(logs, "gdppc"),
                lambda: convergence_clubs(logs, "gdppc", log=True, map=False)):
        with pytest.raises(ValueError, match="strictly positive variable in levels"):
            run()
    with pytest.raises(ValueError, match=r"value\(s\) of zero or less \(in 2000, 2005\)"):
        beta_convergence(logs, "gdppc")


def test_a_logarithm_gets_a_warning(growth_panel):
    logs = growth_panel.assign(log_gdppc=np.log(growth_panel["gdppc"]))
    with pytest.warns(UserWarning, match="looks like a logarithm"):
        res = beta_convergence(logs, "log_gdppc")
    assert any("in levels" in note for note in res.notes)
    with pytest.warns(UserWarning, match="looks like a logarithm"):
        sigma_convergence(logs, "log_gdppc")


# --- the project's data ----------------------------------------------------------------------

@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_without_boundaries_or_weights():
    for dataset in DATASETS:                    # the first dataset whose first variable is positive in two years
        variable = metadata.variables(dataset)[0]
        values = geo.load(dataset, variables=variable).dropna(subset=[variable])
        if pd.api.types.is_numeric_dtype(values[variable]) and (values[variable] > 0).all() \
                and values["year"].nunique() >= 2:
            break
    else:
        pytest.skip("no dataset whose first variable is strictly positive in at least two years")
    years = sorted(int(y) for y in values["year"].unique())

    res = beta_convergence(dataset, variable)
    assert res.horizon == years[-1] - years[0] and res.n_obs > 3 and res.fig_map is None
    assert geo.labels(dataset)[variable] in res.fig.layout.title.text
    spatial = beta_convergence(dataset, variable, model="sar", draws=300)
    assert spatial.w_spec.startswith("queen") and spatial.fig_map is not None and math.isfinite(spatial.rho)
    assert spatial.df["geo_id"].str.startswith(geo.project.country_code()).all() and spatial.df["name"].notna().all()

    if len(years) >= 3:
        assert sigma_convergence(dataset, variable).n_periods == len(years)
    else:
        with pytest.raises(ValueError, match="at least 3 years"):
            sigma_convergence(dataset, variable)
    if len(years) >= 6:
        clubs = convergence_clubs(dataset, variable, log=True)
        assert clubs.fig_map is not None and clubs.membership["name"].notna().all()
    else:
        with pytest.raises(ValueError, match="at least 6 years"):
            convergence_clubs(dataset, variable)
