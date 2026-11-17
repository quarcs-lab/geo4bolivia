"""Understanding the data: find variables, read a dataset's documentation, cite it, label and describe panels.

Everything here reads the Frictionless metadata (``metadata/*.datapackage.json``),
so it works for any dataset, including the ones you save with ``geo.save()``
once they are registered::

    geo.search("poverty")              # which variables match, in which datasets and years
    geo.info("<dataset>")              # what a dataset is, its coverage, sources, license, citation
    geo.reference_years("<dataset>")   # the actual years behind each stored year
    geo.cite("<dataset>")              # how to cite it, with the credits its sources require
    geo.labels(df)                     # {column: readable label}, for plot labels=
    geo.describe(df)                   # summary statistics per variable and year
"""

from __future__ import annotations

import html
import re
import textwrap
import unicodedata

import pandas as pd

from . import metadata, project
from .scales import get as get_scale


def _fold(text) -> str:
    """Lowercase without accents, for matching words."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.lower())


def _variables(ref=None):
    """``(dataset, field, resource)`` for every variable of every dataset, once per scale."""
    for ds in metadata.dataset_ids(ref):
        for res in metadata.package(ds, ref)["resources"]:
            for f in res["schema"]["fields"]:
                if f.get("geo:role", "variable") == "variable":
                    yield ds, f, res


def search(text: str, dataset: str | None = None, ref: str | None = None) -> pd.DataFrame:
    """Find variables whose name, label or description contain every word of ``text``.

    Matching ignores case and accents (``"educacion"`` finds "Educación"). Results
    are ranked: matches in the variable name or label come first.

    Parameters
    ----------
    text : one or more words, e.g. ``"poverty"`` or ``"night lights"``
    dataset : search only this dataset

    Returns
    -------
    One row per variable and scale: ``dataset``, ``variable``, ``label``, ``unit``,
    ``years``, ``scale``, ``units`` (with data) and ``description``. Pass the
    ``dataset`` and ``variable`` to ``geo.load(dataset, variables=variable)``.
    """
    words = _fold(text).split()
    if not words:
        raise ValueError("Pass one or more words to search for, e.g. geo.search('poverty')")
    rows = []
    for ds, f, res in _variables(ref):
        if dataset and ds != dataset:
            continue
        head = _fold(f"{f['name']} {f.get('title', '')}")
        hay = f"{head} {_fold(f.get('description', ''))} {_fold(ds)}"
        if not all(w in hay for w in words):
            continue
        rows.append({"dataset": ds, "variable": f["name"], "label": f.get("title", f["name"]),
                     "unit": f.get("geo:unit", ""), "years": metadata.years_text(metadata.resource_years(res)),
                     "scale": res["geo:scale"], "units": res.get("geo:units"),
                     "description": f.get("description", ""),
                     "_score": sum(w in head for w in words)})
    columns = ["dataset", "variable", "label", "unit", "years", "scale", "units", "description"]
    if not rows:
        return pd.DataFrame(columns=columns)
    out = pd.DataFrame(rows).sort_values(["_score", "dataset"], ascending=[False, True], kind="stable")
    out["units"] = out["units"].astype("Int64")
    return out[columns].reset_index(drop=True)


def reference_years(dataset: str, variable: str | None = None, scale: str | None = None,
                    ref: str | None = None) -> pd.DataFrame:
    """The actual years behind each stored year, one row per variable and stored year.

    Some panels store values at nominal years: the SDG Atlas, for example, stores its
    initial values at 2012 and its final values at 2024, while an indicator may come
    from a survey of 2008 and 2023.

    Parameters
    ----------
    dataset : dataset id
    variable : one variable (default: all)
    scale : the resource's scale (default: the dataset's native scale)

    Returns
    -------
    Columns ``variable``, ``label``, ``year`` (as stored) and ``reference`` (the
    actual years; the stored year when they are the same).
    """
    res = metadata.resource(dataset, scale, ref)
    years = metadata.resource_years(res)
    rows = []
    for f in res["schema"]["fields"]:
        if f.get("geo:role", "variable") != "variable" or (variable and f["name"] != variable):
            continue
        actual = f.get("geo:reference_years") or {}
        for y in years:
            if not actual or str(y) in actual:
                rows.append({"variable": f["name"], "label": f.get("title", f["name"]), "year": y,
                             "reference": str(actual.get(str(y), y))})
    if variable and not rows:
        raise ValueError(f"{dataset!r} has no variable {variable!r}; see geo.dictionary({dataset!r})")
    return pd.DataFrame(rows, columns=["variable", "label", "year", "reference"])


def _docs_url(dataset: str) -> str:
    repo = project.config()["repository"]
    return f"https://github.com/{repo}/blob/{project.config().get('default_ref', 'main')}/docs/datasets/{dataset}.md"


def _year(pkg: dict) -> str:
    return str(pkg.get("geo:updated", ""))[:4] or "n.d."


def _credits(pkg: dict) -> list[str]:
    """The credit each source asks for (originals first)."""
    sources = sorted(pkg.get("sources", []), key=lambda s: s.get("geo:role") != "original")
    out = []
    for s in sources:
        text = s.get("geo:attribution") or s.get("title", "")
        if text and text not in out:
            out.append(text)
    return out


def cite(dataset: str, style: str = "apa", ref: str | None = None) -> str:
    """How to cite a dataset: its recommended citation, then the credits its sources require.

    Parameters
    ----------
    dataset : dataset id
    style : ``"apa"`` (plain text) or ``"bibtex"``

    Returns
    -------
    A string; print it: ``print(geo.cite("<dataset>"))``.
    """
    pkg = metadata.package(dataset, ref)
    cfg = project.config()
    if style == "apa":
        head = pkg.get("geo:citation") or f"{cfg['name']} ({_year(pkg)}). {pkg['title']} [Data set]. {_docs_url(dataset)}"
    elif style == "bibtex":
        key = re.sub(r"[^a-z0-9]", "", cfg.get("short_name", cfg["name"]).lower()) + f"_{dataset}_{_year(pkg)}"
        head = (f"@misc{{{key},\n"
                f"  author       = {{{{{cfg['name']}}}}},\n"
                f"  title        = {{{{{pkg['title']}}}}},\n"
                f"  year         = {{{_year(pkg)}}},\n"
                f"  howpublished = {{\\url{{{_docs_url(dataset)}}}}},\n"
                f"  note         = {{Dataset {dataset}, {cfg['name']}}}\n}}")
    else:
        raise ValueError("style must be 'apa' or 'bibtex'")
    credits = _credits(pkg)
    if not credits:
        return head
    prefix = "% " if style == "bibtex" else ""
    lines = "\n".join(f"{prefix}- {c}" for c in credits)
    return f"{head}\n\n{prefix}Please also credit the original sources:\n{lines}"


class DatasetInfo:
    """A dataset's documentation, printed as text (or as HTML in a notebook). ``.dict`` holds it all."""

    def __init__(self, dataset: str, ref: str | None = None):
        pkg = metadata.package(dataset, ref)
        self.dataset = dataset
        self.dict = pkg
        self.title = pkg.get("title", dataset)
        self.description = pkg.get("description", "")
        self.coverage = [{"scale": r["geo:scale"], "units": r.get("geo:units"),
                          "years": metadata.years_text(metadata.resource_years(r)),
                          "variables": sum(f.get("geo:role", "variable") == "variable" for f in r["schema"]["fields"])}
                         for r in pkg["resources"]]
        mappings: dict[str, int] = {}
        for f in pkg["resources"][0]["schema"]["fields"]:
            if f.get("geo:reference_years"):
                text = "; ".join(f"{k}: {v}" for k, v in f["geo:reference_years"].items())
                mappings[text] = mappings.get(text, 0) + 1
        self.reference_years = mappings
        self.licenses = [lic.get("title") or lic.get("name", "") for lic in pkg.get("licenses", [])]
        self.sources = [{"title": s.get("title", ""), "creator": s.get("geo:creator", ""),
                         "role": s.get("geo:role", ""),
                         "license": (s.get("geo:license") or {}).get("title") or (s.get("geo:license") or {}).get("name", ""),
                         "credit": s.get("geo:attribution", "")} for s in pkg.get("sources", [])]
        self.citation = pkg.get("geo:citation", "")
        self.notes = list(pkg.get("geo:notes", []))
        self.notebooks = [n.get("title", "") for n in pkg.get("geo:notebooks", [])]
        self.docs = _docs_url(dataset)

    def _coverage_lines(self) -> list[str]:
        out = []
        for c in self.coverage:
            units = f"{c['units']} {c['scale']} units" if c["units"] is not None else f"{c['scale']} units"
            out.append(f"{units}, {c['years']}, {c['variables']} variables")
        return out

    def __repr__(self) -> str:
        wrap = lambda t, ind="  ": textwrap.fill(t, 96, initial_indent=ind, subsequent_indent=ind)
        lines = [f"{self.title}  [{self.dataset}]", "", wrap(self.description), "", "Coverage"]
        lines += [f"  - {t}" for t in self._coverage_lines()]
        if self.reference_years:
            lines += ["", "Actual years behind the stored years (geo.reference_years)"]
            lines += [f"  - {k}  ({n} variables)" for k, n in self.reference_years.items()]
        lines += ["", "License of the published files", *[f"  - {lic}" for lic in self.licenses], "", "Sources"]
        for s in self.sources:
            lines.append(wrap(f"- {s['title']}"))
            if s["license"]:
                lines.append(wrap(f"License: {s['license']}", "    "))
        if self.citation:
            lines += ["", "Cite as (geo.cite)", wrap(self.citation)]
        if self.notes:
            lines += ["", "Notes", *[wrap(f"- {n}") for n in self.notes]]
        if self.notebooks:
            lines += ["", "Notebooks", *[f"  - {n}" for n in self.notebooks]]
        lines += ["", f"Documentation: {self.docs}"]
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        e = html.escape
        li = lambda items: "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"
        parts = [f"<h3>{e(self.title)} <code>{e(self.dataset)}</code></h3>", f"<p>{e(self.description)}</p>",
                 "<h4>Coverage</h4>", li(self._coverage_lines())]
        if self.reference_years:
            parts += ["<h4>Actual years behind the stored years</h4>",
                      li(f"{k} ({n} variables)" for k, n in self.reference_years.items())]
        parts += ["<h4>License of the published files</h4>", li(self.licenses), "<h4>Sources</h4>",
                  li(f"{s['title']}" + (f" — License: {s['license']}" if s["license"] else "") for s in self.sources)]
        if self.citation:
            parts += ["<h4>Cite as</h4>", f"<p>{e(self.citation)}</p>"]
        if self.notes:
            parts += ["<h4>Notes</h4>", li(self.notes)]
        if self.notebooks:
            parts += ["<h4>Notebooks</h4>", li(self.notebooks)]
        parts.append(f'<p><a href="{e(self.docs)}" target="_blank">Documentation</a></p>')
        return "<div>" + "".join(parts) + "</div>"


