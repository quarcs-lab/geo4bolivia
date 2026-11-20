"""Maps: the plain map as released, classes, several years side by side and change, on a lattice."""

from itertools import pairwise

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from geo4bolivia import io, metadata, project
from geo4bolivia.discover import labels
from geo4bolivia.plot import map as draw_map

DATASETS = list(metadata.dataset_ids()) if project.local_root() is not None else []
SCHEMES = ["fisher_jenks", "quantiles", "equal_interval"]


@pytest.fixture(scope="module")
def cells(field, units):
    """The cross-section with its boundaries: one row per unit, one year."""
    return units.merge(field, on="geo_id")


@pytest.fixture(scope="module")
def two_years(field, units):
    """Two years with boundaries: between them ``y`` changes by ``x1`` in each unit, and not at all in one."""
    step = field["x1"].where(field["geo_id"] != units["geo_id"].iloc[0], 0.0)
    later = field.assign(year=2021, y=field["y"] + step)
    return units.merge(pd.concat([field, later], ignore_index=True).assign(step=pd.concat([step, step]).to_numpy()),
                       on="geo_id")


def members(fig, subplot=None) -> list[str]:
    """The units drawn (in one of the figure's maps), over all its traces."""
    return [unit for trace in fig.data if subplot in (None, trace.subplot) for unit in trace.locations]


def drawn(fig) -> pd.Series:
    """The value of each unit as the hover shows it (the last number), indexed by unit."""
    return pd.Series({unit: float(row[-1]) for trace in fig.data
                      for unit, row in zip(trace.locations, trace.customdata, strict=True)})


def rgb(trace) -> tuple[int, ...]:
    """The colour of a class, as red, green and blue."""
    return tuple(int(part) for part in trace.colorscale[0][1].removeprefix("rgb(").removesuffix(")").split(","))


def test_the_plain_map_is_still_a_plotly_express_figure(cells):
    fig = draw_map(cells, "y")
    assert isinstance(fig, go.Figure) and len(fig.data) == 1 and fig.data[0].type == "choroplethmap"
    assert fig.layout.title.text == "y, 2020" and fig.layout.coloraxis.colorbar.title.text == "y"
    assert np.allclose(fig.data[0].z, cells["y"]) and list(fig.data[0].hovertext) == list(cells["name"])
    assert fig.layout.meta is None
    styled = draw_map(cells, "y", 2020, None, "Mine", None, range_color=(0, 1), color_continuous_scale="Viridis")
    assert styled.layout.title.text == "Mine" and (styled.layout.coloraxis.cmin, styled.layout.coloraxis.cmax) == (0, 1)
    assert draw_map(cells, "y", year=[2020]).to_json() == fig.to_json()      # a list of one year is that year


@pytest.mark.parametrize("scheme", SCHEMES)
def test_a_scheme_puts_every_unit_in_one_of_k_classes(cells, scheme):
    fig = draw_map(cells, "y", scheme=scheme, k=4)
    assert isinstance(fig, go.Figure) and len(fig.data) == 4 and {t.type for t in fig.data} == {"choroplethmap"}
    assert sorted(members(fig)) == sorted(cells["geo_id"])
    limits = fig.layout.meta["bins"]
    assert len(limits) == 5 and limits == sorted(limits)
    assert limits[0] == cells["y"].min() and limits[-1] == pytest.approx(cells["y"].max())
    values = cells.set_index("geo_id")["y"]
    for trace, (low, high) in zip(fig.data, pairwise(limits), strict=True):
        assert values[list(trace.locations)].between(low - 1e-9, high + 1e-9).all()
        assert trace.showlegend and (" – " in trace.name or " to " in trace.name)
    assert len({rgb(trace) for trace in fig.data}) == 4                      # one colour per class
    assert fig.layout.title.text == "y, 2020" and fig.layout.legend.title.text == "y"
    if scheme == "quantiles":
        assert [len(t.locations) for t in fig.data] == [16] * 4
    if scheme == "equal_interval":
        assert np.allclose(np.diff(limits), (limits[-1] - limits[0]) / 4)


def test_scheme_names_are_forgiving_and_k_defaults_to_five(cells):
    assert len(draw_map(cells, "y", scheme="Fisher-Jenks").data) == 5
    assert draw_map(cells, "y", scheme="equalinterval").layout.meta == draw_map(cells, "y", scheme="equal_interval").layout.meta


