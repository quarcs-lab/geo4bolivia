"""Stata files: each dataset's long panel as a ``.dta`` that documents itself.

``data/<dataset>/<scale>/<dataset>.dta`` (written by ``build.common.publish_stata``, checked by
``validate``) holds one row per unit and year, in Stata's format 118 (Stata 14 and later; Unicode):

- ``unit_id`` (1..N in ``geo_id`` order, value-labelled "Name (Department)"), ``geo_id``, ``year``;
- the unit's name and, for each coarser scale it lies in, its geo ID, name and a value-labelled
  numeric code (``province_id``, ``province``, ``province_code``, ...);
- the dataset's source keys and ``area_km2``;
- the variables, under the names they have in every other format.

Every column has a label (the metadata's ``title``, at most 80 characters) and notes (``notes
<variable>`` in Stata: how it was built, its unit, source, aggregation and reference years); the
dataset has a label (its title) and notes (``notes _dta``: description, how to cite, license,
links, caveats). The file opens declared as a panel (``xtset unit_id year``).

pandas writes the data, labels and value labels; Stata's notes and panel settings are
*characteristics*, which pandas leaves empty, so ``_Writer`` writes that section of the file and
``characteristics()`` reads it back (format 118: each ``<ch>`` holds a 4-byte length, a 129-byte
variable name, a 129-byte characteristic name and the null-terminated text).
"""

from __future__ import annotations

import re
import struct
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from pandas.io.stata import StataReader, StataWriterUTF8

from . import io, metadata, project, store
from .scales import get as get_scale

VERSION = 118
NAME_BYTES = 129
LABEL_CHARS = 80
# The characteristics `xtset <panel> <time>` stores (a time step of 1, Stata's %21x for 1.0)
PANEL = "unit_id"


def stata_path(dataset: str, scale: str) -> str:
    """Where a dataset's Stata file goes: next to its panel, ``data/<dataset>/<scale>/<dataset>.dta``."""
    return f"data/{dataset}/{scale}/{dataset}.dta"


def _short(text: str, n: int = LABEL_CHARS) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _plain(text: str) -> str:
    """Markdown to plain text for Stata's notes."""
    return " ".join(str(text).replace("`", "").split())


def _scale_word(scale: str) -> str:
    """'Municipality' for 'Municipality (map343, SDSN Bolivia 2025)'."""
    return get_scale(scale).label.split(" (")[0]


def panel_settings(panel: str = PANEL, time: str = "year") -> list[tuple[str, str, str]]:
    """The ``_dta`` characteristics of ``xtset <panel> <time>`` with a step of 1."""
    return [("_dta", "_TSpanel", panel), ("_dta", "_TSdelta", "+1.0000000000000X+000"),
            ("_dta", "_TSitrvl", "1"), ("_dta", "_TStvar", time), ("_dta", "tis", time),
            ("_dta", "iis", panel)]


def _notes(var: str, texts: list[str]) -> list[tuple[str, str, str]]:
    texts = [t for t in texts if t]
    return [(var, "note0", str(len(texts)))] + [(var, f"note{i}", t) for i, t in enumerate(texts, 1)]


