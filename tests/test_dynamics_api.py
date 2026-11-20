"""Distribution dynamics: Markov transitions, LISA transitions and rank mobility, with known answers.

``growth_panel`` keeps the order of its units almost exactly (growth depends on the
initial level, with little noise), so its classes and ranks barely move. The two-year
panels built here have an exact answer: a ranking that is kept or reversed, and a
spatial field that is rescaled (every unit keeps its LISA type) or mirrored (hot spots
become cold spots).
"""

import sys

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import metadata
from geo4bolivia.dynamics import LISA_TYPES, lisa_transitions, rank_mobility, spatial_transitions, transitions
from geo4bolivia.panel import change
from geo4bolivia.spatial import lisa, weights

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []
NOTE = "_These are associations, not causal effects. A causal reading needs a research design._"
FIRST, LAST = 2000, 2005                      # the first and last year of growth_panel


def two_years(first: pd.Series, last: pd.Series, ids=None) -> pd.DataFrame:
    """A panel of two years (2010 and 2020) of ``y`` from the values of each year."""
    ids = [f"r{i:02d}" for i in range(len(first))] if ids is None else list(ids)
    return pd.concat([pd.DataFrame({"geo_id": ids, "year": year, "y": np.asarray(values, dtype=float)})
                      for year, values in ((2010, first), (2020, last))], ignore_index=True)


@pytest.fixture(scope="module")
def ladder():
    """Twenty units with the values 1 to 20."""
    return np.arange(1.0, 21.0)


@pytest.fixture(scope="module")
def holes(growth_panel, units):
    """The growth panel without the last year of five units."""
    out = growth_panel.copy()
    out.loc[out["geo_id"].isin(units["geo_id"].iloc[:5]) & (out["year"] == LAST), "gdppc"] = float("nan")
    return out


@pytest.fixture(scope="module")
def rescaled(field):
    """The spatial field in two years; the second is a rescaling of the first."""
    return two_years(field["y"], 2 * field["y"] + 3, ids=field["geo_id"])


@pytest.fixture(scope="module")
def mirrored(field):
    """The spatial field in two years; in the second, high and low values are swapped."""
    return two_years(field["y"], -field["y"], ids=field["geo_id"])


# --- Markov transitions ----------------------------------------------------------------------

@pytest.mark.dynamics
def test_transitions_of_a_kept_and_a_reversed_ranking(ladder):
    pytest.importorskip("giddy")
    kept = transitions(two_years(ladder, ladder * 3), "y", k=2)
    assert kept.p.to_numpy().tolist() == [[1, 0], [0, 1]] and kept.shorrocks == 0
    assert kept.states == ("Q1", "Q2") and kept.n_transitions == 20 and kept.variable == "y"
    reversed_ = transitions(two_years(ladder, 21 - ladder), "y", k=2)
    assert reversed_.p.to_numpy().tolist() == [[0, 1], [1, 0]] and reversed_.shorrocks == 2
    assert reversed_.counts.to_numpy().tolist() == [[0, 10], [10, 0]]


@pytest.mark.dynamics
def test_transitions_of_a_stable_distribution(growth_panel):
    pytest.importorskip("giddy")
    res = transitions(growth_panel, "gdppc", k=4)
    assert list(res.df.columns) == ["geo_id", "name", "year", "gdppc", "state"] and len(res.df) == 64 * 6
    assert res.df["year"].dtype == growth_panel["year"].dtype and res.n_transitions == 64 * 5
    assert np.allclose(res.p.sum(axis=1), 1) and np.diag(res.p).min() > 0.9      # the order barely changes
    assert res.shorrocks < 0.1 and res.fig.data and res.gt is not None
    text = res.interpret()
    assert "highly persistent" in text and text.rstrip().endswith(NOTE)
    fixed = transitions(growth_panel, "gdppc", bins=[8000, 20000], per_year=False)   # levels, not positions
    assert fixed.k == 3 and fixed.scheme == "user_defined"


