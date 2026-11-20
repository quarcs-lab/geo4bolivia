"""The basemap's credit moves off the map: a credit-free style and one line below the map."""

import plotly.graph_objects as go
import pytest

import geo4bolivia as geo
from geo4bolivia._engine import _basemap


def _tiled(style="carto-positron", panels=1):
    fig = go.Figure()
    for i in range(panels):
        name = "map" if i == 0 else f"map{i + 1}"
        fig.add_trace(go.Choroplethmap(subplot=name))
        fig.update_layout({name: {"style": style, "domain": {"x": [i / panels, (i + 1) / panels], "y": [0, 1]}}})
    return fig


def _credits(fig):
    return [note for note in fig.layout.annotations if note.name == _basemap.CREDIT_NAME]


@pytest.mark.parametrize("style", ["carto-positron", "carto-darkmatter", "basic", "light", "open-street-map"])
def test_named_styles_lose_their_box_and_get_one_credit_line(style):
    fig = _basemap.credit(_basemap.credit(_tiled(style, panels=2)))
    for name in ("map", "map2"):
        new = fig.layout[name].style
        assert new["name"].startswith(_basemap.STYLE_PREFIX)
        assert all(source.get("attribution") == "" for source in new["sources"].values())
    (note,) = _credits(fig)                                     # once, even after two calls
    assert "OpenStreetMap" in note.text and note.x == 1.0 and note.y == 0.0


def test_other_styles_and_charts_are_left_alone():
    custom = _basemap.credit(_tiled("white-bg"))
    assert custom.layout.map.style == "white-bg" and not _credits(custom)
    chart = _basemap.credit(go.Figure(go.Scatter(y=[1, 2])))
    assert not _credits(chart)


def test_a_failed_download_keeps_the_named_style(monkeypatch):
    monkeypatch.setattr(_basemap, "_download", lambda url: None)
    fig = _basemap.credit(_tiled())
    assert fig.layout.map.style == "carto-positron" and not _credits(fig)


def test_the_credit_line_gets_room_below_the_map():
    fig = _tiled()
    fig.update_layout(margin={"b": 10})
    assert _basemap.credit(fig).layout.margin.b == _basemap._CREDIT_ROOM


def test_public_maps_credit_their_basemap(field, units):
    figures = [geo.lisa(field, "y", gdf=units).fig, geo.lisa(field, "y", gdf=units, panels="map").fig,
               geo.connectivity(units).fig]
    for fig in figures:
        assert isinstance(fig.layout.map.style, dict) and len(_credits(fig)) == 1
    vector = geo.lisa(field, "y", gdf=units, panels="map", tiles=None).fig
    assert not _credits(vector)
