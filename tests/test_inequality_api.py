"""Inequality between units: the measures, the Lorenz curve and Theil's decomposition, on data with a known answer."""

import math

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import metadata
from geo4bolivia.inequality import inequality, theil_decomposition
from geo4bolivia.spatial import weights

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []
NOTE = "_These are associations, not causal effects. A causal reading needs a research design._"


def table(by_year: dict, **columns) -> pd.DataFrame:
    """A small panel: ``{year: values}``, one unit per value, plus constant columns per unit."""
    n = len(next(iter(by_year.values())))
    ids = [f"x{i}" for i in range(n)]
    return pd.concat([pd.DataFrame({"geo_id": ids, "year": year, "v": values, **columns})
                      for year, values in by_year.items()], ignore_index=True)


def theil(values) -> float:
    shares = np.asarray(values, dtype=float) / np.sum(values)
    return float(np.sum(shares * np.log(shares * len(shares))))


# --- inequality in each year ----------------------------------------------------------------

def test_inequality_falls_where_dispersion_shrinks(growth_panel):
    res = inequality(growth_panel, "gdppc", measures=("gini", "theil", "cv"))
    years = sorted(growth_panel["year"].unique())
    assert list(res.df.columns) == ["year", "n_units", "gini", "theil", "cv"] and list(res.df["year"]) == years
    assert res.variable == "gdppc" and res.n_years == 6 and res.n_units == growth_panel["geo_id"].nunique()
    for measure in ("gini", "theil", "cv"):
        assert res.df[measure].is_monotonic_decreasing
    trend = res.summary.set_index("measure")
    assert (trend["slope"] < 0).all() and (trend["pvalue"] < 0.05).all() and trend["converging"].all()
    assert trend.loc["gini", "first"] == res.df["gini"].iloc[0] and trend.loc["gini", "last"] == res.df["gini"].iloc[-1]
    assert trend.loc["gini", "change"] == pytest.approx(res.df["gini"].iloc[-1] - res.df["gini"].iloc[0])
    text = res.interpret()
    assert "narrowing" in text and "Lorenz" in text and text.endswith(NOTE)
    assert "causes" not in text and "effect of" not in text
    assert res.fig.data and res.gt is not None


def test_lorenz_table_and_figure(growth_panel):
    res = inequality(growth_panel, "gdppc")
    years = sorted(growth_panel["year"].unique())
    assert list(res.lorenz.columns) == ["geo_id", "name", "year", "gdppc", "cum_units", "cum_share"]
    assert len(res.lorenz) == len(growth_panel)                       # every unit in every year
    for _, rows in res.lorenz.groupby("year"):
        assert rows["gdppc"].is_monotonic_increasing and rows["cum_share"].iloc[-1] == pytest.approx(1)
        assert (rows["cum_share"] <= rows["cum_units"] + 1e-12).all()   # the curve lies under the diagonal
    # six years: the figure draws the first and the last, and the line of equality
    assert [t.name.split(" ")[0] for t in res.fig_lorenz.data] == ["Equality", str(years[0]), str(years[-1])]
    assert list(res.fig_lorenz.data[1].x[:1]) == [0] and list(res.fig_lorenz.data[1].y[:1]) == [0]
    # less inequality: the lower half holds more of the total, and the Gini is the area between the curves
    assert res.lorenz_share(years[-1], 0.5) > res.lorenz_share(years[0], 0.5)
    last = res.lorenz[res.lorenz["year"] == years[-1]]
    x, y = np.r_[0, last["cum_units"]], np.r_[0, last["cum_share"]]
    area = float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))
    assert 1 - 2 * area == pytest.approx(res.df["gini"].iloc[-1], abs=1e-9)
    few = inequality(growth_panel, "gdppc", first=years[0], last=years[2])
    assert len(few.fig_lorenz.data) == 1 + 3                          # up to four years: one curve each
    none = inequality(growth_panel, "gdppc", lorenz=False)
    assert none.lorenz is None and none.fig_lorenz is None and "Lorenz" not in none.interpret()


def test_equal_units_have_no_inequality():
    res = inequality(table({2000: [5.0] * 4, 2010: [5.0] * 4}), "v")
    assert res.df["gini"].tolist() == pytest.approx([0, 0]) and res.df["theil"].tolist() == pytest.approx([0, 0])
    assert res.lorenz["cum_share"].tolist() == pytest.approx(res.lorenz["cum_units"].tolist())   # the diagonal
    assert res.lorenz_share(2010, 0.5) == pytest.approx(0.5)
    assert "unchanged" in res.interpret()


def test_one_unit_holds_everything():
    data = table({2000: [0.0, 0.0, 0.0, 10.0], 2010: [0.0, 0.0, 0.0, 10.0]})
    res = inequality(data, "v", measures="gini")
    assert res.df["gini"].tolist() == pytest.approx([0.75, 0.75])      # (n - 1) / n
    assert res.lorenz[res.lorenz["year"] == 2010]["cum_share"].tolist() == [0, 0, 0, 1]
    assert res.lorenz_share(2010, 0.75) == 0 and res.lorenz_share(2010, 1) == 1
    with pytest.raises(ValueError, match=r"strictly positive.*6 value"):
        inequality(data, "v")                                          # Theil's index takes logarithms