def test_explicit_bins_are_the_class_limits(cells):
    y = cells["y"]
    fig = draw_map(cells, "y", bins=[-1, 0, 1])
    assert fig.layout.meta["bins"] == [y.min(), -1, 0, 1, y.max()]           # the data reach beyond the limits
    counts = [(y <= -1).sum(), ((y > -1) & (y <= 0)).sum(), ((y > 0) & (y <= 1)).sum(), (y > 1).sum()]
    assert [len(t.locations) for t in fig.data] == counts and sorted(members(fig)) == sorted(cells["geo_id"])
    wide = draw_map(cells, "y", bins=[-100, 0, 100], scheme="quantiles")     # bins win over a scheme
    assert wide.layout.meta["bins"] == [-100, 0, 100] and len(wide.data) == 2
    assert [t.name for t in wide.data] == ["-100 to 0", "0 to 100"]


def test_several_years_share_one_colour_range(two_years):
    fig = draw_map(two_years, "y", year=[2020, 2021])
    assert len(fig.data) == 2 and [t.subplot for t in fig.data] == ["map", "map2"]
    assert [a.text for a in fig.layout.annotations] == ["<b>2020</b>", "<b>2021</b>"]
    assert {t.coloraxis for t in fig.data} == {"coloraxis"}
    assert fig.layout.coloraxis.cmin == two_years["y"].min() and fig.layout.coloraxis.cmax == two_years["y"].max()
    assert fig.layout.map.domain.x[1] <= fig.layout.map2.domain.x[0]          # side by side
    assert fig.layout.map.center == fig.layout.map2.center and fig.layout.map.zoom == fig.layout.map2.zoom
    for subplot, year in (("map", 2020), ("map2", 2021)):
        assert sorted(members(fig, subplot)) == sorted(two_years["geo_id"].unique())
        part = two_years[two_years["year"] == year].set_index("geo_id")["y"]
        trace = fig.data[0 if year == 2020 else 1]
        assert np.allclose(trace.z, part[list(trace.locations)])
    assert fig.layout.title.text == "y"


