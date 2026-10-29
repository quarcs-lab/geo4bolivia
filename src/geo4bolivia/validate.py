"""Checks that the geography layer and every dataset are consistent.

Run with ``geo4bolivia validate`` (everything) or ``geo4bolivia validate <dataset>``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd

from . import metadata, project, store
from .scales import ancestors
from .scales import scales as registry

NEST_TOLERANCE = 0.995   # share of a child's area that must fall inside its parent


@dataclass
class Report:
    name: str
    errors: list[str] = field(default_factory=list)
    checks: int = 0

    def check(self, ok: bool, message: str) -> bool:
        self.checks += 1
        if not ok:
            self.errors.append(message)
        return ok

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        head = f"{'PASS' if self.ok else 'FAIL'}  {self.name}  ({self.checks} checks, {len(self.errors)} errors)"
        return "\n".join([head, *[f"      - {e}" for e in self.errors]])


def _units() -> pd.DataFrame:
    return pd.read_parquet(store.repo_root() / "geo/units.parquet")


def validate_geo() -> Report:
    rep = Report("geo (scales, units, boundaries, crosswalks)")
    root = store.repo_root()
    units = _units()
    reg = registry()
    rep.check(units["geo_id"].is_unique, "duplicate geo_id in geo/units")
    rep.check(set(units["scale"]) <= set(reg), f"units with unknown scales: {set(units['scale']) - set(reg)}")
    for sid, sc in registry(active_only=True).items():
        u = units[units["scale"] == sid]
        rep.check(len(u) > 0, f"active scale {sid!r} has no units")
        bad = u.loc[~u["geo_id"].map(sc.matches), "geo_id"].tolist()
        rep.check(not bad, f"{sid}: ids not matching {sc.id_pattern}: {bad[:5]}")
        if sc.parent:
            parents = set(units.loc[units["scale"] == sc.parent, "geo_id"])
            rep.check(u["parent_id"].isin(parents).all(), f"{sid}: parent_id not found among {sc.parent} units")
            if sc.kind == "admin":
                rep.check((u["geo_id"].str.rsplit("-", n=1).str[0] == u["parent_id"]).all(),
                          f"{sid}: ids do not nest by prefix in parent_id")
        # boundaries
        path = root / f"geo/boundaries/{sid}.parquet"
        if not rep.check(path.exists(), f"missing {path.relative_to(root)}"):
            continue
        b = gpd.read_parquet(path)
        rep.check(set(b["geo_id"]) == set(u["geo_id"]), f"{sid}: boundary ids differ from units")
        rep.check(b.geometry.is_valid.all(), f"{sid}: invalid geometries")
        rep.check(b.crs is not None and (b.crs.to_epsg() == 4326 or b.crs.to_string() == "OGC:CRS84"),
                  f"{sid}: boundaries not in WGS 84 / CRS84")
        rep.check((root / f"geo/boundaries/{sid}.geojson").exists(), f"{sid}: missing GeoJSON boundaries")
    # crosswalks: complete, weights sum to 1, and children really lie inside parents
    for sid in registry(active_only=True):
        for target in ancestors(sid):
            path = root / f"geo/crosswalks/{sid}__{target}.csv"
            if not rep.check(path.exists(), f"missing crosswalk {sid}__{target}"):
                continue
            xw = pd.read_csv(path)
            rep.check(set(xw["geo_id_from"]) == set(units.loc[units["scale"] == sid, "geo_id"]),
                      f"{sid}__{target}: does not cover every {sid} unit")
            sums = xw.groupby("geo_id_from")["weight_area"].sum()
            rep.check(np.allclose(sums, 1.0), f"{sid}__{target}: weights do not sum to 1")
    from .aggregate import overlay_weights  # local import: geometry work only when validating
    for sid, sc in registry(active_only=True).items():
        if not sc.parent:
            continue
        xw = pd.read_csv(root / f"geo/crosswalks/{sid}__{sc.parent}.csv")
        ow = overlay_weights(gpd.read_parquet(root / f"geo/boundaries/{sid}.parquet"),
                             gpd.read_parquet(root / f"geo/boundaries/{sc.parent}.parquet"))
        inside = xw.merge(ow, on=["geo_id_from", "geo_id_to"], how="left")["share_of_from"].fillna(0)
        low = xw.loc[inside.values < NEST_TOLERANCE, "geo_id_from"].tolist()
        rep.check(not low, f"{sid} units less than {NEST_TOLERANCE:.1%} inside their {sc.parent}: {low[:5]}")
    return rep


_PANDAS_KIND = {"string": "O", "integer": "iu", "number": "fiu"}


def validate_dataset(dataset: str) -> Report:
    rep = Report(f"dataset {dataset}")
    root = store.repo_root()
    units = _units()
    pkg = metadata.package(dataset)
    for key in ("name", "title", "description", "licenses", "sources", "resources"):
        rep.check(key in pkg, f"datapackage missing {key!r}")
    licenses = pkg.get("licenses") or [{}]
    rep.check(all(lic.get("name") for lic in licenses), "'licenses' must list licenses that have a 'name'")
    for src in pkg.get("sources", []):
        name = src.get("title", "")[:40]
        rep.check(bool(name), f"a source has no 'title': {src}")
        rep.check(bool(src.get("geo:license", {"name": "-"}).get("name")), f"source {name!r}: geo:license has no 'name'")
    for res in pkg["resources"]:
        sid = res["geo:scale"]
        tag = f"{dataset}[{sid}]"
        url = store.raw_url(res["geo:path"], project.config().get("default_ref", "main"))
        rep.check(res.get("path") == url, f"{tag}: resource path should be the public URL {url}")
        csv_path, pq_path = root / res["geo:path"], root / res["geo:parquet"]
        if not (rep.check(csv_path.exists(), f"{tag}: missing {res['geo:path']}")
                and rep.check(pq_path.exists(), f"{tag}: missing {res['geo:parquet']}")):
            continue
        df = pd.read_parquet(pq_path)
        csv = pd.read_csv(csv_path, dtype={"geo_id": str})
        schema = res["schema"]
        names = [f["name"] for f in schema["fields"]]
        rep.check(list(df.columns) == names, f"{tag}: columns {list(df.columns)} != schema {names}")
        rep.check(list(csv.columns) == names, f"{tag}: CSV columns differ from schema")
        if list(df.columns) != names:
            continue
        try:
            pd.testing.assert_frame_equal(df, csv[names], check_dtype=False, rtol=1e-6)
            rep.check(True, "")
        except AssertionError as exc:
            rep.check(False, f"{tag}: CSV and Parquet differ: {str(exc).splitlines()[0]}")
        for f in schema["fields"]:
            rep.check(bool(f.get("title")), f"{tag}: {f['name']} has no 'title' (its label for plots)")
            rep.check(bool(f.get("description")), f"{tag}: {f['name']} has no 'description'")
            col, kind = df[f["name"]], _PANDAS_KIND.get(f["type"])
            if kind and col.notna().any():
                ok = col.dtype.kind in kind or (f["type"] == "string" and pd.api.types.is_string_dtype(col))
                rep.check(ok, f"{tag}: {f['name']} has dtype {col.dtype}, schema says {f['type']}")
            cons = f.get("constraints", {})
            if cons.get("required"):
                rep.check(col.notna().all(), f"{tag}: {f['name']} has missing values")
            if "pattern" in cons:
                bad = col.dropna()[~col.dropna().map(lambda v: re.fullmatch(cons["pattern"], str(v)) is not None)]
                rep.check(bad.empty, f"{tag}: {f['name']} values not matching {cons['pattern']}: {bad.head(3).tolist()}")
            if "minimum" in cons:
                rep.check((col.dropna() >= cons["minimum"]).all(), f"{tag}: {f['name']} below {cons['minimum']}")
            if "maximum" in cons:
                rep.check((col.dropna() <= cons["maximum"]).all(), f"{tag}: {f['name']} above {cons['maximum']}")
            agg = f.get("geo:aggregation")
            if agg and agg.startswith("weighted_mean:"):
                rep.check(agg.split(":", 1)[1] in names, f"{tag}: weight for {f['name']} is not a field")
            if f.get("geo:role") == "source_key" and "geo:units_column" in f:
                ucol = f["geo:units_column"]
                pairs = df[["geo_id", f["name"]]].drop_duplicates()
                ref = units.loc[units["scale"] == sid, ["geo_id", ucol]].rename(columns={ucol: "_expected"})
                joined = pairs.merge(ref, on="geo_id", how="left")
                as_text = lambda s: s.astype("string").str.removesuffix(".0")   # 57 == "57"
                rep.check((as_text(joined[f["name"]]) == as_text(joined["_expected"])).fillna(False).all(),
                          f"{tag}: {f['name']} disagrees with geo/units.{ucol} for some geo_id")
        pk = schema.get("primaryKey", ["geo_id", "year"])
        rep.check(not df.duplicated(pk).any(), f"{tag}: duplicate {pk}")
        known = set(units.loc[units["scale"] == sid, "geo_id"])
        unknown = sorted(set(df["geo_id"]) - known)
        rep.check(not unknown, f"{tag}: geo_id not in geo/units ({sid}): {unknown[:5]}")
        first, last = res["geo:period"]
        rep.check(df["year"].between(first, last).all(), f"{tag}: years outside geo:period {first}-{last}")
        rep.check(df["year"].min() == first and df["year"].max() == last, f"{tag}: geo:period does not match the data")
    if "geo:map" in pkg:
        _check_map(rep, dataset, pkg["geo:map"])
    return rep


def _check_map(rep: Report, dataset: str, spec: dict) -> None:
    """The headline map (``geo:map``) must name a variable and a year that has data."""
    try:
        res = metadata.resource(dataset, spec.get("scale"))
    except KeyError as exc:
        rep.check(False, f"geo:map: {exc}")
        return
    variable, year = spec.get("variable"), spec.get("year")
    if not rep.check(variable in metadata.variables(dataset, res["geo:scale"]),
                     f"geo:map: {variable!r} is not a variable of {dataset}"):
        return
    df = pd.read_parquet(store.repo_root() / res["geo:parquet"], columns=["year", variable])
    values = df.loc[df["year"] == year, variable].dropna()
    rep.check(not values.empty, f"geo:map: {variable} has no values in {year}")
    if rep.check(spec.get("classify", "log") == "log", f"geo:map: classify must be 'log' or absent"):
        rep.check(spec.get("classify") != "log" or (values > 0).all(),
                  f"geo:map: {variable} has values <= 0, so it cannot be classified on a log scale")


def run(dataset: str | None = None) -> list[Report]:
    targets = [dataset] if dataset else list(metadata.dataset_ids())
    reports = [] if dataset else [validate_geo()]
    reports += [validate_dataset(d) for d in targets]
    return reports
