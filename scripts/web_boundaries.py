"""Write small boundaries for the website's maps from the package's boundaries.

    uv run python scripts/web_boundaries.py [--tolerance METRES] [--digits N]

``geo/boundaries/`` holds geoBoundaries' public-domain polygons (``build/geo.py``), lightly
simplified for analysis. The browser needs far fewer vertices, so the municipalities are
simplified again as a coverage (shared borders stay shared, so no slivers or gaps appear),
snapped to a grid of ``--digits`` decimals in longitude/latitude, and written with ``geo_id``
and ``name``. The departments are the union of those simplified municipalities, so their
outlines fall exactly on the municipal borders; the salt flats and lakes outside every
municipality stay holes.

Outputs (compact GeoJSON, WGS84), read by site/build.mjs and scripts/indicator_map.py:

- ``site/data/municipality.geojson``: properties ``geo_id``, ``name``
- ``site/data/department.geojson``: properties ``geo_id``, ``name``
- ``site/data/country.geojson``: the outline (lakes and salt flats filled) for the hero globe

The CRS comes from project.yaml; paths from the repository layout.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from geo4bolivia import project

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/data"


def to_geojson(gdf: gpd.GeoDataFrame, path: Path, digits: int) -> None:
    features = [{"type": "Feature", "properties": {"geo_id": r.geo_id, "name": r.name},
                 "geometry": shapely.geometry.mapping(r.geometry)}
                for r in gdf.itertuples()]
    text = json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, separators=(",", ":"))
    # mapping() writes floats in full; the grid already holds them to `digits` decimals
    text = re.sub(r"-?\d+\.\d{%d,}" % (digits + 1), lambda x: f"{float(x.group()):.{digits}f}", text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}: {len(features)} features, {path.stat().st_size / 1024:.0f} KB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tolerance", type=float, default=800, help="simplification tolerance in metres")
    ap.add_argument("--digits", type=int, default=4, help="decimals of longitude/latitude")
    args = ap.parse_args()

    units = pd.read_csv(ROOT / "geo/units.csv", dtype=str).set_index("geo_id")
    web = gpd.read_parquet(ROOT / "geo/boundaries/municipality.parquet")[["geo_id", "geometry"]]
    web = web.to_crs(project.equal_area_crs())
    web["geometry"] = shapely.coverage_simplify(web.geometry.to_numpy(), args.tolerance)
    web = web.to_crs("EPSG:4326")
    web["geometry"] = shapely.set_precision(web.geometry.to_numpy(), 10 ** -args.digits)
    empty = web[web.is_empty]
    assert empty.empty, f"simplification emptied {sorted(empty['geo_id'])}"
    print(f"Simplified at {args.tolerance:g} m, {args.digits} decimals: "
          f"{int(shapely.get_num_coordinates(web.geometry.to_numpy()).sum())} vertices, "
          f"{int((~web.is_valid).sum())} invalid")

    web["name"] = web["geo_id"].map(units["name"])
    web = web.sort_values("geo_id")[["geo_id", "name", "geometry"]]
    deps = web.assign(geo_id=web["geo_id"].map(units["department_id"])).dissolve("geo_id").reset_index()
    deps["geometry"] = shapely.set_precision(deps.geometry.to_numpy(), 10 ** -args.digits)
    deps["name"] = deps["geo_id"].map(units["name"])
    to_geojson(web, OUT / "municipality.geojson", args.digits)
    to_geojson(deps[["geo_id", "name", "geometry"]], OUT / "department.geojson", args.digits)
    # The country's outline for the hero globe: the union of the departments without the lake holes
    iso2 = project.config()["country"]["iso2"]
    outline = shapely.union_all(deps.geometry.to_numpy())
    parts = getattr(outline, "geoms", [outline])
    outline = shapely.MultiPolygon([shapely.Polygon(p.exterior) for p in parts if p.area > 1e-4])
    country = gpd.GeoDataFrame({"geo_id": [iso2], "name": [units["name"].get(iso2, iso2)]},
                               geometry=[outline], crs="EPSG:4326")
    to_geojson(country, OUT / "country.geojson", args.digits)


if __name__ == "__main__":
    main()