@pytest.mark.dynamics
def test_transitions_use_the_units_and_years_with_data(growth_panel, holes):
    pytest.importorskip("giddy")
    res = transitions(holes, "gdppc")
    assert res.n_transitions == 59 * 5 and res.df["geo_id"].nunique() == 59
    assert res.notes[0] == "transitions: kept the 59 units with data in all 6 years (5 left out)"
    empty_year = growth_panel.assign(gdppc=growth_panel["gdppc"].where(growth_panel["year"] != 2003))
    assert transitions(empty_year, "gdppc").n_transitions == 64 * 4               # a year without data is skipped


@pytest.mark.dynamics
def test_spatial_transitions_split_the_matrix_by_neighbours(growth_panel, units):
    pytest.importorskip("giddy")
    res = spatial_transitions(growth_panel, "gdppc", gdf=units, k=3)
    assert list(res.df.columns) == ["geo_id", "name", "year", "gdppc", "state", "neighbor_state"]
    assert res.df["name"].str.startswith("Unit ").all() and len(res.df) == 64 * 6
    assert res.k == 3 and res.m == 3 and len(res.p_conditional) == 3 and res.w_spec.startswith("queen")
    assert all(np.allclose(p.sum(axis=1), 1) for p in (res.p_global, *res.p_conditional))
    assert res.dof > 0 and 0 <= res.lr_p <= 1 and res.fig.data and res.interpret().rstrip().endswith(NOTE)
    # the matrix of all units is the classic one, with the same classes
    classic = transitions(growth_panel, "gdppc", k=3, per_year=False, relative=True)
    assert np.allclose(res.p_global, classic.p)
    two = spatial_transitions(growth_panel, "gdppc", gdf=units, k=3, m=2, per_year=True, relative=False)
    assert len(two.p_conditional) == 2 and not two.relative


@pytest.mark.dynamics
def test_spatial_transitions_restrict_the_weights_to_the_units_with_data(holes, units):
    pytest.importorskip("giddy")
    res = spatial_transitions(holes, "gdppc", w=weights(units), gdf=units, k=3)
    assert res.df["geo_id"].nunique() == 59 and "n=59" in res.w_spec
    assert "restricted from 64 units" in res.w_spec


def test_transitions_say_how_to_install_giddy(growth_panel, monkeypatch):
    for module in [m for m in sys.modules if m == "giddy" or m.startswith("giddy.")]:
        monkeypatch.delitem(sys.modules, module)
    monkeypatch.setitem(sys.modules, "giddy", None)
    with pytest.raises(ImportError, match=rf'pip install "{geo.PACKAGE}\[dynamics\]"'):
        transitions(growth_panel, "gdppc")


# --- LISA transitions ------------------------------------------------------------------------

def test_lisa_types_are_kept_when_the_values_are_rescaled(field, units, rescaled):
    res = lisa_transitions(rescaled, "y", gdf=units)
    one = lisa(field, "y", gdf=units)
    assert list(res.df.columns) == ["geo_id", "name", "cluster_2010", "cluster_2020", "moved", "transition"]
    assert res.n_units == 64 and res.n_stayed == 64 and res.n_moved == 0 and res.share_stayed == 1
    assert not res.df["moved"].any() and (res.df["cluster_2010"] == res.df["cluster_2020"]).all()
    assert tuple(res.matrix.index) == tuple(res.matrix.columns) == LISA_TYPES
    assert res.matrix.index.name == "cluster_2010" and res.matrix.columns.name == "cluster_2020"
    assert np.diag(res.matrix).tolist() == [one.n_hh, one.n_lh, one.n_ll, one.n_hl, one.n_ns]
    assert res.matrix.to_numpy().sum() == 64 == np.trace(res.matrix)
    assert res.moran_i_first == pytest.approx(one.moran_i) and res.moran_i_last == pytest.approx(one.moran_i)
    assert res.first == 2010 and res.last == 2020 and res.variable == "y" and res.w_spec == one.w_spec
    assert (res.df.set_index("geo_id")["cluster_2020"] == one.df.set_index("geo_id")["cluster"]).all()


