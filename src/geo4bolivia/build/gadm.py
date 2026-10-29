"""Generic geography from GADM: units and nested boundaries for any country.

GADM (https://gadm.org) publishes the administrative units of every country in
one format: columns ``GID_0, NAME_0, GID_1, NAME_1, GID_2, NAME_2, ...`` with
codes such as ``KHM.16.1_2``. ``from_gadm`` turns the finest level you need
into geo IDs that nest by prefix (``KH``, ``KH-16``, ``KH-16-01``) and dissolves
every coarser level from it, so the scales nest exactly. A project's geo builder
then only adds its own groupings or source keys and calls ``publish_geo``.

The IDs need only the codes: ``gadm_units`` builds the units from a lookup of GADM
codes and names, so a project can keep GADM's numbering while drawing its boundaries
from another source (see ``geoboundaries.py``).
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .. import project
from ..scales import get as get_scale
from .common import dissolve


def _indexes(gid: pd.Series) -> pd.DataFrame:
    """'KHM.16.1_2' -> columns {1: 16, 2: 1} (one per GADM level)."""
    parts = gid.str.replace(r"_\d+$", "", regex=True).str.split(".", expand=True).iloc[:, 1:].astype(int)
    return parts.set_axis(range(1, parts.shape[1] + 1), axis=1)


def gadm_ids(table: pd.DataFrame, levels: dict[int, str]) -> pd.DataFrame:
    """Add the geo ID of every level (``_id0`` ... ``_id<n>``) to a table of finest-level units.

    ``table`` needs the GADM codes ``GID_1`` ... ``GID_<n>`` of the finest level asked in ``levels``
    (geometry is not needed, so a lookup of codes works as well as a GADM file). Each scale's
    ``digits`` in scales.yaml (default 2) sets the zero-padding of its part of the ID.
    """
    cfg = project.config()["country"]
    finest = max(levels)
    idx = _indexes(table[f"GID_{finest}"])
    width = {lvl: get_scale(levels[lvl]).extra.get("digits", 2) for lvl in levels}
    for lvl in range(1, finest + 1):
        w = width.get(lvl, 2)
        if (idx[lvl] >= 10 ** w).any():
            raise ValueError(f"GADM level {lvl} index {idx[lvl].max()} needs more than {w} digits; "
                             f"set digits: in scales.yaml for {levels.get(lvl, f'level {lvl}')!r}")
    out = table.copy()
    out["_id0"] = cfg["iso2"]
    for lvl in range(1, finest + 1):
        w = width.get(lvl, 2)
        out[f"_id{lvl}"] = out[f"_id{lvl - 1}"] + "-" + idx[lvl].map(lambda v, w=w: f"{v:0{w}d}").to_numpy()
    return out


def gadm_units(table: pd.DataFrame, levels: dict[int, str]) -> pd.DataFrame:
    """The units of every scale (country first) from a table of finest-level units.

    ``table`` needs ``GID_k`` and ``NAME_k`` for every level ``k`` in ``levels``. Returns
    ``geo_id``, ``scale``, ``name``, ``parent_id``, ``gid`` (the GADM code) and ``name_gadm``.
    """
    cfg = project.config()["country"]
    table = gadm_ids(table, levels)
    rows = [pd.DataFrame([{"geo_id": cfg["iso2"], "scale": "country", "name": cfg["name"], "gid": cfg["iso3"]}])]
    previous = 0
    for lvl in sorted(levels):
        first = table.drop_duplicates(f"_id{lvl}")
        rows.append(pd.DataFrame({
            "geo_id": first[f"_id{lvl}"], "scale": levels[lvl], "name": first[f"NAME_{lvl}"],
            "parent_id": first[f"_id{previous}"], "gid": first[f"GID_{lvl}"], "name_gadm": first[f"NAME_{lvl}"]}))
        previous = lvl
    return pd.concat(rows, ignore_index=True)


def from_gadm(path, levels: dict[int, str], layer: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Units and boundary layers from a GADM file.

    Parameters
    ----------
    path : a GADM file at the finest level you need (GeoPackage, GeoJSON or
        shapefile), e.g. ``raw/boundaries/gadm41_KHM_2.json``, or a GeoDataFrame
        read from one (to drop units first, e.g. lakes)
    levels : GADM level -> scale id in geo/scales.yaml, e.g. ``{1: "province", 2: "district"}``.
        Level 0 is always the ``country`` scale.
    layer : GeoPackage layer, e.g. ``"ADM_ADM_2"``

    Each scale's ``digits`` in scales.yaml (default 2) sets the zero-padding of its
    part of the ID. Returns ``(units, layers)`` for ``publish_geo``; units carry
    ``gid`` (the GADM code) and ``name_gadm``.
    """
    if isinstance(path, gpd.GeoDataFrame):
        shapes = path.copy()
    else:
        shapes = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    finest = max(levels)
    gid_col = f"GID_{finest}"
    if gid_col not in shapes.columns:
        raise ValueError(f"{path} has no {gid_col}; download GADM at level {finest} or deeper")
    if shapes[gid_col].duplicated().any():           # deeper file: dissolve to the finest level asked
        keep = [c for c in shapes.columns if c[-2:] in {f"_{k}" for k in range(finest + 1)}]
        shapes = shapes.dissolve(by=gid_col, as_index=False)[keep + ["geometry"]]
    units = gadm_units(shapes, levels)
    shapes = gadm_ids(shapes, levels)
    layers = {"country": dissolve(shapes, "_id0")}
    for lvl in sorted(levels):
        layers[levels[lvl]] = dissolve(shapes, f"_id{lvl}") if lvl != finest else \
            shapes[[f"_id{lvl}", "geometry"]].rename(columns={f"_id{lvl}": "geo_id"})
    return units, layers
