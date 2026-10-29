"""Municipal population: raw/pop -> data/municipality/pop."""

import pandas as pd

from .. import store
from .common import ids_from_units, publish, write_docs

DATASET, SCALE = "pop", "municipality"
RAW = "raw/pop/pop.csv"


def build() -> None:
    wide = pd.read_csv(store.repo_root() / RAW)
    df = wide.melt(id_vars="asdf_id", var_name="year", value_name="pop")
    df["year"] = df["year"].str.removeprefix("pop").astype(int)
    df["geo_id"] = df["asdf_id"].astype(str).map(ids_from_units(SCALE, "asdf_id"))   # DS4Bolivia polygon
    # density over the unit's area in the equal-area projection (geo/units.area_km2)
    units = pd.read_parquet(store.repo_root() / "geo/units.parquet")
    area = units.loc[units["scale"] == SCALE].set_index("geo_id")["area_km2"].astype(float)
    df["pop_density"] = df["pop"] / df["geo_id"].map(area)
    publish(DATASET, SCALE, df)
    write_docs(DATASET)
