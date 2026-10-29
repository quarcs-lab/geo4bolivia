"""Municipal SDG Atlas indicators: raw/sdg -> data/municipality/sdg01 ... sdg17.

One dataset per goal: the goal's composite index, its component indicators and two
context variables. Each variable is stored at its reference year (``geo:year`` in the
metadata), so a panel has one row per municipality and reference year.
"""

from functools import partial

import numpy as np
import pandas as pd

from .. import metadata, store
from .common import ids_from_units, publish, tidy_floats, write_docs

SCALE = "municipality"
RAW = "raw/sdg/sdgVariables.csv"
INDICES = "raw/sdg/sdgIndices.csv"
NAMES = "raw/lookups/regionNames.csv"
GOALS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17)   # the Atlas has no index for 12 or 14
CONTEXT = ["population_2020", "urbano_2012"]


def dataset(goal: int) -> str:
    return f"sdg{goal:02d}"


def columns(goal: int, names) -> list:
    """The goal's index, its components (sdg<goal>_...) and the context variables."""
    return [f"index_sdg{goal}"] + [c for c in names if c.startswith(f"sdg{goal}_")] + CONTEXT


def read() -> pd.DataFrame:
    root = store.repo_root()
    wide = pd.read_csv(root / RAW).merge(pd.read_csv(root / INDICES).drop(columns="imds"), on="asdf_id")
    # The values were stored as float32 (53.200001): restore the decimals they print as
    values = [c for c in wide.columns if c != "asdf_id"]
    wide = tidy_floats(wide.astype({c: np.float32 for c in values}))
    # Rows follow DS4Bolivia's attribute rows, not its polygons (three homonym pairs are
    # swapped), so link them by INE code, which geo/units holds for the right polygon
    codes = pd.read_csv(root / NAMES).set_index("asdf_id")["mun_id"]
    wide["mun_id"] = wide["asdf_id"].map(codes)
    wide["geo_id"] = wide["mun_id"].astype(str).map(ids_from_units(SCALE, "mun_id"))
    return wide


def build(goal: int) -> None:
    name = dataset(goal)
    wide = read()
    values = columns(goal, wide.columns)
    year_of = {f["name"]: f["geo:year"] for f in metadata.fields(name) if "geo:year" in f}
    if set(year_of) != set(values):
        raise ValueError(f"{name}: metadata years do not match {sorted(set(values) ^ set(year_of))}")
    latest = max(year_of[c] for c in values[1:] if c not in CONTEXT)
    if year_of[values[0]] != latest:
        raise ValueError(f"{name}: {values[0]} must be stored at its latest component year, {latest}")
    long = wide.melt(id_vars=["geo_id", "mun_id"], value_vars=values, var_name="variable")
    long["year"] = long["variable"].map(year_of)
    df = long.pivot_table(index=["geo_id", "mun_id", "year"], columns="variable", values="value",
                          aggfunc="first", dropna=False).reset_index()
    df = df.dropna(subset=values, how="all")
    publish(name, SCALE, df)
    write_docs(name)


BUILDERS = {dataset(g): partial(build, g) for g in GOALS}
