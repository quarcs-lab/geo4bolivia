"""Interactive maps (Plotly) of any variable: one year, several years side by side, or its change
between two years, on a continuous colour scale or in classes."""

from __future__ import annotations

import math
from itertools import pairwise

import geopandas as gpd
import numpy as np
import pandas as pd

from . import io, project
from .scales import scale_of

SCHEMES = {"fisherjenks": "fisher_jenks", "quantiles": "quantiles", "equalinterval": "equal_interval"}
# What **kwargs may hold when the figure is not drawn by plotly.express (classes, several years, change)
_OPTIONS = ("color_continuous_scale", "range_color", "map_style", "opacity", "center", "zoom", "height", "width")
_MAX_COLUMNS = 3            # maps per row, when several years are drawn side by side
_LIGHTEST = 0.25            # how far into a colour scale the lightest colour sits: visible on a light basemap


def _view(gdf: gpd.GeoDataFrame) -> tuple[dict, float]:
    """Centre and zoom from project.yaml ``map:``, else from the data's bounds."""
    spec = project.config().get("map") or {}
    if "center" in spec:
        return dict(spec["center"]), float(spec.get("zoom", 4))
    minx, miny, maxx, maxy = gdf.total_bounds
    return {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}, 4.0


def _label(df: pd.DataFrame, variable: str, ref: str | None) -> str:
    """The variable's metadata label (its name when the metadata do not know it or cannot be read)."""
    from .discover import labels
    try:
        return labels(df.drop(columns="geometry", errors="ignore"), ref=ref).get(variable, variable)
    except Exception:  # offline, or data that are not in the project
        return variable


_METRES_PER_DEGREE = 111_000.0


def _with_shapes(df: pd.DataFrame, scale: str | None, simplify: float | str | None,
                 ref: str | None) -> gpd.GeoDataFrame:
    """The rows of a table with their unit's name and boundary, in EPSG:4326 and simplified."""
    if not isinstance(df, gpd.GeoDataFrame) or "geometry" not in df.columns:
        scale = scale or scale_of(df["geo_id"].iloc[0], ref)
        shapes = io.boundaries(scale, ref=ref)[["geo_id", "name", "geometry"]]
        df = shapes.merge(pd.DataFrame(df).drop(columns=["name", "geometry"], errors="ignore"), on="geo_id")
    elif "name" not in df.columns:
        try:
            df = io.add_names(df, ref=ref)
        except Exception:  # units that are not in the project
            df = df.assign(name=df["geo_id"].astype(str))
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=getattr(df, "crs", None) or "EPSG:4326").reset_index(drop=True)
    gdf = gdf.to_crs("EPSG:4326")
    if simplify:
        from ._engine._mapping import _wgs84_simplified
        # one boundary per unit (a panel repeats them), simplified as a coverage so neighbours still fit
        tolerance = simplify if simplify == "auto" else float(simplify) * _METRES_PER_DEGREE
        light = _wgs84_simplified(gdf.drop_duplicates("geo_id")[["geo_id", "geometry"]], "geo_id", tolerance)
        gdf["geometry"] = gdf["geo_id"].map(light.set_index("geo_id")["geometry"])
        gdf = gdf.set_geometry("geometry", crs="EPSG:4326")
    return gdf


def _pick_years(df: pd.DataFrame, variable: str, year, change: bool = False) -> list[int]:
    """The years to map, checked against the years with data: those asked for, else the last one
    (for a change: two years, by default the first and the last)."""
    if "year" not in df.columns:
        raise ValueError("The table has no year column, so it cannot be mapped in several years or as a change")
    have = sorted(int(y) for y in df.loc[df[variable].notna(), "year"].dropna().unique())
    if len(have) < 1 + change:
        raise ValueError(f"A change needs two years with data for {variable!r}; the table has {have}" if change
                         else f"No rows with data for {variable!r}")
    if year is None:
        return [have[0], have[-1]] if change else [have[-1]]
    wanted = list(dict.fromkeys(int(y) for y in year)) if isinstance(year, list | tuple | np.ndarray) else [int(year)]
    missing = [y for y in wanted if y not in have]
    if missing:
        raise ValueError(f"No rows for {missing}; the years with data are {have}")
    if change and len(wanted) != 2:
        raise ValueError(f"change=True compares two years: give year=[first, last] or leave it out, not {year!r}")
    return sorted(wanted) if change else wanted


