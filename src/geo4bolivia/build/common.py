"""Helpers shared by the builders: writing tables and generating docs from metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .. import metadata, project, store
from ..project import PACKAGE

TYPES = {"string": "string", "integer": "int64", "number": "float64"}
COLAB_EMPTY = "https://colab.research.google.com/notebooks/empty.ipynb"
COLAB_BADGE = f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({COLAB_EMPTY})"


def read_json(path: str) -> dict:
    return json.loads((store.repo_root() / path).read_text())


def write_json(path: str, obj) -> None:
    (store.repo_root() / path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def tidy_floats(df: pd.DataFrame) -> pd.DataFrame:
    """Turn float32 columns (as stored by Stata) into the float64 values they print as,
    so 0.557 stays 0.557 rather than becoming 0.5569999814."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == np.float32:
            df[col] = pd.to_numeric(df[col].astype(str), errors="coerce").astype("float64")
    return df


def ids_from_units(scale: str, key_column: str) -> dict:
    """Map a source key (e.g. GID_2, shapeISO, GDLcode) to geo IDs for one scale."""
    units = pd.read_parquet(store.repo_root() / "geo/units.parquet")
    u = units[units["scale"] == scale]
    return dict(zip(u[key_column], u["geo_id"]))


def publish(dataset: str, scale: str, df: pd.DataFrame) -> pd.DataFrame:
    """Order and type columns as the metadata schema says, sort, and write CSV + Parquet."""
    res = metadata.resource(dataset, scale)
    names = [f["name"] for f in res["schema"]["fields"]]
    missing = [n for n in names if n not in df.columns]
    if missing:
        raise ValueError(f"{dataset}[{scale}]: builder output lacks {missing}")
    df = df[names].sort_values(["geo_id", "year"]).reset_index(drop=True)
    for f in res["schema"]["fields"]:
        df[f["name"]] = df[f["name"]].astype(TYPES[f["type"]])
    root = store.repo_root()
    for rel in (res["geo:path"], res["geo:parquet"]):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(root / res["geo:path"], index=False)
    df.to_parquet(root / res["geo:parquet"], index=False)
    print(f"  wrote {res['geo:path']} and {res['geo:parquet']}  ({len(df):,} rows)")
    _record_coverage(dataset, scale, df)
    return df


def _record_coverage(dataset: str, scale: str, df: pd.DataFrame) -> None:
    """Write the resource's ``geo:period``, ``geo:years`` and ``geo:units`` from the data."""
    path = metadata.package_path(dataset)
    pkg = read_json(path)
    years = sorted(int(y) for y in df["year"].unique())
    found = {"geo:period": [years[0], years[-1]], "geo:years": years, "geo:units": int(df["geo_id"].nunique())}
    for i, res in enumerate(pkg["resources"]):
        if res["geo:scale"] == scale:
            ordered = {}
            for key, value in res.items():          # keep the three together, after geo:scale
                if key in found:
                    continue
                ordered[key] = value
                if key == "geo:scale":
                    ordered.update(found)
            pkg["resources"][i] = ordered
    write_json(path, pkg)
    metadata.clear_cache()


def wide_paths(dataset: str, scale: str) -> dict[str, str]:
    """Where a dataset's wide files go: next to its panel, ``data/<dataset>/<scale>/<dataset>_wide.*``."""
    stem = f"data/{dataset}/{scale}/{dataset}_wide"
    return {"geo:gpkg": f"{stem}.gpkg", "geo:geojson": f"{stem}.geojson"}


def _light_boundaries(scale: str):
    """The boundaries of the GeoJSON: ``wide_geojson_boundaries`` in project.yaml (a path with
    ``{scale}``, e.g. the website's simplified maps), else the analysis boundaries."""
    import geopandas as gpd

    from .. import io
    pattern = project.config().get("wide_geojson_boundaries")
    path = store.repo_root() / pattern.format(scale=scale) if pattern else None
    if path is not None and path.is_file():
        shapes = gpd.read_file(path)[["geo_id", "geometry"]]
        return shapes.to_crs("EPSG:4326") if shapes.crs else shapes.set_crs("EPSG:4326")
    return io.boundaries(scale)[["geo_id", "geometry"]]


