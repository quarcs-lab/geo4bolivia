"""Convergence: do lagging units catch up (beta), does dispersion fall (sigma), and do clubs form?"""

from __future__ import annotations

import dataclasses
import re
import warnings

import numpy as np
import pandas as pd

from . import _inputs

ENTITY, TIME = _inputs.ENTITY, _inputs.TIME


def _keep(df: pd.DataFrame, rows) -> pd.DataFrame:
    """The selected rows, with the panel ids and labels that ``df`` declares."""
    out = df[rows].reset_index(drop=True)
    out.attrs = dict(df.attrs)
    return out


def _years(df: pd.DataFrame, variable: str, what: str) -> list[int]:
    """The years with data for ``variable``; an error when the table has no years."""
    if TIME not in df.columns:
        raise ValueError(f"{what} compares years, so the table needs a {TIME!r} column")
    have = _inputs.years(df, variable)
    if not have:
        raise ValueError(f"No rows with data for {variable!r}")
    return have


def _span(df: pd.DataFrame, variable: str, first, last, what: str) -> tuple[int, int, list[int]]:
    """The first and last year to use (checked) and the years with data between them."""
    have = _years(df, variable, what)
    first = have[0] if first is None else _inputs.pick_year(df, variable, first)
    last = have[-1] if last is None else _inputs.pick_year(df, variable, last)
    if last < first:
        raise ValueError(f"last ({last}) must not be before first ({first})")
    return first, last, [y for y in have if first <= y <= last]


def _positive(df: pd.DataFrame, variable: str, what: str) -> None:
    """Raise unless every value of ``variable`` is strictly positive."""
    bad = df[df[variable] <= 0]
    if len(bad):
        from .metadata import years_text
        raise ValueError(
            f"{what} takes the logarithm of the variable, so it needs a strictly positive variable in levels: "
            f"{variable!r} has {len(bad)} value(s) of zero or less (in {years_text(bad[TIME])}). "
            f"If {variable!r} is already a logarithm, pass its exponential instead.")


def _logged(df: pd.DataFrame, variable: str, what: str) -> list[str]:
    """A warning (returned as a note) when the name or the label of ``variable`` says it is a logarithm."""
    from ._engine._labels import resolve_label
    from ._engine._validation import AnalysisWarning
    label = resolve_label(df, variable)
    if not (re.search(r"(^|_)(ln|log)(_|$)", variable, re.I) or re.search(r"\b(ln|log|logarithm)\b", label, re.I)):
        return []
    note = (f"{variable!r} looks like a logarithm" + (f" ({label})" if label != variable else "")
            + f": {what} takes the logarithm itself, so pass the variable in levels (its exponential)")
    warnings.warn(note, AnalysisWarning, stacklevel=3)
    return [note]


def _long_enough(need: int, ref: str | None) -> str:
    """A sentence naming the project's datasets with at least ``need`` years ('' when none can be found)."""
    try:
        from . import io, metadata
        found = {}
        for row in io.datasets(ref).itertuples():
            years = metadata.resource_years(metadata.resource(row.dataset, row.scale, ref))
            if len(years) >= need:
                found.setdefault(row.dataset, row.years)
    except Exception:  # offline, or no catalog
        return ""
    if not found:
        return ""
    listed = [f"{dataset} ({years})" for dataset, years in found.items()]
    more = f" and {len(listed) - 8} more" if len(listed) > 8 else ""
    return f" Datasets with at least {need} years: {', '.join(listed[:8])}{more}."


def _too_short(what: str, why: str, need: int, variable: str, have: list[int], instead: str,
               ref: str | None) -> ValueError:
    """The error for a panel with too few years for a method: what it needs, what the data have, where to go."""
    from .metadata import years_text
    return ValueError(
        f"{what} {why}, so it needs at least {need} years; {variable!r} has {len(have)} ({years_text(have)})."
        f"{_long_enough(need, ref)} {instead}")


def _balanced(df: pd.DataFrame, variable: str, years: list[int], what: str) -> tuple[pd.DataFrame, list[str]]:
    """The units observed in every one of ``years``, and a note on the units left out."""
    rows = df[df[TIME].isin(years) & df[variable].notna()]
    seen = rows.groupby(ENTITY)[TIME].nunique()
    complete = set(seen.index[seen.to_numpy() == len(years)])
    if len(complete) < 2:
        raise ValueError(f"{what} needs at least 2 units with data for {variable!r} in every year from "
                         f"{years[0]} to {years[-1]}; {len(complete)} of {len(seen)} have them. "
                         "Try a shorter window with first= and last=.")
    notes = []
    if len(complete) < len(seen):
        notes.append(f"{len(seen) - len(complete)} of {len(seen)} units were left out: no data for {variable!r} "
                     f"in every year from {years[0]} to {years[-1]}")
    return _keep(df, df[TIME].isin(years) & df[ENTITY].isin(complete)), notes