def _limits(values: np.ndarray, scheme: str | None, k: int, bins, zero: bool) -> list[float]:
    """The class limits of ``values``: the lowest value, the limits between classes, the highest value."""
    lo, hi = float(values.min()), float(values.max())
    if bins is not None:
        try:
            edges = [float(b) for b in bins]
        except (TypeError, ValueError):
            raise ValueError(f"bins must be a list of numbers (class limits), not {bins!r}") from None
        if not edges or not np.isfinite(edges).all() or any(b <= a for a, b in pairwise(edges)):
            raise ValueError(f"bins must be class limits in increasing order, not {bins!r}")
        edges = [lo] * (lo < edges[0]) + edges + [hi] * (hi > edges[-1])
        return edges if len(edges) > 1 else [lo, hi]
    name = SCHEMES.get(str(scheme).lower().replace("_", "").replace("-", "").replace(" ", ""))
    if name is None:
        raise ValueError(f"Unknown scheme {scheme!r}; use one of {sorted(SCHEMES.values())}, or bins=[...]")
    if isinstance(k, bool) or not isinstance(k, int | np.integer) or k < 2:
        raise ValueError(f"k must be a number of classes of at least 2, not {k!r}")
    if len(np.unique(values)) < k:
        raise ValueError(f"k={k} classes need at least {k} different values; the data have {len(np.unique(values))}")

    def upper(part: np.ndarray, classes: int) -> list[float]:
        """The upper limit of each class of ``part`` (fewer classes when it has few different values)."""
        import mapclassify
        classes = min(classes, len(np.unique(part)))
        if classes < 2:
            return [float(part.max())]
        found = sorted({float(b) for b in mapclassify.classify(part, name, k=classes).bins})
        return [*found[:-1], float(part.max())]

    if zero and lo < 0 < hi:                                # classes within the falls and within the rises
        falls, rises = values[values < 0], values[values >= 0]
        k_falls = min(max(round(k * len(falls) / len(values)), 1), k - 1)
        return [lo, *upper(falls, k_falls)[:-1], 0.0, *upper(rises, k - k_falls)]
    return [lo, *upper(values, k)]


def _classes(values: np.ndarray, edges: list[float], zero: bool) -> np.ndarray:
    """The class of each value. Class ``i`` runs from above ``edges[i]`` to ``edges[i + 1]``, and the
    first one includes its lower limit. On a map of change, no change (zero) belongs with the rises."""
    index = np.clip(np.searchsorted(np.asarray(edges[1:]), values, side="left"), 0, len(edges) - 2)
    if zero and 0.0 in edges[1:-1]:
        index[values == 0] = edges.index(0.0)
    return index


def _class_names(edges: list[float]) -> list[str]:
    """The legend text of each class, its range: ``10 – 20``, or ``-5 to 0`` when a limit is negative."""
    from ._engine._theme import compact_number
    between = " to " if min(edges) < 0 else " – "
    return [f"{compact_number(a)}{between}{compact_number(b)}" for a, b in pairwise(edges)]


def _colorscale(custom, diverging: bool) -> list:
    """The colour scale: the one given (in any form Plotly Express takes), else the package's diverging
    scale, or its sequential one without the near-white end that a light basemap would hide."""
    import plotly.colors as pc

    from ._engine._theme import active_diverging_scale, active_sequential_scale
    if custom is None and diverging:
        return active_diverging_scale()
    if custom is None:
        stops = [i / 8 for i in range(9)]
        colors = pc.sample_colorscale(active_sequential_scale(), [_LIGHTEST + (1 - _LIGHTEST) * at for at in stops])
        return [list(stop) for stop in zip(stops, colors, strict=True)]
    if isinstance(custom, str):
        return pc.get_colorscale(custom)
    return pc.make_colorscale(list(custom)) if isinstance(custom[0], str) else [list(stop) for stop in custom]


