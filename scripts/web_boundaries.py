"""Write small, public-domain boundaries for the website's interactive maps.

    uv run python scripts/web_boundaries.py [--tolerance METRES] [--digits N]

The browser maps cannot use the GADM boundaries in ``geo/boundaries/`` (GADM forbids
redistribution), so they draw geoBoundaries' gbOpen polygons (public domain) and key them by the
observatory's ``geo_id``. The GeoJSONs (~40 MB) are not committed: ``raw/boundaries/geoboundaries/``
keeps their API metadata (``*.meta.json``), whose ``gjDownloadURL`` pins a geoBoundaries commit, and the
script downloads the files there, unedited, when they are missing.

1. each geoBoundaries ADM3 polygon is matched to the GADM municipality it overlaps most, by
   area in the equal-area CRS of project.yaml; the match must be one-to-one over all units;
2. each ADM1 polygon is matched to a GADM department the same way, and every matched
   municipality must lie in the department its geo_id says (checked through ADM1);
3. the municipalities are simplified as a coverage (shared borders stay shared), snapped to a
   grid of ``--digits`` decimals in longitude/latitude, and written with ``geo_id`` and the
   harmonized ``name`` from geo/units.csv; the departments are the union of those simplified
   municipalities, so their outlines fall exactly on the municipal borders.

Outputs (compact GeoJSON, WGS84):

- ``site/data/municipality.geojson``: properties ``geo_id``, ``name``
- ``site/data/department.geojson``: properties ``geo_id``, ``name``
- ``site/data/country.geojson``: the outline (lakes and salt flats filled) for the hero globe

Diagnostics (overlap shares, low-overlap units, name differences to review) are printed.
Country codes, CRS and paths come from project.yaml and the repository layout.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from geo4bolivia import project

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/boundaries/geoboundaries"
OUT = ROOT / "site/data"
LOW_SHARE = 0.80


def norm(name: str) -> str:
    """Lower case, no accents, no punctuation, single spaces."""
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def match(gb: gpd.GeoDataFrame, gadm: gpd.GeoDataFrame, label: str) -> pd.DataFrame:
    """Best GADM geo_id for each geoBoundaries polygon (largest overlap), checked 1:1."""
    inter = gpd.overlay(gb[["gb_idx", "geometry"]], gadm[["geo_id", "geometry"]],
                        how="intersection", keep_geom_type=True)
    inter["overlap"] = inter.area
    best = inter.sort_values("overlap", ascending=False).drop_duplicates("gb_idx")
    best = best.set_index("gb_idx").reindex(gb["gb_idx"])
    missing = best["geo_id"].isna()
    assert not missing.any(), f"{label}: {missing.sum()} geoBoundaries polygons overlap no GADM unit"
    out = pd.DataFrame({
        "gb_idx": gb["gb_idx"].to_numpy(),
        "shapeName": gb["shapeName"].to_numpy(),
        "geo_id": best["geo_id"].to_numpy(),
        "overlap": best["overlap"].to_numpy(),
    })
    out["share_gb"] = out["overlap"] / gb.area.to_numpy()
    out["share_gadm"] = out["overlap"] / out["geo_id"].map(gadm.set_index("geo_id").area).to_numpy()
    dup = out["geo_id"][out["geo_id"].duplicated()]
    assert dup.empty, f"{label}: several geoBoundaries polygons match {sorted(dup.unique())}"
    assert len(out) == len(gadm) and set(out["geo_id"]) == set(gadm["geo_id"]), (
        f"{label}: {len(out)} geoBoundaries polygons vs {len(gadm)} GADM units, "
        f"unmatched GADM: {sorted(set(gadm['geo_id']) - set(out['geo_id']))}")
    return out


def report(m: pd.DataFrame, names: pd.Series, label: str) -> None:
    share = m[["share_gb", "share_gadm"]].min(axis=1)
    print(f"\n{label}: {len(m)} polygons matched 1:1")
    print(f"  overlap share: min {share.min():.3f} (of geoBoundaries area {m['share_gb'].min():.3f}, "
          f"of GADM area {m['share_gadm'].min():.3f}), median {share.median():.3f}")
    low = m[share < LOW_SHARE]
    print(f"  units below {LOW_SHARE:.0%} overlap: {len(low)}")
    for r in low.itertuples():
        print(f"    {r.geo_id:<14} {names[r.geo_id]!r:<32} geoBoundaries {r.shapeName!r:<32} "
              f"share of gB {r.share_gb:.3f}, of GADM {r.share_gadm:.3f}")
    diff = m[m["shapeName"].map(norm) != m["geo_id"].map(names).map(norm)]
    print(f"  name differences to review: {len(diff)}")
    for r in diff.itertuples():
        print(f"    {r.geo_id:<14} units.csv {names[r.geo_id]!r:<34} geoBoundaries {r.shapeName!r:<34} "
              f"share {min(r.share_gb, r.share_gadm):.3f}")


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

    iso3 = project.config()["country"]["iso3"]
    crs = project.equal_area_crs()
    units = pd.read_csv(ROOT / "geo/units.csv", dtype=str)
    names = units.set_index("geo_id")["name"]

    def gadm(scale: str) -> gpd.GeoDataFrame:
        return gpd.read_parquet(ROOT / f"geo/boundaries/{scale}.parquet")[["geo_id", "geometry"]].to_crs(crs)

    def gboundaries(level: str) -> gpd.GeoDataFrame:
        path = RAW / f"geoBoundaries-{iso3}-{level}.geojson"
        if not path.exists():
            url = json.loads((RAW / f"geoBoundaries-{iso3}-{level}.meta.json").read_text())["gjDownloadURL"]
            print(f"downloading {url}")
            urllib.request.urlretrieve(url, path)
        gdf = gpd.read_file(path).to_crs(crs)
        gdf["geometry"] = gdf.make_valid()
        return gdf.reset_index(names="gb_idx")

    mun_gadm, dep_gadm = gadm("municipality"), gadm("department")
    adm3, adm1 = gboundaries("ADM3"), gboundaries("ADM1")
    print(f"geoBoundaries: {len(adm3)} ADM3, {len(adm1)} ADM1; GADM: {len(mun_gadm)} municipalities, "
          f"{len(dep_gadm)} departments")

    mun = match(adm3, mun_gadm, "municipality")
    report(mun, names, "Municipalities (ADM3 -> GADM)")
    dep = match(adm1, dep_gadm, "department")
    report(dep, names, "Departments (ADM1 -> GADM)")

    # Nesting: the ADM1 polygon holding most of each ADM3 must be the matched municipality's department
    adm1_dep = adm1.assign(dep_id=adm1["gb_idx"].map(dep.set_index("gb_idx")["geo_id"]))
    within = gpd.overlay(adm3[["gb_idx", "geometry"]], adm1_dep[["dep_id", "geometry"]],
                         how="intersection", keep_geom_type=True)
    within = within.assign(a=within.area).sort_values("a", ascending=False).drop_duplicates("gb_idx")
    expected = mun.set_index("gb_idx")["geo_id"].map(units.set_index("geo_id")["department_id"])
    wrong = within.set_index("gb_idx")["dep_id"].reindex(expected.index) != expected
    print(f"\nNesting: {int(wrong.sum())} municipalities whose geoBoundaries ADM1 differs from their geo_id's department")
    for i in expected.index[wrong]:
        print(f"    {mun.set_index('gb_idx').at[i, 'geo_id']} {adm3.at[i, 'shapeName']!r}")
    assert not wrong.any(), "geoBoundaries ADM3 polygons do not nest in the matched departments"

    # Simplify as a coverage (shared edges simplified once), then snap to the output grid
    web = adm3[["gb_idx", "geometry"]].assign(geo_id=mun.set_index("gb_idx")["geo_id"].reindex(adm3["gb_idx"]).to_numpy())
    web["geometry"] = shapely.coverage_simplify(web.geometry.to_numpy(), args.tolerance)
    web = web.to_crs("EPSG:4326")
    web["geometry"] = shapely.set_precision(web.geometry.to_numpy(), 10 ** -args.digits)
    empty = web[web.is_empty]
    assert empty.empty, f"simplification emptied {sorted(empty['geo_id'])}"
    print(f"\nSimplified at {args.tolerance:g} m, {args.digits} decimals: "
          f"{int(shapely.get_num_coordinates(web.geometry.to_numpy()).sum())} vertices, "
          f"{int((~web.is_valid).sum())} invalid")

    web["name"] = web["geo_id"].map(names)
    web = web.sort_values("geo_id")[["geo_id", "name", "geometry"]]
    deps = (web.assign(geo_id=web["geo_id"].map(units.set_index("geo_id")["department_id"]))
            .dissolve("geo_id").reset_index())
    deps["geometry"] = shapely.set_precision(deps.geometry.to_numpy(), 10 ** -args.digits)
    deps["name"] = deps["geo_id"].map(names)
    to_geojson(web, OUT / "municipality.geojson", args.digits)
    to_geojson(deps[["geo_id", "name", "geometry"]], OUT / "department.geojson", args.digits)
    # The country's outline for the hero globe: the union of the departments without the lake holes
    iso2 = project.config()["country"]["iso2"]
    outline = shapely.union_all(deps.geometry.to_numpy())
    parts = getattr(outline, "geoms", [outline])
    outline = shapely.MultiPolygon([shapely.Polygon(p.exterior) for p in parts if p.area > 1e-4])
    country = gpd.GeoDataFrame({"geo_id": [iso2], "name": [names.get(iso2, iso2)]}, geometry=[outline], crs="EPSG:4326")
    to_geojson(country, OUT / "country.geojson", args.digits)


if __name__ == "__main__":
    main()
