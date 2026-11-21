"""Exploring a panel without space: correlations, extremes, distributions, scatterplots and trends.

The answers are known in closed form: ``toy`` builds a small panel whose columns are exact
functions of each other, and the fixtures plant a positive relation (``field``) and a
falling, narrowing variable (``growth_panel``).
"""

import numpy as np
import pandas as pd
import pytest

import geo4bolivia as geo
from geo4bolivia import metadata
from geo4bolivia._engine.pedagogy._interpret._shared import _ASSOC_NOTE
from geo4bolivia.explore import correlation, distribution, extremes, scatter, trend

DATASETS = list(metadata.dataset_ids()) if geo.project.local_root() is not None else []
SD = np.sqrt(7.5)                       # the standard deviation of 1, 2, ..., 9


def toy(years=(2010, 2020)) -> pd.DataFrame:
    """Nine units (three in the East, six in the West) observed in ``years``.

    With ``a`` = 1..9 and ``t`` = 0, 1, ... the position of the year: ``level`` = a + 10 t
    (symmetric: mean 5 + 10 t, quartiles 3, 5, 7 + 10 t), ``double`` = 2 level + 3,
    ``opposite`` = -level, ``cube`` = a ** 3 (monotonic, not linear), ``flip`` = a, and -a
    in the last year, ``pace`` = a + 5 t in the East and a + t in the West,
    ``people`` = 100 a.
    """
    a = np.arange(1.0, 10.0)
    east = a <= 3
    parts = []
    for t, year in enumerate(years):
        level = a + 10 * t
        parts.append(pd.DataFrame({
            "geo_id": [f"U{int(i):02d}" for i in a], "name": [f"Unit {int(i)}" for i in a], "year": year,
            "region": np.where(east, "East", "West"), "a": a, "level": level, "double": 2 * level + 3,
            "opposite": -level, "cube": a ** 3, "flip": a if year != years[-1] else -a,
            "pace": a + np.where(east, 5, 1) * t, "people": 100 * a}))
    return pd.concat(parts, ignore_index=True)


def named(df: pd.DataFrame) -> pd.DataFrame:
    """A fixture panel with unit names, as ``load`` returns it."""
    return df.assign(name="Unit " + df["geo_id"])


def unit_lines(fig) -> int:
    """How many unit trajectories the first trace of a trend figure draws."""
    return sum(value is None for value in fig.data[0].x)


# --- correlation ------------------------------------------------------------------------------

def test_correlation_recovers_exact_relations():
    res = correlation(toy(), ["level", "double", "opposite", "cube"])
    assert res.year == 2020 and res.n == 9 and res.variables == ("level", "double", "opposite", "cube")
    assert res.df.loc["level", "double"] == pytest.approx(1.0)
    assert res.df.loc["level", "opposite"] == pytest.approx(-1.0)
    assert 0.9 < res.df.loc["level", "cube"] < 0.999                  # monotonic, not linear
    assert correlation(toy(), ["level", "cube"], method="spearman").df.loc["level", "cube"] == pytest.approx(1.0)
    assert list(res.pairs.columns) == ["variable_1", "variable_2", "correlation"] and len(res.pairs) == 6
    assert res.pairs["correlation"].is_monotonic_decreasing


def test_correlation_figure_table_and_reading():
    res = correlation(toy(), ["level", "double", "opposite"], digits=3, title="My title")
    heat = res.fig.data[0]
    assert heat.type == "heatmap" and np.asarray(heat.z).shape == (3, 3)
    assert (heat.zmin, heat.zmid, heat.zmax) == (-1, 0, 1) and heat.texttemplate == "%{z:.3f}"
    assert res.fig.layout.title.text == "My title"
    html = res.gt.as_raw_html()
    assert "Pearson" in html and "Spearman" in html and "1.000" in html and "A: level" in html
    text = res.interpret()
    assert "strongest positive correlation is between **level** and **double** (r = 1.00)" in text
    assert "strongest negative correlation" in text and "(r = -1.00)" in text and text.endswith(_ASSOC_NOTE)


