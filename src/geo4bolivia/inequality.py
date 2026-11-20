"""Inequality between units: Gini, Theil and the coefficient of variation in each year,
the Lorenz curve, and Theil's index split between and within groups of units."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from . import _inputs, io
from ._engine._types import InequalityOverTimeResult, TheilDecompositionResult
from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE
from ._inputs import ENTITY, NAME, TIME
from .scales import ancestors, scale_of

_ENGINE_TIME = "time"       # the inequality engine's name for the year column of its tables
_MAX_CURVES = 4             # with more years, the Lorenz figure draws the first and the last
_REFLINE = {"dash": "dash", "color": "rgba(0,0,0,0.35)", "width": 1}


# --- results --------------------------------------------------------------------------------

def _engine_view(result):
    """The result as the interpretation texts read it (their year column is ``time``)."""
    return dataclasses.replace(result, df=result.df.rename(columns={TIME: _ENGINE_TIME}))


@dataclass(frozen=True, repr=False)
class InequalityResult(InequalityOverTimeResult):
    """Inequality between units in each year, its trend and the Lorenz curve.

    ``df`` has one row per year (``year``, ``n_units`` and one column per measure, plus
    ``gini_spatial`` and ``gini_spatial_p`` with weights); ``summary`` one row per
    measure (its value in the first and the last year, their change and the log-trend);
    ``lorenz`` one row per unit and year, sorted from the lowest value to the highest,
    with the cumulative shares of units (``cum_units``) and of the variable
    (``cum_share``); ``fig_lorenz`` draws them.
    """

    lorenz: pd.DataFrame | None = None
    fig_lorenz: Any = None

    @property
    def n_years(self) -> int:
        """The number of years compared."""
        return self.n_periods

    def lorenz_share(self, year, share: float) -> float:
        """The share of the variable held by the ``share`` of units with the lowest values, in ``year``."""
        if self.lorenz is None:
            raise ValueError("This result has no Lorenz curve (see its notes)")
        rows = self.lorenz[self.lorenz[TIME] == year]
        return float(np.interp(share, [0.0, *rows["cum_units"]], [0.0, *rows["cum_share"]]))

    def interpret(self, *, lang: str = "en") -> str:
        """Plain-language reading of the level of inequality, its change and the Lorenz curve."""
        from ._engine.pedagogy._interpret import interpret_inequality_over_time

        years = list(self.df[TIME])
        lines, short = [], False
        for line in interpret_inequality_over_time(_engine_view(self), lang=lang).split("\n\n")[:-1]:
            if self.n_periods < 3 and "could not be estimated" in line:
                if not short:           # one sentence instead of one per measure
                    lines.append(f"With two years ({years[0]} and {years[-1]}) the measures can be compared, but "
                                 "their trend cannot be tested: that needs three or more years.")
                short = True
                continue
            lines.append(line)
        if self.lorenz is not None:
            first, last = years[0], years[-1]
            low, top = (lambda y: self.lorenz_share(y, 0.5)), (lambda y: 1 - self.lorenz_share(y, 0.9))
            lines.append(
                f"On the Lorenz curve of {last}, the half of the units with the lowest values holds "
                f"{low(last):.0%} of the total ({low(first):.0%} in {first}) and the tenth with the highest "
                f"values holds {top(last):.0%} ({top(first):.0%}); with no inequality they would hold 50% and 10%.")
        return "\n\n".join([*lines, _ASSOC_NOTE])


@dataclass(frozen=True, repr=False)
class TheilResult(TheilDecompositionResult):
    """Theil's index in each year, split into inequality between groups and within them.

    ``df`` has one row per year: ``year``, ``theil``, ``between``, ``within``,
    ``between_share`` (and ``p_between`` with permutations). ``by`` is the grouping
    column, with ``n_groups`` groups.
    """

    @property
    def by(self) -> str:
        """The grouping column (the engine calls it ``group``)."""
        return self.group

    def interpret(self, *, lang: str = "en") -> str:
        """Plain-language reading of the split between and within groups."""
        from ._engine.pedagogy._interpret import interpret_theil_decomposition

        lines = interpret_theil_decomposition(_engine_view(self), lang=lang).split("\n\n")
        shares = self.df["between_share"].dropna()
        if len(shares) > 1 and f"{shares.iloc[0]:.0%}" == f"{shares.iloc[-1]:.0%}":
            # The engine reads any difference as a rise or a fall, even one that rounds away ("from 6% to 6%").
            lines = [f"Over the window, the between-group share stayed at about {shares.iloc[-1]:.0%}."
                     if line.startswith("Over the window, the between-group share") else line for line in lines]
        return "\n\n".join(lines)


def _as(cls, result, **changes):
    """An engine result as ``cls`` (a subclass of its class), with ``year`` instead of ``time`` in ``df``."""
    values = {f.name: getattr(result, f.name) for f in dataclasses.fields(result)}
    values["df"] = values["df"].rename(columns={_ENGINE_TIME: TIME})
    return cls(**{**values, **changes})


# --- checks ---------------------------------------------------------------------------------

def _require_years(df: pd.DataFrame, what: str) -> None:
    if TIME not in df.columns:
        raise ValueError(f"The table needs a {TIME!r} column: {what} is measured in each year")


def _require_positive(df: pd.DataFrame, variable: str, hint: str = "") -> None:
    """Theil's index takes logarithms of shares: say which rows cannot enter it."""
    bad = df[df[variable] <= 0]
    if len(bad):
        names = bad[NAME] if NAME in bad.columns else bad[ENTITY]
        where = ", ".join(f"{n} in {y}" for n, y in list(zip(names, bad[TIME], strict=True))[:3])
        raise ValueError(f"Theil's index needs strictly positive values, but {variable!r} has {len(bad)} "
                         f"value(s) <= 0 (e.g. {where}){hint}")


