"""Dataset metadata: one Frictionless Data Package per dataset, ``data/<dataset>/datapackage.json``.

Every dataset has a folder of its own: ``data/<dataset>/`` holds its datapackage, its
generated README and one subfolder per map or scale with the files
(``data/<dataset>/<scale>/<dataset>.csv`` and ``.parquet``). ``data/index.json`` lists the
dataset ids. Each package lists one resource per spatial scale the dataset is published at.
GDO-specific information lives in ``geo:``-prefixed properties:

- package: ``geo:categories``, ``geo:notes``, ``geo:notebooks``,
  ``geo:weights`` (``{"population": "sdg"}``: the dataset that holds each weight a
  ``weighted_mean:<field>`` rule names when the field is not in this dataset;
  ``geo.aggregate()`` and ``geo.combine()`` load it from there),
  ``geo:map`` (the headline map: ``{"variable", "year"[, "scale", "classify": "log",
  "panels": [first, last]]}``; ``panels`` draws the page map as one panel per year),
  ``geo:updated``
- source: ``geo:role`` (``original`` | ``intermediary``), ``geo:creator``,
  ``geo:homepage``, ``geo:license`` (``{"name", "title", "path"}``, the license of
  the source itself) and ``geo:attribution`` (the credit text the source asks for)
- resource: ``geo:scale``, ``geo:period`` ([first, last] year), ``geo:years``
  (every year with rows, e.g. ``[2012, 2024]`` for a two-period panel), ``geo:units``
  (number of units with rows), ``geo:path`` (CSV path in the repo,
  ``data/<dataset>/<scale>/<dataset>.csv``), ``geo:parquet``,
  ``geo:source_geometry``. The build writes ``geo:period``, ``geo:years`` and ``geo:units``
  from the data.
- field: ``geo:unit``, ``geo:source``, ``geo:role`` (``id`` | ``time`` |
  ``source_key`` | ``variable``), ``geo:aggregation`` (``sum`` | ``mean`` |
  ``min`` | ``max`` | ``weighted_mean:<field>`` | ``none``) and, when a panel stores
  values at nominal years, ``geo:reference_years`` (``{"2012": "2008", "2024":
  "average 2022–2024"}``: the actual years behind each stored year)

Standard Frictionless properties carry the rest: each field's ``title`` is its
label for plots and its ``description`` says how it was built; the package's
``licenses`` is the license of the published files.
"""

from __future__ import annotations

import json
from functools import cache

from . import project, store

INDEX = "data/index.json"   # list of dataset ids, so remote clients can discover them


def package_path(dataset: str) -> str:
    """Where a dataset's datapackage lives in the data repository."""
    return f"data/{dataset}/datapackage.json"


@cache
def dataset_ids(ref: str | None = None) -> tuple[str, ...]:
    return tuple(json.load(store.open_binary(INDEX, ref))["datasets"])


@cache
def package(dataset: str, ref: str | None = None) -> dict:
    if dataset not in dataset_ids(ref):
        raise KeyError(f"Unknown dataset {dataset!r}; available: {', '.join(dataset_ids(ref))}")
    return json.load(store.open_binary(package_path(dataset), ref))


def clear_cache() -> None:
    """Forget metadata read so far (after the build rewrites a datapackage)."""
    dataset_ids.cache_clear()
    package.cache_clear()


def resource(dataset: str, scale: str | None = None, ref: str | None = None) -> dict:
    """The dataset's resource at ``scale`` (its first, native scale by default)."""
    resources = package(dataset, ref)["resources"]
    if scale is None:
        return resources[0]
    for res in resources:
        if res["geo:scale"] == scale:
            return res
    have = ", ".join(r["geo:scale"] for r in resources)
    raise KeyError(f"{dataset!r} is published at: {have}. Use geo.aggregate() to reach {scale!r}.")


def fields(dataset: str, scale: str | None = None, ref: str | None = None) -> list[dict]:
    return resource(dataset, scale, ref)["schema"]["fields"]


def variables(dataset: str, scale: str | None = None, ref: str | None = None) -> list[str]:
    return [f["name"] for f in fields(dataset, scale, ref) if f.get("geo:role", "variable") == "variable"]


def aggregation_rules(dataset: str, scale: str | None = None, ref: str | None = None) -> dict[str, str]:
    return {f["name"]: f.get("geo:aggregation", "none")
            for f in fields(dataset, scale, ref) if f.get("geo:role", "variable") == "variable"}


def weight_sources(dataset: str, ref: str | None = None) -> dict[str, str]:
    """``{weight field: dataset}`` from ``geo:weights``: where to find weights this dataset lacks."""
    return dict(package(dataset, ref).get("geo:weights", {}))


def observatory_citation() -> str:
    """The observatory's own citation (``citation: apa`` in project.yaml)."""
    cfg = project.config()
    cited = (cfg.get("citation") or {}).get("apa")
    return cited or f"{cfg['name']}. {cfg.get('website') or 'https://github.com/' + cfg['repository']}"


def citations(pkg: dict) -> list[str]:
    """How to cite a dataset, in order: its original sources, then who processes and maintains the
    data, then the other sources (boundaries, intermediaries). APA, one string each.

    The maintainer is the observatory (``citation`` in project.yaml), unless the package carries a
    ``geo:citation`` of its own, as a dataset saved with ``geo.save(..., citation=)`` does.
    """
    sources = pkg.get("sources", [])
    original = [s.get("title", "") for s in sources if s.get("geo:role") == "original"]
    others = [s.get("title", "") for s in sources if s.get("geo:role") != "original"]
    out: list[str] = []
    for text in [*original, pkg.get("geo:citation") or observatory_citation(), *others]:
        if text and text not in out:
            out.append(text)
    return out


def resource_years(res: dict) -> list[int]:
    """The years a resource has rows for: ``geo:years``, else every year of ``geo:period``."""
    if res.get("geo:years"):
        return [int(y) for y in res["geo:years"]]
    first, last = res["geo:period"]
    return list(range(int(first), int(last) + 1))


def years_text(years) -> str:
    """'2001–2020' for consecutive years, '2012, 2024' otherwise."""
    years = sorted(set(int(y) for y in years))
    if not years:
        return "—"
    if len(years) == 1:
        return str(years[0])
    if years == list(range(years[0], years[-1] + 1)):
        return f"{years[0]}–{years[-1]}"
    return ", ".join(map(str, years))


def field_index(ref: str | None = None) -> dict[str, dict]:
    """Every field of every dataset by name (the first dataset that defines a name wins)."""
    out: dict[str, dict] = {}
    for ds in dataset_ids(ref):
        for res in package(ds, ref)["resources"]:
            for f in res["schema"]["fields"]:
                out.setdefault(f["name"], {**f, "dataset": ds})
    return out
