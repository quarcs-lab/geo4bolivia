"""Generic boundaries from geoBoundaries, keyed by a project's own geo IDs.

geoBoundaries (https://www.geoboundaries.org; Runfola et al. 2020, PLoS ONE 15(4): e0231866)
publishes the administrative units of every country, each with a ``shapeID``. Its gbOpen
release only holds boundaries whose sources allow redistribution; check each country's
``boundaryLicense`` in the API metadata (Bolivia's, from GeoBolivia, is public domain).

geoBoundaries has no hierarchical codes, so the geo IDs come from elsewhere (e.g. GADM's
numbering, ``gadm.gadm_units``) and a lookup ``shapeID -> geo_id`` of the finest scale, made
once by area overlap (see a project's ``scripts/match_geoboundaries.py``), attaches them.
``from_geoboundaries`` then simplifies the finest units as a coverage (shared borders stay
shared, so no slivers or gaps appear) and builds every coarser scale as the exact union of
its units, so the scales nest exactly and keep the holes the source leaves (lakes, salt
flats that belong to no unit).
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from ..scales import scales as registry


def from_geoboundaries(path, lookup: pd.DataFrame, units: pd.DataFrame, key: str = "shapeID",
                       tolerance_m: float | None = 100) -> dict:
    """Boundary layers of every active scale from a geoBoundaries file of the finest scale.

    Parameters
    ----------
    path : the unedited geoBoundaries GeoJSON (e.g. ``raw/boundaries/geoboundaries/
        geoBoundaries-BOL-ADM3.geojson``) or a GeoDataFrame read from one
    lookup : one row per polygon, with ``key`` and ``geo_id`` (units of the finest scale)
    units : the units of every scale (``geo_id``, ``scale``, ``parent_id``), as passed to
        ``publish_geo``; ``parent_id`` chains each unit to the coarser scales
    tolerance_m : coverage simplification in metres of the project's equal-area CRS
        (``None`` keeps the source's vertices)

    Returns ``{scale: GeoDataFrame}`` (``geo_id``, polygons in WGS 84) for ``publish_geo``.
    """
    import shapely

    from .. import project

    shapes = path.copy() if isinstance(path, gpd.GeoDataFrame) else gpd.read_file(path)
    ids = lookup.set_index(key)["geo_id"]
    if ids.index.duplicated().any() or ids.duplicated().any():
        raise ValueError("the geoBoundaries lookup must match polygons and units one to one")
    shapes["geo_id"] = shapes[key].map(ids)
    unmatched = shapes.loc[shapes["geo_id"].isna(), key]
    if not unmatched.empty:
        raise ValueError(f"{len(unmatched)} geoBoundaries polygons are not in the lookup, e.g. {list(unmatched[:3])}")
    finest = units.loc[units["geo_id"].isin(ids), "scale"].unique()
    if len(finest) != 1:
        raise ValueError(f"the lookup's geo_ids must all be units of one scale, got {list(finest)}")
    finest = finest[0]
    missing = set(units.loc[units["scale"] == finest, "geo_id"]) - set(shapes["geo_id"])
    if missing:
        raise ValueError(f"{len(missing)} {finest} units have no geoBoundaries polygon, e.g. {sorted(missing)[:3]}")

    shapes = shapes[["geo_id", "geometry"]].to_crs(project.equal_area_crs())
    shapes["geometry"] = shapes.make_valid()
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
    for scale in registry(active_only=True):
        if scale == finest:
            continue
        group = shapes["geo_id"].map(lambda g, s=scale: chain[g].get(s))
        if group.isna().any():
            raise ValueError(f"some {finest} units do not lie in any {scale} unit")
        merged = [(gid, shapely.union_all(part.geometry.to_numpy())) for gid, part in shapes.groupby(group)]
        layers[scale] = gpd.GeoDataFrame(merged, columns=["geo_id", "geometry"], crs=shapes.crs).to_crs("EPSG:4326")
    return layers