def test_lisa_types_swap_when_the_values_are_mirrored(field, units, mirrored):
    res = lisa_transitions(mirrored, "y", gdf=units, tiles=None)
    one = lisa(field, "y", gdf=units)
    expected = pd.DataFrame(0, index=LISA_TYPES, columns=LISA_TYPES)
    for origin, destination, n in (("High-High", "Low-Low", one.n_hh), ("Low-Low", "High-High", one.n_ll),
                                   ("Low-High", "High-Low", one.n_lh), ("High-Low", "Low-High", one.n_hl),
                                   ("Not significant", "Not significant", one.n_ns)):
        expected.loc[origin, destination] = n
    assert one.n_hh > 0 and one.n_ll > 0                       # the planted clustering gives both kinds of cluster
    assert (res.matrix.to_numpy() == expected.to_numpy()).all()
    assert res.n_stayed == one.n_ns and res.n_moved == 64 - one.n_ns and res.df["moved"].sum() == res.n_moved
    assert res.moran_i_first == pytest.approx(res.moran_i_last) and res.p_sim_first == res.p_sim_last
    assert res.shares.loc["High-High", "Low-Low"] == 1 and np.allclose(res.shares.dropna().sum(axis=1), 1)
    assert res.shares.isna().all(axis=1).tolist() == (res.matrix.sum(axis=1) == 0).tolist()
    assert "High-High → Low-Low" in set(res.df["transition"])
    assert res.tidy()["units"].sum() == 64 and len(res.tidy()) == 25


def test_lisa_transition_figures_and_reading(units, mirrored):
    res = lisa_transitions(mirrored, "y", gdf=units, title="Mirror")
    heat = res.fig.data[0]
    assert res.fig.layout.title.text == "Mirror" and (np.asarray(heat.text) == res.matrix.to_numpy()).all()
    assert list(heat.x) == list(heat.y) == list(LISA_TYPES) and np.nanmax(heat.z) == 1
    assert [trace.name for trace in res.fig_map.data] == [*LISA_TYPES, "Changed type since 2010"]
    assert sum(len(trace.locations) for trace in res.fig_map.data[:5]) == 64
    assert "2020" in res.fig_map.layout.title.text and "2010" in res.fig_map.data[0].hovertemplate
    outline = res.fig_map.data[-1]
    assert outline.type == "scattermap" and list(outline.lon).count(None) == res.n_moved   # one ring per unit
    assert lisa_transitions(mirrored, "y", gdf=units, tiles=None).fig_map.data[-1].type == "scattergeo"
    text = res.interpret()
    assert f"{res.n_stayed} of 64 units" in text and "The most common change is from" in text
    assert "still High-High" in text and text.rstrip().endswith(NOTE) and "effect of" not in text


def test_lisa_transitions_use_the_units_with_data_in_both_years(growth_panel, holes, units):
    res = lisa_transitions(holes, "gdppc", gdf=units)
    assert (res.first, res.last, res.n_units) == (FIRST, LAST, 59) and "n=59" in res.w_spec
    assert res.notes[0].startswith("lisa_transitions: kept the 59 units with data in 2000 and 2005")
    given = lisa_transitions(holes, "gdppc", w=weights(units), gdf=units)
    assert given.n_units == 59 and "restricted from 64 units" in given.w_spec
    assert (given.matrix == res.matrix).all().all()
    middle = lisa_transitions(holes, "gdppc", 2001, 2003, gdf=units)             # all units have these years
    assert (middle.first, middle.last, middle.n_units) == (2001, 2003, 64)
    assert list(middle.df.columns[2:4]) == ["cluster_2001", "cluster_2003"]


# --- rank mobility ---------------------------------------------------------------------------

def test_rank_mobility_of_a_reversed_ranking(ladder):
    res = rank_mobility(two_years(ladder, 21 - ladder), "y", k=4, top=3)
    assert list(res.df.columns) == ["geo_id", "name", "y_2010", "y_2020", "rank_2010", "rank_2020", "rank_change",
                                    "group_2010", "group_2020"]
    assert res.spearman == pytest.approx(-1) and res.kendall == pytest.approx(-1)
    assert res.mean_abs_change == 10 and res.median_abs_change == 10 and res.share_same_group == 0
    assert (res.n_units, res.n_climbed, res.n_fell) == (20, 10, 10)
    assert (res.df["rank_2010"] + res.df["rank_2020"] == 21).all() and list(res.df["rank_2020"]) == list(range(1, 21))
    assert res.matrix.to_numpy().tolist() == np.fliplr(np.eye(4)).tolist()        # Q1 went to Q4, Q2 to Q3...
    assert res.counts.to_numpy().sum() == 20 and list(res.matrix.index) == ["Q1", "Q2", "Q3", "Q4"]
    assert res.matrix.index.name == "group_2010" and res.matrix.columns.name == "group_2020"
    assert list(res.climbers["rank_change"]) == [19, 17, 15] and list(res.fallers["rank_change"]) == [-19, -17, -15]
    assert res.climbers["geo_id"].iloc[0] == "r00" and res.fallers["geo_id"].iloc[0] == "r19"   # 1 -> 20, 20 -> 1
    assert "reversed" in res.interpret()


