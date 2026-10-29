"""Match geoBoundaries' municipalities to the observatory's geo IDs (run once; its output is a raw lookup).

    uv run python scripts/match_geoboundaries.py

The geo IDs (BO-DD-PP-MM) follow the GADM 4.1 numbering, and until version 0.2 the boundaries in
``geo/boundaries/`` were GADM's. Since then they are geoBoundaries' gbOpen polygons (public domain,
from GeoBolivia), which ``build/geo.py`` keys by this script's lookup:

1. each geoBoundaries ADM3 polygon (``raw/boundaries/geoboundaries/``) is matched to the published
   municipality it overlaps most, by area in the equal-area CRS of project.yaml; the match must be
   one-to-one over all units;
2. each ADM1 polygon is matched to a department the same way, and every matched municipality must
   lie in the department its geo_id says.

It was first run against the GADM-based ``geo/boundaries/`` (commit 5abdbd6); run again on the
geoBoundaries-based ones, it reproduces the same lookup. Output: ``raw/lookups/municipalities339_geoboundaries.csv``
(``geo_id``, ``GID_3``, ``shapeID``, ``shapeName``, overlap shares). Diagnostics are printed:
low-overlap units (salt flats and lakes that geoBoundaries leaves outside every municipality) and
name differences to review.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

from geo4bolivia import project

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/boundaries/geoboundaries"
OUT = ROOT / "raw/lookups/municipalities339_geoboundaries.csv"
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


def main() -> None:
    iso3 = project.config()["country"]["iso3"]
    crs = project.equal_area_crs()
    units = pd.read_csv(ROOT / "geo/units.csv", dtype=str)
    names = units.set_index("geo_id")["name"]

    def published(scale: str) -> gpd.GeoDataFrame:
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

    mun_units, dep_units = published("municipality"), published("department")
    adm3, adm1 = gboundaries("ADM3"), gboundaries("ADM1")
    print(f"geoBoundaries: {len(adm3)} ADM3, {len(adm1)} ADM1; published: {len(mun_units)} municipalities, "
          f"{len(dep_units)} departments")

    mun = match(adm3, mun_units, "municipality")
    report(mun, names, "Municipalities (ADM3 -> geo_id)")
    dep = match(adm1, dep_units, "department")
    report(dep, names, "Departments (ADM1 -> geo_id)")

    # Nesting: the ADM1 polygon holding most of each ADM3 must be the matched municipality's department
    adm1_dep = adm1.assign(dep_id=adm1["gb_idx"].map(dep.set_index("gb_idx")["geo_id"]))
    within = gpd.overlay(adm3[["gb_idx", "geometry"]], adm1_dep[["dep_id", "geometry"]],
                         how="intersection", keep_geom_type=True)
    within = within.assign(a=within.area).sort_values("a", ascending=False).drop_duplicates("gb_idx")
    expected = mun.set_index("gb_idx")["geo_id"].map(units.set_index("geo_id")["department_id"])
    wrong = within.set_index("gb_idx")["dep_id"].reindex(expected.index) != expected
    print(f"\nNesting: {int(wrong.sum())} municipalities whose geoBoundaries ADM1 differs from their geo_id's department")
    assert not wrong.any(), "geoBoundaries ADM3 polygons do not nest in the matched departments"

    gid = units.set_index("geo_id")["gid"]
    out = pd.DataFrame({
        "geo_id": mun["geo_id"], "GID_3": mun["geo_id"].map(gid),
        "shapeID": adm3.set_index("gb_idx").loc[mun["gb_idx"], "shapeID"].to_numpy(),
        "shapeName": mun["shapeName"],
        "share_gb": mun["share_gb"].round(4), "share_unit": mun["share_gadm"].round(4),
    }).sort_values("geo_id")
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}: {len(out)} rows")


if __name__ == "__main__":
    main()
