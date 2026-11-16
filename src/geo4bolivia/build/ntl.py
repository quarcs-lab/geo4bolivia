"""Municipal night-time lights per capita: raw/ntl -> data/municipality/ntl."""

import pandas as pd

from .. import store
from .common import publish, write_docs
from .geo import link_ds4bolivia_polygons

DATASET, SCALE = "ntl", "municipality"
RAW = "raw/ntl/ln_NTLpc.csv"


def build() -> None:
    wide = pd.read_csv(store.repo_root() / RAW)
    # ln_NTLpc2012, ..., ln_t400NTLpc2020 -> one row per polygon and year
    df = wide.set_index("asdf_id")
    df.columns = pd.MultiIndex.from_frame(df.columns.str.extract(r"^(\w+?)(\d{4})$"), names=["variable", "year"])
    df = df.stack("year", future_stack=True).reset_index()
    df["year"] = df["year"].astype(int)
    df = link_ds4bolivia_polygons(df)   # DS4Bolivia polygons; none for the 10 changed or new units
    publish(DATASET, SCALE, df)
    write_docs(DATASET)