def test_correlation_chooses_the_year_and_the_variables():
    df = toy()
    assert correlation(df, ["a", "flip"]).df.loc["a", "flip"] == pytest.approx(-1.0)            # the last year
    assert correlation(df, ["a", "flip"], year=2010).df.loc["a", "flip"] == pytest.approx(1.0)
    pooled = correlation(df, ["a", "flip"], year="all")
    assert pooled.df.loc["a", "flip"] == pytest.approx(0.0, abs=1e-12) and pooled.n == 18 and pooled.year is None
    assert "all years" in pooled.fig.layout.title.text
    everything = correlation(df.assign(source_id=range(len(df)), empty=np.nan))
    assert set(everything.variables) == {"a", "level", "double", "opposite", "cube", "flip", "pace", "people"}
    assert "empty" in everything.notes[0]                             # a variable without data is left out, and said
    with pytest.raises(ValueError, match="no data or do not vary"):
        correlation(df.assign(empty=np.nan), ["level", "empty"])
    with pytest.raises(ValueError, match="at least two"):
        correlation(df, ["level"])


def test_correlation_uses_the_units_with_every_variable(field):
    holes = named(field)
    holes.loc[:4, "x2"] = np.nan
    res = correlation(holes)
    assert res.n == len(field) - 5 and "5 of 64" in res.notes[0]
    assert res.df.loc["x1", "y"] > 0.5 and res.df.loc["x2", "y"] < 0   # y is built from x1 - 0.5 x2
    assert "name" not in res.variables and res.year == 2020


# --- extremes ---------------------------------------------------------------------------------

def test_extremes_finds_the_two_ends():
    res = extremes(toy(), "level", n=3)
    assert list(res.df.columns) == ["geo_id", "name", "region", "level", "rank", "end"]
    assert list(res.df["name"]) == ["Unit 9", "Unit 8", "Unit 7", "Unit 3", "Unit 2", "Unit 1"]
    assert list(res.df["rank"]) == [1, 2, 3, 7, 8, 9] and list(res.df["end"]) == ["highest"] * 3 + ["lowest"] * 3
    assert (res.highest, res.lowest, res.median, res.n_units, res.year, res.variable) == (19, 11, 15, 9, 2020, "level")
    assert list(extremes(toy(), "level", 2010, n=1).df["level"]) == [9, 1]


def test_extremes_figure_table_and_reading():
    res = extremes(toy(), "level", n=2)
    top, bottom = res.fig.data
    assert top.type == "bar" and top.orientation == "h" and (top.name, bottom.name) == ("Highest 2", "Lowest 2")
    assert list(top.x) == [19, 18] and list(bottom.x) == [12, 11] and top.marker.color != bottom.marker.color
    assert list(res.fig.layout.yaxis.ticktext) == ["Unit 9", "Unit 8", "Unit 2", "Unit 1"]
    assert "Highest 2" in res.gt.as_raw_html() and "Unit 9" in res.gt.as_raw_html()
    text = res.interpret()
    assert "ranges from 11 (Unit 1) to 19 (Unit 9)" in text and "The 2 lowest: Unit 1 (11), Unit 2 (12)." in text
    assert text.endswith(_ASSOC_NOTE)


def test_extremes_tells_homonyms_apart_and_checks_n():
    df = toy()
    df["name"] = df["name"].replace({"Unit 1": "Twin", "Unit 9": "Twin"})
    assert list(extremes(df, "level", n=1).fig.layout.yaxis.ticktext) == ["Twin (West)", "Twin (East)"]
    assert extremes(toy(), "level", n=2).notes == ()
    ties = extremes(toy().assign(level=lambda d: d["level"].clip(upper=17)), "level", n=2)     # 17, 17, 17, 16, ...
    assert ties.notes == ("1 more unit(s) share the value 17 of the last of the 2 highest shown.",)
    with pytest.raises(ValueError, match="at least 10 units with data; there are 9 in 2020"):
        extremes(toy(), "level", n=5)
    with pytest.raises(ValueError, match="one year"):
        extremes(toy(), "level", year="all")


