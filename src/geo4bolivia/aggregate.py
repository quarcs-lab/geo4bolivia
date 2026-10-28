"""Moving data between spatial scales.

- ``aggregate`` goes *up* a nested hierarchy (e.g. district -> province ->
  country) using the published crosswalks and per-variable rules.
- ``overlay`` moves data between scales that do not nest (grids, custom zones,
  historical boundaries) by area-weighted interpolation.
"""

from __future__ import annotations

import warnings

import geopandas as gpd
import pandas as pd

from . import io, metadata, project
from .scales import ancestors, scale_of

# Equal-area projection from project.yaml, so areas and overlay weights are exact
EQUAL_AREA_CRS = project.equal_area_crs()
RULES = ("sum", "mean", "min", "max", "weighted_mean:<field>", "none")


def _scale_of(df: pd.DataFrame) -> str:
    found = {scale_of(i) for i in df["geo_id"].drop_duplicates()}
    if len(found) != 1:
        raise ValueError(f"Rows mix units from several scales: {sorted(found)}")
    return found.pop()


def _resolve_rules(variables, dataset, rules):
    resolved = dict(metadata.aggregation_rules(dataset)) if dataset else {}
    resolved.update(rules or {})
    missing = [v for v in variables if resolved.get(v, "none") == "none"]
    if missing:
        raise ValueError(
            f"No aggregation rule for: {', '.join(missing)}. Pass rules={{'{missing[0]}': 'mean'}} "
            f"(one of {', '.join(RULES)}) or leave these variables out with variables=[...]."
        )
    for v in variables:
        r = resolved[v]
        if not (r in ("sum", "mean", "min", "max") or r.startswith("weighted_mean:")):
            raise ValueError(f"Unknown rule {r!r} for {v!r}; use one of {', '.join(RULES)}")
    return {v: resolved[v] for v in variables}


