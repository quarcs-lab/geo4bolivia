"""Build your own datasets: link, combine, extract from rasters, check and save.

These functions work anywhere, including Google Colab without a clone of the
repository. A typical workflow::

    import geo4bolivia as geo
    mine = geo.link(my_table, scale="province", on="Province")   # names/codes -> geo_id
    geo.check(mine, scale="province")                            # same rules as the published data
    both = geo.combine(["env", "hdi"], scale="gdl", extra=[mine])  # one panel, one scale
    lights = geo.zonal("viirs_2020.tif", scale="district", year=2020, name="ntl")
    geo.save(both, "my_panel", scale="gdl", variables={...})     # CSV + Parquet + datapackage
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from . import io, metadata, project, store
from .aggregate import aggregate
from .scales import ancestors, get as get_scale, scale_of
from .scales import scales as registry


# --- link: attach geo_id to any table --------------------------------------------------

def normalize(text) -> str:
    """Comparable form of a unit name: no accents, case, spaces or punctuation."""
    if pd.isna(text):
        return ""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _candidates(units: pd.DataFrame) -> list[str]:
    skip = {"scale", "parent_id", "area_km2"} | {c for c in units.columns if c.endswith("_id") and c != "geo_id"}
    return [c for c in units.columns if c not in skip and units[c].notna().any()]


def link(df: pd.DataFrame, scale: str, on: str, key: str = "auto", errors: str = "raise",
         ref: str | None = None) -> pd.DataFrame:
    """Attach ``geo_id`` to a table that identifies units by name or by a source code.

    Parameters
    ----------
    df : your table (one row per unit, or per unit and year)
    scale : scale of your units, e.g. ``"province"`` (see ``geo.scales()``)
    on : the column of ``df`` that identifies the unit
    key : the column of ``geo.units(scale)`` to match against: ``"name"``, a
        source code such as ``"gid"`` (GADM), ``"shapeISO"`` or ``"GDLcode"``, or
        ``"auto"``: the column matching most values, with the others filling the
        gaps (so mixed spellings from different sources still link). Matching ignores
        accents, case, spaces and punctuation ("BântéayMéanchey" = "Banteay Meanchey").
    errors : ``"raise"`` (default), ``"warn"`` or ``"ignore"`` for values that match no unit

    Returns a copy of ``df`` with ``geo_id`` as its first column.
    """
    units = io.units(scale, ref=ref)
    if units.empty:
        raise ValueError(f"No units at scale {scale!r}; active scales: {', '.join(registry(active_only=True))}")
    values = df[on].map(normalize)
    columns = _candidates(units) if key == "auto" else [key]
    ranked = []
    for col in columns:
        if col not in units.columns:
            raise KeyError(f"geo.units({scale!r}) has no column {col!r}; try one of {_candidates(units)}")
        lookup = units.dropna(subset=[col])
        mapping = dict(zip(lookup[col].map(normalize), lookup["geo_id"]))
        mapping.pop("", None)
        ranked.append((int(values.isin(mapping).sum()), col, mapping))
    ranked.sort(key=lambda r: -r[0])
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0] > 0:
        a, b = ranked[0], ranked[1]
        shared = values[values.isin(a[2]) & values.isin(b[2])]
        if (shared.map(a[2]) != shared.map(b[2])).any():
            raise ValueError(f"{on!r} matches both {a[1]!r} and {b[1]!r} with different units; pass key=...")
    best = ranked[0][1]
    ids = pd.Series(pd.NA, index=df.index, dtype="object")
    for hits, _, mapping in ranked:      # best column first, the others fill the gaps
        if hits:
            ids = ids.fillna(values.map(mapping))
    out = df.copy()
    out.insert(0, "geo_id", ids)
    missing = sorted(set(df.loc[out["geo_id"].isna(), on].dropna().astype(str)))
    if missing and errors != "ignore":
        known = units[best].dropna().astype(str).tolist()
        hints = [f"{m!r} (did you mean {difflib.get_close_matches(m, known, n=1, cutoff=0.6)[0]!r}?)"
                 if difflib.get_close_matches(m, known, n=1, cutoff=0.6) else repr(m) for m in missing[:10]]
        message = (f"{len(missing)} value(s) of {on!r} match no {scale} {best!r}: {', '.join(hints)}. "
                   f"Fix them, e.g. df[{on!r}] = df[{on!r}].replace({{...}}), or pass errors='warn'.")
        if errors == "raise":
            raise ValueError(message)
        warnings.warn(message, stacklevel=2)
    return out


# --- check: the same rules the published datasets follow -------------------------------

def check(df: pd.DataFrame, scale: str | None = None, time: str | None = "year",
          ref: str | None = None) -> list[str]:
    """Problems that would stop ``df`` from being a valid panel at ``scale`` (empty list = OK).

    Checks: a ``geo_id`` column, ids known at the scale, one row per unit (and
    year) and integer years.
    """
    problems = []
    if "geo_id" not in df.columns:
        return ["no geo_id column: use geo.link() first"]
    ids = df["geo_id"].dropna()
    if df["geo_id"].isna().any():
        problems.append(f"{df['geo_id'].isna().sum()} rows without geo_id")
    if scale is None:
        found, unrecognised = set(), []
        for i in ids.drop_duplicates():
            try:
                found.add(scale_of(i))
            except ValueError:
                unrecognised.append(i)
        if unrecognised:
            problems.append(f"geo_id matching no scale's id pattern: {unrecognised[:5]}")
        if not found:
            return problems
        if len(found) != 1:
            return problems + [f"ids from several scales: {sorted(found)}"]
        scale = found.pop()
    unknown = sorted(set(ids) - set(io.units(scale, ref=ref)["geo_id"]))
    if unknown:
        problems.append(f"geo_id not found at scale {scale!r}: {unknown[:5]}")
    keys = ["geo_id"] + ([time] if time and time in df.columns else [])
    if df.duplicated(keys).any():
        problems.append(f"{df.duplicated(keys).sum()} duplicate rows for {keys}")
    if time and time in df.columns and not pd.api.types.is_integer_dtype(df[time]):
        problems.append(f"{time!r} is not an integer column")
    if time and time not in df.columns:
        problems.append(f"no {time!r} column (pass time=None for a cross-section)")
    return problems


# --- combine: several datasets on one scale ---------------------------------------------

def combine(datasets, scale: str, years=None, extra=(), rules: dict | None = None,
            ref: str | None = None) -> pd.DataFrame:
    """Merge datasets into one panel at ``scale``, aggregating finer ones up.

    Parameters
    ----------
    datasets : dataset ids, or ``{dataset: [variables]}`` to pick variables
    scale : target scale; each dataset must be published at it or nest in it
    years : as in ``geo.load``
    extra : your own panels (with ``geo_id`` and ``year``) at ``scale``
    rules : aggregation rules overriding the metadata, ``{variable: rule}``

    Variables without an aggregation rule (``none``) are dropped, with a warning,
    when a dataset has to be aggregated. Clashing column names get the dataset
    id as a prefix (``hdi_POP``).
    """
    picks = datasets if isinstance(datasets, dict) else {d: None for d in datasets}
    frames: list[tuple[str, pd.DataFrame]] = []
    for ds, variables in picks.items():
        native = metadata.resource(ds)["geo:scale"]
        published = [r["geo:scale"] for r in metadata.package(ds)["resources"]]
        at = scale if scale in published else native
        df = io.load(ds, scale=at, years=years, variables=variables, ref=ref)
        if at != scale:
            if scale not in ancestors(at):
                raise ValueError(f"{ds!r} is published at {at!r}, which does not nest in {scale!r}. "
                                 f"Use geo.overlay() to move it, then pass the result in extra=.")
            have = dict(metadata.aggregation_rules(ds, at), **(rules or {}))
            candidates = [v for v in metadata.variables(ds, at) if v in df.columns]
            df = df[["geo_id", "year", *candidates]]
            keep = [v for v in candidates if have.get(v, "none") != "none"]
            dropped = [v for v in candidates if v not in keep]
            if dropped:
                warnings.warn(f"{ds}: no aggregation rule for {dropped}; dropped. Pass rules= to keep them.",
                              stacklevel=2)
            df = aggregate(df, to=scale, dataset=ds, rules=rules, variables=keep).drop(columns="n_units")
        frames.append((ds, df))
    frames += [(f"extra{i}", df) for i, df in enumerate(extra, 1)]
    seen: dict[str, int] = {}
    for _, df in frames:
        for c in df.columns:
            seen[c] = seen.get(c, 0) + 1
    out = None
    for name, df in frames:
        df = df.rename(columns={c: f"{name}_{c}" for c in df.columns
                                if seen[c] > 1 and c not in ("geo_id", "year")})
        on = ["geo_id", "year"] if "year" in df.columns and (out is None or "year" in out.columns) else ["geo_id"]
        out = df if out is None else out.merge(df, on=on, how="outer")
    return out.sort_values([c for c in ("geo_id", "year") if c in out.columns]).reset_index(drop=True)


# --- zonal: summarise a raster over units -----------------------------------------------

ZONAL_STATS = ("sum", "mean", "min", "max", "median", "count")


def zonal(raster, scale, stats=("sum", "mean"), name: str = "value", year: int | None = None,
          band: int = 1, all_touched: bool = False, ref: str | None = None) -> pd.DataFrame:
    """Summarise a raster (GeoTIFF path or URL) over the units of a scale.

    Parameters
    ----------
    raster : path or URL of a raster, or ``{year: path}`` for an annual series
    scale : a scale id, or a GeoDataFrame with ``geo_id`` and polygons
    stats : any of ``sum``, ``mean``, ``min``, ``max``, ``median``, ``count``
    name : prefix of the output columns (``name_sum``, ``name_mean``, ...)
    year : year to record when ``raster`` is a single file
    all_touched : count every pixel a unit touches (default: pixel centres inside)

    Needs ``rasterio``: in Colab, ``!pip install -q "geo4bolivia[raster]"``.
    Pixels are not split at unit edges, so use a fine raster, or
    ``all_touched=True`` for very small units. Nodata pixels are ignored.
    """
    try:
        import rasterio
        from rasterio.mask import mask as rio_mask
    except ImportError as exc:  # pragma: no cover
        raise ImportError(f'zonal() needs rasterio: !pip install -q "{project.PACKAGE}[raster]"') from exc
    bad = [s for s in stats if s not in ZONAL_STATS]
    if bad:
        raise ValueError(f"Unknown stats {bad}; use {ZONAL_STATS}")
    if isinstance(raster, dict):
        return pd.concat([zonal(path, scale, stats, name, y, band, all_touched, ref) for y, path in raster.items()],
                         ignore_index=True)
    shapes = io.boundaries(scale, ref=ref) if isinstance(scale, str) else scale
    rows = []
    with rasterio.open(raster) as src:
        shapes = shapes.to_crs(src.crs) if src.crs else shapes
        for gid, geom in zip(shapes["geo_id"], shapes.geometry):
            row = {"geo_id": gid}
            try:
                data, _ = rio_mask(src, [geom], crop=True, filled=False, indexes=band, all_touched=all_touched)
                values = data.compressed().astype("float64")
                values = values[np.isfinite(values)]
            except ValueError:            # unit outside the raster
                values = np.array([])
            for s in stats:
                if s == "count":
                    row[f"{name}_count"] = int(values.size)
                else:
                    row[f"{name}_{s}"] = float(getattr(np, s)(values)) if values.size else np.nan
            rows.append(row)
    out = pd.DataFrame(rows)
    if year is not None:
        out.insert(1, "year", int(year))
    return out


# --- save: write a dataset in the repository's format -----------------------------------

_TYPES = {"i": "integer", "u": "integer", "f": "number", "b": "boolean"}


def save(df: pd.DataFrame, name: str, scale: str, directory=".", title: str | None = None,
         description: str = "", variables: dict | None = None, sources=(), citation: str | None = None,
         license: str = "CC-BY-4.0") -> dict:
    """Save a panel exactly like the published datasets, ready to share or contribute.

    Writes ``<directory>/data/<scale>/<name>.csv`` and ``.parquet`` and
    ``<directory>/metadata/<name>.datapackage.json`` (Frictionless). Describe each
    variable in ``variables``: ``{"pop": {"description": "Population",
    "unit": "people", "aggregation": "sum", "source": "WorldPop"}}``. The
    aggregation rule (``sum``, ``mean``, ``weighted_mean:<field>``, ``none``, ...)
    tells ``geo.aggregate()`` how to move the variable to coarser scales.

    Returns the datapackage as a dict.
    """
    problems = check(df, scale)
    if problems:
        raise ValueError("Fix these first:\n- " + "\n- ".join(problems))
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
        raise ValueError("name must be lowercase letters, digits, '-' or '_' (it becomes a file name)")
    variables = variables or {}
    keys = ["geo_id", "year"] if "year" in df.columns else ["geo_id"]
    df = df.drop(columns="geometry", errors="ignore")
    df = df[keys + [c for c in df.columns if c not in keys]].sort_values(keys).reset_index(drop=True)
    sc = get_scale(scale)
    fields = [{"name": "geo_id", "type": "string", "description": f"{sc.label} ID", "geo:role": "id",
               "constraints": {"required": True, "pattern": sc.id_pattern}}]
    if "year" in df.columns:
        fields.append({"name": "year", "type": "integer", "description": "Year", "geo:role": "time",
                       "constraints": {"required": True}})
    for col in df.columns[len(keys):]:
        info = variables.get(col, {})
        fields.append({"name": col, "type": _TYPES.get(df[col].dtype.kind, "string"),
                       "description": info.get("description", ""), "geo:unit": info.get("unit", ""),
                       "geo:aggregation": info.get("aggregation", "none"), "geo:source": info.get("source", "")})
    root = Path(directory)
    csv_rel, pq_rel = f"data/{scale}/{name}.csv", f"data/{scale}/{name}.parquet"
    (root / csv_rel).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(root / csv_rel, index=False)
    df.to_parquet(root / pq_rel, index=False)
    years = [int(df["year"].min()), int(df["year"].max())] if "year" in df.columns else None
    package = {
        "name": name, "title": title or name, "description": description, "version": "1.0.0",
        "licenses": [{"name": license}],
        "sources": [s if isinstance(s, dict) else {"title": s} for s in sources],
        "geo:categories": [], "geo:notes": [],
        "resources": [{
            "name": f"{name}-{scale}", "path": store.raw_url(csv_rel, project.config().get("default_ref", "main")),
            "format": "csv", "mediatype": "text/csv",
            "encoding": "utf-8", "geo:scale": scale, "geo:period": years,
            "geo:path": csv_rel, "geo:parquet": pq_rel,
            "schema": {"primaryKey": keys, "fields": fields},
        }],
    }
    if citation:
        package["geo:citation"] = citation
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / f"metadata/{name}.datapackage.json").write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {root / csv_rel}, {root / pq_rel} and {root / f'metadata/{name}.datapackage.json'}")
    return package