def test_units_without_a_name_still_get_one(field):
    res = extremes(field, "y")
    assert list(res.df.columns) == ["geo_id", "name", "y", "rank", "end"] and res.df["name"].notna().all()
    assert res.df["y"].iloc[0] == field["y"].max() and res.df["y"].iloc[-1] == field["y"].min()


# --- distribution -----------------------------------------------------------------------------

def test_distribution_summary_is_exact():
    res = distribution(toy(), "level")
    assert list(res.df.columns) == ["year", "n", "mean", "sd", "min", "p25", "median", "p75", "max", "skewness"]
    assert list(res.df["year"]) == [2010, 2020] and list(res.df["n"]) == [9, 9]
    assert list(res.df["mean"]) == [5, 15] and list(res.df["median"]) == [5, 15]
    assert list(res.df["p25"]) == [3, 13] and list(res.df["p75"]) == [7, 17]
    assert list(res.df["min"]) == [1, 11] and list(res.df["max"]) == [9, 19]
    assert res.df["sd"].tolist() == pytest.approx([SD, SD]) and res.df["skewness"].tolist() == pytest.approx([0, 0])
    assert res.year is None and res.kind == "histogram" and res.variable == "level"
    text = res.interpret()
    assert "rose from 5 to 15" in text and "roughly symmetric" in text and text.endswith(_ASSOC_NOTE)


def test_histograms_overlay_up_to_four_years(growth_panel):
    two = distribution(toy(), "level", bins=6)
    assert [t.name for t in two.fig.data] == ["2010", "2020"] and two.fig.layout.barmode == "overlay"
    assert all(t.type == "bar" and len(t.y) == 6 and sum(t.y) == 9 for t in two.fig.data)
    one = distribution(toy(), "level", 2010)
    assert len(one.fig.data) == 1 and one.year == 2010 and len(one.df) == 1 and "in 2010 averages 5" in one.interpret()
    panel = named(growth_panel)                                       # six years: the last one only
    last = distribution(panel, "gdppc")
    assert len(last.fig.data) == 1 and last.year == 2005 and "6 years" in last.notes[0]
    assert sum(last.fig.data[0].y) == panel["geo_id"].nunique() and len(last.fig.data[0].y) == 30
    assert len(distribution(panel, "gdppc", year="all").fig.data) == 6
    assert list(distribution(panel, "gdppc", year=[2005, 2000]).df["year"]) == [2000, 2005]


@pytest.mark.parametrize(("kind", "trace"), [("box", "box"), ("violin", "violin"), ("ridgeline", "scatter")])
def test_distribution_kinds_compare_every_year(growth_panel, kind, trace):
    res = distribution(named(growth_panel), "gdppc", kind=kind)
    assert len(res.df) == 6 and len(res.fig.data) == 6 and all(t.type == trace for t in res.fig.data)
    assert res.year is None and res.fig.layout.title.text == "Distribution of gdppc by year"
    assert res.df["sd"].is_monotonic_decreasing and "narrowed" in res.interpret()    # planted sigma-convergence
    assert (res.df["skewness"] > 0).all()                             # levels of a log-normal variable


