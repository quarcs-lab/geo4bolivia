"""Working with panels: the change of each unit between two years."""

from __future__ import annotations

import numpy as np
import pandas as pd

_KEYS = ("geo_id", "year")


def change(df: pd.DataFrame, variables=None, first: int | None = None, last: int | None = None) -> pd.DataFrame:
    """The change of each unit between two years of a panel, one row per unit.

    Parameters
    ----------
    df
        A long panel with ``geo_id``, ``year`` and variables (e.g. from ``geo.load``)
    variables
        A variable or list of them (default: every numeric variable)
    first, last
        The two years to compare (default: the panel's first and last year)

    Returns
    -------
    pandas.DataFrame
        One row per unit. For each variable ``v``: ``v_<first>``, ``v_<last>``,
        ``v_change`` (last minus first), ``v_pct_change`` (in percent of the first
        value), ``v_annual_change`` (the change divided by the years between them),
        ``v_rank_<first>`` and ``v_rank_<last>`` (1 = highest value) and
        ``v_rank_change`` (positive when the unit climbed). Text columns that are
        constant within a unit (``name``, ``department``...) are kept.

        The years are the stored years: for panels stored at nominal years (see
        ``geo.reference_years``), the actual span of an indicator may differ.
    """
    if "geo_id" not in df.columns or "year" not in df.columns:
        raise ValueError("change() needs a long panel with geo_id and year columns (e.g. from geo.load)")
    data = df.drop(columns="geometry", errors="ignore")
    years = sorted(int(y) for y in data["year"].dropna().unique())
    if len(years) < 2:
        raise ValueError(f"change() needs at least two years; the panel has {years}")
    first = years[0] if first is None else int(first)
    last = years[-1] if last is None else int(last)
    for y in (first, last):
        if y not in years:
            raise ValueError(f"No rows for {y}; the panel's years are {years}")
    if first == last:
        raise ValueError("first and last must differ")
    if variables is None:
        variables = [c for c in data.columns if c not in _KEYS and not c.endswith("_id")
                     and pd.api.types.is_numeric_dtype(data[c])]
    elif isinstance(variables, str):
        variables = [variables]
    missing = [v for v in variables if v not in data.columns]
    if missing:
        raise ValueError(f"No column(s) {missing} in the panel")

    labels = [c for c in data.columns if c not in _KEYS and c not in variables
              and not pd.api.types.is_numeric_dtype(data[c])
              and (data.groupby("geo_id")[c].nunique(dropna=False) <= 1).all()]
    out = data[["geo_id", *labels]].drop_duplicates("geo_id").set_index("geo_id")
    a = data[data["year"] == first].set_index("geo_id")
    b = data[data["year"] == last].set_index("geo_id")
    span = last - first
    for v in variables:
        x0, x1 = a[v].reindex(out.index), b[v].reindex(out.index)
        r0 = x0.rank(ascending=False, method="min")
        r1 = x1.rank(ascending=False, method="min")
        out[f"{v}_{first}"] = x0
        out[f"{v}_{last}"] = x1
        out[f"{v}_change"] = x1 - x0
        out[f"{v}_pct_change"] = (x1 - x0) / x0.abs().replace(0, np.nan) * 100
        out[f"{v}_annual_change"] = (x1 - x0) / span
        out[f"{v}_rank_{first}"] = r0.astype("Int64")
        out[f"{v}_rank_{last}"] = r1.astype("Int64")
        out[f"{v}_rank_change"] = (r0 - r1).astype("Int64")
    out = out.reset_index()
    if df.attrs.get("geo:scale"):                 # the map the units are on, as load records it
        out.attrs["geo:scale"] = df.attrs["geo:scale"]
    return out