def _class_colors(edges: list[float], scale: list, diverging: bool) -> list[str]:
    """One colour per class. Sequential: light to dark. Diverging: the classes below zero take one side
    of the scale and those above zero the other, darker the further their rank from zero; a class
    that holds zero takes the neutral midpoint."""
    import plotly.colors as pc
    n = len(edges) - 1
    if not diverging:
        return pc.sample_colorscale(scale, [1.0] if n == 1 else [i / (n - 1) for i in range(n)])
    side = [1 if a >= 0 else -1 if b <= 0 else 0 for a, b in pairwise(edges)]
    below, above = side.count(-1), side.count(1)
    steps, seen, at = max(below, above), 0, []
    for s in side:
        seen += abs(s)                                      # classes met so far, not counting one that holds zero
        from_zero = below - seen + 1 if s < 0 else seen - below
        at.append(0.5 + s * 0.5 * (_LIGHTEST + (1 - _LIGHTEST) * from_zero / steps) if s else 0.5)
    return pc.sample_colorscale(scale, at)


def _draw(panels: list[tuple[str | None, gpd.GeoDataFrame]], column: str, *, legend: str, title: str,
          edges: list[float] | None, diverging: bool, hover: list[tuple[str, str]], options: dict):
    """One map per panel in a single figure, in common classes (``edges``) or on a common colour axis."""
    import plotly.graph_objects as go

    from ._engine._mapping import _POLYGON_EDGE, _subset_fc
    from ._engine._theme import apply_default_layout

    unknown = sorted(set(options) - set(_OPTIONS))
    if unknown:
        raise TypeError(f"map() does not take {unknown} with classes, several years or change=True; "
                        f"there it takes {list(_OPTIONS)}")
    scale = _colorscale(options.get("color_continuous_scale"), diverging)
    center, zoom = _view(panels[0][1])
    columns = min(len(panels), _MAX_COLUMNS)
    rows = math.ceil(len(panels) / columns)
    zoom = options.get("zoom", zoom - math.log2(max(columns, 2) / 2))    # three narrow maps: a wider view
    view = {"style": options.get("map_style", "carto-positron"), "center": options.get("center", center), "zoom": zoom}
    gap_x, gap_y = 0.02, 0.1 if rows > 1 else 0.0
    width, height = (1 - gap_x * (columns - 1)) / columns, (1 - gap_y * (rows - 1)) / rows
    names = _class_names(edges) if edges else []
    colors = _class_colors(edges, scale, diverging) if edges else []
    lines = "".join(f"<br>{text}: %{{customdata[{i + 1}]:,.6~r}}" for i, (_, text) in enumerate(hover))
    shared = {"marker": {"line": dict(_POLYGON_EDGE), "opacity": options.get("opacity", 1.0)},
              "hovertemplate": f"<b>%{{customdata[0]}}</b>{lines}<extra></extra>"}

    fig, in_legend = go.Figure(), set()
    for i, (head, part) in enumerate(panels):
        row, col = divmod(i, columns)
        subplot = "map" if i == 0 else f"map{i + 1}"
        left, top = col * (width + gap_x), 1 - row * (height + gap_y)
        domain = {"x": [left, min(left + width, 1.0)], "y": [max(top - height, 0.0), top]}
        fig.update_layout({subplot: {**view, "domain": domain}})
        if head is not None:
            fig.add_annotation(text=f"<b>{head}</b>", x=left + width / 2, y=top, xref="paper", yref="paper",
                               xanchor="center", yanchor="bottom", showarrow=False)
        shapes = dict(part[["geo_id", "geometry"]].set_index("geo_id").__geo_interface__)
        ids = part["geo_id"].astype(str).to_numpy()
        values = part[column].to_numpy(dtype=float)
        custom = np.column_stack([part["name"].astype(str).to_numpy(dtype=object),
                                  *(part[c].to_numpy(dtype=object) for c, _ in hover)])
        if not edges:
            fig.add_trace(go.Choroplethmap(geojson=shapes, locations=ids, z=values, customdata=custom, subplot=subplot,
                                           coloraxis="coloraxis", name=head or legend, showlegend=False, **shared))
            continue
        index = _classes(values, edges, diverging)
        for j, name in enumerate(names):
            members = index == j
            if not members.any():
                continue
            fig.add_trace(go.Choroplethmap(
                geojson=_subset_fc(shapes, ids[members]), locations=ids[members], z=np.full(int(members.sum()), j),
                customdata=custom[members], subplot=subplot, colorscale=[[0.0, colors[j]], [1.0, colors[j]]],
                showscale=False, name=name, legendgroup=f"class {j + 1}", legendrank=j + 1,
                showlegend=j not in in_legend, **shared))
            in_legend.add(j)                                # one legend entry per class, whatever the map

    apply_default_layout(fig, title=title, margin={"l": 10, "r": 10, "t": 60 if len(panels) == 1 else 84, "b": 10},
                         legend={"title": {"text": legend}})
    if edges:
        fig.update_layout(meta={"bins": [float(e) for e in edges]})
    else:
        every = np.concatenate([part[column].to_numpy(dtype=float) for _, part in panels])
        low, high = float(every.min()), float(every.max())
        if diverging:                                       # the same distance on both sides of zero
            low, high = -max(abs(low), abs(high)), max(abs(low), abs(high))
        low, high = options.get("range_color", (low, high))
        fig.update_layout(coloraxis={"colorscale": scale, "cmin": low, "cmax": high, **({"cmid": 0} if diverging else {}),
                                     "colorbar": {"title": {"text": legend, "side": "right"}, "thickness": 14,
                                                  "len": 0.85, "outlinewidth": 0}})
    size = {key: options[key] for key in ("height", "width") if key in options}
    if rows > 1:
        size.setdefault("height", 110 + 380 * rows)
    return fig.update_layout(**size)