def info(dataset: str, ref: str | None = None) -> DatasetInfo:
    """What a dataset is: description, coverage (scales, units, years), actual reference
    years, license, sources with their licenses, citation, notes and notebooks.

    Parameters
    ----------
    dataset : dataset id (see ``geo.datasets()``)

    Returns
    -------
    A ``DatasetInfo``: in a notebook it displays as formatted HTML; ``print()``
    gives plain text, and ``.dict`` the full datapackage.
    """
    return DatasetInfo(dataset, ref)


# --- labels and summaries ----------------------------------------------------------------

_DERIVED = [  # suffixes written by geo.change(), most specific first
    (r"^(?P<v>.+)_pct_change$", "% change in {label}"),
    (r"^(?P<v>.+)_annual_change$", "Annual change in {label}"),
    (r"^(?P<v>.+)_rank_change$", "Rank change in {label}"),
    (r"^(?P<v>.+)_rank_(?P<y>\d{4})$", "Rank in {label}, {y}"),
    (r"^(?P<v>.+)_change$", "Change in {label}"),
    (r"^(?P<v>.+)_(?P<y>\d{4})$", "{label}, {y}"),
]


def _scale_label(name: str) -> str | None:
    try:
        return get_scale(name).label
    except KeyError:
        return None


def labels(data, ref: str | None = None) -> dict[str, str]:
    """Readable labels for the columns of a panel (or every field of a dataset id).

    Variables take their metadata ``title``; columns written by ``geo.change()``
    (``<var>_2024``, ``<var>_change``...) are labelled from their variable; group
    columns (``department``) take the scale's label.

    Parameters
    ----------
    data : a panel (any DataFrame) or a dataset id

    Returns
    -------
    ``{column: label}`` for the columns it knows. Pass it to Plotly:
    ``px.scatter(df, x=..., y=..., labels=geo.labels(df))``.
    """
    if isinstance(data, str):
        return {f["name"]: f.get("title", f["name"]) for f in metadata.fields(data, ref=ref)}
    known = {k: f.get("title", k) for k, f in metadata.field_index(ref).items()}
    known.update({"geo_id": "geo ID", "name": "Unit name", "year": "Year", "n_units": "Units",
                  "coverage": "Share of units with data", "scale": "Scale"})
    out = {}
    for col in data.columns:
        if col in known:
            out[col] = known[col]
            continue
        scale_label = _scale_label(col)
        if scale_label:
            out[col] = scale_label
            continue
        for pattern, template in _DERIVED:
            m = re.match(pattern, col)
            if m and m.group("v") in known:
                out[col] = template.format(label=known[m.group("v")], y=m.groupdict().get("y", ""))
                break
    return out


