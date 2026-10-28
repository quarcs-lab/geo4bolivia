"""Match the 339 GADM 4.1 municipalities to the DS4Bolivia municipalities (one-off).

Writes ``raw/lookups/municipalities339_gadm.csv``, which ``build/geo.py`` and the
dataset builders read. Run it again only if an input changes, and review the diff:

    uv run python scripts/match_municipalities.py

Inputs (in ``raw/``):
- ``boundaries/gadm41_BOL_3.json``: GADM 4.1 level 3 (339 municipalities + 5 Lake Titicaca polygons)
- ``boundaries/bolivia339geoqueryOpt.geojson``: DS4Bolivia's 339 polygons (``asdf_id``)
- ``lookups/regionNames.csv``: DS4Bolivia's attribute rows (``asdf_id``, ``mun``, ``dep``, INE ``mun_id``)

Two DS4Bolivia keys are matched, because they do not always describe the same municipality:

- ``asdf_id`` (polygon): the DS4Bolivia polygon with the largest share of its area
  inside the GADM polygon. Data computed from the polygons (population, night-time
  lights, satellite embeddings) follow this key.
- ``asdf_id_atlas`` (attribute row): the regionNames row that names this municipality.
  It equals ``asdf_id`` except for three pairs of homonyms in different departments
  (San Javier, El Puente, Santa Rosa), whose rows are swapped between the two polygons
  in DS4Bolivia. Data joined by municipality code (the SDG Atlas variables) follow
  this key, and ``mun_id`` comes from this row.

The script stops unless the match is one-to-one, every polygon lies mostly (> 80 %)
in its GADM partner, and the corrected INE codes nest exactly in the GADM
departments and provinces (one INE code per GADM unit and vice versa).
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = RAW / "lookups/municipalities339_gadm.csv"
CRS = "+proj=aea +lat_0=-16.5 +lon_0=-64.5 +lat_1=-11 +lat_2=-21 +datum=WGS84 +units=m +no_defs"
MIN_SHARE = 0.8


def norm(text: str) -> str:
    """'Nuestra Señora de La Paz' -> 'nuestrasenoradelapaz'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def fail(message: str) -> None:
    sys.exit(f"match_municipalities: {message}")


def main() -> None:
    gadm = gpd.read_file(RAW / "boundaries/gadm41_BOL_3.json")
    gadm = gadm[gadm["TYPE_3"] != "Lago"].to_crs(CRS)
    rows = pd.read_csv(RAW / "lookups/regionNames.csv")
    polys = gpd.read_file(RAW / "boundaries/bolivia339geoqueryOpt.geojson").to_crs(CRS)
    polys["asdf_id"] = polys["asdf_id"].astype(int)
    if len(gadm) != 339 or len(polys) != 339 or len(rows) != 339:
        fail(f"expected 339 units everywhere, got GADM {len(gadm)}, polygons {len(polys)}, rows {len(rows)}")

    # 1. polygon match: largest share of each DS4Bolivia polygon inside a GADM polygon
    gadm["geometry"] = gadm.buffer(0)
    polys["geometry"] = polys.buffer(0)
    polys["poly_area"] = polys.area
    parts = gpd.overlay(polys[["asdf_id", "poly_area", "geometry"]], gadm[["GID_3", "geometry"]],
                        how="intersection", keep_geom_type=True)
    parts["share"] = parts.area / parts["poly_area"]
    best = parts.sort_values("share", ascending=False).drop_duplicates("asdf_id")[["asdf_id", "GID_3", "share"]]
    if len(best) != 339 or best["GID_3"].nunique() != 339:
        fail("the polygon match is not one-to-one")
    if (best["share"] < MIN_SHARE).any():
        fail(f"polygons below {MIN_SHARE:.0%} overlap:\n{best[best['share'] < MIN_SHARE]}")

    m = gadm[["GID_1", "GID_2", "GID_3", "NAME_1", "NAME_2", "NAME_3"]].merge(best, on="GID_3")
    m = m.merge(rows[["asdf_id", "mun", "dep"]], on="asdf_id")

    # 2. attribute row: the row naming this municipality in this department
    m["asdf_id_atlas"] = m["asdf_id"]
    moved = m["dep"].map(norm) != m["NAME_1"].map(norm)
    keyed = rows.assign(k=rows["mun"].map(norm) + "|" + rows["dep"].map(norm)).set_index("k")["asdf_id"]
    for i in m.index[moved]:
        k = norm(m.at[i, "mun"]) + "|" + norm(m.at[i, "NAME_1"])
        if k not in keyed.index:
            fail(f"no regionNames row for {m.at[i, 'mun']} in {m.at[i, 'NAME_1']}")
        m.at[i, "asdf_id_atlas"] = keyed[k]
    if m["asdf_id_atlas"].nunique() != 339:
        fail("the attribute rows are not a permutation of the 339 rows")
    attrs = rows.set_index("asdf_id").loc[m["asdf_id_atlas"]].reset_index()
    m["mun_id"] = attrs["mun_id"].to_numpy()
    m["name"] = attrs["mun"].to_numpy()
    if (attrs["dep"].map(norm).to_numpy() != m["NAME_1"].map(norm).to_numpy()).any():
        fail("department names still disagree after the correction")

    # 3. the corrected INE codes must nest exactly in GADM departments and provinces
    m["ine_dep"], m["ine_prov"] = m["mun_id"] // 10000, m["mun_id"] // 100
    for gid, ine in (("GID_1", "ine_dep"), ("GID_2", "ine_prov")):
        pairs = m[[gid, ine]].drop_duplicates()
        if pairs[gid].duplicated().any() or pairs[ine].duplicated().any():
            fail(f"INE {ine} codes do not match GADM {gid} one-to-one:\n{pairs[pairs[gid].duplicated(keep=False)]}")

    out = m.assign(
        name_gadm=m["NAME_3"], ine_code=m["mun_id"].map("{:06d}".format),
        share=m["share"].round(4), swapped=m["asdf_id"] != m["asdf_id_atlas"],
    )[["GID_3", "name_gadm", "name", "asdf_id", "asdf_id_atlas", "mun_id", "ine_code", "share", "swapped"]]
    out = out.sort_values("GID_3", key=lambda s: s.str.extract(r"BOL\.(\d+)\.(\d+)\.(\d+)").astype(int)
                          .apply(tuple, axis=1)).reset_index(drop=True)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} municipalities, "
          f"{(out['name'].map(norm) != out['name_gadm'].map(norm)).sum()} spelled differently in GADM, "
          f"{int(out['swapped'].sum())} with swapped DS4Bolivia attribute rows, "
          f"lowest overlap {out['share'].min():.1%}")


if __name__ == "__main__":
    main()