def contents(dataset: str, scale: str | None = None, ref: str | None = None) -> dict:
    """Everything the Stata file holds: ``data`` (the table), ``data_label``, ``variable_labels``,
    ``value_labels`` and ``characteristics`` (``(variable, name, text)``: notes and panel settings)."""
    pkg = metadata.package(dataset, ref)
    res = metadata.resource(dataset, scale, ref)
    sid = res["geo:scale"]
    fields = {f["name"]: f for f in res["schema"]["fields"]}
    long = pd.read_parquet(store.open_binary(res["geo:parquet"], ref))
    word = _scale_word(sid)

    unit_table = io.units(sid, ref=ref).sort_values("geo_id").reset_index(drop=True)
    ids = pd.DataFrame({"geo_id": unit_table["geo_id"], "unit_id": range(1, len(unit_table) + 1),
                        "name": unit_table["name"]})
    groups = io.wide_id_columns(sid, ref)        # coarser scales, finest first (province, department)
    value_labels: dict[str, dict[int, str]] = {}
    labels: dict[str, str] = {}
    notes: dict[str, list[str]] = {}
    group_cols: list[str] = []
    for g in groups:
        gw = _scale_word(g)
        table = io.units(g, ref=ref).sort_values("geo_id").reset_index(drop=True)
        names = table.set_index("geo_id")["name"]
        codes = {gid: i for i, gid in enumerate(table["geo_id"], 1)}
        # a name used twice in a scale (e.g. four provinces called Cercado) gets its parent's name
        parent = get_scale(g).parent
        parent_names = io.units(parent, ref=ref).set_index("geo_id")["name"] if parent and parent in groups else None
        dup = names[names.duplicated(keep=False)].index
        shown = {gid: (f"{names[gid]} ({parent_names[table.set_index('geo_id').loc[gid, 'parent_id']]})"
                       if parent_names is not None and gid in dup else names[gid]) for gid in table["geo_id"]}
        ids[f"{g}_id"] = unit_table[f"{g}_id"]
        ids[g] = ids[f"{g}_id"].map(names)
        ids[f"{g}_code"] = ids[f"{g}_id"].map(codes).astype("int32")
        value_labels[f"{g}_code"] = {codes[gid]: shown[gid] for gid in table["geo_id"]}
        labels[f"{g}_id"] = _short(f"{gw} geo ID")
        labels[g] = _short(f"{gw} name")
        labels[f"{g}_code"] = _short(f"{gw} (numeric code, labelled with its name)")
        notes[f"{g}_id"] = [f"Geo ID of the {gw.lower()} the unit lies in ({g} in the observatory's geo/units)."]
        notes[g] = [f"Name of the {gw.lower()} the unit lies in."]
        notes[f"{g}_code"] = [f"The {gw.lower()} as a number, 1 to {len(table)} in geo ID order, labelled with "
                              f"its name, for factor variables such as i.{g}_code."]
        group_cols += [f"{g}_id", g, f"{g}_code"]
    coarsest = groups[-1] if groups else None
    if coarsest:
        top = ids[coarsest]
        value_labels[PANEL] = {int(u): f"{n} ({t})" for u, n, t in zip(ids["unit_id"], ids["name"], top)}
    else:
        value_labels[PANEL] = {int(u): n for u, n in zip(ids["unit_id"], ids["name"])}
    ids["area_km2"] = unit_table["area_km2"].astype("float64")

    keys = [f["name"] for f in res["schema"]["fields"] if f.get("geo:role") == "source_key"]
    variables = [f["name"] for f in res["schema"]["fields"] if f.get("geo:role", "variable") == "variable"]
    df = long[["geo_id", "year", *keys, *variables]].merge(ids, on="geo_id", how="left", validate="many_to_one")
    order = [PANEL, "geo_id", "year", "name", *group_cols, *keys, "area_km2", *variables]
    df = df[order].sort_values([PANEL, "year"]).reset_index(drop=True)
    for col in df.columns:   # types Stata takes: nullable integers with gaps become floats (missing: .)
        s = df[col]
        if isinstance(s.dtype, pd.StringDtype) or s.dtype == object:
            df[col] = s.astype("object").where(s.notna(), "").astype(str)
        elif pd.api.types.is_integer_dtype(s.dtype):
            fits = s.notna().all() and (s.dropna().abs() < 2_147_483_620).all()
            df[col] = s.astype("int32") if fits else s.astype("float64")
        elif pd.api.types.is_bool_dtype(s.dtype):
            df[col] = s.astype("float64")
        else:
            df[col] = s.astype("float64")
    df[PANEL] = df[PANEL].astype("int32")
    df["year"] = df["year"].astype("int32")

    labels.update({
        PANEL: _short(f"Panel unit: {word.lower()} 1 to {len(ids)}, labelled with its name"),
        "name": _short(f"{word} name"),
        "area_km2": "Area (km²)",
    })
    notes[PANEL] = [f"A number for each {word.lower()} of the map {sid} (1 to {len(ids)}, in geo ID order), labelled "
                    f"with its name{' and ' + _scale_word(coarsest).lower() if coarsest else ''}; the panel variable of "
                    "xtset unit_id year. geo_id is the same unit as text, the key shared with every other file "
                    "of the observatory."]
    notes["name"] = [f"Name of the {word.lower()}."]
    notes["area_km2"] = [f"Area of the {word.lower()} in km², measured on its boundary in the project's equal-area "
                         "projection."]
    for name in ["geo_id", "year", *keys, *variables]:
        f = fields.get(name, {})
        labels[name] = _short(f.get("title") or name)
        texts = [_plain(f.get("description", ""))]
        extra = []
        if f.get("geo:unit"):
            extra.append(f"Unit: {f['geo:unit']}.")
        if f.get("geo:source"):
            extra.append(f"Source: {_plain(f['geo:source'])}.")
        if f.get("geo:role", "variable") == "variable":
            extra.append(f"Aggregation to coarser units: {f.get('geo:aggregation', 'none')}.")
        texts.append(" ".join(extra))
        if f.get("geo:reference_years"):
            texts.append("Actual reference years of the stored years: "
                         + "; ".join(f"{k}: {v}" for k, v in f["geo:reference_years"].items()) + ".")
        notes[name] = texts

    cfg = project.config()
    repo, website = cfg["repository"], cfg.get("website", "")
    folder = f"https://github.com/{repo}/tree/{cfg.get('default_ref', 'main')}/data/{dataset}"
    years = metadata.years_text(long["year"])
    cites = metadata.citations(pkg)
    lic = "; ".join(f"{x.get('title') or x.get('name') or 'unnamed license'}" + (f" ({x['path']})" if x.get("path") else "")
                    for x in pkg.get("licenses", []))
    credits = [f"{s.get('geo:creator') or s.get('title', '')}: {s['geo:license'].get('title') or s['geo:license'].get('name', '')}"
               + (f"; required credit: {s['geo:attribution']}" if s.get("geo:attribution") else "")
               + (f"; {s['geo:homepage']}" if s.get("geo:homepage") else "")
               for s in pkg.get("sources", []) if s.get("geo:license")]
    dataset_notes = [
        f"{pkg['title']}. {_plain(pkg['description'])}",
        f"One row per {word.lower()} and year: {df['geo_id'].nunique()} units "
        f"({get_scale(sid).label[len(word):].strip(' ()') or sid}), years {years}, {len(df):,} rows. "
        "Declared as a panel: xtset unit_id year.",
        f"Variable names are those of the observatory's CSV, Parquet and wide files and of the Python package "
        f"{project.PACKAGE}. Each label is a short name; notes <variable> shows how the variable was built, its "
        "unit, source, aggregation and reference years.",
        *[f"How to cite ({i} of {len(cites)}, in this order): {c}" for i, c in enumerate(cites, 1)],
        f"License of this file: {lic}. " + " ".join(f"{c}." for c in credits),
        f"Documentation, metadata and every format: {folder}" + (f" . Website: {website}" if website else ""),
        *[f"Note: {_plain(n)}" for n in pkg.get("geo:notes", [])],
        f"Generated by {project.PACKAGE} from data/{dataset}/datapackage.json"
        + (f", updated {pkg['geo:updated']}" if pkg.get("geo:updated") else "") + ".",
    ]
    chars = _notes("_dta", dataset_notes) + panel_settings()
    for col in df.columns:
        chars += _notes(col, notes.get(col, []))
    return {"data": df, "data_label": _short(pkg["title"]), "variable_labels": {c: labels[c] for c in df.columns},
            "value_labels": value_labels, "characteristics": chars,
            "time_stamp": datetime.fromisoformat(str(pkg.get("geo:updated") or "2000-01-01")[:10])}


