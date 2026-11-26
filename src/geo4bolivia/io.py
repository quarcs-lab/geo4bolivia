"""Loading datasets, units, boundaries and crosswalks."""

from __future__ import annotations

import warnings
from functools import cache
from numbers import Integral

import geopandas as gpd
import pandas as pd

from . import metadata, store
from .scales import ancestors, check, scales_of
from .scales import get as get_scale

#: Where a table records the scale (the map) of its units, in ``DataFrame.attrs``: ``load`` sets it,
#: and pandas keeps it through filtering and copying.
SCALE_KEY = "geo:scale"


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
         wide: str | bool | None = None, geometry: bool = False, names: bool = False, groups=None,
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
        ``True`` returns the dataset's wide table (``geo.wide_table``): one row per unit,
        with its name, its province and department, its source keys and area, and every
        variable once per year (``<variable>_<year>``), as in the published
        ``<dataset>_wide.gpkg`` and ``.geojson`` files. A variable name returns one row per
        unit with that variable's years only (``<variable><year>``, without the underscore,
        as before version 0.9.1)
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
    if wide is True:
        return wide_table(dataset, scale=scale, years=years, variables=variables, geometry=geometry, ref=ref)
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
    df.attrs[SCALE_KEY] = res["geo:scale"]
    return df


def wide_columns(dataset: str, scale: str | None = None, ref: str | None = None) -> list[dict]:
    """The variable columns of a dataset's wide table, in order: each variable of the schema
    once per year of the resource, ``{"column": "<variable>_<year>", "variable", "year", "field"}``."""
    res = metadata.resource(dataset, scale, ref)
    years = metadata.resource_years(res)
    fields = [f for f in res["schema"]["fields"] if f.get("geo:role", "variable") == "variable"]
    return [{"column": f"{f['name']}_{y}", "variable": f["name"], "year": int(y), "field": f}
            for f in fields for y in years]


def wide_id_columns(scale: str, ref: str | None = None) -> list[str]:
    """The coarser scales whose IDs and names a wide table carries: every scale the units lie in,
    finest first, but a scale with a single unit (the country)."""
    return [a for a in ancestors(scale, ref) if len(_ids(a, ref)) > 1]


