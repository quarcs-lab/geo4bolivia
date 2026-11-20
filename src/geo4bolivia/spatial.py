"""Spatial dependence: weights, the neighbour graph, global Moran's I and LISA clusters."""

from __future__ import annotations

import geopandas as gpd

from . import _inputs


def _units(data, gdf, ref):
    """Boundaries for a scale id, a dataset id, a panel or a GeoDataFrame."""
    if isinstance(data, gpd.GeoDataFrame) and gdf is None:
        return _inputs.shapes(None, data)
    if isinstance(data, str):
        from .scales import scales as registry
        if data in registry(ref):
            return _inputs.shapes(None, gdf, scale=data, ref=ref)
    return _inputs.shapes(_inputs.panel(data, gdf=gdf, ref=ref), gdf, ref=ref)


def weights(data, method: str = "queen", *, k: int = 6, threshold: float | None = None, power: float = 1.0,
            row_standardize: bool = True, attach_islands: bool = True, gdf=None, ref: str | None = None):
    """Spatial weights for the units of a scale, a dataset or a panel.

    Parameters
    ----------
    data
        A scale id (every unit of that scale), a dataset id or a panel (the units
        with data), or a GeoDataFrame with ``geo_id``
    method
        ``"queen"`` (units sharing a border or a corner), ``"rook"`` (a border),
        ``"knn"`` (the ``k`` nearest), ``"distance_band"`` (within ``threshold``
        metres) or ``"inverse_distance"`` (within the same band, weighted by distance ** -``power``)
    k
        Neighbours for ``"knn"``
    threshold
        Distance in metres for ``"distance_band"`` (default: the smallest
        distance at which every unit has a neighbour)
    power
        Distance decay for ``"inverse_distance"``
    row_standardize
        Make each unit's weights sum to one
    attach_islands
        Link a unit without contiguous neighbours to its nearest unit
    gdf
        Boundaries to use instead of the project's

    Returns
    -------
    libpysal.weights.W
        A ``libpysal.weights.W`` keyed by ``geo_id``, to pass as ``w=`` to the spatial
        functions. They build queen weights themselves when ``w`` is not given.
    """
    from ._engine.weights import make_weights
    return make_weights(_units(data, gdf, ref), method=method, k=k, threshold=threshold, power=power,
                        row_standardize=row_standardize, attach_islands=attach_islands, entity=_inputs.ENTITY)


def connectivity(data, w=None, *, method: str = "queen", tiles: str | None = "carto-positron",
                 title: str | None = None, gdf=None, ref: str | None = None):
    """A map of the neighbour links of a set of weights, with the distribution of neighbours per unit.

    Parameters
    ----------
    data
        A scale id, a dataset id or a panel, or a GeoDataFrame with ``geo_id``
    w
        The weights to draw (default: ``method`` weights built from the boundaries)
    method
        The weights to build when ``w`` is not given (see ``weights``)
    tiles
        The basemap style (``None``: no basemap)
    title
        The figure title
    gdf
        Boundaries to use instead of the project's

    Returns
    -------
    result object
        A result with ``.fig`` (the links over the map), ``.fig_hist`` (neighbours per
        unit), ``.df`` (one row per unit with its number of neighbours), the weights
        ``.w`` and ``.interpret()``.
    """
    from ._engine._mapping import _wgs84_simplified
    from ._engine.weights import explore_connectivity_map
    geo = _units(data, gdf, ref)
    w = _inputs.spatial_weights(geo, w, method=method)       # built on the boundaries in full detail
    drawn = _wgs84_simplified(geo, _inputs.ENTITY, "auto")   # drawn lighter: the figure stays small
    if _inputs.NAME in geo.columns:
        drawn[_inputs.NAME] = geo[_inputs.NAME].to_numpy()
    return _inputs.finish(explore_connectivity_map(drawn, w=w, entity=_inputs.ENTITY, tiles=tiles, title=title), geo)


