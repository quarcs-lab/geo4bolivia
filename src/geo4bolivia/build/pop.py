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
    publish(DATASET, SCALE, df)
    write_docs(DATASET)