def test_distribution_by_group():
    res = distribution(toy(), "level", by="region", kind="box")
    assert list(res.df["region"]) == ["East", "West"] and list(res.df["n"]) == [3, 6]
    assert list(res.df["mean"]) == [12, 16.5] and res.year == 2020 and res.by == "region"
    assert [t.name for t in res.fig.data] == ["East", "West"] and list(res.fig.data[0].y) == [11, 12, 13]
    assert res.fig.layout.xaxis.title.text == "region" and res.fig.layout.yaxis.title.text == "level"
    assert "highest in **West** (16.5) and lowest in **East** (12)" in res.interpret()
    assert list(distribution(toy(), "level", 2010, by="region", kind="violin").df["mean"]) == [2, 6.5]
    assert list(distribution(toy(), "level", "all", by="region").df["n"]) == [6, 12]           # both years pooled
    assert [t.name for t in distribution(toy(), "level", by="region").fig.data] == ["East", "West"]
    assert len(distribution(toy(), "level", by="region", kind="ridgeline").fig.data) == 2
    with pytest.raises(ValueError, match="No column"):
        distribution(toy(), "level", by="nothing")


# --- scatter ----------------------------------------------------------------------------------

def test_scatter_recovers_the_line():
    res = scatter(toy(), "level", "double")
    assert (res.slope, res.intercept, res.r2, res.corr) == pytest.approx((2, 3, 1, 1))
    assert (res.n, res.year, res.x, res.y, res.fit) == (9, 2020, "level", "double", "ols")
    assert list(res.df.columns) == ["geo_id", "name", "year", "level", "double"] and len(res.df) == 9
    points, line = res.fig.data
    assert points.mode == "markers" and points.hovertext[0] == "Unit 1" and list(points.x) == list(range(11, 20))
    assert line.mode == "lines" and (line.y[0], line.y[-1]) == pytest.approx((25, 41))
    assert "slope = 2" in res.fig.layout.annotations[0].text and "n = 9" in res.fig.layout.annotations[0].text
    assert res.fig.layout.xaxis.title.text == "level" and res.fig.layout.yaxis.title.text == "double"
    assert "positively correlated (r = 1.00" in res.interpret() and res.interpret().endswith(_ASSOC_NOTE)
    down = scatter(toy(), "level", "opposite", 2010)
    assert down.slope == pytest.approx(-1) and down.corr == pytest.approx(-1) and down.year == 2010
    assert "negatively correlated" in down.interpret() and "lower opposite" in down.interpret()


def test_scatter_in_logs_gives_the_elasticity():
    df = toy()
    df["power"] = 5 * df["level"] ** 1.5
    res = scatter(df, "level", "power", log_x=True, log_y=True)
    assert (res.slope, res.intercept, res.r2) == pytest.approx((1.5, np.log(5), 1))
    assert res.fig.layout.xaxis.type == "log" and res.fig.layout.yaxis.type == "log"
    assert "1% more of level goes with 1.5% higher power" in res.interpret()
    df.loc[df["name"] == "Unit 1", "level"] = 0.0                     # no logarithm: left out, and said
    less = scatter(df, "level", "power", log_x=True)
    assert less.n == 8 and "zero or less" in less.notes[0]


def test_scatter_fits_colours_and_sizes(field):
    df = toy()
    smooth = scatter(df, "level", "cube", fit="lowess")
    assert smooth.fig.data[-1].name == "LOWESS smooth" and not smooth.fig.layout.annotations
    assert smooth.slope > 0 and "LOWESS" in smooth.interpret()        # the numbers of the line are still reported
    assert [t.mode for t in scatter(df, "level", "cube", fit=None).fig.data] == ["markers"]
    groups = scatter(df, "level", "double", color="region", size="people")
    assert [t.name for t in groups.fig.data[:2]] == ["East", "West"] and groups.fig.layout.showlegend
    assert list(groups.fig.data[0].marker.size) == [100, 200, 300] and "region" in groups.df and "people" in groups.df
    shaded = scatter(df, "level", "double", color="people", fit=None).fig.data[0]
    assert shaded.marker.showscale and list(shaded.marker.color) == list(df["people"].iloc[:9])
    planted = scatter(named(field), "x1", "y")
    assert planted.slope > 0.5 and planted.p_value < 0.01 and 0 < planted.r2 < 1
    assert scatter(named(field), "x2", "y").corr < 0
    with pytest.raises(ValueError, match="non-negative"):
        scatter(df, "level", "double", size="opposite")
    with pytest.raises(ValueError, match="fit must be"):
        scatter(df, "level", "double", fit="cubic")