def test_rank_one_is_the_lowest_value_when_ascending(ladder):
    res = rank_mobility(two_years(ladder, 21 - ladder), "y", k=4, ascending=True)
    by_unit = res.df.set_index("geo_id")
    assert by_unit.loc["r00", ["rank_2010", "rank_2020", "rank_change"]].tolist() == [1, 20, -19]
    assert by_unit.loc["r00", ["group_2010", "group_2020"]].tolist() == ["Q1", "Q4"]   # groups are of the values
    assert res.spearman == pytest.approx(-1) and res.ascending and "lowest value" in res.interpret()


def test_rank_mobility_of_a_kept_ranking(ladder):
    res = rank_mobility(two_years(ladder, np.exp(ladder / 4)), "y", k=5)
    assert res.spearman == pytest.approx(1) and res.kendall == pytest.approx(1)
    assert res.mean_abs_change == 0 and res.share_same_group == 1 and res.n_climbed == res.n_fell == 0
    assert res.matrix.to_numpy().tolist() == np.eye(5).tolist() and (res.df["rank_change"] == 0).all()
    assert res.climbers.empty and res.fallers.empty and res.gt is not None
    text = res.interpret()
    assert "very stable" in text and "20 kept their rank" in text and text.rstrip().endswith(NOTE)


def test_rank_mobility_agrees_with_change(growth_panel):
    res = rank_mobility(growth_panel, "gdppc")
    assert (res.first, res.last, res.n_units, res.k) == (FIRST, LAST, 64, 5) and res.spearman > 0.99
    both = res.df.merge(change(growth_panel, "gdppc"), on="geo_id")
    assert (both["rank_2000"] == both["gdppc_rank_2000"]).all() and (both["rank_2005"] == both["gdppc_rank_2005"]).all()
    assert (both["rank_change"] == both["gdppc_rank_change"]).all()
    assert (both["gdppc_2005_x"] == both["gdppc_2005_y"]).all()
    assert np.allclose(res.matrix.sum(axis=1), 1) and res.share_same_group == np.trace(res.counts) / 64
    assert res.mean_abs_change == res.df["rank_change"].abs().mean()
    assert res.glance().loc[0, "variable"] == "gdppc" and res.tidy() is res.df and res.notes == ()


def test_rank_mobility_uses_the_units_with_data_in_both_years(holes):
    res = rank_mobility(holes, "gdppc")
    assert res.n_units == 59 and list(res.df["rank_2005"]) == list(range(1, 60))
    assert res.notes == ("rank_mobility: kept the 59 units with data in 2000 and 2005 (5 left out)",)
    assert rank_mobility(holes, "gdppc", last=2004).n_units == 64


def test_rank_mobility_figures(ladder):
    res = rank_mobility(two_years(ladder, 21 - ladder), "y", k=4, title="Ranks")
    line, climbed, fell, same = res.fig.data
    assert res.fig.layout.title.text == "Ranks" and list(line.x) == list(line.y) == [1, 20]      # the 45° line
    assert (climbed.name, fell.name, same.name) == ("Climbed (10)", "Fell (10)", "Same rank (0)")
    assert all(a > b for a, b in zip(climbed.x, climbed.y, strict=True)) and climbed.customdata[0][0] == "r00"
    assert res.fig.layout.xaxis.autorange == "reversed" and res.fig.layout.yaxis.autorange == "reversed"
    assert np.allclose(res.fig_matrix.data[0].z, res.matrix) and res.fig_matrix.data[0].text[0][3] == "1.00"
    assert "Climbed the most" in res.gt.as_raw_html() and "+19" in res.gt.as_raw_html()


