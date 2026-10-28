"""Dataset metadata: one Frictionless Data Package per dataset in ``metadata/``.

Each package lists one resource per spatial scale the dataset is published at.
GDO-specific information lives in ``geo:``-prefixed properties:

- package: ``geo:categories``, ``geo:citation``, ``geo:notes``, ``geo:notebooks``
- resource: ``geo:scale``, ``geo:period`` ([first, last] year), ``geo:path``
  (CSV path in the repo), ``geo:parquet``, ``geo:source_geometry``
- field: ``geo:unit``, ``geo:source``, ``geo:role`` (``id`` | ``time`` |
  ``source_key`` | ``variable``) and ``geo:aggregation`` (``sum`` | ``mean`` |
  ``min`` | ``max`` | ``weighted_mean:<field>`` | ``none``)
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import store

INDEX = "metadata/index.json"   # list of dataset ids, so remote clients can discover them


@lru_cache(maxsize=None)
def dataset_ids() -> tuple[str, ...]:
    return tuple(json.load(store.open_binary(INDEX))["datasets"])


@lru_cache(maxsize=None)
def package(dataset: str) -> dict:
    if dataset not in dataset_ids():
        raise KeyError(f"Unknown dataset {dataset!r}; available: {', '.join(dataset_ids())}")
    return json.load(store.open_binary(f"metadata/{dataset}.datapackage.json"))


def resource(dataset: str, scale: str | None = None) -> dict:
    """The dataset's resource at ``scale`` (its first, native scale by default)."""
    resources = package(dataset)["resources"]
    if scale is None:
        return resources[0]
    for res in resources:
        if res["geo:scale"] == scale:
            return res
    have = ", ".join(r["geo:scale"] for r in resources)
    raise KeyError(f"{dataset!r} is published at: {have}. Use geo.aggregate() to reach {scale!r}.")


def fields(dataset: str, scale: str | None = None) -> list[dict]:
    return resource(dataset, scale)["schema"]["fields"]


def variables(dataset: str, scale: str | None = None) -> list[str]:
    return [f["name"] for f in fields(dataset, scale) if f.get("geo:role", "variable") == "variable"]


def aggregation_rules(dataset: str, scale: str | None = None) -> dict[str, str]:
    return {f["name"]: f.get("geo:aggregation", "none")
            for f in fields(dataset, scale) if f.get("geo:role", "variable") == "variable"}