# --- trend ------------------------------------------------------------------------------------

def test_trend_follows_a_linear_rise():
    res = trend(toy((2000, 2010, 2020)), "level")
    assert list(res.df.columns) == ["year", "mean", "lower", "upper", "n"] and list(res.df["year"]) == [2000, 2010, 2020]
    assert list(res.df["mean"]) == [5, 15, 25] and list(res.df["n"]) == [9, 9, 9]
    assert res.df["lower"].tolist() == pytest.approx([5 - SD / 3, 15 - SD / 3, 25 - SD / 3])      # one standard error
    assert res.df["upper"].tolist() == pytest.approx([5 + SD / 3, 15 + SD / 3, 25 + SD / 3])
    assert (res.first, res.last, res.value_first, res.value_last, res.change) == (2000, 2020, 5, 25, 20)
    assert res.share_rising == 1 and res.n_units == 9 and res.variable == "level"
    each, band, line = res.fig.data
    assert each.name == "Each unit" and unit_lines(res.fig) == 9 and band.fill == "toself"
    assert line.name == "Mean" and list(line.y) == [5, 15, 25] and list(line.x) == [2000, 2010, 2020]
    text = res.interpret()
    assert "rose from 5 to 25 (a change of +20)" in text and "Every unit" in text and text.endswith(_ASSOC_NOTE)


def test_trend_of_the_median_and_without_units():
    res = trend(toy((2000, 2010, 2020)), "level", stat="median", units=False)
    assert list(res.df["median"]) == [5, 15, 25] and list(res.df["lower"]) == [3, 13, 23]          # the quartiles
    assert list(res.df["upper"]) == [7, 17, 27] and len(res.fig.data) == 2
    assert "interquartile range" in res.interpret() and "interquartile" in res.fig.layout.title.subtitle.text


def test_trend_by_group_names_who_grew_most():
    res = trend(toy((2000, 2010, 2020)), "pace", by="region")
    assert list(res.df.columns) == ["year", "region", "mean", "lower", "upper", "n"] and len(res.df) == 6
    east, west = res.df[res.df["region"] == "East"], res.df[res.df["region"] == "West"]
    assert list(east["mean"]) == [2, 7, 12] and list(west["mean"]) == [6.5, 7.5, 8.5] and list(east["n"]) == [3] * 3
    assert [t.name for t in res.fig.data if t.mode == "lines+markers"] == ["East", "West"]
    text = res.interpret()
    assert "**East** grew most (+10, from 2 to 12)" in text and "**West** grew least (+2)" in text
    assert "gap between the highest and the lowest group narrowed from 4.5 to 3.5" in text


def test_trend_draws_a_reproducible_sample_of_units(growth_panel):
    panel = named(growth_panel)
    res = trend(panel, "gdppc", max_units=10)
    assert unit_lines(res.fig) == 10 and "sample of 10 of the 64" in res.notes[0]
    assert list(res.fig.data[0].text) == list(trend(panel, "gdppc", max_units=10).fig.data[0].text)
    assert len(res.df) == 6 and list(res.df["n"]) == [64] * 6           # the statistics use every unit
    assert res.change < 0 and "fell" in res.interpret() and unit_lines(trend(panel, "gdppc").fig) == 64


def test_trend_needs_two_years(field):
    with pytest.raises(ValueError, match=r"at least two years with data for 'y'; the table has \[2020\]"):
        trend(named(field), "y")
    with pytest.raises(ValueError, match="no year column"):
        trend(named(field).drop(columns="year"), "y")


# --- every function ---------------------------------------------------------------------------

