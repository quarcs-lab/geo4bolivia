"""A quick interactive map of any variable (needs plotly: the ``[plot]`` extra, preinstalled in Colab)."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from . import io, project
from .discover import labels as _labels
from .scales import scale_of


def _view(gdf: gpd.GeoDataFrame) -> tuple[dict, float]:
    """Centre and zoom from project.yaml ``map:``, else from the data's bounds."""
    spec = project.config().get("map") or {}
    if "center" in spec:
        return dict(spec["center"]), float(spec.get("zoom", 4))
    minx, miny, maxx, maxy = gdf.total_bounds
    return {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}, 4.0


def map(data, variable: str, year: int | None = None, scale: str | None = None, title: str | None = None,
        simplify: float | None = 0.005, ref: str | None = None, **kwargs):
    """An interactive choropleth map (Plotly) of one variable in one year.

    Parameters
    ----------
    data : a dataset id, or a panel with ``geo_id`` (with or without geometry), e.g.
        from ``geo.load``, ``geo.change`` or ``geo.aggregate``
    variable : the column to colour by
    year : the year to map (default: the last year with data); ignored for tables
        without a ``year`` column
    scale : the units' scale (default: inferred from ``geo_id``)
    title : the figure title (default: the variable's label and the year)
    simplify : tolerance in degrees for simplifying the drawn boundaries (about 500 m by
        default, invisible at the country's scale; it keeps the figure light). ``None``
        draws them in full detail
    **kwargs : passed to ``plotly.express.choropleth_map`` (e.g.
        ``color_continuous_scale="Viridis"``, ``range_color=(0, 100)``)

    Returns a ``plotly.graph_objects.Figure``; it displays in a notebook, and
    ``.show()`` displays it from a script or a cell that does more afterwards.
    """
    try:
        import plotly.express as px
    except ImportError as exc:  # pragma: no cover
        raise ImportError(f'map() needs plotly: !pip install -q "{project.PACKAGE}[plot]"') from exc
    if isinstance(data, str):
        df = io.load(data, variables=variable, ref=ref)
    else:
        df = data
    if variable not in df.columns:
        raise ValueError(f"No column {variable!r} to map")
    if "year" in df.columns:
        if year is None:
            year = int(df.loc[df[variable].notna(), "year"].max())
        df = df[df["year"] == year]
        if df.empty:
            raise ValueError(f"No rows for {year}")
    if not isinstance(df, gpd.GeoDataFrame) or "geometry" not in df.columns:
        scale = scale or scale_of(df["geo_id"].iloc[0], ref)
        shapes = io.boundaries(scale, ref=ref)[["geo_id", "name", "geometry"]]
        df = shapes.merge(pd.DataFrame(df).drop(columns=["name", "geometry"], errors="ignore"), on="geo_id")
    elif "name" not in df.columns:
        df = io.add_names(df, ref=ref)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=getattr(df, "crs", None) or "EPSG:4326").reset_index(drop=True)
    gdf = gdf.to_crs("EPSG:4326")
    if simplify:
        gdf["geometry"] = gdf.geometry.simplify(simplify, preserve_topology=True)
    names = _labels(gdf.drop(columns="geometry"), ref=ref)
    label = names.get(variable, variable)
    center, zoom = _view(gdf)
    options = {"center": center, "zoom": zoom, "hover_name": "name", "labels": {variable: label},
               "title": title or (f"{label}, {year}" if year is not None else label)}
    options.update(kwargs)
    return px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color=variable, **options)