def test_several_years_share_one_set_of_classes(two_years):
    fig = draw_map(two_years, "y", year=[2020, 2021], scheme="quantiles", k=4)
    limits = fig.layout.meta["bins"]
    assert limits[0] == two_years["y"].min() and limits[-1] == pytest.approx(two_years["y"].max())
    assert sum(len(t.locations) for t in fig.data) == len(two_years)
    for subplot in ("map", "map2"):
        assert sorted(members(fig, subplot)) == sorted(two_years["geo_id"].unique())
    names = list(dict.fromkeys(t.name for t in sorted(fig.data, key=lambda t: t.legendrank)))
    assert len(names) == 4 and sum(bool(t.showlegend) for t in fig.data) == 4      # one legend entry per class
    assert len({t.legendgroup for t in fig.data}) == 4 == len({(t.legendgroup, t.name) for t in fig.data})
    pooled = {name: sum(len(t.locations) for t in fig.data if t.name == name) for name in names}
    assert list(pooled.values()) == [len(two_years) // 4] * 4                       # quantiles of both years together
    colours = {t.name: rgb(t) for t in fig.data}
    assert all(rgb(t) == colours[t.name] for t in fig.data) and len(set(colours.values())) == 4


def test_more_than_three_years_wrap_into_rows(two_years):
    decades = pd.concat([two_years.assign(year=two_years["year"] + 10 * i) for i in range(3)])
    fig = draw_map(decades, "y", year=[2020, 2021, 2030, 2031, 2040], bins=[0])
    assert {t.subplot for t in fig.data} == {"map", "map2", "map3", "map4", "map5"}
    assert [a.text for a in fig.layout.annotations] == [f"<b>{y}</b>" for y in (2020, 2021, 2030, 2031, 2040)]
    assert fig.layout.map4.domain.y[1] < fig.layout.map.domain.y[0] and fig.layout.height > 450        # a second row
    assert fig.layout.map3.zoom < draw_map(two_years, "y", year=[2020, 2021]).layout.map.zoom          # narrower maps


def test_change_is_last_minus_first_and_centred_at_zero(two_years):
    fig = draw_map(two_years, "y", change=True)
    step = two_years.drop_duplicates("geo_id").set_index("geo_id")["step"]
    assert len(fig.data) == 1 and np.allclose(fig.data[0].z, step[list(fig.data[0].locations)])
    axis = fig.layout.coloraxis
    assert axis.cmid == 0 and axis.cmin == -axis.cmax and axis.cmax == pytest.approx(step.abs().max())
    assert fig.layout.title.text == "y: change from 2020 to 2021"
    assert "2020" in fig.data[0].hovertemplate and "2021" in fig.data[0].hovertemplate
    assert draw_map(two_years, "y", year=[2021, 2020], change=True).to_json() == fig.to_json()


def test_classes_of_a_change_split_at_zero(two_years):
    fig = draw_map(two_years, "y", change=True, scheme="fisher_jenks", k=4)
    limits = fig.layout.meta["bins"]
    assert 0.0 in limits[1:-1] and len(limits) == 5
    step = two_years.drop_duplicates("geo_id").set_index("geo_id")["step"]
    assert np.allclose(drawn(fig)[step.index], step)
    assert len(fig.data) == 4
    for trace, (low, high) in zip(fig.data, pairwise(limits), strict=True):
        assert (step[list(trace.locations)] < 0).all() if high <= 0 else (step[list(trace.locations)] >= 0).all()
        red, _, blue = rgb(trace)
        assert (red > blue) == (high <= 0)                                   # falls and rises take opposite hues
        assert low >= 0 or high <= 0                                         # no class holds both
    unchanged = next(t for t in fig.data if step.index[step == 0][0] in t.locations)
    assert unchanged.name.startswith("0 to ")                                # no change is drawn with the rises


def test_bad_arguments_are_refused(cells, two_years):
    for bad, message in (({"scheme": "pretty"}, "Unknown scheme 'pretty'; use one of"),
                         ({"scheme": "quantiles", "k": 1}, "k must be"), ({"scheme": "quantiles", "k": 2.5}, "k must be"),
                         ({"scheme": "quantiles", "k": 100}, "100 different values; the data have 64"),
                         ({"bins": [2, 1]}, "increasing order"), ({"bins": []}, "increasing order"),
                         ({"bins": ["low", "high"]}, "list of numbers")):
        with pytest.raises(ValueError, match=message):
            draw_map(cells, "y", **bad)
    with pytest.raises(ValueError, match="No column"):
        draw_map(cells, "nothing", scheme="quantiles")
    with pytest.raises(ValueError, match=r"No rows for \[1999\]; the years with data are \[2020, 2021\]"):
        draw_map(two_years, "y", year=[2020, 1999])
    with pytest.raises(ValueError, match="two years"):
        draw_map(cells, "y", change=True)                                    # a single year of data
    with pytest.raises(ValueError, match="two years"):
        draw_map(two_years, "y", year=2021, change=True)
    with pytest.raises(ValueError, match="no year column"):
        draw_map(cells.drop(columns="year"), "y", year=[2020, 2021])
    with pytest.raises(TypeError, match="numeric"):
        draw_map(cells.assign(y=cells["y"].astype(str)), "y", scheme="quantiles")
    with pytest.raises(TypeError, match="hover_data"):
        draw_map(cells, "y", scheme="quantiles", hover_data=["x1"])


def test_options_of_the_drawn_maps(cells):
    fig = draw_map(cells, "y", scheme="quantiles", k=3, color_continuous_scale="Viridis", map_style="open-street-map",
                   zoom=7, center={"lat": 20.4, "lon": 78.4}, opacity=0.5, height=300, title="Mine")
    assert fig.layout.map.style == "open-street-map" and fig.layout.map.zoom == 7 and fig.layout.map.center.lat == 20.4
    assert fig.layout.height == 300 and fig.layout.title.text == "Mine" and fig.data[0].marker.opacity == 0.5
    assert fig.data[0].colorscale[0][1] != draw_map(cells, "y", scheme="quantiles", k=3).data[0].colorscale[0][1]
    no_years = draw_map(cells.drop(columns="year"), "y", scheme="quantiles")
    assert no_years.layout.title.text == "y" and len(no_years.data) == 5


@pytest.mark.data
@pytest.mark.skipif(not DATASETS, reason="needs a checkout of the data repository with datasets")
def test_maps_the_project_data_in_classes_and_over_time():
    dataset = DATASETS[0]
    variable = metadata.variables(dataset)[0]
    df = io.load(dataset, variables=variable).dropna(subset=[variable])
    years = sorted(int(y) for y in df["year"].unique())
    fig = draw_map(dataset, variable, scheme="quantiles")
    assert 2 <= len(fig.data) <= 5 and len(fig.layout.meta["bins"]) == len(fig.data) + 1
    assert sorted(members(fig)) == sorted(df.loc[df["year"] == years[-1], "geo_id"])
    assert fig.layout.title.text == f"{labels(dataset)[variable]}, {years[-1]}"
    assert fig.layout.map.center.lat == project.config()["map"]["center"]["lat"]
    if len(years) > 1:
        both = draw_map(df, variable, year=[years[0], years[-1]], scheme="fisher_jenks")
        assert {t.subplot for t in both.data} == {"map", "map2"}
        assert both.layout.meta["bins"][0] == df.loc[df["year"].isin([years[0], years[-1]]), variable].min()
        change = draw_map(df, variable, change=True)
        assert change.layout.coloraxis.cmid == 0 and f"{years[0]} to {years[-1]}" in change.layout.title.text
