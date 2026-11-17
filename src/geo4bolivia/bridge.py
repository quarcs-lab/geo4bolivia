"""Hand data to companion packages.

Two companion packages analyse the panels this package loads or builds. Both take
a long panel ``df`` and a data dictionary (one row per column with ``var_name``,
``var_def``, ``label``, ``type``, ``role``, ``can_be_na``):

- `geometrics <https://quarcs-lab.github.io/geometrics/>`_: regional growth,
  convergence and inequality with spatial methods; also needs geometries (``gdf``)::

      gdf, df, df_dict = geo.for_geometrics("<dataset>", variables="<variable>")
      df = gm.set_labels(df, df_dict, set_panel=True)
      gm.analyze_beta_convergence(df, "<variable>", gdf=gdf, w=gm.make_weights(gdf))  # levels

- `expdpy <https://cmg777.github.io/expdpy/>`_: panel exploration and panel
  econometrics (within/between, fixed and random effects, Hausman, clustered SEs)::

      df, df_def = geo.for_expdpy("<dataset>", groups=["<coarser scale>"])
      df = ex.set_labels(df, df_def, set_panel=True)
      ex.analyze_panel_table(df, "<y>", ["<x>"])
"""

from __future__ import annotations

import pandas as pd

from . import io, metadata
from .scales import ancestors, scale_of
from .scales import get as get_scale


def _describe(fields) -> dict:
    """``{name: (label, definition)}`` from metadata fields."""
    out = {}
    for f in fields:
        unit = f.get("geo:unit")
        out[f["name"]] = (f.get("title") or f.get("description", ""),
                          f.get("description", "") + (f" ({unit})" if unit else ""))
    return out


def _group_label(scale: str, ref=None) -> tuple[str, str]:
    label = get_scale(scale, ref).label
    return f"{label} name", f"Name of the {label} the unit lies in"


def _panel_inputs(data, scale, years, variables, labels, groups, ref):
    """The shared work: panel with names (and group names), data dictionary, and the scale."""
    if isinstance(data, str):
        df = io.load(data, scale=scale, years=years, variables=variables, ref=ref)
        scale = metadata.resource(data, scale, ref)["geo:scale"]
        described = _describe(metadata.fields(data, scale, ref))
    else:
        # your own panel: columns named like published variables keep their metadata labels
        described = {k: v for k, v in _describe(metadata.field_index(ref).values()).items()}
        df = data.drop(columns="geometry", errors="ignore").copy()
        if scale is None:
            found = {scale_of(i, ref) for i in df["geo_id"].dropna().drop_duplicates()}
            if len(found) != 1:
                raise ValueError(f"Rows mix units from several scales: {sorted(found)}")
            scale = found.pop()
    for name, text in (labels or {}).items():
        described[name] = (text, text)

    groups = [groups] if isinstance(groups, str) else list(groups or [])
    present = [c for c in df.columns if c in ancestors(scale, ref) and c not in groups]  # from an earlier call
    df = io.add_names(df, groups=present + groups, scale=scale, ref=ref).reset_index(drop=True)
    for col in present + groups:
        described[col] = _group_label(col, ref)

    rows = []
    for col in df.columns:
        if col == "geo_id":
            typ, role, text = "entity", "", ("geo ID", "geo ID")
        elif col == "name":
            typ, role, text = "factor", "entity_name", ("Unit name", "Name")
        elif col == "year":
            typ, role, text = "time", "", ("Year", "Year")
        else:
            typ = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "factor"
            role, text = "", described.get(col, ("", ""))
        rows.append({"var_name": col, "var_def": text[1], "label": text[0] or col, "type": typ, "role": role,
                     "can_be_na": typ not in ("entity", "time")})
    return df, pd.DataFrame(rows), scale


def for_geometrics(data, scale: str | None = None, years=None, variables=None, labels: dict | None = None,
                   groups=None, ref: str | None = None):
    """``(gdf, df, df_dict)`` in the format geometrics expects.

    Parameters
    ----------
    data : a dataset id (see ``geo.datasets()``) or your own panel with ``geo_id`` and ``year``
        (from ``geo.link``, ``geo.combine``, ``geo.zonal``...)
    scale, years, variables : as in ``geo.load`` (for a dataset id)
    labels : ``{variable: description}`` for your own columns (dataset variables are
        described from the metadata)
    groups : coarser scales whose unit names to add as columns, e.g. ``["province"]``

    Returns
    -------
    gdf : GeoDataFrame with ``geo_id`` and ``geometry`` (EPSG:4326)
    df : the panel with ``geo_id``, ``name``, ``year``, the group names and the variables
    df_dict : one row per ``df`` column with ``var_name``, ``var_def``, ``label``,
        ``type`` (entity / time / factor / numeric), ``role`` and ``can_be_na``
    """
    df, df_dict, scale = _panel_inputs(data, scale, years, variables, labels, groups, ref)
    gdf = io.boundaries(scale, ref=ref)[["geo_id", "geometry"]]
    gdf = gdf[gdf["geo_id"].isin(df["geo_id"])].reset_index(drop=True)
    return gdf, df, df_dict


def for_expdpy(data, scale: str | None = None, years=None, variables=None, labels: dict | None = None,
               groups=None, ref: str | None = None):
    """``(df, df_def)`` in the format expdpy expects.

    Parameters
    ----------
    data : a dataset id or your own panel with ``geo_id`` and ``year``
    scale, years, variables : as in ``geo.load`` (for a dataset id)
    labels : ``{variable: description}`` for your own columns
    groups : coarser scales whose unit names to add as columns

    These are the parameters of ``for_geometrics``. ``groups`` is handy for expdpy's
    by-group views, e.g. ``groups=["department"]`` adds a ``department`` column
    (the department's name) for ``ex.explore_trend_plot_by_group``.

    Returns
    -------
    df : the panel with ``geo_id``, ``name``, ``year``, the group names and the variables
    df_def : the data dictionary (``var_name``, ``var_def``, ``label``, ``type``,
        ``role``, ``can_be_na``); pass both to ``ex.set_labels(df, df_def, set_panel=True)``
    """
    df, df_def, _ = _panel_inputs(data, scale, years, variables, labels, groups, ref)
    return df, df_def
