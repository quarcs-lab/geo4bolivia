"""Two maps of the same units: shared geo IDs, and how a table finds the map it is on.

A synthetic project with two maps whose units share their IDs (``mapa``, 16 cells, and
``mapb``, the same cells with the last two merged into one), as a country's municipal maps
of two years do. Everything is built in a temporary data folder with the package's own
``publish_geo``.
"""

import importlib
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

import geo4bolivia as geo
from geo4bolivia import io, metadata, project, store

registry = importlib.import_module("geo4bolivia.scales")    # geo4bolivia.scales is also the public function

SCALES = """
country:
  label: Country
  kind: admin
  parent: null
  id_pattern: '^BO$'
  status: active
mapa:
  label: Map A (16 units)
  kind: admin
  parent: country
  id_pattern: '^BO-\\d{2}$'
  status: active
mapb:
  label: Map B (15 units)
  kind: admin
  parent: country
  id_pattern: '^BO-\\d{2}$'
  nesting: ids
  status: active
"""


def _caches():
    return (project.local_root, project.config, metadata.package, metadata.dataset_ids,
            registry._registry, io._units, io._ids)


@pytest.fixture
def two_maps(tmp_path, monkeypatch):
    """A data folder with the two maps; the package reads it instead of the project's."""
    from geo4bolivia.build.common import publish_geo

    shutil.copy(Path(__file__).resolve().parents[1] / "project.yaml", tmp_path / "project.yaml")
    (tmp_path / "geo").mkdir()
    (tmp_path / "geo" / "scales.yaml").write_text(SCALES)
    monkeypatch.setenv(f"{project.ENV_PREFIX}_DATA_DIR", str(tmp_path))
    for f in _caches():
        f.cache_clear()

    lon0, lat0, step = -65.0, -17.0, 0.5
    cells = [box(lon0 + c * step, lat0 + r * step, lon0 + (c + 1) * step, lat0 + (r + 1) * step)
             for r in range(4) for c in range(4)]
    ids_a = [f"BO-{i:02d}" for i in range(1, 17)]
    a = gpd.GeoDataFrame({"geo_id": ids_a}, geometry=cells, crs="EPSG:4326")
    b = gpd.GeoDataFrame({"geo_id": ids_a[:14] + ["BO-15"]},
                         geometry=cells[:14] + [cells[14].union(cells[15])], crs="EPSG:4326")
    country = gpd.GeoDataFrame({"geo_id": ["BO"]}, geometry=[a.union_all()], crs="EPSG:4326")
    units = pd.concat([
        pd.DataFrame({"geo_id": ["BO"], "scale": "country", "name": "Country"}),
        pd.DataFrame({"geo_id": ids_a, "scale": "mapa", "name": [f"Unit {i}" for i in ids_a], "parent_id": "BO"}),
        pd.DataFrame({"geo_id": b["geo_id"], "scale": "mapb", "name": [f"Unit {i}" for i in b["geo_id"]],
                      "parent_id": "BO"}),
    ], ignore_index=True)
    publish_geo(units, {"country": country, "mapa": a, "mapb": b})
    yield tmp_path
    monkeypatch.delenv(f"{project.ENV_PREFIX}_DATA_DIR")
    for f in _caches():
        f.cache_clear()


def _panel(ids, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"geo_id": ids, "year": 2020, "y": rng.normal(size=len(ids)).cumsum()})


def test_maps_share_their_ids(two_maps):
    units = geo.units()
    assert len(geo.units("mapa")) == 16 and len(geo.units("mapb")) == 15
    assert units["geo_id"].duplicated().any() and not units.duplicated(["scale", "geo_id"]).any()
    assert geo.boundaries("mapb").attrs[io.SCALE_KEY] == "mapb"
    assert geo.scale_of("BO") == "country"
    with pytest.raises(ValueError, match="several maps"):
        geo.scale_of("BO-01")
    with pytest.raises(ValueError, match="Unknown scale or map 'municipality'"):
        geo.boundaries("municipality")
    from geo4bolivia.validate import validate_geo
    report = validate_geo()
    assert report.ok, report


def test_the_ids_choose_the_map_when_only_one_has_them_all(two_maps):
    assert io.table_scale(_panel([f"BO-{i:02d}" for i in range(1, 17)])) == "mapa"   # BO-16 is only in mapa


def test_units_on_both_maps_need_map(two_maps):
    df = _panel([f"BO-{i:02d}" for i in range(1, 16)])
    with pytest.raises(ValueError, match=r"more than one map \(mapa, mapb\); pass map="):
        geo.moran(df, "y")
    res = geo.moran(df, "y", map="mapb")
    assert res.w_spec.endswith("(on mapb)") and len(res.df) == 15
    assert geo.moran(df, "y", map="mapa").w_spec.endswith("(on mapa)")
    with pytest.raises(ValueError, match="Unknown scale or map"):
        geo.moran(df, "y", map="mapc")


def test_a_recorded_map_survives_filtering(two_maps):
    df = _panel([f"BO-{i:02d}" for i in range(1, 16)])
    df.attrs[io.SCALE_KEY] = "mapb"
    kept = df[df["geo_id"] != "BO-01"]
    assert io.table_scale(kept) == "mapb"
    assert geo.lisa(kept, "y").w_spec.endswith("(on mapb)")
    assert geo.map(kept, "y") is not None


def test_names_and_aggregation_on_shared_ids(two_maps):
    df = _panel([f"BO-{i:02d}" for i in range(1, 16)])
    named = geo.add_names(df)                       # names do not depend on the map
    assert named["name"].iloc[0] == "Unit BO-01" and io.SCALE_KEY not in named.attrs
    with pytest.raises(ValueError, match="pass map="):
        geo.aggregate(df, to="country", rules={"y": "sum"})
    up = geo.aggregate(df, to="country", rules={"y": "sum"}, map="mapb")
    assert up["y"].iloc[0] == pytest.approx(df["y"].sum()) and up.attrs[io.SCALE_KEY] == "country"
    assert store.repo_root() == two_maps