def publish_wide(dataset: str) -> None:
    """Write the dataset's wide files: one row per unit, one column per variable and year
    (``io.wide_table``), as a GeoPackage on the analysis boundaries (``geo/boundaries``) with a
    second table, ``variables``, describing every column (``io.wide_dictionary``), and as a
    GeoJSON on the light boundaries (``_light_boundaries``). Records their paths in the
    resource (``geo:gpkg``, ``geo:geojson``).

    The GeoPackage's internal timestamps are set to the dataset's ``geo:updated``, so rebuilding
    unchanged data writes the same bytes.
    """
    import geopandas as gpd
    import pyogrio

    from .. import io
    root = store.repo_root()
    path = metadata.package_path(dataset)
    pkg = read_json(path)
    stamp = f"{str(pkg.get('geo:updated') or '2000-01-01')[:10]}T00:00:00.000Z"
    for i, res in enumerate(pkg["resources"]):
        sid = res["geo:scale"]
        paths = wide_paths(dataset, sid)
        table = io.wide_table(dataset, sid)
        gpkg, geojson = root / paths["geo:gpkg"], root / paths["geo:geojson"]
        gpkg.parent.mkdir(parents=True, exist_ok=True)
        for old in (gpkg, geojson):
            old.unlink(missing_ok=True)
        shapes = io.boundaries(sid)[["geo_id", "geometry"]]
        full = gpd.GeoDataFrame(table.merge(shapes, on="geo_id", how="left"), geometry="geometry", crs=shapes.crs)
        pyogrio.set_gdal_config_options({"OGR_CURRENT_DATE": stamp})
        try:
            pyogrio.write_dataframe(full, gpkg, layer=dataset, driver="GPKG")
            pyogrio.write_dataframe(io.wide_dictionary(dataset, sid), gpkg, layer="variables", driver="GPKG",
                                    append=True)
        finally:
            pyogrio.set_gdal_config_options({"OGR_CURRENT_DATE": None})
        light = _light_boundaries(sid)
        web = gpd.GeoDataFrame(table.merge(light, on="geo_id", how="left"), geometry="geometry", crs="EPSG:4326")
        pyogrio.write_dataframe(web, geojson, driver="GeoJSON", layer=dataset,
                                layer_options={"COORDINATE_PRECISION": 5, "RFC7946": "YES", "WRITE_NAME": "NO"})
        size = lambda p: f"{p.stat().st_size / 1e6:.1f} MB"
        print(f"  wrote {paths['geo:gpkg']} ({size(gpkg)}) and {paths['geo:geojson']} ({size(geojson)})")
        ordered = {}
        for key, value in res.items():          # the two paths right after geo:parquet
            if key in paths:
                continue
            ordered[key] = value
            if key == "geo:parquet":
                ordered.update(paths)
        pkg["resources"][i] = ordered
    write_json(path, pkg)
    metadata.clear_cache()


def publish_stata(dataset: str) -> None:
    """Write the dataset's Stata file (``stata.write``): the long panel in format 118 with the unit's
    names, a value-labelled panel ID (``xtset unit_id year``), labels and notes. Records its path in
    the resource (``geo:dta``, right after the wide files). Its timestamp is the dataset's
    ``geo:updated``, so rebuilding unchanged data writes the same bytes."""
    from .. import stata
    root = store.repo_root()
    path = metadata.package_path(dataset)
    pkg = read_json(path)
    for i, res in enumerate(pkg["resources"]):
        out = stata.stata_path(dataset, res["geo:scale"])
        (root / out).parent.mkdir(parents=True, exist_ok=True)
        stata.write(dataset, res["geo:scale"], root / out)
        print(f"  wrote {out} ({(root / out).stat().st_size / 1e6:.1f} MB)")
        ordered, placed = {}, False
        anchor = "geo:geojson" if "geo:geojson" in res else "geo:parquet"
        for key, value in res.items():
            if key == "geo:dta":
                continue
            ordered[key] = value
            if key == anchor:
                ordered["geo:dta"], placed = out, True
        if not placed:
            ordered["geo:dta"] = out
        pkg["resources"][i] = ordered
    write_json(path, pkg)
    metadata.clear_cache()