@pytest.mark.dynamics
def test_rank_groups_are_the_classes_of_transitions(growth_panel):
    pytest.importorskip("giddy")
    ends = growth_panel[growth_panel["year"].isin([FIRST, LAST])]
    for k in (3, 5):
        assert np.allclose(rank_mobility(growth_panel, "gdppc", k=k).matrix, transitions(ends, "gdppc", k=k).p)


# --- inputs ----------------------------------------------------------------------------------

def test_inputs_are_checked(field, growth_panel, units, ladder):
    for function in (transitions, spatial_transitions, lisa_transitions, rank_mobility):
        with pytest.raises(ValueError, match="No column"):
            function(growth_panel, "nothing")
        with pytest.raises(TypeError, match="numeric"):
            function(growth_panel.assign(gdppc=growth_panel["gdppc"].astype(str)), "gdppc")
        with pytest.raises(ValueError, match=r"needs at least two years of 'y'; the data have \[2020\]"):
            function(field, "y")
        with pytest.raises(ValueError, match="needs a 'year' column"):
            function(field.drop(columns="year"), "y")
    for function in (lisa_transitions, rank_mobility):
        with pytest.raises(ValueError, match="No rows for 1999; the years with data are"):
            function(growth_panel, "gdppc", first=1999)
        with pytest.raises(ValueError, match="first must be earlier than last"):
            function(growth_panel, "gdppc", first=LAST, last=FIRST)
    centred = growth_panel.assign(gdppc=growth_panel["gdppc"] - growth_panel["gdppc"].max())
    with pytest.raises(ValueError, match="relative=True divides the values by each year's mean"):
        transitions(centred, "gdppc", relative=True)
    with pytest.raises(ValueError, match="relative=True divides the values by each year's mean"):
        spatial_transitions(centred, "gdppc", gdf=units)
    with pytest.raises(ValueError, match="at least as many units as groups"):
        rank_mobility(two_years(ladder[:3], ladder[:3]), "y")
    with pytest.raises(ValueError, match="is the same in every unit in 2020"):
        rank_mobility(two_years(ladder, ladder * 0), "y")
    with pytest.raises(ValueError, match="k=1 needs to be at least 2"):
        rank_mobility(two_years(ladder, ladder), "y", k=1)


# --- the project's data ----------------------------------------------------------------------

@pytest.mark.data
@pytest.mark.dynamics
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_without_boundaries_or_weights():
    for dataset in DATASETS:                    # the first dataset whose first variable has two years of numbers
        variable = metadata.variables(dataset)[0]
        values = geo.load(dataset, variables=variable).dropna(subset=[variable])
        if pd.api.types.is_numeric_dtype(values[variable]) and values["year"].nunique() >= 2:
            break
    else:
        pytest.skip("no dataset whose first variable is numeric and has at least two years")
    years = sorted(int(y) for y in values["year"].unique())
    label, country = geo.labels(dataset)[variable], geo.project.country_code()

    ranks = rank_mobility(dataset, variable)
    assert (ranks.first, ranks.last) == (years[0], years[-1]) and ranks.n_units > 3 and -1 <= ranks.spearman <= 1
    assert label in ranks.fig.layout.title.text and ranks.df["geo_id"].str.startswith(country).all()
    assert ranks.df["name"].notna().all() and ranks.interpret()

    clusters = lisa_transitions(dataset, variable)
    assert clusters.w_spec.startswith("queen") and clusters.n_units == ranks.n_units
    assert clusters.matrix.to_numpy().sum() == clusters.n_units == clusters.n_stayed + clusters.n_moved
    assert label in clusters.fig.layout.title.text and label in clusters.fig_map.layout.title.text

    pytest.importorskip("giddy")
    classic = transitions(dataset, variable)
    units = classic.df["geo_id"].nunique()
    assert classic.n_transitions == units * (len(years) - 1) and label in classic.fig.layout.title.text
    spatial = spatial_transitions(dataset, variable, relative=False)
    assert spatial.w_spec.startswith("queen") and spatial.df["geo_id"].nunique() == units
    assert spatial.df["name"].notna().all() and len(spatial.p_conditional) == spatial.m
