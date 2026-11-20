"""Loading datasets, units, boundaries and crosswalks."""

from __future__ import annotations

import warnings
from functools import cache
from numbers import Integral

import geopandas as gpd
import pandas as pd

from . import metadata, store
from .scales import ancestors, scale_of
from .scales import get as get_scale


def datasets(ref: str | None = None) -> pd.DataFrame:
    """The catalog: one row per dataset and scale.

    Returns
    -------
    pandas.DataFrame
        Columns ``dataset`` (the id to pass to ``geo.load``), ``scale``, ``title``,
        ``years`` (e.g. ``"2001–2020"`` for an annual panel or ``"2012, 2024"`` for two
        periods), ``units`` (units with data), ``variables`` (how many), ``first_year``,
        ``last_year``, ``license``, ``categories`` and the ``csv`` and ``parquet`` paths.
    """
    columns = ["dataset", "scale", "title", "years", "units", "variables", "first_year", "last_year",
               "license", "categories", "csv", "parquet"]
    rows = []
    for ds in metadata.dataset_ids(ref):
        pkg = metadata.package(ds, ref)
        for res in pkg["resources"]:
            first, last = res["geo:period"]
            rows.append({"dataset": ds, "scale": res["geo:scale"], "title": pkg["title"],
                         "years": metadata.years_text(metadata.resource_years(res)),
                         "units": res.get("geo:units"),
                         "variables": len(metadata.variables(ds, res["geo:scale"], ref)),
                         "first_year": first, "last_year": last,
                         "license": ", ".join(lic.get("name", "") for lic in pkg.get("licenses", [])),
                         "categories": ", ".join(pkg.get("geo:categories", [])),
                         "csv": res["geo:path"], "parquet": res["geo:parquet"]})
    out = pd.DataFrame(rows, columns=columns)
    out["units"] = out["units"].astype("Int64")
    return out


def _reference_text(ref_years: dict | None) -> str:
    return "; ".join(f"{stored}: {actual}" for stored, actual in (ref_years or {}).items())