def wide_table(dataset: str, scale: str | None = None, years=None, variables=None, geometry: bool = False,
               ref: str | None = None):
    """A dataset as one row per unit and one column per variable and year.

    The table of the published ``data/<dataset>/<scale>/<dataset>_wide.gpkg`` and
    ``.geojson`` files, and of ``geo.load(dataset, wide=True)``.

    Parameters
    ----------
    dataset
        Dataset id
    scale
        Its scale (default: its native one)
    years, variables
        Keep only these years (an int, a list, or a ``(first, last)`` range) and variables
    geometry
        Attach the unit boundaries (``geo.boundaries``) and return a GeoDataFrame

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
        One row per unit of the scale, in ``geo_id`` order: ``geo_id``, ``name``, the ID and
        name of each coarser unit it lies in (e.g. ``province_id``, ``province``,
        ``department_id``, ``department``), the dataset's source keys (e.g. ``mun_id``), its
        ``area_km2``, then every variable once per year, ``<variable>_<year>``, in the order of
        the metadata. A variable gets a column for every year of the dataset, empty where it has
        no values (e.g. a variable measured in the final period only).
    """
    res = metadata.resource(dataset, scale, ref)
    sid = res["geo:scale"]
    long = pd.read_parquet(store.open_binary(res["geo:parquet"], ref))
    if long.duplicated(["geo_id", "year"]).any():
        raise ValueError(f"{dataset!r} has duplicate unit-years, so it has no wide table")
    columns = wide_columns(dataset, sid, ref)
    if years is not None:
        keep = set(_as_years(years))
        columns = [c for c in columns if c["year"] in keep]
        if not columns:
            raise ValueError(f"{dataset!r} has no rows for {years!r}")
    if variables is not None:
        wanted = [variables] if isinstance(variables, str) else list(variables)
        unknown = sorted(set(wanted) - {c["variable"] for c in columns})
        if unknown:
            raise ValueError(f"{dataset!r} has no variable(s) {unknown}; see geo.dictionary({dataset!r})")
        columns = [c for c in columns if c["variable"] in wanted]
    unit_table = units(sid, ref=ref).sort_values("geo_id").set_index("geo_id")
    out = pd.DataFrame(index=unit_table.index)
    out["name"] = unit_table["name"]
    for group in wide_id_columns(sid, ref):
        out[f"{group}_id"] = unit_table[f"{group}_id"]
        out[group] = out[f"{group}_id"].map(units(group, ref=ref).set_index("geo_id")["name"])
    keys = [f["name"] for f in res["schema"]["fields"] if f.get("geo:role") == "source_key"]
    if keys:
        out = out.join(long.drop_duplicates("geo_id").set_index("geo_id")[keys])
    out["area_km2"] = unit_table["area_km2"]
    values = {}
    for c in columns:
        rows = long.loc[long["year"] == c["year"], ["geo_id", c["variable"]]].set_index("geo_id")[c["variable"]]
        values[c["column"]] = rows.reindex(out.index)
    out = pd.concat([out, pd.DataFrame(values, index=out.index)], axis=1).rename_axis("geo_id").reset_index()
    for c in columns:   # keep each variable's type (an all-empty column of an integer stays nullable)
        kind = c["field"].get("type")
        if kind == "integer":
            out[c["column"]] = out[c["column"]].astype("Int64")
        elif kind == "number":
            out[c["column"]] = out[c["column"]].astype("float64")
    if geometry:
        shapes = boundaries(sid, ref=ref)[["geo_id", "geometry"]]
        out = gpd.GeoDataFrame(out.merge(shapes, on="geo_id", how="left"), geometry="geometry", crs=shapes.crs)
    out.attrs[SCALE_KEY] = sid
    return out