def moran(data, variable: str, year=None, *, w=None, permutations: int = 999, seed: int | None = 12345,
          title: str | None = None, gdf=None, ref: str | None = None):
    """Global Moran's I of a variable: is it clustered in space?

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    variable
        The numeric column to test
    year
        The year to test (default: the last with data), or ``"all"`` for Moran's I
        in every year, on the units that have data in all of them
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    permutations
        Random permutations behind the pseudo p-value
    seed
        Makes the permutations reproducible (``None``: leave the random state alone)
    title
        The figure title
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        For one year, a result with ``.moran_i``, ``.p_sim``, ``.z_sim``, ``.fig`` (the Moran
        scatterplot: each unit's standardized value against its neighbours' mean), ``.df``
        (one row per unit with its quadrant) and ``.interpret()``.

        For ``year="all"``, a result with ``.df`` (one row per year: ``moran_i``, ``p_sim``,
        ``z_sim``), ``.fig`` (Moran's I over time) and ``.interpret()``.
    """
    from ._engine import dependence
    everything = isinstance(year, str) and year.lower() == "all"
    if everything:
        df, geo, w = _inputs.spatial(data, variable, gdf=gdf, w=w, year="all", ref=ref)
        return _inputs.finish(dependence.explore_moran_over_time(df, variable, gdf=geo, w=w, permutations=permutations,
                                                                 seed=seed, title=title))
    df, geo, w = _inputs.spatial(data, variable, gdf=gdf, w=w, year=year, ref=ref)
    return _inputs.finish(dependence.explore_moran_plot(df, variable, gdf=geo, w=w, period=_inputs.one_year(df),
                                                        permutations=permutations, seed=seed, title=title), df)


_PANELS = ("both", "map", "scatter")


def lisa(data, variable: str, year=None, *, w=None, permutations: int = 999, seed: int | None = 12345,
         alpha: float = 0.05, panels: str = "both", tiles: str | None = "carto-positron", title: str | None = None,
         gdf=None, ref: str | None = None):
    """Local Moran (LISA) clusters of a variable: where are the hot spots, cold spots and outliers?

    The figure shows the Moran scatterplot (each unit's standardized value against its
    neighbours' mean, coloured by cluster, grey where not significant) next to the map of
    the clusters. Both are interactive, and a click on a cluster type in the legend shows
    or hides it in both.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    variable
        The numeric column to analyse
    year
        The year to analyse (default: the last with data)
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    permutations
        Random permutations behind each unit's pseudo p-value
    seed
        Makes the permutations reproducible
    alpha
        Significance level below which a unit is assigned to a cluster
    panels
        What ``.fig`` shows: ``"both"`` (the scatterplot and the map side by side),
        ``"map"`` (the cluster map) or ``"scatter"`` (the Moran scatterplot)
    tiles
        The basemap style (``None``: no basemap)
    title
        The figure title
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.fig`` (by default the Moran scatterplot and the cluster map side
        by side; see ``panels``), ``.fig_map`` (the cluster map alone), ``.fig_scatter``
        (the Moran scatterplot alone), ``.df`` (one row per unit: local statistic, p-value and
        ``cluster``: High-High, Low-Low, High-Low, Low-High or not significant), the number
        of units of each type (``.n_hh``, ``.n_ll``, ``.n_hl``, ``.n_lh``, ``.n_ns``), the
        global ``.moran_i`` and ``.interpret()``.
    """
    import dataclasses

    from ._engine import dependence
    from ._engine._labels import resolve_label
    if panels not in _PANELS:
        raise ValueError(f"lisa: panels must be one of {', '.join(map(repr, _PANELS))}, got {panels!r}")
    df, geo, w = _inputs.spatial(data, variable, gdf=gdf, w=w, year=year, ref=ref)
    res = dependence.explore_lisa_cluster_map(df, variable, gdf=geo, w=w, period=_inputs.one_year(df),
                                              permutations=permutations, seed=seed, alpha=alpha, tiles=tiles,
                                              title=title if panels == "map" else None)
    if panels == "scatter":
        res = dataclasses.replace(res, fig=res.fig_scatter)
    elif panels == "both":
        when = f" ({res.period})" if res.period is not None else ""
        both = dependence.lisa_panels(
            res.fig_scatter, res.fig_map,
            title=title or f"LISA: {resolve_label(df, variable)}{when}",
            subtitle=res.w_spec,
            legend_title=f"Cluster (p < {res.alpha:g})",
        )
        res = dataclasses.replace(res, fig=both)
    return _inputs.finish(res, df)


__all__ = ["connectivity", "lisa", "moran", "weights"]