class _Writer(StataWriterUTF8):
    """pandas' format-118 writer, plus Stata's characteristics (notes and panel settings)."""

    def __init__(self, *args, characteristics=(), **kwargs):
        self._characteristics = list(characteristics)
        super().__init__(*args, **kwargs)

    def _write_characteristics(self) -> None:
        self._update_map("characteristics")
        fixed = lambda s: s.encode("utf-8")[: NAME_BYTES - 1].ljust(NAME_BYTES, b"\0")
        bio = BytesIO()
        for var, name, text in self._characteristics:
            body = fixed(var) + fixed(name) + text.encode("utf-8") + b"\0"
            bio.write(b"<ch>" + struct.pack(f"{self._byteorder}I", len(body)) + body + b"</ch>")
        self._write_bytes(self._tag(bio.getvalue(), "characteristics"))


def write(dataset: str, scale: str, path: str | Path, ref: str | None = None) -> dict:
    """Write the dataset's Stata file; returns its ``contents``."""
    c = contents(dataset, scale, ref)
    writer = _Writer(path, c["data"], write_index=False, byteorder="<", version=VERSION,
                     data_label=c["data_label"], variable_labels=c["variable_labels"],
                     value_labels=c["value_labels"], time_stamp=c["time_stamp"],
                     characteristics=c["characteristics"])
    writer.write_file()
    return c


def characteristics(path: str | Path) -> list[tuple[str, str, str]]:
    """The characteristics of a format-118 ``.dta`` file: ``(variable, name, text)``, in file order."""
    raw = Path(path).read_bytes()
    order = "<" if re.search(rb"<byteorder>LSF</byteorder>", raw[:200]) else ">"
    start = raw.index(b"<characteristics>") + len(b"<characteristics>")
    out, pos = [], start
    while raw.startswith(b"<ch>", pos):
        (n,) = struct.unpack(f"{order}I", raw[pos + 4: pos + 8])
        body = raw[pos + 8: pos + 8 + n]
        name = lambda b: b.split(b"\0", 1)[0].decode("utf-8")
        out.append((name(body[:NAME_BYTES]), name(body[NAME_BYTES: 2 * NAME_BYTES]),
                    body[2 * NAME_BYTES:].rstrip(b"\0").decode("utf-8")))
        pos += 8 + n + len(b"</ch>")
    if not raw.startswith(b"</characteristics>", pos):
        raise ValueError(f"{path}: unreadable characteristics")
    return out


def read(path: str | Path) -> dict:
    """What a Stata file holds, in the shape of ``contents``."""
    with StataReader(path, convert_categoricals=False) as r:
        data = r.read()
        return {"data": data, "data_label": r.data_label, "variable_labels": r.variable_labels(),
                "value_labels": r.value_labels(), "characteristics": characteristics(path)}