def test_two_years_compare_without_a_trend(growth_panel):
    years = sorted(growth_panel["year"].unique())
    res = inequality(growth_panel[growth_panel["year"].isin([years[0], years[-1]])], "gdppc")
    assert list(res.df["year"]) == [years[0], years[-1]] and res.n_years == 2
    assert res.summary["slope"].isna().all() and (res.summary["change"] < 0).all()
    assert len(res.notes) == 1 and "three or more years" in res.notes[0]
    text = res.interpret()
    assert "could not be estimated" not in text and text.count("three or more years") == 1
    assert "fell from" in text and text.endswith(NOTE)
    html = res.gt.as_raw_html()
    assert str(years[0]) in html and str(years[-1]) in html and "Gini index" in html
    assert len(res.fig_lorenz.data) == 3 and res.fig.data
    # the same two years as a window keep the years between them, and then there is a trend
    window = inequality(growth_panel, "gdppc", first=years[1], last=years[4])
    assert list(window.df["year"]) == years[1:5] and window.summary["slope"].notna().all()


def test_spatial_gini_uses_boundaries_and_weights(growth_panel, units):
    res = inequality(growth_panel, "gdppc", spatial=True, permutations=19, gdf=units)
    assert {"gini_spatial", "gini_spatial_p"} <= set(res.df.columns) and res.w_spec.startswith("queen")
    assert ((res.df["gini_spatial"] > 0) & (res.df["gini_spatial"] < res.df["gini"])).all()
    assert res.df["gini_spatial_p"].between(0, 1).all() and "neighboring" in res.interpret()
    plain = inequality(growth_panel, "gdppc")
    assert plain.w_spec is None and "gini_spatial" not in plain.df.columns
    assert res.df["gini"].tolist() == pytest.approx(plain.df["gini"].tolist())
    given = inequality(growth_panel, "gdppc", w=weights(units, method="rook"), permutations=0, gdf=units)
    assert given.w_spec.startswith("rook") and given.df["gini_spatial_p"].isna().all()   # w= implies spatial
    holes = growth_panel.copy()
    year = holes["year"].min()
    holes.loc[holes["geo_id"].isin(units["geo_id"].iloc[:3]) & (holes["year"] == year), "gdppc"] = float("nan")
    fewer = inequality(holes, "gdppc", spatial=True, permutations=0, gdf=units)
    assert (fewer.df["n_units"] == len(units) - 3).all() and fewer.lorenz["geo_id"].nunique() == len(units) - 3
    assert any("3 unit(s)" in note for note in fewer.notes)


# --- Theil's index between and within groups ------------------------------------------------

def test_theil_between_and_within_known_answers():
    # 2000: both groups have the same mean, so nothing lies between them;
    # 2010: the members of each group are equal, so nothing lies within them.
    data = table({2000: [1.0, 3.0, 2.0, 2.0], 2010: [1.0, 1.0, 3.0, 3.0]}, g=["a", "a", "b", "b"])
    res = theil_decomposition(data, "v", by="g")
    assert list(res.df.columns) == ["year", "theil", "between", "within", "between_share"]
    assert res.by == "g" and res.n_groups == 2 and res.variable == "v"
    first, last = res.df.iloc[0], res.df.iloc[1]
    assert first["theil"] == pytest.approx(theil([1, 3, 2, 2])) and last["theil"] == pytest.approx(theil([1, 1, 3, 3]))
    assert first["between"] == pytest.approx(0, abs=1e-12) and first["between_share"] == pytest.approx(0, abs=1e-12)
    assert first["within"] == pytest.approx(first["theil"])
    assert last["within"] == pytest.approx(0, abs=1e-12) and last["between_share"] == pytest.approx(1)
    assert last["theil"] == pytest.approx(0.25 * math.log(0.5) + 0.75 * math.log(1.5))
    text = res.interpret()
    assert "100% of it lies between g groups" in text and "rose from 0% to 100%" in text and text.endswith(NOTE)