def wide_dictionary(dataset: str, scale: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """What each variable column of a dataset's wide table holds: ``column``, ``variable``,
    ``year``, ``label``, ``description``, ``unit``, ``source``, ``aggregation`` and ``reference``
    (the actual year behind a stored year, from ``geo:reference_years``; the year itself
    otherwise). The ``variables`` table of the published GeoPackage."""
    rows = []
    for c in wide_columns(dataset, scale, ref):
        f = c["field"]
        rows.append({"column": c["column"], "variable": c["variable"], "year": c["year"],
                     "label": f.get("title", ""), "description": f.get("description", ""),
                     "unit": f.get("geo:unit", ""), "source": f.get("geo:source", ""),
                     "aggregation": f.get("geo:aggregation", "none"),
                     "reference": str((f.get("geo:reference_years") or {}).get(str(c["year"]), c["year"]))})
    return pd.DataFrame(rows, columns=["column", "variable", "year", "label", "description", "unit", "source",
                                       "aggregation", "reference"])


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
    certain = scale is not None or bool(getattr(df, "attrs", {}).get(SCALE_KEY))
    if scale is None:
        found = table_scales(df, ref=ref, strict=False)
        if len(found) != 1:
            if groups:
                raise ValueError(f"Rows mix units from several scales ({sorted(found)}), so groups= cannot be added")
            # a stacked table (e.g. aggregate(to=[...])): each unit takes its own scale's name
            out = df.drop(columns="name", errors="ignore").copy()
            out["name"] = pd.NA
            for one in found:
                own = out["geo_id"].isin(_ids(one, ref)) & out["name"].isna()
                out.loc[own, "name"] = out.loc[own, "geo_id"].map(units(one, ref=ref).set_index("geo_id")["name"])
            first = ["geo_id", "name"] + (["year"] if "year" in out.columns else [])
            return out[first + [c for c in out.columns if c not in first]]
        scale = found[0]
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
    out = out[first + [c for c in out.columns if c not in first]]
    if certain:
        out.attrs[SCALE_KEY] = scale
    return out


def _ambiguous(maps) -> ValueError:
    return ValueError(f"These units are on more than one map ({', '.join(maps)}); pass map= (or scale=) "
                      "to say which one they belong to")


def table_scales(df: pd.DataFrame, scale: str | None = None, ref: str | None = None,
                 strict: bool = True) -> list[str]:
    """The scales (maps) of a table's units.

    In order: ``scale`` when given; the scale the table records (``load`` records it in
    ``df.attrs``); else the scales whose ID patterns the units match. Maps of the same
    units share their IDs, so units that match several are placed on the map that has every
    one of them, and an error asks for ``map=`` when more than one map has them all
    (``strict=False`` takes the first of them instead: enough for names, which maps of
    the same units share).
    """
    if scale is not None:
        return [check(scale, ref)]
    recorded = df.attrs.get(SCALE_KEY) if hasattr(df, "attrs") else None
    if recorded:
        return [recorded]
    groups: dict[tuple[str, ...], list[str]] = {}
    for gid in df["geo_id"].dropna().astype(str).unique():
        groups.setdefault(tuple(scales_of(gid, ref)), []).append(gid)
    found: list[str] = []
    for candidates, members in groups.items():
        if not candidates:
            raise ValueError(f"{members[0]!r} matches no scale; known scales: {', '.join(get_scale_ids(ref))}")
        if len(candidates) > 1:
            fit = [c for c in candidates if set(members) <= _ids(c, ref)]
            if len(fit) != 1 and (strict or not fit):
                raise _ambiguous(fit or candidates)
            candidates = tuple(fit)
        if candidates[0] not in found:
            found.append(candidates[0])
    return found


def table_scale(df: pd.DataFrame, scale: str | None = None, ref: str | None = None) -> str:
    """The one scale (map) of a table's units (see ``table_scales``); an error if they mix scales."""
    found = table_scales(df, scale, ref)
    if len(found) != 1:
        raise ValueError(f"Rows mix units from several scales ({', '.join(found) or 'none'})")
    return found[0]


def get_scale_ids(ref: str | None = None) -> list[str]:
    from .scales import scales as registry
    return list(registry(ref=ref))


@cache
def _ids(scale: str, ref: str | None) -> frozenset:
    """The geo IDs of a scale's published units."""
    u = _units(ref)
    return frozenset(u.loc[u["scale"] == scale, "geo_id"].astype(str))


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
    return (df if scale is None else df[df["scale"] == check(scale, ref)]).reset_index(drop=True).copy()


def boundaries(scale: str, ref: str | None = None) -> gpd.GeoDataFrame:
    """Unit polygons for a scale (CRS84), with ``geo_id`` and ``name``.

    Parameters
    ----------
    scale
        A scale id (see ``geo.scales()``)
    """
    out = gpd.read_parquet(store.open_binary(f"geo/boundaries/{check(scale, ref)}.parquet", ref))
    out.attrs[SCALE_KEY] = scale
    return out


def crosswalk(source: str, target: str, ref: str | None = None) -> pd.DataFrame:
    """Links between two scales: ``geo_id_from``, ``geo_id_to``, ``weight_area``.

    Parameters
    ----------
    source
        The finer scale, e.g. a municipal map
    target
        A coarser scale it nests in, e.g. ``"department"``

    Returns
    -------
    pandas.DataFrame
        ``weight_area`` is the share of the source unit's area inside the target unit
        (1.0 for nested scales). Crosswalks are published for every pair of active
        scales where one nests in the other, from finer to coarser.
    """
    return pd.read_csv(store.open_binary(f"geo/crosswalks/{check(source, ref)}__{check(target, ref)}.csv", ref))