def _window(df: pd.DataFrame, variable: str, first, last) -> pd.DataFrame:
    """The rows from ``first`` to ``last`` (both checked against the years with data)."""
    have = _inputs.years(df, variable)
    if not have:
        raise ValueError(f"No rows with data for {variable!r}")
    lo = _inputs.pick_year(df, variable, first) if first is not None else have[0]
    hi = _inputs.pick_year(df, variable, last) if last is not None else have[-1]
    if lo > hi:
        raise ValueError(f"first ({lo}) must not be after last ({hi})")
    kept = [y for y in have if lo <= y <= hi]
    if len(kept) < 2:
        asked = "" if first is None and last is None else f" from {lo} to {hi}"
        raise ValueError(f"inequality compares years, so it needs at least two with data for {variable!r}; "
                         f"the table has {kept}{asked}" + (f" (years with data: {have})" if asked else ""))
    out = df[df[TIME].isin(kept)].reset_index(drop=True)
    out.attrs = dict(df.attrs)
    return out


# --- the Lorenz curve -----------------------------------------------------------------------

def _lorenz_table(df: pd.DataFrame, variable: str) -> pd.DataFrame | None:
    """One row per unit and year, from the lowest value to the highest, with cumulative shares.

    ``None`` when the curve is not defined (negative values, or a total that is not positive).
    """
    cols = [c for c in (ENTITY, NAME, TIME, variable) if c in df.columns]
    rows = df[cols].dropna(subset=[variable]).drop_duplicates([ENTITY, TIME])
    if (rows[variable] < 0).any() or (rows.groupby(TIME)[variable].sum() <= 0).any():
        return None
    rows = rows.sort_values([TIME, variable, ENTITY], kind="stable").reset_index(drop=True)
    by_year = rows.groupby(TIME)[variable]
    rows["cum_units"] = (by_year.cumcount() + 1) / by_year.transform("size")
    rows["cum_share"] = by_year.cumsum() / by_year.transform("sum")
    return rows