def test_theil_by_a_column_of_the_table(growth_panel):
    ids = sorted(growth_panel["geo_id"].unique())
    data = growth_panel.assign(half=np.where(growth_panel["geo_id"].isin(ids[: len(ids) // 2]), "first", "second"))
    res = theil_decomposition(data, "gdppc", by="half", permutations=19)
    assert res.by == "half" and res.n_groups == 2 and list(res.df["year"]) == sorted(data["year"].unique())
    assert (res.df["between"] + res.df["within"]).tolist() == pytest.approx(res.df["theil"].tolist())
    assert res.df["between_share"].between(0, 1).all() and res.df["p_between"].between(0, 1).all()
    assert res.df["theil"].tolist() == pytest.approx(inequality(data, "gdppc").df["theil"].tolist())
    assert res.fig.data and res.gt is not None and "half" in res.interpret()
    one_year = theil_decomposition(data[data["year"] == data["year"].max()], "gdppc", by="half")
    assert len(one_year.df) == 1 and "Over the window" not in one_year.interpret()


def test_a_share_that_rounds_to_the_same_number_did_not_move():
    data = table({2000: [1.0, 1.5, 3.0, 3.5], 2010: [1.0, 1.5, 3.0, 3.501]}, g=["a", "a", "b", "b"])
    text = theil_decomposition(data, "v", by="g").interpret()
    assert "stayed at about" in text and "rose from" not in text and "fell from" not in text


# --- errors ---------------------------------------------------------------------------------

def test_inputs_are_checked(growth_panel, field):
    with pytest.raises(ValueError, match="No column"):
        inequality(growth_panel, "nothing")
    with pytest.raises(ValueError, match="No rows for 1999"):
        inequality(growth_panel, "gdppc", first=1999)
    with pytest.raises(ValueError, match="at least two"):
        inequality(field, "x1", measures="gini")                       # a single year
    with pytest.raises(ValueError, match="at least two"):
        inequality(growth_panel, "gdppc", first=2003, last=2003)
    with pytest.raises(ValueError, match="must not be after"):
        inequality(growth_panel, "gdppc", first=2004, last=2001)
    with pytest.raises(ValueError, match="year"):
        inequality(growth_panel.drop(columns="year").drop_duplicates("geo_id"), "gdppc")
    with pytest.raises(ValueError, match="unknown measure"):
        inequality(growth_panel, "gdppc", measures=("gini", "atkinson"))
    with pytest.raises(TypeError, match="numeric"):
        inequality(growth_panel.assign(gdppc=growth_panel["gdppc"].astype(str)), "gdppc")
    with pytest.raises(ValueError, match="geo_id"):
        theil_decomposition(growth_panel.rename(columns={"geo_id": "id"}), "gdppc", by="year")


def test_theil_needs_groups_and_positive_values(growth_panel):
    with pytest.raises(ValueError, match="by is required"):
        theil_decomposition(growth_panel, "gdppc")                     # units outside the project: no default
    with pytest.raises(ValueError, match="neither a column"):
        theil_decomposition(growth_panel, "gdppc", by="nothing")
    grouped = growth_panel.assign(g=growth_panel["geo_id"].str[-1], one="all")
    with pytest.raises(ValueError, match="at least 2"):
        theil_decomposition(grouped, "gdppc", by="one")
    negative = grouped.assign(gdppc=grouped["gdppc"] - grouped["gdppc"].median())
    with pytest.raises(ValueError, match="strictly positive"):
        theil_decomposition(negative, "gdppc", by="g")
    moving = grouped.assign(g=grouped["g"].where(grouped["year"] < grouped["year"].max(), "z"))
    with pytest.raises(ValueError, match="constant within"):
        theil_decomposition(moving, "gdppc", by="g")


# --- the project's data ---------------------------------------------------------------------

def _positive_panel():
    """The first dataset whose first variable is strictly positive and has two or more years."""
    for dataset in DATASETS:
        variable = metadata.variables(dataset)[0]
        values = geo.load(dataset, variables=variable).dropna(subset=[variable])
        if len(values) and (values[variable] > 0).all() and values["year"].nunique() >= 2:
            return dataset, variable, values
    return None


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_with_the_default_groups():
    found = _positive_panel()
    if found is None:
        pytest.skip("no dataset whose first variable is strictly positive in two or more years")
    dataset, variable, values = found
    res = inequality(dataset, variable)
    assert list(res.df["year"]) == sorted(values["year"].unique()) and (res.df["gini"] > 0).all()
    assert geo.labels(dataset)[variable] in res.fig.layout.title.text
    assert geo.labels(dataset)[variable] in res.fig_lorenz.layout.title.text
    assert res.lorenz["geo_id"].str.startswith(geo.project.country_code()).all() and res.lorenz["name"].notna().all()

    scale = geo.scale_of(values["geo_id"].iloc[0])
    unit_table = geo.units(scale).set_index("geo_id").loc[values["geo_id"].unique()]
    groups = {s: unit_table[f"{s}_id"].nunique() for s in geo.ancestors(scale) if f"{s}_id" in unit_table.columns}
    groups = {s: n for s, n in groups.items() if n >= 2}
    if not groups:
        pytest.skip("the units nest in no coarser scale with two or more units")
    dec = theil_decomposition(dataset, variable)                       # by: the coarsest scale with 2+ units
    assert groups[dec.by] == min(groups.values()) == dec.n_groups
    assert (dec.df["between"] + dec.df["within"]).tolist() == pytest.approx(dec.df["theil"].tolist())
    assert dec.df["theil"].tolist() == pytest.approx(res.df["theil"].tolist())
    assert geo.labels(dataset)[variable] in dec.fig.layout.title.text and dec.interpret().endswith(NOTE)
    for by, n in groups.items():        # a scale groups by its units, also where their names repeat
        assert theil_decomposition(dataset, variable, by=by).n_groups == n
        named = geo.load(dataset, variables=variable, groups=[by])
        assert theil_decomposition(named, variable, by=by).n_groups == n
