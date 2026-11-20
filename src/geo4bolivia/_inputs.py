"""Preparing the inputs of the analysis functions.

Every analysis function accepts a dataset id or a panel (``geo_id``, ``year`` and
variables, e.g. from ``load``) and finds the rest itself: the units' names and labels
from the metadata, their boundaries from the units' scale, and queen contiguity weights
from those boundaries. Explicit ``gdf=`` and ``w=`` replace what would be found, so the
functions also run on data that are not in the project.

The functions here translate that into what the analysis engine (``_engine``) expects:
a plain DataFrame with the panel ids and labels declared, a GeoDataFrame keyed by
``geo_id``, and ``libpysal`` weights keyed the same way.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable

import geopandas as gpd
import pandas as pd

from . import io
from .scales import scale_of

ENTITY, TIME, NAME = "geo_id", "year", "name"


def as_list(value) -> list:
    """``None`` -> ``[]``; a string -> ``[string]``; anything else -> a list."""
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _labels(df: pd.DataFrame, ref: str | None) -> dict[str, str]:
    """Metadata labels for the columns that have one (none when the metadata cannot be read)."""
    from .discover import labels
    try:
        return labels(df, ref=ref)
    except Exception:  # offline, or data that are not in the project
        return {}


def _with_names(df: pd.DataFrame, gdf, groups: list[str], ref: str | None) -> pd.DataFrame:
    """Add ``name`` (and group columns) when they are missing and can be found."""
    wanted = [g for g in groups if g not in df.columns]
    if NAME in df.columns and not wanted:
        return df
    if gdf is not None and NAME in getattr(gdf, "columns", []) and NAME not in df.columns and not wanted:
        return df.assign(**{NAME: df[ENTITY].map(gdf.set_index(ENTITY)[NAME]).fillna(df[ENTITY])})
    try:
        named = io.add_names(df, groups=wanted or None, ref=ref)
        return named if NAME not in df.columns else named.assign(**{NAME: df[NAME].to_numpy()})
    except Exception:
        if wanted:
            raise
        return df.assign(**{NAME: df[ENTITY].astype(str)})


def panel(data, variables=None, *, groups=None, gdf=None, numeric: bool = True, ref: str | None = None) -> pd.DataFrame:
    """A dataset id or a frame, as a plain panel ready for the engine.

    Parameters
    ----------
    data
        A dataset id, or a table with ``geo_id`` (and ``year``), with or without geometry
    variables
        The columns the analysis needs; they must exist (and be numeric)
    groups
        Coarser scales whose unit names are needed as columns (e.g. ``"department"``)
    gdf
        Explicit boundaries, used for the units' names when the table has none

    Returns
    -------
    pandas.DataFrame
        A copy with ``name`` (and the groups), whose ``attrs`` declare the panel ids
        (``geo_id``, ``year``, ``name``) and the labels of its columns for the engine.
    """
    from ._engine._labels import set_labels
    from ._engine._panel import set_panel

    variables, groups = as_list(variables), as_list(groups)
    if isinstance(data, str):
        df = io.load(data, variables=variables or None, names=True, groups=groups or None, ref=ref)
    else:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a dataset id or a DataFrame with a geo_id column")
        if ENTITY not in data.columns:
            raise ValueError(f"The table needs a {ENTITY!r} column (as returned by load)")
        df = pd.DataFrame(data).drop(columns="geometry", errors="ignore").copy()
        missing = [v for v in variables if v not in df.columns]
        if missing:
            raise ValueError(f"No column(s) {missing} in the table; it has {[c for c in df.columns if c != ENTITY]}")
        df = _with_names(df, gdf, groups, ref)
    if numeric:
        text = [v for v in variables if not pd.api.types.is_numeric_dtype(df[v])]
        if text:
            raise TypeError(f"Column(s) {text} must be numeric")
    df = df.reset_index(drop=True)
    set_panel(df, entity=ENTITY, time=TIME if TIME in df.columns else None, entity_name=NAME)
    set_labels(df, {k: v for k, v in _labels(df, ref).items() if k not in (ENTITY, NAME, TIME)})
    return df


def years(df: pd.DataFrame, variables=None) -> list[int]:
    """The years of a panel with data for every one of ``variables``, sorted; ``[]`` without a year column."""
    if TIME not in df.columns:
        return []
    cols = as_list(variables)
    rows = df[df[cols].notna().all(axis=1)] if cols else df
    return sorted(int(y) for y in rows[TIME].dropna().unique())


def pick_year(df: pd.DataFrame, variables, year) -> int | None:
    """The year to analyse: the one asked for (checked), else the last with data; ``None`` without years."""
    have = years(df, variables)
    if not have:
        if year is not None and TIME not in df.columns:
            raise ValueError("The table has no year column, so year= cannot be used")
        if TIME in df.columns:
            raise ValueError(f"No year has data for {as_list(variables)}")
        return None
    if year is None:
        return have[-1]
    if int(year) not in have:
        raise ValueError(f"No rows for {year}; the years with data are {have}")
    return int(year)


def shapes(df: pd.DataFrame | None, gdf=None, *, scale: str | None = None, ids: Iterable | None = None,
           ref: str | None = None) -> gpd.GeoDataFrame:
    """The boundaries of the units of a panel, keyed by ``geo_id``.

    Parameters
    ----------
    df
        The panel whose units are needed (``None`` with ``scale`` or ``gdf``: every unit)
    gdf
        Explicit boundaries with a ``geo_id`` column (default: the project's, for the units' scale)
    scale
        The units' scale (default: inferred from ``geo_id``)
    ids
        Keep only these units (default: the units of ``df``)
    """
    from ._engine._geo import _GEO_KEY

    if ids is None and df is not None:
        ids = df[ENTITY].dropna().unique()
    if gdf is None:
        if scale is None:
            if df is None or not len(df):
                raise ValueError("Give a scale, boundaries (gdf=) or a table with units")
            scale = scale_of(df[ENTITY].iloc[0], ref)
        gdf = io.boundaries(scale, ref=ref)
    elif not isinstance(gdf, gpd.GeoDataFrame) or ENTITY not in gdf.columns:
        raise ValueError(f"gdf must be a GeoDataFrame with a {ENTITY!r} column")
    out = gdf[[c for c in (ENTITY, NAME) if c in gdf.columns] + [gdf.geometry.name]]
    if ids is not None:
        out = out[out[ENTITY].isin(set(ids))]
        if out.empty:
            raise ValueError("None of the table's geo_id values is in the boundaries")
    out = out.reset_index(drop=True)
    if out.crs is None:
        out = out.set_crs("EPSG:4326")
    out.attrs[_GEO_KEY] = {"entity": ENTITY, "entity_name": NAME if NAME in out.columns else None}
    return out


def spatial_weights(gdf: gpd.GeoDataFrame, w=None, *, method: str = "queen", **options):
    """The weights to use: the ones given, else contiguity (or ``method``) weights built from ``gdf``.

    Given weights that cover more units than ``gdf`` are restricted to its units (and
    standardized again), so they can be built once for a scale and reused on datasets
    that lack some units.
    """
    from ._engine._validation import AnalysisWarning
    from ._engine.weights import make_weights
    if w is None:
        # What the engine warns about here (an island attached to its nearest neighbour, the
        # projection used for distances) is recorded in the weights' description, which every
        # result carries as ``w_spec``: a default should not warn on every call.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", AnalysisWarning)
            return make_weights(gdf, method=method, entity=ENTITY, **options)
    ids = list(gdf[ENTITY])
    known = set(w.id_order)
    if set(ids) == known:
        return w
    absent = [i for i in ids if i not in known]
    if absent:
        raise ValueError(f"The weights lack {len(absent)} unit(s) of the data (e.g. {absent[:3]}); "
                         "build them with weights() on the same units")
    from libpysal.weights import w_subset
    spec = getattr(w, "geo_meta", {}).get("spec")
    transform = w.transform
    sub = w_subset(w, ids, silence_warnings=True)
    sub.transform = transform
    if spec:
        sub.geo_meta = {"spec": f"{str(spec).replace(f'n={w.n}', f'n={sub.n}')} (restricted from {w.n} units)"}
    return sub


def one_year(df: pd.DataFrame) -> int | None:
    """The year of a panel that holds a single year (``None`` without a year column)."""
    have = years(df)
    return have[0] if len(have) == 1 else None


def spatial(data, variables=None, *, year=None, gdf=None, w=None, groups=None, weights: bool = True,
            ref: str | None = None) -> tuple[pd.DataFrame, gpd.GeoDataFrame, object]:
    """The three inputs of a spatial analysis: the panel, its boundaries and its weights.

    Parameters
    ----------
    data, variables, groups, gdf
        See ``panel``
    year
        ``None`` or a year: keep that year only (the last with data for every
        variable when ``None``); ``"all"``: keep every year with data; a list of years:
        keep those
    w
        The weights to use (default: queen contiguity)
    weights
        ``False`` skips the weights (``None`` is returned in their place)

    Notes
    -----
    The panel keeps only the units with data for every variable in every year kept, the
    boundaries are restricted to those units, and the default weights are built on them:
    a unit without data is not a neighbour, and every table and statistic refers to the
    same set of units.
    """
    df = panel(data, variables, groups=groups, gdf=gdf, ref=ref)
    cols = as_list(variables)
    if TIME in df.columns:
        if isinstance(year, str) and year.lower() == "all":
            df = df[df[TIME].isin(years(df, cols))]        # a year without any data is not a year of the panel
        elif isinstance(year, list | tuple):
            df = df[df[TIME].isin([pick_year(df, cols, y) for y in year])]
        else:
            df = df[df[TIME] == pick_year(df, cols, year)]
    elif year is not None and not (isinstance(year, str) and year.lower() == "all"):
        raise ValueError("The table has no year column, so year= cannot be used")
    if cols:
        ok = df[cols].notna().all(axis=1)
        n_years = df[TIME].nunique() if TIME in df.columns else 1
        counts = ok.groupby(df[ENTITY]).sum()
        ids = counts.index[counts.to_numpy() == n_years]
        if not len(ids):
            raise ValueError(f"No unit has data for {cols} in every year kept ({years(df) or 'no years'})")
    else:
        ids = df[ENTITY].unique()
    geo = shapes(df, gdf, ids=ids, ref=ref)
    kept = df[df[ENTITY].isin(set(geo[ENTITY]))].reset_index(drop=True)
    kept.attrs = dict(df.attrs)
    return kept, geo, (spatial_weights(geo, w) if weights else None)

def finish(result, names: pd.Series | pd.DataFrame | None = None):
    """An engine result as the public functions return it.

    Its tables use the package's column names (``geo_id`` and ``year`` instead of the
    engine's ``entity`` and ``period``), and those with one row per unit get the unit
    ``name`` next to ``geo_id`` when ``names`` (a panel, or a Series indexed by
    ``geo_id``) is given.
    """
    import dataclasses

    out = _whole_years(result._public_view())
    if names is None:
        return out
    if isinstance(names, pd.DataFrame):
        if NAME not in names.columns:
            return out
        names = names.drop_duplicates(ENTITY).set_index(ENTITY)[NAME]
    changes = {}
    for field, frame in out._frames().items():
        if ENTITY in frame.columns and NAME not in frame.columns:
            frame = frame.copy()
            frame.insert(frame.columns.get_loc(ENTITY) + 1, NAME, frame[ENTITY].map(names))
            changes[field] = frame
    return dataclasses.replace(out, **changes) if changes else out


def _whole_years(result):
    """A result whose ``year`` columns hold whole numbers as integers (the engine may return floats or objects)."""
    import dataclasses

    changes = {}
    for field, frame in result._frames().items():
        if TIME not in frame.columns or pd.api.types.is_integer_dtype(frame[TIME]):
            continue
        numbers = pd.to_numeric(frame[TIME], errors="coerce")
        if numbers.notna().all() and (numbers % 1 == 0).all():
            changes[field] = frame.assign(**{TIME: numbers.astype(int)})
    return dataclasses.replace(result, **changes) if changes else result