def _finish(result, df: pd.DataFrame, notes: list[str]):
    """An engine result as the public functions return it, with whole years and this module's notes first."""
    out = _inputs.finish(result, df)
    changes = {}
    for field, frame in out._frames().items():
        if TIME in frame.columns and pd.api.types.is_float_dtype(frame[TIME]) and (frame[TIME] % 1 == 0).all():
            changes[field] = frame.astype({TIME: int})
    if notes:
        changes["notes"] = (*notes, *out.notes)
    return dataclasses.replace(out, **changes) if changes else out


def beta_convergence(data, variable: str, controls=None, *, first=None, last=None, model: str = "ols", w=None,
                     fixed_effects=None, vcov: str = "hetero", draws: int = 10_000, seed: int = 12345,
                     min_obs: int = 10, title: str | None = None,
                     map: str | None = None, gdf=None, ref: str | None = None):
    """Beta-convergence: did the units that started lower grow faster between two years?

    Regresses each unit's average yearly log growth between ``first`` and ``last`` on the
    logarithm of its level in ``first``. A negative slope is convergence.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        A numeric, strictly positive column in levels (its logarithm is taken here,
        so do not pass a variable that is already a logarithm)
    controls
        Numeric column(s) that enter at their value in ``first`` (conditional convergence)
    first, last
        The two years (default: the first and the last year with data)
    model
        ``"ols"``, or a spatial model estimated on the boundaries' weights: ``"sar"``
        (spatial lag of growth), ``"sem"`` (spatial error), ``"slx"`` (spatial lags of the
        regressors) or ``"sdm"`` (spatial Durbin: both lags)
    w
        Spatial weights from ``weights`` for the spatial models (default: queen contiguity
        among the units with data in both years)
    fixed_effects
        Column(s), or coarser scale(s) the units lie in (e.g. the scale above
        them), that enter as dummy variables
    vcov
        Standard errors of the OLS estimate: ``"hetero"`` (robust, HC1) or ``"iid"``
    draws
        Simulation draws behind the standard errors of the spatial models' impacts
    seed
        Makes the draws reproducible
    min_obs
        The fewest units the regression accepts
    title
        The figure title
    map
        The map (scale) the units are drawn on and their neighbours found, e.g. one of
        the project's municipal maps (default: the data's own map; needed only for a table
        whose units are on several maps and that does not record which, see ``geo.scales()``)
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``).
        Boundaries are loaded only for the spatial models; with ``"ols"``, passing ``gdf``
        adds the growth map

    Returns
    -------
    result object
        A result with ``.beta_total`` (the slope; for the spatial models the total impact, next
        to ``.beta_direct`` and ``.beta_indirect``, the spillover), their standard errors
        ``.se_total``, ``.se_direct`` and ``.se_indirect``, ``.speed`` (of convergence, per
        year) and ``.half_life`` (years to close half of a gap), ``.rho`` and ``.lam`` (the
        spatial parameters), ``.r2``, ``.aic``, ``.n_obs``, ``.horizon`` (years between
        ``first`` and ``last``), ``.df`` (one row per unit: ``initial``, ``final``, ``growth``
        and the controls), ``.fig`` (growth against the initial log level, with the fitted
        line), ``.fig_conditional`` (the same with controls and fixed effects partialled out;
        ``None`` without them), ``.fig_map`` (the map of growth; ``None`` without
        boundaries), ``.gt`` and ``.summary`` (the estimates; the OLS column is always
        there), ``.impacts`` (every regressor's impacts, spatial models), ``.w_spec``,
        ``.notes`` and ``.interpret()``.
    """
    from ._engine import convergence as engine

    what = "beta_convergence"
    if model not in engine._BETA_MODELS:
        raise ValueError(f"Unknown model {model!r}; choose from {list(engine._BETA_MODELS)}")
    controls, fixed = _inputs.as_list(controls), _inputs.as_list(fixed_effects)
    if isinstance(data, str):
        from . import metadata
        columns = {f["name"] for f in metadata.fields(data, ref=ref)}
    else:
        columns = set(getattr(data, "columns", []))
    groups = [f for f in fixed if f not in columns]       # coarser scales, added as columns of unit names
    if groups:
        from .scales import scales as registry
        try:
            known = set(registry(ref=ref))
        except Exception:  # offline, or data that are not in the project
            known = set()
        unknown = [g for g in groups if g not in known]
        if unknown:
            raise ValueError(f"fixed_effects {unknown}: no such column in the data, and no such scale"
                             + (f" (the scales are {sorted(known)})" if known else ""))
    df =_inputs.panel(data, [variable, *controls, *[f for f in fixed if f in columns]], groups=groups, gdf=gdf,
                      scale=map,
                       numeric=False, ref=ref)
    text = [v for v in [variable, *controls] if not pd.api.types.is_numeric_dtype(df[v])]
    if text:
        raise TypeError(f"Column(s) {text} must be numeric")

    first, last, _ = _span(df, variable, first, last, what)
    if first == last:
        every = _inputs.years(df, variable)
        raise ValueError(f"{what} compares two years; " + (f"first and last are both {first}" if len(every) > 1
                                                          else f"{variable!r} has data for {every[0]} only"))
    start = df[df[TIME] == first].dropna(subset=[variable, *controls, *fixed])
    end = df[(df[TIME] == last) & df[variable].notna()]
    ids = set(start[ENTITY]) & set(end[ENTITY])
    seen = df.loc[df[TIME].isin([first, last]) & df[variable].notna(), ENTITY].nunique()
    extra = f", and for {[*controls, *fixed]} in {first}" if controls or fixed else ""
    if not ids:
        raise ValueError(f"No unit has data for {variable!r} in both {first} and {last}{extra}")
    notes = [f"growth between {first} and {last}"]
    if len(ids) < seen:
        notes.append(f"{seen - len(ids)} of {seen} units were left out: no data for {variable!r} in both "
                     f"{first} and {last}{extra}")
    df = _keep(df, df[TIME].isin([first, last]) & df[ENTITY].isin(ids))
    _positive(df, variable, what)
    notes += _logged(df, variable, what)

    geo = None
    if model != "ols":
        df, geo, w = _inputs.spatial(df, variable, year=[first, last], gdf=gdf, scale=map, w=w, ref=ref)
        if len(geo) < len(ids):
            notes.append(f"{len(ids) - len(geo)} of {len(ids)} units were left out: they are not in the boundaries")
    elif gdf is not None:
        geo = _inputs.shapes(df, gdf, scale=map, ref=ref)
    res = engine.analyze_beta_convergence(
        df, variable, controls or None, entity=ENTITY, time=TIME, start=first, end=last, model=model, gdf=geo,
        w=w if model != "ols" else None, fixed_effects=fixed or None, vcov=vcov, n_draws=draws, seed=seed,
        min_obs=min_obs, title=title)
    return _finish(res, df, notes)