years_text = metadata.years_text


def coverage(df: pd.DataFrame, column: str) -> str:
    return years_text(df.loc[df[column].notna(), "year"])


def write_docs(dataset: str) -> None:
    """Generate data/<dataset>/README.md (shown on GitHub when the dataset's folder is opened)
    from the metadata and the published data."""
    root = store.repo_root()
    publish_wide(dataset)
    publish_stata(dataset)
    pkg = metadata.package(dataset)
    units = pd.read_parquet(root / "geo/units.parquet")
    folder = f"data/{dataset}/"
    rel = lambda path: path[len(folder):] if path.startswith(folder) else f"../../{path}"
    tree = ["```text", f"data/{dataset}/",
            "├── README.md          this page, generated from datapackage.json",
            "├── datapackage.json   the metadata (Frictionless): variables, units, sources, licenses"]
    for i, res in enumerate(pkg["resources"]):
        last = i == len(pkg["resources"]) - 1
        branch, stem = ("└── ", "    ") if last else ("├── ", "│   ")
        tree += [f"{branch}{res['geo:scale']}/".ljust(23) + f"the {res['geo:scale']} data",
                 f"{stem}├── {Path(res['geo:path']).name}".ljust(len(stem) + 4 + 23) + "the panel: one row per unit and year",
                 f"{stem}├── {Path(res['geo:parquet']).name}".ljust(len(stem) + 4 + 23) + "the same, typed and compressed",
                 f"{stem}├── {Path(res['geo:gpkg']).name}".ljust(len(stem) + 4 + 23)
                 + "wide: one row per unit, a column per variable and year, boundaries",
                 f"{stem}├── {Path(res['geo:geojson']).name}".ljust(len(stem) + 4 + 23)
                 + "the same, on lighter boundaries, for web maps",
                 f"{stem}└── {Path(res['geo:dta']).name}".ljust(len(stem) + 4 + 23)
                 + "the panel for Stata: names, labels, notes, xtset"]
    tree.append("```")
    lines = [f"# {pkg['title']}", "",
             f"> Generated by `{PACKAGE} build` from [`datapackage.json`](datapackage.json). Edit that file, not this one.",
             "", "## Overview", "", pkg["description"], ""]
    lines += [f"- **Dataset id:** `{dataset}`",
              f"- **Categories:** {', '.join(pkg.get('geo:categories', []))}",
              "", "## This folder", "", *tree]
    for res in pkg["resources"]:
        df = pd.read_parquet(root / res["geo:parquet"])
        sid = res["geo:scale"]
        n_units = (units["scale"] == sid).sum()
        first, last = res["geo:period"]
        lines += ["", f"## Scale: {sid}", "",
                  f"- **Units:** {df['geo_id'].nunique()} of {n_units} {sid} units",
                  f"- **Period:** {first}–{last}, "
                  + ("annual" if years_text(df["year"]) == f"{first}–{last}" else f"years {years_text(df['year'])}")
                  + f" ({len(df):,} rows: one per unit and year)",
                  f"- **Source geometry:** {res.get('geo:source_geometry', '—')}",
                  "", "| File | Format | Download |", "| --- | --- | --- |",
                  f"| [`{rel(res['geo:path'])}`]({rel(res['geo:path'])}) | CSV | [raw]({store.raw_url(res['geo:path'])}) |",
                  f"| [`{rel(res['geo:parquet'])}`]({rel(res['geo:parquet'])}) | Parquet | "
                  f"[raw]({store.raw_url(res['geo:parquet'])}) |",
                  f"| [`{rel(res['geo:gpkg'])}`]({rel(res['geo:gpkg'])}) | GeoPackage, wide | "
                  f"[raw]({store.raw_url(res['geo:gpkg'])}) |",
                  f"| [`{rel(res['geo:geojson'])}`]({rel(res['geo:geojson'])}) | GeoJSON, wide | "
                  f"[raw]({store.raw_url(res['geo:geojson'])}) |",
                  f"| [`{rel(res['geo:dta'])}`]({rel(res['geo:dta'])}) | Stata, long panel (labels and notes) | "
                  f"[raw]({store.raw_url(res['geo:dta'])}) |",
                  "", f"The wide files have one row per {sid} unit, with its name, the units it lies in, "
                  "its source keys and area, then every variable once per year, `<variable>_<year>` "
                  f"(e.g. `{_example_column(res)}`); a variable has a column for every year, empty where it "
                  "has no values. The GeoPackage carries the analysis boundaries and a second table, "
                  "`variables`, that describes every column (label, description, unit, source, reference "
                  "year); the GeoJSON carries lighter boundaries for web maps.",
                  "", "The Stata file (format 118, Stata 14 and later) is the panel with each unit's name, the "
                  "units it lies in (as text and as labelled codes), its source keys and area, and a numeric "
                  "`unit_id` labelled with the unit's name; it opens declared as a panel (`xtset unit_id year`). "
                  "Every variable has a label, and `notes <variable>` shows how it was built; `notes _dta` "
                  "describes the dataset and how to cite it.",
                  "", "| Variable | Label | Description | Unit | Coverage | Aggregation | Source |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for f in res["schema"]["fields"]:
            agg = f.get("geo:aggregation", "—" if f.get("geo:role", "variable") != "variable" else "none")
            desc = f.get("description", "")
            if f.get("geo:reference_years"):
                desc += " Reference years: " + "; ".join(f"{k}: {v}" for k, v in f["geo:reference_years"].items()) + "."
            lines.append(f"| `{f['name']}` | {f.get('title', '')} | {desc} | {f.get('geo:unit', '')} | "
                         f"{coverage(df, f['name'])} | {agg} | {f.get('geo:source', '')} |")
    native = pkg["resources"][0]
    lines += ["", "## Load it", "", "```python",
              f"!pip install -q {PACKAGE}                       # Google Colab",
              f"import {PACKAGE} as geo", "",
              f'geo.dictionary("{dataset}")                     # variables, units, aggregation rules',
              f'df = geo.load("{dataset}")                      # panel: one row per unit and year',
              f'gdf = geo.load("{dataset}", geometry=True)      # with {native["geo:scale"]} boundaries',
              f'wide = geo.load("{dataset}", wide=True)         # one row per unit, a column per variable and year',
              "```", "", COLAB_BADGE, "", "Without the package:", "", "```python", "import pandas as pd",
              "import geopandas as gpd", "",
              f'df = pd.read_csv("{store.raw_url(native["geo:path"])}")',
              f'wide = gpd.read_file("{store.raw_url(native["geo:gpkg"])}", layer="{dataset}")',
              "```", "", COLAB_BADGE]
    if pkg.get("geo:notes"):
        lines += ["", "## Notes", ""] + [f"- {n}" for n in pkg["geo:notes"]]
    if pkg.get("geo:notebooks"):
        lines += ["", "## Related notebooks", ""] + [f"- [{n['title']}]({n['path']})" for n in pkg["geo:notebooks"]]
    lines += ["", "## Sources", ""] + [
        f"- {s['title']}" + (f" {s['path']}" if s.get("path") else "") for s in pkg["sources"]]
    lines += ["", "## Cite", "", "Please cite, in this order, the original sources, the observatory that processes "
              "and maintains these data, and the other sources:", ""]
    lines += [f"{i}. {c}" for i, c in enumerate(metadata.citations(pkg), 1)]
    lines += ["", "## License", ""] + [f"- These files: {link(lic)}" for lic in pkg["licenses"]] + [
        f"- {s.get('geo:creator') or s['title']}: {link(s['geo:license'])}"
        + (f". Required credit: “{s['geo:attribution']}”" if s.get("geo:attribution") else "")
        for s in pkg["sources"] if s.get("geo:license")]
    out = root / folder / "README.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"  wrote {folder}README.md")


def _example_column(res: dict) -> str:
    """A wide column name to show in the README: the first variable in the last year."""
    var = next((f["name"] for f in res["schema"]["fields"] if f.get("geo:role", "variable") == "variable"), "variable")
    return f"{var}_{metadata.resource_years(res)[-1]}"


def link(lic: dict) -> str:
    """A license as Markdown: its title (or name), linked to its text when known."""
    text = lic.get("title") or lic["name"]
    return f"[{text}]({lic['path']})" if lic.get("path") else text


def write_catalog() -> None:
    """Regenerate the variable catalog (``catalog`` in project.yaml) and data/README.md from all metadata."""
    root = store.repo_root()
    rows, table = [], []
    for ds in metadata.dataset_ids():
        pkg = metadata.package(ds)
        for res in pkg["resources"]:
            first, last = res["geo:period"]
            csv, pq = (res[k].removeprefix("data/") for k in ("geo:path", "geo:parquet"))
            wide = "".join(f" · [`{label}`]({res[k].removeprefix('data/')})"
                           for k, label in (("geo:gpkg", "_wide.gpkg"), ("geo:geojson", "_wide.geojson"),
                                            ("geo:dta", ".dta")) if res.get(k))
            table.append(f"| [`{ds}/`]({ds}/) | {pkg['title']} | `{res['geo:scale']}` | "
                         f"{first}–{last} | [`{csv}`]({csv}) · [`.parquet`]({pq}){wide} |")
            for f in res["schema"]["fields"]:
                rows.append({"dataset": ds, "scale": res["geo:scale"], "varname": f["name"],
                             "varlabel": f.get("title", ""), "description": f.get("description", ""),
                             "unit": f.get("geo:unit", ""), "aggregation": f.get("geo:aggregation", ""),
                             "source": f.get("geo:source", "")})
    catalog = project.config().get("catalog", "definitions.csv")
    columns = ["dataset", "scale", "varname", "varlabel", "description", "unit", "aggregation", "source"]
    pd.DataFrame(rows, columns=columns).to_csv(root / catalog, index=False)
    readme = ["# Data", "",
              f"> Generated by `{PACKAGE} build`. One folder per dataset: its `README.md` (variables, sources, "
              "how to load and cite it), its metadata `datapackage.json`, and one subfolder per map or scale with "
              "the panel (one row per unit `geo_id` and `year`, variables as columns) as CSV and Parquet, and "
              "wide (one row per unit, a column per variable and year, with boundaries) as GeoPackage and "
              "GeoJSON, and the panel for Stata (`.dta`, with names, labels and notes). `index.json` lists the "
              "datasets.",
              "", "| Dataset | Title | Scale | Years | Files |", "| --- | --- | --- | --- | --- |", *table,
              "", "Unit names, parents and source keys: [`geo/units.csv`](../geo/units.csv). "
              f"All variables in one table: [`{catalog}`](../{catalog})."]
    (root / "data").mkdir(exist_ok=True)
    (root / "data/README.md").write_text("\n".join(readme) + "\n")
    print(f"  wrote {catalog} and data/README.md")


def split_camel(name: str) -> str:
    """'MongkolBorei' -> 'Mongkol Borei' (GADM names in the source have no spaces)."""
    return re.sub(r"(?<=[a-zâêîôûéèàùœçñ])(?=[A-ZÂÊÎÔÛÉÈÀÙŒÇÑ])", " ", name)


# --- geography --------------------------------------------------------------------------

def polygonal(geom):
    """make_valid can return collections; keep only the polygon parts."""
    from shapely import make_valid
    from shapely.geometry import MultiPolygon, Polygon
    geom = make_valid(geom)
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    polys = [p for g in parts for p in (g.geoms if isinstance(g, MultiPolygon) else [g])]
    return MultiPolygon(polys)


def dissolve(layer, by: str):
    """Dissolve a layer into the units named in column ``by`` (returned as ``geo_id``).

    Neighbouring source polygons rarely share edges exactly, so dissolving leaves
    slivers between them as holes. A hole is kept only if it is a hole of the source
    layer too (a lake) or another source unit fills it (an enclave); gaps are filled.
    """
    from shapely import STRtree, unary_union
    from shapely.geometry import MultiPolygon, Polygon

    out = layer.dissolve(by=by).reset_index()[[by, "geometry"]].rename(columns={by: "geo_id"})
    parts = [p for g in layer.geometry for p in getattr(g, "geoms", [g]) if not p.is_empty]
    tree = STRtree(parts)
    source_holes = unary_union([Polygon(r) for p in parts for r in p.interiors]) if any(p.interiors for p in parts) else None

    def real(ring, outer) -> bool:
        hole = Polygon(ring)
        if hole.area < 1e-9 * outer.area:               # degenerate ring: zero area up to rounding
            return False
        if source_holes is not None and hole.intersection(source_holes).area > 0.5 * hole.area:
            return True
        filled = sum(parts[i].intersection(hole).area for i in tree.query(hole))
        return filled > 0.5 * hole.area

    def fill_gaps(geom):
        polys = [Polygon(p.exterior, [r for r in p.interiors if real(r, Polygon(p.exterior))])
                 for p in getattr(geom, "geoms", [geom])]
        return polys[0] if len(polys) == 1 else MultiPolygon(polys)

    out["geometry"] = out.geometry.map(fill_gaps)
    return out


def publish_geo(units: pd.DataFrame, layers: dict) -> pd.DataFrame:
    """Write everything in geo/ from units and boundary layers built by a project's geo builder.

    Parameters
    ----------
    units : one row per unit of every active scale, with ``geo_id``, ``scale``,
        ``name`` and ``parent_id`` (the unit of the ``parent`` scale it lies in),
        plus any source keys and source names (``gid``, ``shapeISO``, ...). Units of a
        grouping scale (``children:`` in scales.yaml) are found through a
        ``<grouping>_id`` column on the units they group, e.g. ``gdl_id`` on provinces.
    layers : ``{scale: GeoDataFrame}`` with ``geo_id`` and polygons in WGS 84, one
        per active scale. Dissolve coarser layers from the finest one so that
        every scale nests exactly.

    Adds ``<scale>_id`` columns (the unit's id at every coarser scale) and
    ``area_km2``, then writes geo/units.csv/.parquet, geo/boundaries/<scale>.geojson/.parquet
    and geo/crosswalks/<from>__<to>.csv for every nested pair.
    """
    import geopandas as gpd

    from ..aggregate import EQUAL_AREA_CRS
    from ..scales import ancestors
    from ..scales import scales as registry

    active = list(registry(active_only=True))
    missing = set(active) - set(layers)
    if missing:
        raise ValueError(f"no boundaries for active scale(s) {sorted(missing)}")
    units = units.copy()
    for col in ("geo_id", "scale", "name"):
        if col not in units.columns:
            raise ValueError(f"units need a {col!r} column")
    if "parent_id" not in units.columns:
        units["parent_id"] = pd.NA

    # every unit carries the ids of all scales it nests in (and its own)
    id_cols = {s: f"{s}_id" for s in active}
    for scale, col in id_cols.items():
        if col not in units.columns:
            units[col] = pd.NA
        own = units["scale"] == scale
        units.loc[own, col] = units.loc[own, "geo_id"]
    # parents are units of the scales others nest in, whose geo IDs are unique (maps of the same
    # units share their IDs, but no scale nests in a map)
    reg = registry(active_only=True)
    parents = units[units["scale"].isin({reg[s].parent for s in active} - {None})]
    if parents["geo_id"].duplicated().any():
        twice = sorted(parents.loc[parents["geo_id"].duplicated(), "geo_id"])
        raise ValueError(f"parent units share geo IDs: {twice[:3]}")
    scale_of_id = parents.set_index("geo_id")["scale"]
    for scale, col in id_cols.items():   # parent_id gives the parent scale's column
        has = units["parent_id"].notna() & (units["parent_id"].map(scale_of_id) == scale)
        units.loc[has, col] = units.loc[has, col].fillna(units.loc[has, "parent_id"])
    for _ in active:                      # then inherit everything else from the parent
        parent = units[units["scale"].isin(set(parents["scale"]))].set_index("geo_id").loc[:, list(id_cols.values())]
        inherited = parent.reindex(units["parent_id"]).set_axis(units.index)
        units[list(id_cols.values())] = units[list(id_cols.values())].fillna(inherited)
    for scale in active:
        if units.loc[units["scale"] == scale, "geo_id"].duplicated().any():
            raise ValueError(f"{scale} units repeat a geo ID")
    for scale in active:
        u = units[units["scale"] == scale]
        for anc in ancestors(scale):
            if anc in id_cols and u[id_cols[anc]].isna().any():
                raise ValueError(f"{scale} units lack {id_cols[anc]}: set parent_id, or {id_cols[anc]} "
                                 f"for a grouping scale")

    root = store.repo_root()
    out = root / "geo/boundaries"
    out.mkdir(parents=True, exist_ok=True)
    area = {}
    for scale in active:
        names = units.loc[units["scale"] == scale].set_index("geo_id")["name"]
        layer = gpd.GeoDataFrame(layers[scale][["geo_id", "geometry"]], geometry="geometry")
        layer = layer.set_crs("EPSG:4326") if layer.crs is None else layer.to_crs("EPSG:4326")
        layer["geometry"] = layer.geometry.map(polygonal)
        layer.insert(1, "name", layer["geo_id"].map(names))
        layer = layer.sort_values("geo_id").reset_index(drop=True)
        area.update({(scale, g): a for g, a in zip(layer["geo_id"], layer.to_crs(EQUAL_AREA_CRS).area / 1e6)})
        layer.to_parquet(out / f"{scale}.parquet", index=False)
        (out / f"{scale}.geojson").unlink(missing_ok=True)
        layer.to_file(out / f"{scale}.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
        print(f"  wrote geo/boundaries/{scale}.geojson and .parquet  ({len(layer)} units)")
    units["area_km2"] = pd.Series([area.get(k) for k in zip(units["scale"], units["geo_id"])],
                                  index=units.index, dtype=float).round(2)

    first = ["geo_id", "scale", "name", "parent_id", *id_cols.values()]
    columns = first + [c for c in units.columns if c not in first and c != "area_km2"] + ["area_km2"]
    order = {s: i for i, s in enumerate(active)}
    units = units[units["scale"].isin(active)].reindex(columns=columns).sort_values(
        ["scale", "geo_id"], key=lambda c: c.map(order) if c.name == "scale" else c).reset_index(drop=True)
    units.to_csv(root / "geo/units.csv", index=False)
    units.astype({c: "string" for c in columns if c != "area_km2"}).to_parquet(root / "geo/units.parquet", index=False)
    print(f"  wrote geo/units.csv and .parquet  ({len(units)} units)")

    xdir = root / "geo/crosswalks"
    xdir.mkdir(parents=True, exist_ok=True)
    for old in xdir.glob("*.csv"):
        old.unlink()
    for scale in active:
        for target in ancestors(scale):
            if target not in id_cols:
                continue
            u = units[units["scale"] == scale]
            xw = pd.DataFrame({"geo_id_from": u["geo_id"], "geo_id_to": u[id_cols[target]], "weight_area": 1.0})
            xw.to_csv(xdir / f"{scale}__{target}.csv", index=False)
            print(f"  wrote geo/crosswalks/{scale}__{target}.csv  ({len(xw)} rows)")
    return units
