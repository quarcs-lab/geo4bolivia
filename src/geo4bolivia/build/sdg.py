"""Municipal SDG Atlas indicators: raw/sdg -> data/municipality/sdg.

Each indicator is stored at its reference year (``geo:year`` in the metadata),
so the panel has one row per municipality and reference year.
"""

import numpy as np
import pandas as pd

from .. import metadata, store
from .common import ids_from_units, publish, tidy_floats, write_docs

DATASET, SCALE = "sdg", "municipality"
RAW = "raw/sdg/sdgVariables.csv"
NAMES = "raw/lookups/regionNames.csv"


def build() -> None:
    root = store.repo_root()
    wide = pd.read_csv(root / RAW)
    # The values were stored as float32 (53.200001): restore the decimals they print as
    values = [c for c in wide.columns if c != "asdf_id"]
    wide = tidy_floats(wide.astype({c: np.float32 for c in values}))
    # Rows follow DS4Bolivia's attribute rows, not its polygons (three homonym pairs are
    # swapped), so link them by INE code, which geo/units holds for the right polygon
    codes = pd.read_csv(root / NAMES).set_index("asdf_id")["mun_id"]
    wide["mun_id"] = wide["asdf_id"].map(codes)
    wide["geo_id"] = wide["mun_id"].astype(str).map(ids_from_units(SCALE, "mun_id"))
    year_of = {f["name"]: f["geo:year"] for f in metadata.fields(DATASET) if "geo:year" in f}
    if set(year_of) != set(values):
        raise ValueError(f"{DATASET}: metadata years do not cover {sorted(set(values) ^ set(year_of))}")
    long = wide.melt(id_vars=["geo_id", "mun_id"], value_vars=values, var_name="variable")
    long["year"] = long["variable"].map(year_of)
    df = long.pivot_table(index=["geo_id", "mun_id", "year"], columns="variable", values="value",
                          aggfunc="first", dropna=False).reset_index()
    df = df.dropna(subset=values, how="all")
    publish(DATASET, SCALE, df)
    write_docs(DATASET)