def map(data, variable: str, year=None, scale: str | None = None, title: str | None = None,
        simplify: float | str | None = "auto", ref: str | None = None, *, scheme: str | None = None, k: int = 5,
        bins=None, change: bool = False, **kwargs):
    """An interactive choropleth map (Plotly) of one variable: in one year, in several years side by
    side, or its change between two years; on a continuous colour scale or in classes.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (with or without geometry), e.g.
        from ``geo.load``, ``geo.change`` or ``geo.aggregate``
    variable
        The column to colour by
    year
        The year to map (default: the last year with data), or a list of years
        (``[2012, 2024]``): one map per year, side by side, in the same classes or on the
        same colour range, computed over all the years shown, so the maps can be
        compared. Ignored for tables without a ``year`` column
    scale
        The units' scale (default: inferred from ``geo_id``)
    title
        The figure title (default: the variable's label and the year)
    simplify
        How much to simplify the drawn boundaries, which keeps the figure light.
        ``"auto"`` (the default) removes detail smaller than about 1/600 of the map's
        extent, invisible at the scale of the whole map; a number is a tolerance in
        degrees (0.005 is about 500 m), for maps you will zoom into; ``None`` draws
        the boundaries in full detail. Neighbouring units keep fitting each other
    scheme
        Draw classes instead of a continuous scale, one colour per class with its
        range in the legend: ``"fisher_jenks"`` (natural breaks: similar values together),
        ``"quantiles"`` (the same number of units in each class) or ``"equal_interval"``
        (classes of the same width)
    k
        The number of classes of a ``scheme``
    bins
        Explicit class limits in increasing order (``[20, 40, 60]``), instead of a
        ``scheme``; values below the first or above the last limit get a class of their own
    change
        Map the change of the variable (last minus first year, as ``geo.change``
        computes it) between the first and last year with data, or between the two years
        given in ``year``, on a diverging scale centred at zero. With a ``scheme``, the
        classes split at zero: they are computed within the falls and within the rises
    **kwargs
        For the continuous map of one year, passed to
        ``plotly.express.choropleth_map`` (e.g. ``color_continuous_scale="Viridis"``,
        ``range_color=(0, 100)``). With classes, several years or ``change``, the options
        are ``color_continuous_scale``, ``range_color``, ``map_style``, ``opacity``,
        ``center``, ``zoom``, ``height`` and ``width``

    Returns
    -------
    plotly.graph_objects.Figure
        A ``plotly.graph_objects.Figure``; it displays in a notebook, and ``.show()``
        displays it from a script or a cell that does more afterwards. A map in classes
        keeps their limits in ``fig.layout.meta["bins"]``.
    """
    try:
        import plotly.express as px
    except ImportError as exc:  # pragma: no cover
        raise ImportError("map() needs plotly: pip install plotly") from exc
    if isinstance(data, str):
        df = io.load(data, variables=variable, ref=ref)
    else:
        df = data
    if variable not in df.columns:
        raise ValueError(f"No column {variable!r} to map")
    classed = scheme is not None or bins is not None
    if isinstance(year, list | tuple | np.ndarray) and len(year) == 1 and not change:
        year = year[0]
    several = isinstance(year, list | tuple | np.ndarray)

    if not (classed or several or change):                  # one year on a continuous scale: Plotly Express
        if "year" in df.columns:
            if year is None:
                year = int(df.loc[df[variable].notna(), "year"].max())
            df = df[df["year"] == year]
            if df.empty:
                raise ValueError(f"No rows for {year}")
        gdf = _with_shapes(df, scale, simplify, ref)
        label = _label(gdf, variable, ref)
        center, zoom = _view(gdf)
        options = {"center": center, "zoom": zoom, "hover_name": "name", "labels": {variable: label},
                   "title": title or (f"{label}, {year}" if year is not None else label)}
        options.update(kwargs)
        return px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color=variable, **options)

    if not pd.api.types.is_numeric_dtype(df[variable]):
        raise TypeError(f"Column {variable!r} must be numeric to map it in classes, in several years or as a change")
    label = _label(df, variable, ref)
    column, legend, hover = variable, label, [(variable, label)]
    if change:
        from .panel import change as _change
        first, last = _pick_years(df, variable, year, change=True)
        table = _change(df, variable, first=first, last=last)
        if isinstance(df, gpd.GeoDataFrame) and "geometry" in df.columns:
            table = df[["geo_id", "geometry"]].drop_duplicates("geo_id").merge(table, on="geo_id")
        column, legend = f"{variable}_change", "Change"
        hover = [(f"{variable}_{first}", str(first)), (f"{variable}_{last}", str(last)), (column, legend)]
        panels = [(None, _with_shapes(table[table[column].notna()], scale, simplify, ref))]
        title = title or f"{label}: change from {first} to {last}"
    elif several:
        years = _pick_years(df, variable, year)
        gdf = _with_shapes(df[df["year"].isin(years) & df[variable].notna()], scale, simplify, ref)
        panels = [(str(y), gdf[gdf["year"] == y]) for y in years]
        title = title or label
    else:
        year = _pick_years(df, variable, year)[0] if "year" in df.columns else None
        if year is not None:
            df = df[df["year"] == year]
        panels = [(None, _with_shapes(df[df[variable].notna()], scale, simplify, ref))]
        title = title or (f"{label}, {year}" if year is not None else label)
    if any(part.empty for _, part in panels):
        raise ValueError(f"No units with data for {variable!r} to map")
    edges = None
    if classed:
        edges = _limits(np.concatenate([part[column].to_numpy(dtype=float) for _, part in panels]), scheme, k, bins,
                        zero=change)
    return _draw(panels, column, legend=legend, title=title, edges=edges, diverging=change, hover=hover, options=kwargs)
