"""Spatial heterogeneity: multiscale geographically weighted regression (MGWR), with the mgwr library."""

from __future__ import annotations

from . import _inputs, project


def _prepare(function: str, data, y: str, x, year, gdf, ref):
    """The panel and boundaries of a local regression (after checking that mgwr is installed)."""
    try:
        import mgwr  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(f'{function}() needs mgwr: pip install "{project.PACKAGE}[mgwr]"') from exc
    x = _inputs.as_list(x)
    if not x:
        raise ValueError("x needs at least one column")
    if y in x:
        raise ValueError(f"y ({y!r}) cannot also be in x")
    if len(set(x)) != len(x):
        raise ValueError(f"x repeats a column: {x}")
    df, geo, _ = _inputs.spatial(data, [y, *x], year=year, gdf=gdf, weights=False, ref=ref)
    return df, geo, x


def mgwr(data, y: str, x, year=None, *, kernel: str = "bisquare", criterion: str = "AICc", max_iter: int = 200,
         tiles: str | None = "carto-positron", title: str | None = None, gdf=None, ref: str | None = None):
    """Multiscale geographically weighted regression: where, and at which scale, does ``x`` relate to ``y``?

    A regression of ``y`` on ``x`` is fitted at every unit, weighting the other units by
    the distance between centroids, so each coefficient becomes a surface that can be
    mapped. MGWR finds one bandwidth per term: a bandwidth close to the number of units
    means an association that is about the same everywhere (a global process), a small
    one an association that changes from place to place (a local process). It follows
    the workflow of the mgwr library (Oshan et al. 2019): the variables are
    z-standardized, so the coefficients are in standard deviations and comparable;
    the bandwidths are the numbers of nearest units, found by back-fitting; and each
    term's local t-tests are corrected for multiple testing at the 5% level.

    It is slow: the search fits the model again and again, which takes about half a
    minute with several hundred units and one or two variables, and longer with more
    of either.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load`` or ``combine``
    y
        The numeric column to explain
    x
        The explanatory column, or a list of them
    year
        The year to analyse (default: the last with data for ``y`` and ``x``)
    kernel
        How weights fall with distance: ``"bisquare"``, ``"gaussian"`` or ``"exponential"``
    criterion
        What the bandwidth search minimises: ``"AICc"``, ``"AIC"``, ``"BIC"`` or ``"CV"``
    max_iter
        The most rounds of the bandwidth search (fewer is faster and rougher)
    tiles
        The basemap style (``None``: no basemap)
    title
        The title of the residual map; each coefficient map adds its variable
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.bw`` (the bandwidth of each term, in nearest units) and
        ``.bw_interval`` (its 95% interval); ``.df`` (one row per unit: ``<column>_coef``,
        ``_se``, ``_t`` and ``_significant`` for the intercept ``const`` and each column of
        ``x``, the ``residual`` and ``local_cn``, the local condition number, which signals
        local collinearity above about 30); ``.figs`` (a map of the local coefficients per
        term, by column name, with the units that are not significant in grey); ``.fig``
        (the residual map); ``.gt`` (the summary table) and ``.gt_bw`` (the bandwidth
        table); ``.r2``, ``.aicc``, ``.adj_alpha`` and ``.critical_t`` (per term),
        ``.notes`` and ``.interpret()``.
    """
    from ._engine.gwr import analyze_mgwr
    df, geo, x = _prepare("mgwr", data, y, x, year, gdf, ref)
    return _inputs.finish(analyze_mgwr(df, y, x, gdf=geo, period=_inputs.one_year(df), kernel=kernel,
                                       criterion=criterion, max_iter=max_iter, tiles=tiles, title=title), df)


__all__ = ["mgwr"]