def _lorenz_fig(table: pd.DataFrame, variable: str, label: str, gini: dict):
    """The Lorenz curve of each year (the first and the last when there are many) and the line of equality."""
    import plotly.graph_objects as go

    from ._engine._theme import apply_default_layout, color_for

    years = sorted(table[TIME].unique().tolist())
    shown = years if len(years) <= _MAX_CURVES else [years[0], years[-1]]
    fig = go.Figure(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Equality", line=_REFLINE, hoverinfo="skip"))
    for i, year in enumerate(shown):
        rows = table[table[TIME] == year]
        names = rows[NAME] if NAME in rows.columns else rows[ENTITY]
        value = gini.get(year, float("nan"))
        fig.add_trace(go.Scatter(
            x=[0.0, *rows["cum_units"]], y=[0.0, *rows["cum_share"]], mode="lines",
            name=f"{year} (Gini {value:.3f})" if math.isfinite(value) else str(year),
            line={"color": color_for(i), "width": 2},
            text=["", *(f"{n}: {v:.4g}" for n, v in zip(names, rows[variable], strict=True))],
            hovertemplate=f"%{{text}}<br>the lowest %{{x:.1%}} of units hold %{{y:.1%}} of the total<extra>{year}</extra>"))
    apply_default_layout(
        fig, title=f"Lorenz curve: {label}",
        subtitle=None if len(shown) == len(years) else f"First and last of {len(years)} years",
        xaxis={"title": "Cumulative share of units, from the lowest value to the highest",
               "tickformat": ".0%", "range": [0, 1]},
        yaxis={"title": "Cumulative share of the total", "tickformat": ".0%", "range": [0, 1]})
    return fig


# --- inequality in each year ----------------------------------------------------------------

def _with_levels(summary: pd.DataFrame, tab: pd.DataFrame) -> pd.DataFrame:
    """The trend table with each measure's value in the first and the last year, and their change."""
    out = summary.copy()
    first = [float(tab[m].iloc[0]) for m in out["measure"]]
    last = [float(tab[m].iloc[-1]) for m in out["measure"]]
    out.insert(1, "first", first)
    out.insert(2, "last", last)
    out.insert(3, "change", [b - a for a, b in zip(first, last, strict=True)])
    return out


def _levels_gt(tab: pd.DataFrame, label: str, n_units: int):
    """With two years there is no trend to tabulate: the measures in both years and their change."""
    from great_tables import GT

    from ._engine.regional_inequality import _MEASURE_LABELS

    def text(value: float, pattern: str = "{:.4g}") -> str:
        return pattern.format(value) if math.isfinite(value) else "—"

    y0, y1 = tab[TIME].iloc[0], tab[TIME].iloc[-1]
    rows = [(m, float(tab[m].iloc[0]), float(tab[m].iloc[-1])) for m in _MEASURE_LABELS if m in tab.columns]
    disp = pd.DataFrame({
        "Measure": [_MEASURE_LABELS[m] for m, _, _ in rows],
        str(y0): [text(a) for _, a, _ in rows],
        str(y1): [text(b) for _, _, b in rows],
        "Change": [text(b - a, "{:+.4g}") for _, a, b in rows],
        "Change (%)": [text((b / a - 1) * 100 if a else float("nan"), "{:+.1f}") for _, a, b in rows]})
    return (GT(disp, rowname_col="Measure")
            .tab_header(title=f"Inequality: {label}", subtitle=f"{y0} and {y1}, {n_units} units")
            .tab_source_note("With two years the measures can be compared, but their trend cannot be tested: "
                             "that needs three or more years."))


def inequality(data, variable: str, *, measures=("gini", "theil"), first=None, last=None, spatial: bool = False,
               w=None, permutations: int = 99, lorenz: bool = True, title: str | None = None, gdf=None,
               ref: str | None = None) -> InequalityResult:
    """Inequality between units in each year: is it narrowing or widening?

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to measure, in levels (not logs)
    measures
        ``"gini"``, ``"theil"`` (needs strictly positive values) and/or ``"cv"``
        (the coefficient of variation: standard deviation over the mean)
    first, last
        The first and the last year to use (default: every year with data);
        the years between them are used too
    spatial
        Add the spatial Gini: the part of the Gini owed to pairs of neighbouring
        units, with a permutation test. It needs boundaries and weights, and uses the
        units with data in every year. Giving ``w`` implies it
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    permutations
        Random permutations behind the spatial Gini's pseudo p-value (0: no test)
    lorenz
        Also draw the Lorenz curve
    title
        The title of the main figure
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    InequalityResult
        A result with ``.df`` (one row per year: ``n_units`` and one column per measure, plus
        ``gini_spatial`` and ``gini_spatial_p`` when spatial), ``.fig`` (the measures over
        time), ``.summary`` (one row per measure: its value in the ``first`` and ``last``
        year, their ``change``, and the ``slope``, ``se`` and ``pvalue`` of its log-trend,
        which needs three or more years), ``.gt`` (the trends; with two years, the measures
        in both years), ``.lorenz`` (one row per unit and year, from the lowest value to the
        highest, with the cumulative share of units ``cum_units`` and of the variable
        ``cum_share``), ``.fig_lorenz`` (one curve per year, the first and the last when
        there are more than four, with the line of equality), ``.lorenz_share(year, share)``,
        ``.n_years``, ``.n_units``, ``.w_spec``, ``.notes`` and ``.interpret()``.
    """
    from ._engine._labels import resolve_label
    from ._engine.regional_inequality import analyze_inequality_over_time

    measures = tuple(str(m).lower() for m in _inputs.as_list(measures))
    df = _inputs.panel(data, variable, gdf=gdf, ref=ref)
    _require_years(df, "inequality")
    df = _window(df, variable, first, last)
    if "theil" in measures:
        _require_positive(df, variable, hint='; use measures=("gini", "cv"), which accept zeros')
    notes: list[str] = []
    geo = None
    if spatial or w is not None:
        n_all = df.loc[df[variable].notna(), ENTITY].nunique()
        df, geo, w = _inputs.spatial(df, variable, year="all", gdf=gdf, w=w, ref=ref)
        if (left_out := n_all - df[ENTITY].nunique()) > 0:
            notes.append(f"inequality: {left_out} unit(s) without data in every year or without boundaries were "
                         f"left out, so every measure refers to the same {df[ENTITY].nunique()} units")
    res = analyze_inequality_over_time(df, variable, measures=measures, gdf=geo, w=w, permutations=permutations,
                                       title=title)

    tab = res.df.rename(columns={_ENGINE_TIME: TIME})
    label = resolve_label(df, variable)
    changes: dict[str, Any] = {"summary": _with_levels(res.summary, tab)}
    if res.n_periods < 3:
        notes.append(f"inequality: a trend needs three or more years; these data have {res.n_periods} "
                     f"({', '.join(str(y) for y in tab[TIME])})")
        notes += [n for n in res.notes if "its trend was not estimated" not in n]
        changes["gt"] = _levels_gt(tab, label, res.n_units)
    else:
        notes += res.notes
    if lorenz:
        table = _lorenz_table(df, variable)
        if table is None:
            notes.append("inequality: no Lorenz curve, which needs values that are not negative and a positive total")
        else:
            gini = dict(zip(tab[TIME], tab["gini"], strict=True)) if "gini" in tab.columns else {}
            changes.update(lorenz=table, fig_lorenz=_lorenz_fig(table, variable, label, gini))
    return _inputs.finish(_as(InequalityResult, res, notes=tuple(notes), **changes), df)


# --- Theil's index between and within groups ------------------------------------------------

def _nesting(df: pd.DataFrame, ref: str | None):
    """The units' scale, the coarser scales they nest in and their unit table; ``None`` for ids outside the project."""
    try:
        found = {scale_of(i, ref) for i in df[ENTITY].dropna().unique()}
        if len(found) != 1:
            return None
        scale = found.pop()
        return scale, ancestors(scale, ref), io.units(scale, ref=ref).set_index(ENTITY)
    except Exception:  # ids that match no scale, or no registry to read
        return None


def _grouped(df: pd.DataFrame, by: str | None, ref: str | None) -> tuple[pd.DataFrame, str, list[str]]:
    """The panel with its grouping column: ``by`` as given, or the coarser scale it names.

    A scale's column holds the geo ids of its units, not their names, which repeat.
    Returns the panel, the name of the column and notes.
    """
    from ._engine._labels import set_labels

    nesting = _nesting(df, ref)
    scale, above, table = nesting if nesting else (None, [], None)

    def ids(group: str) -> pd.Series | None:
        column = f"{group}_id"
        return df[ENTITY].map(table[column]) if table is not None and column in table.columns else None

    notes: list[str] = []
    if by is None:
        if nesting is None:
            raise ValueError("by is required for units that are not in the project's scales: "
                             "give the column of the table that groups them")
        sizes = {g: int(ids(g).nunique()) for g in above if ids(g) is not None}
        sizes = {g: n for g, n in sizes.items() if n >= 2}
        if not sizes:
            raise ValueError(f"The {scale!r} units with data nest in no coarser scale with two or more units; "
                             "give by=, a column of the table that groups them")
        by = min(sizes, key=sizes.get)          # the coarsest: the fewest groups (ties: the nearest scale)
    elif not isinstance(by, str):
        raise TypeError("by must be the name of a column or of a coarser scale")
    if by in df.columns:
        codes = ids(by) if by in above else None
        # A column of unit names (as load(..., groups=...) adds) merges the units that share a name.
        if (codes is not None and codes.notna().all() and codes.nunique() > df[by].nunique()
                and df.groupby(codes)[by].nunique().max() == 1):
            notes.append(f"theil_decomposition: {codes.nunique() - df[by].nunique()} of the {by!r} names repeat, "
                         "so the units are grouped by the geo id of the unit they lie in, not by its name")
            df = df.assign(**{by: codes.to_numpy()})
        return df, by, notes
    if by not in above or ids(by) is None:
        nests = f"; {scale!r} units nest in {above}" if nesting else ""
        raise ValueError(f"by={by!r} is neither a column of the table nor a coarser scale of its units{nests}. "
                         f"The table has {[c for c in df.columns if c not in (ENTITY, TIME)]}")
    attrs = dict(df.attrs)
    df = df.assign(**{by: ids(by).to_numpy()})
    df.attrs = attrs
    try:
        set_labels(df, {by: io.group_label(by, ref)})
    except Exception:
        pass
    return df, by, notes


def theil_decomposition(data, variable: str, by: str | None = None, *, permutations: int = 0, seed: int = 12345,
                        title: str | None = None, ref: str | None = None) -> TheilResult:
    """Theil's index split in two: inequality between groups of units and inequality within them.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to measure, in levels and strictly positive
    by
        The groups: a column of the table, or a coarser scale the units nest in (see
        ``ancestors``). Default: the coarsest such scale with two or more units. A unit
        must stay in the same group in every year
    permutations
        Random reassignments of units to groups behind the pseudo p-value of
        the between component (0: no test)
    seed
        Makes the permutations reproducible
    title
        The figure title

    Returns
    -------
    TheilResult
        A result with ``.df`` (one row per year: ``theil``, ``between``, ``within``, which
        add up to it, ``between_share``, and ``p_between`` with permutations), ``.fig`` (the
        two components stacked, with the between share), ``.gt``, ``.by``, ``.n_groups``,
        ``.notes`` and ``.interpret()``.
    """
    from ._engine.regional_inequality import analyze_theil_decomposition

    df = _inputs.panel(data, variable, ref=ref)
    _require_years(df, "Theil's index")
    if not _inputs.years(df, variable):
        raise ValueError(f"No rows with data for {variable!r}")
    _require_positive(df, variable)
    attrs = dict(df.attrs)
    df, by, notes = _grouped(df, by, ref)
    df.attrs = {**attrs, **df.attrs}
    res = analyze_theil_decomposition(df, variable, by, permutations=permutations, seed=seed, title=title)
    return _inputs.finish(_as(TheilResult, res, notes=(*notes, *res.notes)), df)


__all__ = ["inequality", "theil_decomposition"]