def test_inputs_are_checked(field):
    df = named(field)
    for call in (lambda d, v: correlation(d, [v, "x1"]), extremes, distribution, lambda d, v: scatter(d, "x1", v),
                 lambda d, v: scatter(d, v, "x1")):
        with pytest.raises(ValueError, match="No column"):
            call(df, "nothing")
        with pytest.raises(TypeError, match="numeric"):
            call(df.assign(y=df["y"].astype(str)), "y")
        with pytest.raises(ValueError, match="geo_id"):
            call(df.rename(columns={"geo_id": "id"}), "y")
    for call in (lambda y: correlation(df, year=y), lambda y: extremes(df, "y", y), lambda y: distribution(df, "y", y),
                 lambda y: scatter(df, "x1", "y", y)):
        with pytest.raises(ValueError, match="No rows for 1999; the years with data are \\[2020\\]"):
            call(1999)
    with pytest.raises(ValueError, match="kind must be"):
        distribution(df, "y", kind="pie")
    with pytest.raises(ValueError, match="method must be"):
        correlation(df, method="cosine")
    with pytest.raises(ValueError, match="stat must be"):
        trend(df, "y", stat="mode")


def test_a_table_without_years_is_one_cross_section(field):
    df = named(field).drop(columns="year")
    assert correlation(df).year is None and extremes(df, "y").n_units == 64
    assert len(distribution(df, "y").df) == 1 and scatter(df, "x1", "y").n == 64
    assert len(distribution(df, "y", kind="box").fig.data) == 1
    with pytest.raises(ValueError, match="no year column"):
        extremes(df, "y", year=2020)
    with pytest.raises(ValueError, match="ridgeline"):
        distribution(df, "y", kind="ridgeline")


def test_readings_describe_associations_only(field, growth_panel):
    df, panel = named(field), named(growth_panel)
    results = [correlation(df), extremes(df, "y"), distribution(df, "y"), distribution(panel, "gdppc", kind="box"),
               scatter(df, "x1", "y"), scatter(df, "x1", "y", fit="lowess"), trend(panel, "gdppc"),
               trend(toy(), "pace", by="region")]
    for res in results:
        text = res.interpret()
        assert text.endswith(_ASSOC_NOTE) and "causes" not in text and "effect of" not in text.replace(_ASSOC_NOTE, "")
        assert res.fig.data and isinstance(res.notes, tuple) and type(res).__name__ in repr(res)


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_runs_on_the_project_data_with_its_labels_and_scales():
    dataset = DATASETS[0]
    variables = metadata.variables(dataset)
    variable, label = variables[0], geo.labels(dataset)[variables[0]]
    ends = extremes(dataset, variable)
    assert ends.df["geo_id"].str.startswith(geo.project.country_code()).all() and ends.df["name"].notna().all()
    assert label in ends.fig.layout.title.text and ends.fig.layout.xaxis.title.text == label
    shape = distribution(dataset, variable, kind="box")
    assert shape.fig.layout.yaxis.title.text == label and shape.df["n"].max() == ends.n_units
    coarser = geo.ancestors(metadata.resource(dataset)["geo:scale"])
    if coarser:                                                       # a coarser scale is added by its id
        groups = distribution(dataset, variable, by=coarser[0], kind="box")
        assert groups.df.columns[0] == coarser[0] and groups.df["n"].sum() == ends.n_units
        assert groups.year == ends.year
    if len(variables) > 1:
        assert correlation(dataset).df.shape[0] >= 2
        pair = scatter(dataset, variables[0], variables[1])
        assert pair.n > 3 and -1 <= pair.corr <= 1 and pair.fig.layout.yaxis.title.text == geo.labels(dataset)[variables[1]]
    if len(metadata.resource_years(metadata.resource(dataset))) > 1:
        path = trend(dataset, variable, by=coarser[0] if coarser else None)
        assert path.first < path.last and label in path.fig.layout.title.text
