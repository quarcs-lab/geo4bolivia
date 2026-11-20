"""Basemap credits that stay off the map.

MapLibre, which draws Plotly's tiled maps, credits the tiles in a white box over the map's
corner that starts open, and Plotly has no setting to close or move it. MapLibre takes that
credit from the style's sources, so ``credit`` replaces a named style (CARTO's, Plotly's
aliases for them, OpenStreetMap's) with the same style whose sources carry no attribution,
and writes the credit the tiles' licences require as one small line below the map instead.

CARTO's styles are downloaded from CARTO once per session, as Plotly itself would do when the
figure is shown (their tile URLs change with CARTO's releases, so they are not copied into the
package). If the download fails, the named style is kept, with MapLibre's box. Other styles (a
style URL, ``white-bg``, a style of the user's own) are left as they are.

The styles built here carry ``name: "geo4bolivia:<style>"``, so a page that prefers MapLibre's
own credit (the documentation site) can recognise them and restore the named style.
"""

from __future__ import annotations

import copy
import functools
import json
import urllib.request
from collections.abc import Mapping
from typing import Any

from plotly.basedatatypes import BaseFigure

#: Name given to the credit annotation, so it is added once and can be found again.
CREDIT_NAME = "basemap-credit"
#: Prefix of the ``name`` of the styles built here.
STYLE_PREFIX = "geo4bolivia:"

_OSM = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
_CARTO_GL = "https://basemaps.cartocdn.com/gl/{}-gl-style/style.json"

#: CARTO's styles by Plotly's names: the style each one downloads.
CARTO = {
    "carto-positron": "positron",
    "carto-darkmatter": "dark-matter",
    "carto-voyager": "voyager",
    "carto-positron-nolabels": "positron-nolabels",
    "carto-darkmatter-nolabels": "dark-matter-nolabels",
    "carto-voyager-nolabels": "voyager-nolabels",
}
#: Plotly's other names for the same styles (``basic``, its default, is CARTO's Voyager).
ALIASES = {"basic": "carto-voyager", "streets": "carto-voyager", "outdoors": "carto-voyager",
           "light": "carto-positron", "dark": "carto-darkmatter"}
#: OpenStreetMap's own tiles, as Plotly draws ``open-street-map``.
OSM_STYLE = {
    "version": 8,
    "sources": {"osm": {"type": "raster", "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                        "tileSize": 256, "maxzoom": 19, "attribution": ""}},
    "layers": [{"id": "osm", "type": "raster", "source": "osm"}],
}
_TIMEOUT = 5.0
#: Bottom margin, in pixels, that holds the credit line below a map at the figure's foot.
_CREDIT_ROOM = 24


@functools.cache
def _download(url: str) -> str | None:
    """The text at ``url``, or ``None`` if it cannot be fetched (cached for the session)."""
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as response:
            return response.read().decode("utf-8")
    except (OSError, ValueError):
        return None


def _style(name: str) -> tuple[dict[str, Any], str] | None:
    """The named style without attribution, and the credit it requires; ``None`` if unavailable."""
    if name == "open-street-map":
        style, credit_text = copy.deepcopy(OSM_STYLE), _OSM
    else:
        text = _download(_CARTO_GL.format(CARTO[name]))
        try:
            style = json.loads(text) if text else None
        except ValueError:
            style = None
        if not isinstance(style, dict) or not isinstance(style.get("sources"), dict):
            return None
        credits = []
        for source in style["sources"].values():
            if isinstance(source, dict):
                if source.get("attribution"):
                    credits.append(str(source["attribution"]).replace("&copy;", "©"))
                source["attribution"] = ""
        credit_text = " ".join(dict.fromkeys(credits)) or _OSM
    style["name"] = f"{STYLE_PREFIX}{name}"
    return style, credit_text


def _named(style: Any) -> str | None:
    """The style a subplot's ``style`` names among those handled here (no style: ``basic``)."""
    if style is None:
        style = "basic"
    if not isinstance(style, str):
        return None
    style = ALIASES.get(style, style)
    return style if style in CARTO or style == "open-street-map" else None


def _map_subplots(fig: BaseFigure) -> list[str]:
    """The ``map`` subplots that draw tiled traces (``map``, ``map2``, ...)."""
    return list(dict.fromkeys(trace.subplot or "map" for trace in fig.data
                              if trace.type in ("choroplethmap", "scattermap", "densitymap")))


def credit(fig: Any) -> Any:
    """Move the basemap credit of a Plotly figure off its map; return the figure.

    Every ``map`` subplot drawn on a named CARTO or OpenStreetMap style gets that style without
    attribution, and the figure gets one small credit line below the bottom-right of those maps.
    A figure without such a map (vector maps, charts) is returned unchanged. Safe to call twice.
    """
    if not isinstance(fig, BaseFigure):
        return fig
    credits: dict[str, None] = {}
    corner: tuple[float, float] | None = None
    for name in _map_subplots(fig):
        sub = fig.layout[name]
        named = _named(sub.style)
        built = _style(named) if named is not None else None
        if built is None:
            continue
        sub.style, text = built
        credits[text] = None
        x = sub.domain.x[1] if sub.domain.x is not None else 1.0
        y = sub.domain.y[0] if sub.domain.y is not None else 0.0
        if corner is None or (y, -x) < (corner[1], -corner[0]):
            corner = (x, y)
    if corner is None or any(note.name == CREDIT_NAME for note in fig.layout.annotations or ()):
        return fig
    if corner[1] <= 0 and fig.layout.margin.b is not None and fig.layout.margin.b < _CREDIT_ROOM:
        fig.layout.margin.b = _CREDIT_ROOM            # room for the line below the map
    fig.add_annotation(
        name=CREDIT_NAME, text=" · ".join(credits), x=corner[0], y=corner[1], xref="paper", yref="paper",
        xanchor="right", yanchor="top", yshift=-2, showarrow=False, align="right",
        font={"size": 10, "color": "#888888"},
    )
    return fig


def credit_all(value: Any) -> None:
    """``credit`` every figure in ``value``: a figure, or a dict, list or tuple holding figures."""
    if isinstance(value, BaseFigure):
        credit(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            credit_all(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            credit_all(item)