def dictionary(dataset: str, scale: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """The variable dictionary of a dataset, one row per column.

    Parameters
    ----------
    dataset
        Dataset id (see ``geo.datasets()``)
    scale
        The resource's scale (default: the dataset's native scale)

    Returns
    -------
    pandas.DataFrame
        Columns ``variable``, ``label`` (the field's ``title``, a readable name for
        plot axes and legends), ``description`` (how it was built), ``unit``, ``role``
        (id, time, source_key or variable), ``aggregation`` (the rule ``geo.aggregate``
        uses), ``source`` and ``reference_years`` (the actual years behind each stored
        year, e.g. ``"2012: 2008; 2024: 2023"``, when they differ).
    """
    return pd.DataFrame([{"variable": f["name"], "label": f.get("title", f["name"]),
                          "description": f.get("description", ""),
                          "unit": f.get("geo:unit", ""), "role": f.get("geo:role", "variable"),
                          "aggregation": f.get("geo:aggregation", ""), "source": f.get("geo:source", ""),
                          "reference_years": _reference_text(f.get("geo:reference_years"))}
                         for f in metadata.fields(dataset, scale, ref)])


def _as_years(years) -> list[int]:
    if isinstance(years, Integral):
        return [int(years)]
    if isinstance(years, tuple) and len(years) == 2:
        return list(range(int(years[0]), int(years[1]) + 1))
    return [int(y) for y in years]


def load(dataset: str, scale: str | None = None, years=None, variables=None,
         wide: str | None = None, geometry: bool = False, names: bool = False, groups=None,
         ref: str | None = None):
    """Load a dataset as a panel: one row per unit (``geo_id``) and year.

    Parameters
    ----------
    dataset
        Dataset id (see ``geo.datasets()``)
    scale
        Scale to load; defaults to the dataset's native scale
    years
        An int, a list of ints, or a ``(first, last)`` range (inclusive)
    variables
        A variable or list of variables to keep (``geo_id`` and ``year``
        are always kept); ``geo.search()`` and ``geo.dictionary()`` list them
    wide
        A variable name; returns one row per unit with one column per year
        (``<variable><year>``)
    geometry
        Attach unit boundaries (and names) and return a GeoDataFrame
    names
        Add the unit ``name``
    groups
        Coarser scales whose unit names to add as columns, e.g.
        ``["department"]`` adds a ``department`` column (implies ``names``)
    ref
        Git branch, tag or commit to read from GitHub (default: local checkout or ``main``)

    Notes
    -----
    Raises ``ValueError`` for unknown variables, and for years that have no rows
    (listing the years the dataset has).
    """
    res = metadata.resource(dataset, scale, ref)
    df = pd.read_parquet(store.open_binary(res["geo:parquet"], ref))
    if years is not None:
        wanted = _as_years(years)
        have = sorted(int(y) for y in df["year"].unique())
        absent = sorted(set(wanted) - set(have))
        if not set(wanted) & set(have):
            raise ValueError(f"{dataset!r} has no rows for {years!r}; its years are {metadata.years_text(have)}")
        if absent and not (isinstance(years, tuple) and len(years) == 2):
            warnings.warn(f"{dataset!r} has no rows for {absent}; its years are {metadata.years_text(have)}",
                          stacklevel=2)
        df = df[df["year"].isin(wanted)]
    if variables is not None:
        wanted = [variables] if isinstance(variables, str) else list(variables)
        unknown = [v for v in wanted if v not in df.columns]
        if unknown:
            raise ValueError(f"{dataset!r} has no variable(s) {unknown}; see geo.dictionary({dataset!r})")
        keep = ["geo_id", "year", *wanted]
        df = df[[c for c in df.columns if c in keep]]
    if wide is not None:
        if wide not in df.columns:
            raise ValueError(f"wide={wide!r} is not a column of the loaded data")
        df = df.pivot(index="geo_id", columns="year", values=wide)
        df.columns = [f"{wide}{y}" for y in df.columns]
        df = df.reset_index()
    df = df.reset_index(drop=True)
    if names or groups:
        df = add_names(df, groups=groups, scale=res["geo:scale"], ref=ref)
    if geometry:
        shapes = boundaries(res["geo:scale"], ref=ref)[["geo_id", "name", "geometry"]]
        df = shapes.merge(df.drop(columns="name", errors="ignore"), on="geo_id", how="right")
    return df


def add_names(df: pd.DataFrame, groups=None, scale: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """Add the unit ``name`` and, for each scale in ``groups``, the name of the unit it lies in.

    Parameters
    ----------
    df
        Any table with ``geo_id``
    groups
        A coarser scale or list of them (see ``geo.ancestors``), e.g. ``["department"]``
    scale
        The units' scale (default: inferred from ``geo_id``)

    Returns
    -------
    pandas.DataFrame
        A copy with ``name`` and one column per group (the group unit's name) after
        ``geo_id`` (and ``year``).
    """
    if scale is None:
        found = {scale_of(i, ref) for i in df["geo_id"].dropna().drop_duplicates()}
        if len(found) != 1:
            raise ValueError(f"Rows mix units from several scales: {sorted(found)}")
        scale = found.pop()
    groups = [groups] if isinstance(groups, str) else list(groups or [])
    unit_table = units(scale, ref=ref).set_index("geo_id")
    out = df.drop(columns=["name", *groups], errors="ignore").copy()
    out["name"] = out["geo_id"].map(unit_table["name"])
    for group in groups:
        if group not in ancestors(scale, ref):
            raise ValueError(f"{scale!r} units do not nest in {group!r}; groups must be among {ancestors(scale, ref)}")
        group_names = units(group, ref=ref).set_index("geo_id")["name"]
        out[group] = out["geo_id"].map(unit_table[f"{group}_id"]).map(group_names)
    first = ["geo_id", "name"] + (["year"] if "year" in out.columns else []) + groups
    return out[first + [c for c in out.columns if c not in first]]


def group_label(scale: str, ref: str | None = None) -> str:
    """The readable label of a scale, e.g. ``"Department"``."""
    return get_scale(scale, ref).label


@cache
def _units(ref: str | None) -> pd.DataFrame:
    return pd.read_parquet(store.open_binary("geo/units.parquet", ref))


def units(scale: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """All units (or the units of one scale) with names, parents and source keys.

    Parameters
    ----------
    scale
        A scale id (see ``geo.scales()``); default: every scale

    Returns
    -------
    pandas.DataFrame
        Every row has ``geo_id``, ``scale``, ``name``, ``parent_id``, ``area_km2``, a
        ``<scale>_id`` column for each coarser scale it lies in, and the codes each
        source uses for it (e.g. ``ine_code``), which ``geo.link(..., key=...)`` matches.
    """
    df = _units(ref)
    return (df if scale is None else df[df["scale"] == scale]).reset_index(drop=True).copy()


def boundaries(scale: str, ref: str | None = None) -> gpd.GeoDataFrame:
    """Unit polygons for a scale (CRS84), with ``geo_id`` and ``name``.

    Parameters
    ----------
    scale
        A scale id (see ``geo.scales()``)
    """
    return gpd.read_parquet(store.open_binary(f"geo/boundaries/{scale}.parquet", ref))


def crosswalk(source: str, target: str, ref: str | None = None) -> pd.DataFrame:
    """Links between two scales: ``geo_id_from``, ``geo_id_to``, ``weight_area``.

    Parameters
    ----------
    source
        The finer scale, e.g. ``"municipality"``
    target
        A coarser scale it nests in, e.g. ``"department"``

    Returns
    -------
    pandas.DataFrame
        ``weight_area`` is the share of the source unit's area inside the target unit
        (1.0 for nested scales). Crosswalks are published for every pair of active
        scales where one nests in the other, from finer to coarser.
    """
    return pd.read_csv(store.open_binary(f"geo/crosswalks/{source}__{target}.csv", ref))