def sigma_convergence(data, variable: str, *, first=None, last=None, vcov: str = "hetero",
                      title: str | None = None, ref: str | None = None):
    """Sigma-convergence: does the dispersion of a variable across units fall over time?

    Measures the dispersion of the logarithm of ``variable`` in every year, on the units
    observed in all of them, and estimates its trend. A negative trend is convergence.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        A numeric, strictly positive column in levels (its logarithm is taken here)
    first, last
        The first and last year to use (default: every year with data). The
        trend needs at least three years
    vcov
        Standard errors of the trend: ``"hetero"`` (robust, HC1) or ``"iid"``
    title
        The figure title

    Returns
    -------
    result object
        A result with ``.std_slope`` (the trend of the log standard deviation per year:
        negative when dispersion falls), ``.std_se``, ``.std_pvalue`` and ``.std_r2``, the
        same for the Gini index (``.gini_slope``...) and the coefficient of variation
        (``.cv_slope``...), ``.n_units``, ``.n_periods``, ``.df`` (one row per year:
        ``n_units``, ``mean``, ``std``, ``gini`` and ``cv`` of the logarithm), ``.fig``
        (dispersion over time with the fitted trends), ``.gt`` and ``.summary`` (one row per
        measure), ``.notes`` (among them the units left out for lack of data) and
        ``.interpret()``.
    """
    from ._engine import convergence as engine

    what = "sigma_convergence"
    df = _inputs.panel(data, variable, ref=ref)
    first, last, years = _span(df, variable, first, last, what)
    if len(years) < 3:
        raise _too_short(what, "estimates the trend of dispersion over time", 3, variable, years,
                         "To compare the dispersion of two years, use inequality.", ref)
    df, notes = _balanced(df, variable, years, what)
    _positive(df, variable, what)
    notes += _logged(df, variable, what)
    res = engine.analyze_sigma_convergence(df, variable, entity=ENTITY, time=TIME, start=first, end=last, vcov=vcov,
                                           title=title)
    return _finish(res, df, notes)