def aggregate(df: pd.DataFrame, to: str, dataset: str | None = None, rules: dict | None = None,
              variables=None, weights: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate a panel up to a coarser, nested scale.

    Parameters
    ----------
    df : panel with ``geo_id``, optionally ``year``, and variable columns
    to : target scale id (must contain the source scale, see ``geo.ancestors``)
    dataset : take each variable's ``geo:aggregation`` rule from this dataset's metadata
    rules : explicit rules that override the metadata, e.g. ``{"y": "weighted_mean:pop"}``
    variables : variables to aggregate (default: every numeric column except ids and year,
        leaving out, with a warning, those without a rule)
    weights : extra columns to join on ``geo_id`` (and ``year`` if present) for
        ``weighted_mean`` rules whose weight is not already in ``df``

    Returns one row per target unit (and year) with an ``n_units`` column: the
    number of source units that contributed.
    """
    source = _scale_of(df)
    if to == source:
        return df.copy()
    if to not in ancestors(source):
        raise ValueError(f"{source!r} units do not nest in {to!r}; use geo.overlay() instead.")

    keys = ["geo_id", "year"] if "year" in df.columns else ["geo_id"]
    if variables is None:
        # every numeric column except ids; variables without a rule are skipped with a warning
        variables = [c for c in df.columns if c not in keys and c != "geometry"
                     and pd.api.types.is_numeric_dtype(df[c])]
        known = dict(metadata.aggregation_rules(dataset)) if dataset else {}
        known.update(rules or {})
        if dataset or rules:
            skipped = [v for v in variables if known.get(v, "none") == "none"]
            if skipped and len(skipped) < len(variables):
                warnings.warn(f"No aggregation rule for {skipped}; left out. Pass rules= to include them.",
                              stacklevel=2)
                variables = [v for v in variables if v not in skipped]
    elif isinstance(variables, str):
        variables = [variables]
    rule = _resolve_rules(variables, dataset, rules)

    data = df.drop(columns="geometry", errors="ignore")
    if weights is not None:
        on = [k for k in keys if k in weights.columns]
        data = data.merge(weights, on=on, how="left")
    xw = io.crosswalk(source, to)[["geo_id_from", "geo_id_to"]]
    data = data.merge(xw, left_on="geo_id", right_on="geo_id_from", how="left")
    if data["geo_id_to"].isna().any():
        bad = data.loc[data["geo_id_to"].isna(), "geo_id"].unique()[:5]
        raise ValueError(f"Units missing from the {source}->{to} crosswalk: {list(bad)}")

    group = ["geo_id_to"] + keys[1:]
    out = data.groupby(group)["geo_id"].nunique().rename("n_units").to_frame()
    for var, r in rule.items():
        g = data.groupby(group)
        if r == "sum":
            out[var] = g[var].sum(min_count=1)
        elif r in ("mean", "min", "max"):
            out[var] = getattr(g[var], r)()
        else:
            w = r.split(":", 1)[1]
            if w not in data.columns:
                raise ValueError(f"Weight {w!r} for {var!r} is not in the data; pass it via weights=")
            ok = data[var].notna() & data[w].notna()
            num = (data[var] * data[w]).where(ok).groupby([data[c] for c in group]).sum(min_count=1)
            den = data[w].where(ok).groupby([data[c] for c in group]).sum(min_count=1)
            out[var] = num / den
    out = out.reset_index().rename(columns={"geo_id_to": "geo_id"})
    return out[["geo_id", *keys[1:], *rule, "n_units"]]


def _as_target(target, id_col: str) -> gpd.GeoDataFrame:
    if isinstance(target, str):
        return io.boundaries(target)[["geo_id", "geometry"]]
    if id_col not in target.columns:
        raise ValueError(f"Target GeoDataFrame needs an id column {id_col!r}")
    return target[[id_col, "geometry"]].rename(columns={id_col: "geo_id"})


def overlay_weights(source, target, id_col: str = "geo_id") -> pd.DataFrame:
    """Area of every source-target intersection, in an equal-area projection.

    ``source`` and ``target`` are scale ids or GeoDataFrames with an id column.
    Returns ``geo_id_from``, ``geo_id_to``, ``area_km2``, ``share_of_from`` (the
    part of the source unit inside the target) and ``share_of_to``.
    """
    src = _as_target(source, id_col).to_crs(EQUAL_AREA_CRS)
    tgt = _as_target(target, id_col).to_crs(EQUAL_AREA_CRS)
    src["area_from"] = src.area
    tgt["area_to"] = tgt.area
    pieces = gpd.overlay(src.rename(columns={"geo_id": "geo_id_from"}),
                         tgt.rename(columns={"geo_id": "geo_id_to"}), how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.area
    pieces = pieces.groupby(["geo_id_from", "geo_id_to"], as_index=False).agg(
        area=("area", "sum"), area_from=("area_from", "first"), area_to=("area_to", "first"))
    pieces["share_of_from"] = pieces["area"] / pieces["area_from"]
    pieces["share_of_to"] = pieces["area"] / pieces["area_to"]
    pieces["area_km2"] = pieces["area"] / 1e6
    return pieces[["geo_id_from", "geo_id_to", "area_km2", "share_of_from", "share_of_to"]]


def overlay(df: pd.DataFrame, target, extensive=(), intensive=(), source=None,
            id_col: str = "geo_id") -> pd.DataFrame:
    """Area-weighted interpolation of a panel onto non-nested units.

    Parameters
    ----------
    df : panel with ``geo_id``, optionally ``year``, and the variables
    target : a scale id or a GeoDataFrame with ``id_col`` and polygons (e.g. a grid)
    extensive : counts/totals (population, GDP): split by the share of each
        source unit's area falling in the target, then summed
    intensive : rates/averages (GDP per capita, HDI): area-weighted mean over
        the parts of source units inside the target
    source : the source scale or GeoDataFrame (default: inferred from ``geo_id``)

    Assumes values are spread uniformly within each source unit. Returns one row
    per target unit (and year), with ``geo_id`` holding the target ids.
    """
    extensive, intensive = list(extensive), list(intensive)
    if not extensive and not intensive:
        raise ValueError("Name the variables to move: extensive=[...] and/or intensive=[...]")
    w = overlay_weights(source if source is not None else _scale_of(df), target, id_col)
    keys = ["year"] if "year" in df.columns else []
    data = df.drop(columns="geometry", errors="ignore").merge(
        w, left_on="geo_id", right_on="geo_id_from", how="inner")
    group = ["geo_id_to", *keys]
    parts = []
    for var in extensive:
        parts.append((data[var] * data["share_of_from"]).groupby([data[c] for c in group]).sum(min_count=1).rename(var))
    for var in intensive:
        ok = data[var].notna()
        num = (data[var] * data["area_km2"]).where(ok).groupby([data[c] for c in group]).sum(min_count=1)
        den = data["area_km2"].where(ok).groupby([data[c] for c in group]).sum(min_count=1)
        parts.append((num / den).rename(var))
    out = pd.concat(parts, axis=1).reset_index().rename(columns={"geo_id_to": "geo_id"})
    return out
