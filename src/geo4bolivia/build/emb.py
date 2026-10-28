"""Municipal satellite embeddings 2017: raw/emb and raw/embpw -> data/municipality/emb, embpw."""

import pandas as pd

from .. import store
from .common import ids_from_units, publish, write_docs

SCALE, YEAR = "municipality", 2017
RAW = {"emb": "raw/emb/satelliteEmbeddings2017.csv",
       "embpw": "raw/embpw/satelliteEmbeddings2017popWeighted.csv"}   # its pop_sum (the weights) is left out


def _build(dataset: str) -> None:
    df = pd.read_csv(store.repo_root() / RAW[dataset]).assign(year=YEAR)
    df["geo_id"] = df["asdf_id"].astype(str).map(ids_from_units(SCALE, "asdf_id"))   # DS4Bolivia polygon
    publish(dataset, SCALE, df)
    write_docs(dataset)


def build() -> None:
    _build("emb")


def build_pw() -> None:
    _build("embpw")