def convergence_clubs(data, variable: str, *, first=None, last=None, log: bool = False, hp_filter: bool = True,
                      hp_lambda: float = 400.0, trim: float = 0.3, tcrit: float = -1.65, cr: float = 0.0,
                      increment: float = 0.05, max_cr: float = 3.0, fraction: float = 0.0, adjust: bool = False,
                      merge: str = "ps", draw_map: bool = True, tiles: str | None = "carto-positron",
                      title: str | None = None,
                      map: str | None = None, gdf=None, ref: str | None = None):
    """Convergence clubs (Phillips and Sul): do all units converge, or do groups of them?

    Tests whether the units' paths converge (the log t test) and, when they do not, sorts
    the units into clubs that converge among themselves, on the units observed in every year.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to analyse, used as given: pass a logarithm, or set ``log``
    first, last
        The first and last year to use (default: every year with data). The
        years in between must all be there: at least 6 of them at the default ``trim``
    log
        Take the logarithm of ``variable`` first (it must then be strictly positive)
    hp_filter
        Analyse each unit's Hodrick-Prescott trend instead of its raw path
    hp_lambda
        The filter's smoothing (400 for yearly data)
    trim
        The share of the first years that the log t regression leaves out
    tcrit
        The t-statistic above which convergence is not rejected (-1.65: the 5% level)
    cr, increment, max_cr
        The threshold for adding a unit to a club's core group, the step
        by which it is raised while the club fails the test, and its ceiling
    fraction
        Sort the units by their mean over the last ``1 - fraction`` of the years
        instead of the last year (0)
    adjust
        Add the units to a club one at a time (Schnurbus et al.) instead of raising ``cr``
    merge
        Join neighbouring clubs that converge together: ``"ps"`` (until none do),
        ``"single"`` (one pass) or ``"none"``
    draw_map
        Draw the map of the clubs (``False``: no boundaries are loaded)
    tiles
        The basemap style (``None``: no basemap)
    title
        The figure title
    map
        The map (scale) the units are drawn on and their neighbours found, e.g. one of
        the project's municipal maps (default: the data's own map; needed only for a table
        whose units are on several maps and that does not record which, see ``geo.scales()``)
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.n_clubs``, ``.n_divergent`` (units in no club), ``.converged`` (all
        units form one club), ``.global_tstat`` and ``.global_beta`` (the log t test on all
        units), ``.n_units``, ``.n_periods``, ``.membership`` (one row per unit with its
        ``club``; 0 = in no club), ``.summary`` and ``.gt`` (one row per club with its test),
        ``.df`` (one row per unit and year: ``value``, the ``relative`` path and ``club``),
        ``.fig`` (the clubs' average paths), ``.fig_paths`` (every unit's path),
        ``.fig_clubs`` (one panel per club), ``.fig_map`` (the map of the clubs; ``None``
        without boundaries), ``.notes`` and ``.interpret()``.
    """
    from ._engine import clubs as engine

    what = "convergence_clubs"
    if not 0.0 < trim < 1.0:
        raise ValueError(f"trim must be between 0 and 1; got {trim}")
    df = _inputs.panel(data, variable, gdf=gdf, scale=map, ref=ref)
    first, last, years = _span(df, variable, first, last, what)
    left = len(years) - engine._sround(trim * len(years))          # the engine's rule: years left after the trim
    if left < 4:
        need = next(n for n in range(4, 10_000) if n - engine._sround(trim * n) >= 4)
        why = f"follows the units' paths over time (its log t regression leaves out the first {trim:.0%} of the years)"
        instead = ("A smaller trim needs fewer years. " if len(years) >= 4 and need > 4 else "") + (
            "With two years, use beta_convergence (catching up) or inequality (dispersion).")
        raise _too_short(what, why, need, variable, years, instead, ref)
    df, notes = _balanced(df, variable, years, what)
    if log:
        from ._engine._labels import resolve_label, set_labels
        _positive(df, variable, f"{what} with log=True")
        df[variable] = np.log(df[variable].to_numpy(dtype=float))
        set_labels(df, {variable: f"log {resolve_label(df, variable)}"})

    geo = None
    if draw_map:
        try:
            geo = _inputs.shapes(df, gdf, scale=map, ref=ref)
        except Exception as error:
            if gdf is not None:
                raise
            notes.append(f"no map: the units' boundaries could not be found ({error}); pass gdf=")
    res = engine.analyze_convergence_clubs(
        df, variable, entity=ENTITY, time=TIME, gdf=geo, hp_filter=hp_filter, hp_lambda=hp_lambda, trim=trim,
        tcrit=tcrit, cr=cr, increment=increment, max_cr=max_cr, fraction=fraction, adjust=adjust, merge=merge,
        tiles=tiles, title=title)
    return _finish(res, df, notes)


__all__ = ["beta_convergence", "convergence_clubs", "sigma_convergence"]
