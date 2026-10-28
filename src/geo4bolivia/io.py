"""Loading datasets, units, boundaries and crosswalks."""

from __future__ import annotations

from functools import lru_cache
from numbers import Integral

import geopandas as gpd
import pandas as pd

from . import metadata, store


def datasets() -> pd.DataFrame:
    """One row per dataset and scale: what is available, where, and for which years."""
    columns = ["dataset", "scale", "title", "first_year", "last_year", "variables", "csv", "parquet"]
    rows = []
    for ds in metadata.dataset_ids():
        pkg = metadata.package(ds)
        for res in pkg["resources"]:
            first, last = res["geo:period"]
            rows.append({"dataset": ds, "scale": res["geo:scale"], "title": pkg["title"],
                         "first_year": first, "last_year": last,
                         "variables": len(metadata.variables(ds, res["geo:scale"])),
                         "csv": res["geo:path"], "parquet": res["geo:parquet"]})
    return pd.DataFrame(rows, columns=columns)


def dictionary(dataset: str, scale: str | None = None) -> pd.DataFrame:
    """The variable dictionary of a dataset: name, description, unit, aggregation rule, source."""
    return pd.DataFrame([{"variable": f["name"], "description": f.get("description", ""),
                          "unit": f.get("geo:unit", ""), "role": f.get("geo:role", "variable"),
                          "aggregation": f.get("geo:aggregation", ""), "source": f.get("geo:source", "")}
                         for f in metadata.fields(dataset, scale)])


def load(dataset: str, scale: str | None = None, years=None, variables=None,
         wide: str | None = None, geometry: bool = False, ref: str | None = None):
    """Load a dataset as a panel: one row per unit (``geo_id``) and year.

    Parameters
    ----------
    dataset : dataset id, e.g. ``"gdppc"`` (see ``geo.datasets()``)
    scale : scale to load; defaults to the dataset's native scale
    years : an int, an iterable of ints, or a ``(first, last)`` range
    variables : subset of variables to keep (``geo_id`` and ``year`` are always kept)
    wide : a variable name; returns one row per unit with one column per year
    geometry : attach unit boundaries and return a GeoDataFrame
    ref : git branch, tag or commit to read from GitHub (default: local checkout or ``main``)
    """
    res = metadata.resource(dataset, scale)
    df = pd.read_parquet(store.open_binary(res["geo:parquet"], ref))
    if years is not None:
        if isinstance(years, Integral):
            years = [int(years)]
        elif isinstance(years, tuple) and len(years) == 2:
            years = range(years[0], years[1] + 1)
        df = df[df["year"].isin(list(years))]
    if variables is not None:
        wanted = [variables] if isinstance(variables, str) else list(variables)
        unknown = [v for v in wanted if v not in df.columns]
        if unknown:
            raise ValueError(f"{dataset!r} has no variable(s) {unknown}; see geo.dictionary({dataset!r})")
        keep = ["geo_id", "year", *wanted]
        df = df[[c for c in df.columns if c in keep]]
    if wide is not None:
        df = df.pivot(index="geo_id", columns="year", values=wide)
        df.columns = [f"{wide}{y}" for y in df.columns]
        df = df.reset_index()
    df = df.reset_index(drop=True)
    if geometry:
        shapes = boundaries(res["geo:scale"], ref=ref)[["geo_id", "name", "geometry"]]
        df = shapes.merge(df, on="geo_id", how="right")
    return df


@lru_cache(maxsize=None)
def _units(ref: str | None) -> pd.DataFrame:
    return pd.read_parquet(store.open_binary("geo/units.parquet", ref))


def units(scale: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """All units (or the units of one scale) with names, parents and source keys."""
    df = _units(ref)
    return (df if scale is None else df[df["scale"] == scale]).reset_index(drop=True).copy()


def boundaries(scale: str, ref: str | None = None) -> gpd.GeoDataFrame:
    """Unit polygons for a scale (CRS84), with ``geo_id`` and ``name``."""
    return gpd.read_parquet(store.open_binary(f"geo/boundaries/{scale}.parquet", ref))


def crosswalk(source: str, target: str, ref: str | None = None) -> pd.DataFrame:
    """Links between two scales: ``geo_id_from``, ``geo_id_to``, ``weight_area``.

    ``weight_area`` is the share of the source unit's area inside the target unit
    (1.0 for nested scales). Crosswalks are published for every pair of active
    scales where one nests in the other, from finer to coarser.
    """
    return pd.read_csv(store.open_binary(f"geo/crosswalks/{source}__{target}.csv", ref))
