"""Generic boundaries from a polygon file of the finest scale, keyed by a project's own geo IDs.

``from_polygons`` takes any polygon layer of the finest scale (a national statistics office's or
an observatory's municipal map, geoBoundaries, ...) with a key column and a lookup ``key ->
geo_id``; ``from_geoboundaries`` is the same for geoBoundaries files (key ``shapeID``).

geoBoundaries (https://www.geoboundaries.org; Runfola et al. 2020, PLoS ONE 15(4): e0231866)
publishes the administrative units of every country, each with a ``shapeID``. Its gbOpen
release only holds boundaries whose sources allow redistribution; check each country's
``boundaryLicense`` in the API metadata (Bolivia's, from GeoBolivia, is public domain).

geoBoundaries has no hierarchical codes, so the geo IDs come from elsewhere (e.g. GADM's
numbering, ``gadm.gadm_units``) and a lookup ``shapeID -> geo_id`` of the finest scale, made
once by area overlap, attaches them (e.g. geo4bolivia's ``scripts/match_geoboundaries.py`` of
version 0.3; a map keyed by official codes, such as an INE code, needs only a code lookup, as
in geo4bolivia's ``scripts/match_municipalities343.py``).
``from_polygons`` then cleans the finest units as a coverage (small overlaps between neighbours
are given to one of them and shared edges made identical; shapely >= 2.2), simplifies them
(shared borders stay shared, so no slivers or gaps appear) and builds every coarser scale as the exact union of
its units, so the scales nest exactly and keep the holes the source leaves (lakes, salt
flats that belong to no unit).
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from ..scales import ancestors
from ..scales import scales as registry


def from_geoboundaries(path, lookup: pd.DataFrame, units: pd.DataFrame, key: str = "shapeID",
                       tolerance_m: float | None = 100) -> dict:
    """Boundary layers of every active scale from a geoBoundaries file of the finest scale
    (see ``from_polygons``; the key is geoBoundaries' ``shapeID``)."""
    return from_polygons(path, lookup, units, key=key, tolerance_m=tolerance_m)


def from_polygons(path, lookup: pd.DataFrame, units: pd.DataFrame, key: str,
                  tolerance_m: float | None = 100, scale: str | None = None) -> dict:
    """Boundary layers of a scale and of every active scale it nests in, from its polygon file.

    Parameters
    ----------
    path : the unedited polygon file (GeoJSON, shapefile, GeoPackage) or a GeoDataFrame read
        from one, with one polygon per unit of the finest scale and a ``key`` column
    lookup : one row per polygon, with ``key`` and ``geo_id`` (units of the finest scale)
    units : the units of every scale (``geo_id``, ``scale``, ``parent_id``), as passed to
        ``publish_geo``; ``parent_id`` chains each unit to the coarser scales
    tolerance_m : coverage simplification in metres of the project's equal-area CRS
        (``None`` keeps the source's vertices)
    scale : the scale of the polygons (default: the one scale whose units the lookup names;
        name it when two maps share their geo IDs)

    Returns ``{scale: GeoDataFrame}`` (``geo_id``, polygons in WGS 84) for ``publish_geo``.
    """
    import shapely

    from .. import project

    shapes = path.copy() if isinstance(path, gpd.GeoDataFrame) else gpd.read_file(path)
    ids = lookup.set_index(key)["geo_id"]
    if ids.index.duplicated().any() or ids.duplicated().any():
        raise ValueError("the lookup must match polygons and units one to one")
    shapes["geo_id"] = shapes[key].map(ids)
    unmatched = shapes.loc[shapes["geo_id"].isna(), key]
    if not unmatched.empty:
        raise ValueError(f"{len(unmatched)} polygons are not in the lookup, e.g. {list(unmatched[:3])}")
    if scale is None:
        found = units.loc[units["geo_id"].isin(ids), "scale"].unique()
        if len(found) != 1:
            raise ValueError(f"the lookup's geo_ids must all be units of one scale, got {list(found)}; name it (scale=)")
        scale = found[0]
    finest = scale
    coarser = [s for s in ancestors(finest) if s in registry(active_only=True)]
    units = units[units["scale"].isin([finest, *coarser])]
    missing = set(units.loc[units["scale"] == finest, "geo_id"]) - set(shapes["geo_id"])
    if missing:
        raise ValueError(f"{len(missing)} {finest} units have no polygon, e.g. {sorted(missing)[:3]}")

    if shapes["geo_id"].duplicated().any():
        raise ValueError("the polygon file has several rows for one unit; dissolve it first")
    shapes = shapes[["geo_id", "geometry"]].to_crs(project.equal_area_crs())
    shapes["geometry"] = shapes.make_valid()
    if hasattr(shapely, "coverage_clean"):   # shapely >= 2.2: remove overlaps and match shared edges first
        shapes["geometry"] = shapely.coverage_clean(shapes.geometry.to_numpy())
    if tolerance_m:
        shapes["geometry"] = shapely.coverage_simplify(shapes.geometry.to_numpy(), tolerance_m)
    shapes = shapes.sort_values("geo_id").reset_index(drop=True)

    # each finest unit's id at every coarser scale, following parent_id
    parent = units.set_index("geo_id")["parent_id"]
    scale_of = units.set_index("geo_id")["scale"]
    chain = {}
    for gid in shapes["geo_id"]:
        row, cur = {}, gid
        while isinstance(cur, str):
            row[scale_of[cur]] = cur
            cur = parent.get(cur)
        chain[gid] = row
    layers = {finest: shapes.to_crs("EPSG:4326")}
    for target in coarser:
        group = shapes["geo_id"].map(lambda g, s=target: chain[g].get(s))
        if group.isna().any():
            raise ValueError(f"some {finest} units do not lie in any {target} unit")
        merged = [(gid, shapely.union_all(part.geometry.to_numpy())) for gid, part in shapes.groupby(group)]
        layers[target] = gpd.GeoDataFrame(merged, columns=["geo_id", "geometry"], crs=shapes.crs).to_crs("EPSG:4326")
    return layers
