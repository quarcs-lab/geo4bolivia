"""TEMPLATE for a new dataset builder. Copy to builders/<dataset>.py in the data repository.

Steps (see CONTRIBUTING_DATA.md):
1. Put the original files in raw/<dataset>/ and never edit them.
2. Write metadata/<dataset>.datapackage.json (copy an existing one) and add the
   id to metadata/index.json.
3. Fill in this builder: read the raw file, attach `geo_id` from a source key,
   and return every field listed in the metadata schema.
4. Register it in DATASETS in builders/__init__.py, then run:
       uv run geo4bolivia build <dataset> && uv run geo4bolivia validate <dataset>
"""

import pandas as pd

from geo4bolivia import store
from geo4bolivia.build.common import ids_from_units, publish, tidy_floats, write_docs

DATASET, SCALE = "mydataset", "district"          # scale: an active scale in geo/scales.yaml
RAW = "raw/mydataset/original-file.csv"


def build() -> None:
    df = tidy_floats(pd.read_csv(store.repo_root() / RAW))
    # Map the source key to geo IDs with a column of geo/units:
    #   GADM codes -> "gid", geoBoundaries -> "shapeISO", Global Data Lab -> "GDLcode".
    # Units identified by name instead? Use the package's matcher:
    #   from geo4bolivia import link; df = link(df, SCALE, on="Province")
    df["geo_id"] = df["GID_2"].map(ids_from_units(SCALE, "gid"))
    publish(DATASET, SCALE, df)   # checks columns against the schema, writes CSV + Parquet
    write_docs(DATASET)           # docs/datasets/<dataset>.md