def describe(df: pd.DataFrame, variables=None, by: str | None = "year", ref: str | None = None) -> pd.DataFrame:
    """Summary statistics of a panel's variables, per ``by`` group (default: per year).

    Parameters
    ----------
    df : a panel, e.g. from ``geo.load``
    variables : a variable or list of them (default: every numeric variable)
    by : a column to group by: ``"year"`` (default), ``None`` to pool all rows, or a
        group such as ``"department"`` (after ``geo.load(..., groups=["department"])``)

    Returns
    -------
    One row per variable (and group): ``variable``, ``label``, ``unit``, ``count``,
    ``mean``, ``std``, ``min``, ``p25``, ``median``, ``p75`` and ``max``.
    """
    skip = {"geo_id", "year", "n_units", "coverage"} | ({by} if by else set())
    if variables is None:
        variables = [c for c in df.columns if c not in skip and c != "geometry" and not c.endswith("_id")
                     and pd.api.types.is_numeric_dtype(df[c])]
    elif isinstance(variables, str):
        variables = [variables]
    index = metadata.field_index(ref)
    names = labels(df[[*variables]], ref=ref)
    data = df.drop(columns="geometry", errors="ignore")
    long = data.melt(id_vars=[by] if by else [], value_vars=variables, var_name="variable")
    keys = ["variable", by] if by else ["variable"]
    g = long.groupby(keys, sort=False)["value"]
    out = pd.DataFrame({"count": g.count(), "mean": g.mean(), "std": g.std(), "min": g.min(),
                        "p25": g.quantile(0.25), "median": g.median(), "p75": g.quantile(0.75),
                        "max": g.max()}).reset_index()
    out.insert(1, "label", out["variable"].map(names).fillna(out["variable"]))
    out.insert(2, "unit", out["variable"].map(lambda v: index.get(v, {}).get("geo:unit", "")))
    order = {v: i for i, v in enumerate(variables)}
    out = out.sort_values([by] if by else [], kind="stable") if by else out
    out = out.sort_values("variable", key=lambda s: s.map(order), kind="stable").reset_index(drop=True)
    return out
