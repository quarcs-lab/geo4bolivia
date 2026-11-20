"""Exploring a panel without using space: correlations, extremes, distributions, scatterplots and trends."""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import _inputs
from ._engine._labels import resolve_label
from ._engine._theme import (
    ANNOTATION_BG,
    active_diverging_scale,
    active_sequential_scale,
    annotation_corner,
    apply_default_layout,
    color_for,
)
from ._engine.pedagogy import Interpretable
from ._engine.pedagogy._format import significance_phrase
from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE

ENTITY, TIME, NAME = _inputs.ENTITY, _inputs.TIME, _inputs.NAME

_NOT_VARIABLES = {ENTITY, NAME, TIME, "n_units", "coverage"}
_NEUTRAL = "#4a4a4a"                    # fitted lines, drawn over points of any colour
_UNIT_LINES = "rgba(120,120,120,0.22)"  # each unit's own trajectory, behind the summary
_SEED = 12345                           # the sample of unit trajectories is reproducible


# --- shared helpers ---------------------------------------------------------------------------

def _is_all(year) -> bool:
    return isinstance(year, str) and year.lower() == "all"


def _num(value) -> str:
    """A number for a sentence: thousands separators when large, three significant digits otherwise."""
    x = float(value)
    if math.isnan(x):
        return "NaN"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:.3g}"


def _decimals(values) -> int:
    """Decimals that show about three significant digits of the largest value (between 1 and 6)."""
    peak = float(np.nanmax(np.abs(np.asarray(values, dtype=float))))
    return int(np.clip(2 - math.floor(math.log10(peak)), 1, 6)) if peak > 0 else 1


def _signed(value) -> str:
    return ("+" if float(value) > 0 else "") + _num(value)


def _when(period) -> str:
    return f" in {period}" if period is not None else ""


def _rgba(color: str, alpha: float) -> str:
    h = color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def _wrap(text, width: int = 26) -> str:
    """A long label on several lines (Plotly breaks lines at ``<br>``)."""
    return "<br>".join(textwrap.wrap(str(text), width, break_long_words=False)) or str(text)


def _point_scale() -> list:
    """The sequential scale without its lightest part, which would vanish as a point on white."""
    stops = [[float(pos), colour] for pos, colour in active_sequential_scale() if float(pos) >= 0.25]
    low, high = stops[0][0], stops[-1][0]
    return [[(pos - low) / (high - low), colour] for pos, colour in stops]


def _numeric_variables(df: pd.DataFrame) -> list[str]:
    """The numeric columns that are variables: not ids, not the year."""
    return [c for c in df.columns
            if c not in _NOT_VARIABLES and not str(c).endswith("_id")
            and pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


def _group_columns(df: pd.DataFrame, variable: str) -> list[str]:
    """The text columns that describe a unit (e.g. the coarser unit it lies in)."""
    return [c for c in df.columns
            if c not in _NOT_VARIABLES and c != variable and not str(c).endswith("_id")
            and not pd.api.types.is_numeric_dtype(df[c])]


def _panel(data, variables, others=(), ref: str | None = None) -> pd.DataFrame:
    """The panel with its numeric ``variables`` and the ``others``: columns to group or colour by.

    Each of the ``others`` is a column of the table (or a variable of the dataset), or a
    coarser scale of its units, whose unit names are then added as a column.
    """
    variables = _inputs.as_list(variables)
    others = [c for c in dict.fromkeys(others) if c is not None]
    if isinstance(data, str):
        from .scales import scales as registry
        known = registry(ref)
        groups = [c for c in others if c in known]
        columns = list(dict.fromkeys(variables + [c for c in others if c not in groups]))
        df = _inputs.panel(data, columns if variables else None, groups=groups, numeric=False, ref=ref)
        missing = [c for c in others if c not in df.columns]
        if missing:
            raise ValueError(f"No column(s) {missing} in {data!r}; it has {[c for c in df.columns if c != ENTITY]}")
    else:
        df = _inputs.panel(data, variables, numeric=False, ref=ref)
        groups = [c for c in others if c not in df.columns]
        if groups:
            try:
                df = _inputs.panel(df, variables, groups=groups, numeric=False, ref=ref)
            except Exception as err:
                raise ValueError(f"No column(s) {groups} in the table, and not a coarser scale of its units; "
                                 f"it has {[c for c in df.columns if c != ENTITY]}") from err
    text = [v for v in variables if not pd.api.types.is_numeric_dtype(df[v])]
    if text:
        raise TypeError(f"Column(s) {text} must be numeric")
    return df


def _one_year(df: pd.DataFrame, variable: str | None, year, *, pooled: bool = True):
    """The rows of one year (the last with data for ``variable`` by default), and that year.

    ``"all"`` keeps every row (where ``pooled`` allows it); so does a table without a
    year column. The year is then ``None``.
    """
    if _is_all(year):
        if not pooled:
            raise ValueError('year must be one year here, not "all"')
        return df, None
    if isinstance(year, list | tuple | set):
        raise ValueError("year must be one year" + (' or "all"' if pooled else "") + ", not a list")
    period = _inputs.pick_year(df, variable, year)
    return (df if period is None else df[df[TIME] == period]), period


def _pooled_text(df: pd.DataFrame, year, period) -> str:
    """How a title names the rows used: ``", 2024"``, ``", all years"`` or nothing."""
    if period is not None:
        return f", {period}"
    return ", all years" if _is_all(year) and TIME in df.columns else ""


def _strength(r: float) -> str:
    a = abs(r)
    return "strong" if a >= 0.7 else "moderate" if a >= 0.4 else "weak" if a >= 0.2 else "very weak"


def _letters(k: int) -> list[str]:
    """A, B, ..., Z, AA, AB, ...: the column headers of the correlation table."""
    out = []
    for i in range(1, k + 1):
        text = ""
        while i:
            i, rest = divmod(i - 1, 26)
            text = chr(65 + rest) + text
        out.append(text)
    return out


# --- results ----------------------------------------------------------------------------------

@dataclass(frozen=True, repr=False)
class CorrelationResult(Interpretable):
    """Result of ``correlation``.

    ``df`` is the correlation matrix (``method``), ``pairs`` the same coefficients one row
    per pair, strongest positive first; ``gt`` shows Pearson above the diagonal and
    Spearman below. ``n`` is the number of observations with data for every variable.
    """

    df: pd.DataFrame
    fig: go.Figure
    gt: object
    pairs: pd.DataFrame
    variables: tuple[str, ...]
    method: str
    n: int
    period: int | None
    labels: dict
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """The strongest positive and negative pairs, in words."""
        name = self.method.capitalize() if self.method != "kendall" else "Kendall's tau"
        pairs = self.pairs.dropna(subset=["correlation"])
        if pairs.empty:
            return "\n\n".join(["No correlation could be computed: the variables do not vary.", _ASSOC_NOTE])

        def pair(row) -> str:
            return (f"**{self.labels.get(row.variable_1, row.variable_1)}** and "
                    f"**{self.labels.get(row.variable_2, row.variable_2)}** (r = {row.correlation:.2f})")

        top, bottom = pairs.iloc[0], pairs.iloc[-1]
        lines = [f"{name} correlations between {len(self.variables)} variables{_when(self.period)}, "
                 f"on the {self.n:,} observations with data for all of them."]
        if len(pairs) == 1:
            sign = "positive" if top.correlation > 0 else "negative"
            lines.append(f"The correlation between {pair(top)} is {_strength(top.correlation)} and {sign}.")
        else:
            if top.correlation > 0:
                lines.append(f"The strongest positive correlation is between {pair(top)}: "
                             f"a {_strength(top.correlation)} association, in which units with more of one "
                             "tend to have more of the other.")
            else:
                lines.append(f"No pair is positively correlated: the highest correlation is between {pair(top)}.")
            if bottom.correlation < 0:
                lines.append(f"The strongest negative correlation is between {pair(bottom)}: "
                             f"a {_strength(bottom.correlation)} association, in which units with more of one "
                             "tend to have less of the other.")
            else:
                lines.append(f"No pair is negatively correlated: the lowest correlation is between {pair(bottom)}.")
            weakest = pairs.loc[pairs["correlation"].abs().idxmin()]
            if len(pairs) > 2:
                lines.append(f"The weakest correlation, in either direction, is between {pair(weakest)}.")
        lines.append("A coefficient near +1 or -1 means two variables move together closely, in the same or in "
                     "opposite directions; near 0, that knowing one says little about the other. The table "
                     "(`.gt`) sets Pearson correlations (above the diagonal) against Spearman rank correlations "
                     "(below): a large gap between the two points to a non-linear relation or to outliers.")
        return "\n\n".join([*lines, _ASSOC_NOTE])


@dataclass(frozen=True, repr=False)
class ExtremesResult(Interpretable):
    """Result of ``extremes``.

    ``df`` has the ``n`` highest units and then the ``n`` lowest, from the highest value
    to the lowest: ``geo_id``, ``name``, group columns, the variable, ``rank`` (1 = highest
    among the ``n_units`` with data) and ``end`` (``"highest"`` or ``"lowest"``).
    """

    df: pd.DataFrame
    fig: go.Figure
    gt: object
    var: str
    period: int | None
    n: int
    n_units: int
    highest: float
    lowest: float
    median: float
    label: str
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """The two ends of the ranking, in words."""
        top = self.df[self.df["end"] == "highest"]
        bottom = self.df[self.df["end"] == "lowest"]

        def listed(rows) -> str:
            return ", ".join(f"{name} ({_num(value)})" for name, value in zip(rows[NAME], rows[self.var], strict=True))

        lines = [
            f"**{self.label}**{_when(self.period)} ranges from {_num(self.lowest)} "
            f"({bottom[NAME].iloc[-1]}) to {_num(self.highest)} ({top[NAME].iloc[0]}) across the "
            f"{self.n_units:,} units with data; the median unit has {_num(self.median)}.",
            f"The {self.n} highest: {listed(top)}.",
            f"The {self.n} lowest: {listed(bottom.iloc[::-1])}.",
            f"The gap between the two ends is {_num(self.highest - self.lowest)}. Extreme values deserve a second "
            "look before any analysis: they may be the most interesting units, very small units whose rates "
            "are noisy, or errors in the data.",
        ]
        return "\n\n".join([*lines, _ASSOC_NOTE])


@dataclass(frozen=True, repr=False)
class DistributionResult(Interpretable):
    """Result of ``distribution``.

    ``df`` has one row per year (or per group of ``by``): ``n``, ``mean``, ``sd``, ``min``,
    ``p25``, ``median``, ``p75``, ``max`` and ``skewness``. ``period`` is the year when the
    figure shows a single one.
    """

    df: pd.DataFrame
    fig: go.Figure
    var: str
    kind: str
    by: str | None
    period: int | None
    label: str
    by_label: str | None = None
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """Centre, spread and shape of the distribution, in words."""
        df = self.df

        def shape(row) -> str:
            skew = float(row["skewness"])
            if math.isnan(skew):
                return ""
            if abs(skew) < 0.5:
                text = "roughly symmetric"
            else:
                tail, pull = ("high", "above") if skew > 0 else ("low", "below")
                side = "right" if skew > 0 else "left"
                text = (f"{'strongly ' if abs(skew) >= 1 else ''}{side}-skewed: a tail of {tail} values "
                        f"pulls the mean {pull} the median")
            return f" The distribution is {text} (skewness {skew:.2f})."

        def one(row, where: str) -> str:
            return (f"**{self.label}**{where} averages {_num(row['mean'])} across {int(row['n']):,} units "
                    f"(median {_num(row['median'])}, standard deviation {_num(row['sd'])}). Half of the units "
                    f"lie between {_num(row['p25'])} and {_num(row['p75'])}, and the full range runs from "
                    f"{_num(row['min'])} to {_num(row['max'])}.{shape(row)}")

        split = df.columns[0] if df.columns[0] != "n" else None
        if split is None or len(df) == 1:
            where = _when(self.period) if split in (None, TIME) else f" in {df[split].iloc[0]}{_when(self.period)}"
            lines = [one(df.iloc[0], where)]
        elif split == TIME:
            a, b = df.iloc[0], df.iloc[-1]
            iqr_a, iqr_b = a["p75"] - a["p25"], b["p75"] - b["p25"]
            moved = "rose" if b["mean"] > a["mean"] else "fell" if b["mean"] < a["mean"] else "stayed"
            spread = "narrowed" if b["sd"] < a["sd"] else "widened" if b["sd"] > a["sd"] else "did not change"
            lines = [
                f"Between {int(a[TIME])} and {int(b[TIME])}, the mean of **{self.label}** {moved} from "
                f"{_num(a['mean'])} to {_num(b['mean'])}, and the median went from {_num(a['median'])} to "
                f"{_num(b['median'])}.",
                f"The spread across units {spread}: the standard deviation went from {_num(a['sd'])} to "
                f"{_num(b['sd'])}, and the interquartile range (the middle half of the units) from "
                f"{_num(iqr_a)} to {_num(iqr_b)}.",
                one(b, f" in {int(b[TIME])}"),
            ]
        else:
            hi, lo = df.loc[df["median"].idxmax()], df.loc[df["median"].idxmin()]
            lines = [
                f"By {self.by_label or split}{_when(self.period)} ({len(df)} groups), the median of "
                f"**{self.label}** is highest in **{hi[split]}** ({_num(hi['median'])}) and lowest in "
                f"**{lo[split]}** ({_num(lo['median'])}).",
            ]
            spread = df.dropna(subset=["sd"])
            if len(spread) > 1:
                wide, tight = spread.loc[spread["sd"].idxmax()], spread.loc[spread["sd"].idxmin()]
                lines.append(
                    f"Units differ most within **{wide[split]}** (standard deviation {_num(wide['sd'])}) and "
                    f"least within **{tight[split]}** ({_num(tight['sd'])}). Where the groups' distributions "
                    "barely overlap, the differences between groups are large compared with those within them.")
        if self.kind in ("box", "violin"):
            where = "In each box" if self.kind == "box" else "In the box inside each violin"
            lines.append(f"{where}, the line is the median and the box holds the middle half of the units; "
                         "points beyond the whiskers are unusually high or low units.")
        return "\n\n".join([*lines, _ASSOC_NOTE])


@dataclass(frozen=True, repr=False)
class ScatterResult(Interpretable):
    """Result of ``scatter``.

    ``slope``, ``intercept``, ``r2`` and ``p_value`` are those of the least-squares line of
    ``y`` on ``x`` and ``corr`` is their Pearson correlation, on the ``n`` units with data
    for both. With ``log_x`` or ``log_y`` they refer to the natural logarithms.
    """

    df: pd.DataFrame
    fig: go.Figure
    x: str
    y: str
    period: int | None
    slope: float
    intercept: float
    r2: float
    corr: float
    p_value: float
    n: int
    fit: str | None
    log_x: bool
    log_y: bool
    labels: dict
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """Direction, strength and slope of the relation, in words."""
        x, y = self.labels.get(self.x, self.x), self.labels.get(self.y, self.y)
        more = "higher" if self.slope > 0 else "lower"
        if abs(self.corr) < 0.1:
            first = (f"Across {self.n:,} units{_when(self.period)}, **{y}** and **{x}** are essentially "
                     f"uncorrelated (r = {self.corr:.2f}): knowing one says little about the other.")
        else:
            first = (f"Across {self.n:,} units{_when(self.period)}, **{y}** and **{x}** are "
                     f"{'positively' if self.corr > 0 else 'negatively'} correlated (r = {self.corr:.2f}, a "
                     f"{_strength(self.corr)} association): units with higher {x} tend to have {more} {y}.")
        b = abs(self.slope)
        if self.log_x and self.log_y:
            reading = f"1% more of {x} goes with {_num(b)}% {more} {y}, on average (both are in logs)"
        elif self.log_y:
            reading = (f"one more unit of {x} goes with about {_num(100 * b)}% {more} {y}, on average "
                       f"({y} is in logs)")
        elif self.log_x:
            reading = f"1% more of {x} goes with {_num(b / 100)} {more} {y}, on average ({x} is in logs)"
        else:
            reading = f"one more unit of {x} goes with {_num(b)} {more} {y}, on average"
        lines = [
            first,
            f"The least-squares line has a slope of {_num(self.slope)}: {reading}. The line accounts for "
            f"{self.r2:.0%} of the variation in {y} across units (R² = {self.r2:.2f}); the slope is "
            f"{significance_phrase(self.p_value)}, by a test that treats the units as independent of each other.",
        ]
        if self.fit == "lowess":
            lines.append("The curve drawn is a local (LOWESS) smooth, which follows the data without assuming a "
                         "straight line: where it bends, the slope above is only an average.")
        return "\n\n".join([*lines, _ASSOC_NOTE])


@dataclass(frozen=True, repr=False)
class TrendResult(Interpretable):
    """Result of ``trend``.

    ``df`` has one row per year (and group of ``by``): the statistic (``mean`` or
    ``median``), the band (``lower``, ``upper``) and ``n``. ``value_first``, ``value_last``
    and ``change`` are the statistic across all units in the ``first`` and ``last`` years;
    ``share_rising`` is the share of units with data in both years whose value went up.
    """

    df: pd.DataFrame
    fig: go.Figure
    var: str
    by: str | None
    stat: str
    first: int
    last: int
    value_first: float
    value_last: float
    change: float
    share_rising: float
    n_units: int
    label: str
    by_label: str | None = None
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """The change from the first year to the last, overall and by group, in words."""
        moved = "rose" if self.change > 0 else "fell" if self.change < 0 else "did not change"
        lines = [f"Between {self.first} and {self.last}, the {self.stat} of **{self.label}** across "
                 f"{self.n_units:,} units {moved}"
                 + (f" from {_num(self.value_first)} to {_num(self.value_last)} (a change of {_signed(self.change)})."
                    if self.change else f": it was {_num(self.value_first)} in both years.")]
        if not math.isnan(self.share_rising):
            if self.share_rising in (0.0, 1.0):
                lines.append(("Every unit" if self.share_rising else "No unit") + " with data in both years ended "
                             "higher than it started.")
            else:
                share = f"{self.share_rising:.1%}" if not 0.01 <= self.share_rising <= 0.99 else f"{self.share_rising:.0%}"
                lines.append(f"{share} of the units with data in both years ended higher than "
                             "they started: the summary line describes the typical unit, not every unit.")
        if self.by is not None:
            wide = self.df[self.df[TIME].isin([self.first, self.last])].pivot(index=self.by, columns=TIME,
                                                                              values=self.stat)
            wide = wide.dropna(subset=[c for c in (self.first, self.last) if c in wide.columns])
            if {self.first, self.last} <= set(wide.columns) and len(wide) > 1:
                diff = (wide[self.last] - wide[self.first]).sort_values(ascending=False)
                best, worst = diff.index[0], diff.index[-1]
                tail = (f"**{worst}** fell most ({_signed(diff.iloc[-1])})" if diff.iloc[-1] < 0
                        else f"**{worst}** grew least ({_signed(diff.iloc[-1])})")
                head = (f"**{best}** grew most ({_signed(diff.iloc[0])}, from {_num(wide.loc[best, self.first])} "
                        f"to {_num(wide.loc[best, self.last])})" if diff.iloc[0] > 0
                        else f"**{best}** fell least ({_signed(diff.iloc[0])})")
                gap_a = wide[self.first].max() - wide[self.first].min()
                gap_b = wide[self.last].max() - wide[self.last].min()
                gap = "narrowed" if gap_b < gap_a else "widened" if gap_b > gap_a else "stayed"
                lines.append(f"By {self.by_label or self.by}: {head} and {tail}. The gap between the highest and "
                             f"the lowest group {gap} from {_num(gap_a)} to {_num(gap_b)}.")
        band = ("one standard error on each side of the mean: how precisely the average is known, not how much "
                "units differ" if self.stat == "mean"
                else "the interquartile range: where the middle half of the units lie")
        lines.append(f"The band is {band}.")
        return "\n\n".join([*lines, _ASSOC_NOTE])


# --- correlation ------------------------------------------------------------------------------

def correlation(data, variables=None, year=None, *, method: str = "pearson", digits: int = 2,
                title: str | None = None, ref: str | None = None) -> CorrelationResult:
    """Correlations between the variables of a panel in one year.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    variables
        The numeric columns to correlate (default: every numeric variable; ids
        and the year are left out)
    year
        The year to use (default: the last with data for the first variable), or
        ``"all"`` to pool every year
    method
        ``"pearson"`` (linear), ``"spearman"`` (ranks) or ``"kendall"``: the
        coefficient of the matrix and the heatmap
    digits
        Decimals written in the heatmap and the table
    title
        The figure and table title

    Notes
    -----
    Only the observations with data for every variable are used, so that all the
    coefficients refer to the same units.

    Returns
    -------
    CorrelationResult
        A result with ``.df`` (the correlation matrix), ``.pairs`` (one row per pair, from the
        strongest positive to the strongest negative), ``.fig`` (a heatmap centred at zero with
        the coefficients in the cells), ``.gt`` (a table with Pearson above the diagonal and
        Spearman below), ``.n`` (observations), ``.variables``, ``.year``, ``.notes`` and
        ``.interpret()``.
    """
    if method not in ("pearson", "spearman", "kendall"):
        raise ValueError(f"method must be 'pearson', 'spearman' or 'kendall', not {method!r}")
    chosen = _inputs.as_list(variables)
    df = _panel(data, chosen, ref=ref)
    given = bool(chosen)
    if not given:
        chosen = _numeric_variables(df)
    chosen = list(dict.fromkeys(chosen))
    if len(chosen) < 2:
        raise ValueError(f"correlation needs at least two numeric variables; it got {chosen}")
    rows, period = _one_year(df, chosen[0], year)
    where = _pooled_text(df, year, period)
    notes: list[str] = []

    flat = [v for v in chosen if rows[v].nunique(dropna=True) < 2]       # no data, or a single value
    if flat and given:
        raise ValueError(f"Column(s) {flat} have no data or do not vary{where.replace(', ', ' in ', 1)}, "
                         "so they have no correlation")
    if flat:
        chosen = [v for v in chosen if v not in flat]
        notes.append(f"Left out, without data or variation{where}: {', '.join(flat)}.")
        if len(chosen) < 2:
            raise ValueError(f"correlation needs at least two variables that vary; only {chosen} do{where}")
    sub = rows.dropna(subset=chosen)
    n = len(sub)
    if n < 3:
        raise ValueError(f"correlation needs at least three observations with data for every variable; "
                         f"there are {n}{where}")
    if n < len(rows):
        notes.append(f"{len(rows) - n:,} of {len(rows):,} observations lack data for at least one variable "
                     "and were left out.")

    values = sub[chosen].astype(float)
    matrix = values.corr(method=method)
    pearson = matrix if method == "pearson" else values.corr(method="pearson")
    spearman = matrix if method == "spearman" else values.corr(method="spearman")
    upper = np.triu(np.ones(matrix.shape, dtype=bool), k=1)
    i, j = np.where(upper)
    pairs = pd.DataFrame({"variable_1": [chosen[a] for a in i], "variable_2": [chosen[b] for b in j],
                          "correlation": matrix.to_numpy()[i, j]})
    pairs = pairs.sort_values("correlation", ascending=False, kind="stable", na_position="last").reset_index(drop=True)

    labels = {v: resolve_label(df, v) for v in chosen}
    shown = [labels[v] for v in chosen]
    if len(set(shown)) < len(shown):             # two variables with one label would share a cell
        shown = [f"{labels[v]} ({v})" for v in chosen]
    few = len(chosen) <= 8                        # column labels stay horizontal while they fit
    name = {"pearson": "Pearson", "spearman": "Spearman", "kendall": "Kendall"}[method]
    if title is None:
        title = f"{name} correlations{where}"

    z = matrix.to_numpy(dtype=float)
    fig = go.Figure(go.Heatmap(
        z=z, x=[_wrap(text, 15 if few else 26) for text in shown], y=[_wrap(text) for text in shown],
        zmin=-1.0, zmax=1.0, zmid=0.0, colorscale=active_diverging_scale(),
        xgap=1, ygap=1, texttemplate=f"%{{z:.{int(digits)}f}}" if len(chosen) <= 25 else None,
        colorbar={"title": {"text": "r"}},
        hovertemplate="%{y}<br>%{x}<br>r = %{z:.3f}<extra></extra>"))
    apply_default_layout(fig, title=title)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickangle=0 if few else -90, tickfont={"size": 12})
    fig.update_yaxes(tickfont={"size": 13})
    cell = 112 if few else 62
    fig.update_layout(height=max(420, 190 + cell * len(chosen) * 0.62), width=max(640, 330 + cell * len(chosen)))

    from great_tables import GT
    cells = np.where(upper, pearson.to_numpy(dtype=float), spearman.to_numpy(dtype=float))
    letters = _letters(len(chosen))
    table = pd.DataFrame([["" if a == b or math.isnan(cells[a, b]) else f"{cells[a, b]:.{int(digits)}f}"
                           for b in range(len(chosen))] for a in range(len(chosen))], columns=letters)
    table.insert(0, "variable", [f"{letter}: {text}" for letter, text in zip(letters, shown, strict=True)])
    gt = (GT(table, rowname_col="variable")
          .tab_header(title=title)
          .tab_source_note(f"Pearson correlations above the diagonal, Spearman rank correlations below. "
                           f"Observations: {n:,}."))

    return CorrelationResult(df=matrix, fig=fig, gt=gt, pairs=pairs, variables=tuple(chosen), method=method, n=n,
                             period=period, labels=labels, notes=tuple(notes))


# --- extremes ---------------------------------------------------------------------------------

def extremes(data, variable: str, year=None, *, n: int = 5, title: str | None = None,
             ref: str | None = None) -> ExtremesResult:
    """The units with the highest and the lowest values of a variable in one year.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    variable
        The numeric column to rank
    year
        The year to rank (default: the last with data)
    n
        How many units to show at each end
    title
        The figure and table title

    Returns
    -------
    ExtremesResult
        A result with ``.df`` (the ``n`` highest and the ``n`` lowest units: ``geo_id``,
        ``name``, the group columns of the table, the variable, ``rank`` with 1 for the
        highest, and ``end``: ``"highest"`` or ``"lowest"``), ``.fig`` (horizontal bars, the
        two ends in different colours), ``.gt``, ``.highest``, ``.lowest``, ``.median``,
        ``.n_units`` (units with data), ``.year``, ``.notes`` and ``.interpret()``.
    """
    n = int(n)
    if n < 1:
        raise ValueError("n must be at least 1")
    df = _panel(data, variable, ref=ref)
    label = resolve_label(df, variable)
    rows, period = _one_year(df, variable, year, pooled=False)
    valid = rows[rows[variable].notna()]
    total = len(valid)
    if total < 2 * n:
        raise ValueError(f"The {n} highest and {n} lowest need at least {2 * n} units with data; "
                         f"there are {total}{_when(period)}")
    groups = _group_columns(valid, variable)
    group_labels = {g: resolve_label(df, g) for g in groups}
    valid = valid.assign(rank=valid[variable].rank(ascending=False, method="min").astype(int))
    ordered = valid.sort_values([variable, ENTITY], ascending=[False, True], kind="stable")
    out = pd.concat([ordered.head(n).assign(end="highest"), ordered.tail(n).assign(end="lowest")], ignore_index=True)
    out = out[[ENTITY, NAME, *groups, variable, "rank", "end"]]
    notes = []
    for end, cut in (("highest", out[variable].iloc[n - 1]), ("lowest", out[variable].iloc[n])):
        tied = int((valid[variable] == cut).sum()) - int(((out["end"] == end) & (out[variable] == cut)).sum())
        if tied:
            notes.append(f"{tied} more unit(s) share the value {_num(cut)} of the last of the {n} {end} shown.")

    names = out[NAME].astype(str)
    if names.duplicated().any():                 # homonyms: tell them apart by their group, or their id
        extra = out[groups[-1]].astype(str) if groups else out[ENTITY].astype(str)
        names = names.where(~names.duplicated(keep=False), names + " (" + extra + ")")
    if title is None:
        title = f"{label}: the {n} highest and {n} lowest units{_when(period)}"

    position = np.r_[np.arange(n), np.arange(n) + n + 1]          # one empty slot between the two ends
    integers = pd.api.types.is_integer_dtype(out[variable])
    fig = go.Figure()
    for k, (end, text) in enumerate((("highest", f"Highest {n}"), ("lowest", f"Lowest {n}"))):
        mask = (out["end"] == end).to_numpy()
        fig.add_trace(go.Bar(
            x=out.loc[mask, variable], y=position[mask], orientation="h", name=text,
            marker={"color": color_for(k)}, hovertext=names[mask], customdata=out.loc[mask, "rank"],
            texttemplate="%{x:,.0f}" if integers else "%{x:,.4~g}", textposition="outside", cliponaxis=False,
            hovertemplate=(f"<b>%{{hovertext}}</b><br>{label}: %{{x:,.4~g}}<br>rank %{{customdata}} of {total:,}"
                           "<extra></extra>")))
    apply_default_layout(fig, title=title, height=max(440, 150 + 30 * (2 * n + 1)), bargap=0.25,
                         legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "right", "x": 1.0})
    fig.update_xaxes(title_text=label)
    fig.update_yaxes(tickmode="array", tickvals=list(position), ticktext=list(names), autorange="reversed",
                     showgrid=False, zeroline=False, ticksuffix="  ")

    from great_tables import GT
    block = "  "
    shown = out[["rank", NAME, *groups, variable]].assign(
        **{block: np.where(out["end"] == "highest", f"Highest {n}", f"Lowest {n}")})
    gt = (GT(shown, groupname_col=block)
          .cols_label(**{"rank": "Rank", NAME: "Unit", variable: label, **group_labels})
          .fmt_number(columns=[variable], decimals=0 if integers else _decimals(out[variable]), use_seps=True)
          .tab_header(title=title)
          .tab_source_note(f"Rank 1 is the highest of the {total:,} units with data{_when(period)}."))

    series = valid[variable].astype(float)
    return ExtremesResult(df=out, fig=fig, gt=gt, var=variable, period=period, n=n, n_units=total,
                          highest=float(series.max()), lowest=float(series.min()), median=float(series.median()),
                          label=label, notes=tuple(notes))


# --- distribution -----------------------------------------------------------------------------

_KINDS = ("histogram", "box", "violin", "ridgeline")


def _summary(rows: pd.DataFrame, variable: str, split: str | None) -> pd.DataFrame:
    """n, mean, sd, min, quartiles, max and skewness of ``variable``, per value of ``split``."""
    key = split if split is not None else "_all"
    g = (rows if split is not None else rows.assign(_all=0)).groupby(key, sort=True)[variable]
    out = pd.DataFrame({"n": g.count(), "mean": g.mean(), "sd": g.std(), "min": g.min(), "p25": g.quantile(0.25),
                        "median": g.median(), "p75": g.quantile(0.75), "max": g.max(), "skewness": g.skew()})
    return out.reset_index().drop(columns="_all", errors="ignore")


def distribution(data, variable: str, year=None, *, by: str | None = None, kind: str = "histogram",
                 bins: int = 30, title: str | None = None, ref: str | None = None) -> DistributionResult:
    """The distribution of a variable across units, per year or per group.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    variable
        The numeric column to describe
    year
        A year, a list of years or ``"all"``. By default (``None``) every year is shown
        next to the others, with one exception: a histogram overlays the years only when
        the panel has up to four of them, and otherwise shows the last year with data.
        With ``by``, one year is used: the last with data by default, or every year
        pooled with ``"all"``
    by
        Compare groups instead of years: a column of the table, or a coarser scale of
        its units (e.g. the first-level administrative scale), whose names are added
    kind
        ``"histogram"`` (overlaid, on common bins), ``"box"`` or ``"violin"`` (one per
        year or group) or ``"ridgeline"`` (one density per year or group, stacked)
    bins
        Number of bins of the histogram
    title
        The figure title

    Returns
    -------
    DistributionResult
        A result with ``.df`` (one row per year, or per group of ``by``: ``n``, ``mean``,
        ``sd``, ``min``, ``p25``, ``median``, ``p75``, ``max`` and ``skewness``, the
        sample-adjusted coefficient that is zero for a symmetric distribution), ``.fig``,
        ``.kind``, ``.year`` (when a single year is shown), ``.notes`` and ``.interpret()``.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {list(_KINDS)}, not {kind!r}")
    bins = int(bins)
    if bins < 1:
        raise ValueError("bins must be at least 1")
    df = _panel(data, variable, [by], ref=ref)
    label = resolve_label(df, variable)
    notes: list[str] = []

    if by is not None:
        rows, period = _one_year(df, variable, year)
        split, by_label = by, resolve_label(df, by)
        where = _pooled_text(df, year, period)
        default_title = f"Distribution of {label} by {by_label}{where}"
    elif TIME not in df.columns:
        rows, period = _one_year(df, variable, year)
        split, by_label = None, None
        default_title = f"Distribution of {label}"
    else:
        have = _inputs.years(df, variable)
        if not have:
            raise ValueError(f"No rows with data for {variable!r}")
        if year is None:
            chosen = have if kind != "histogram" or len(have) <= 4 else have[-1:]
            if chosen != have:
                notes.append(f"The panel has {len(have)} years: the histogram shows the last one, {have[-1]}. "
                             "Pass year= (a year or a list) to choose, or use another kind to compare them all.")
        elif _is_all(year):
            chosen = have
        elif isinstance(year, list | tuple | set):
            chosen = sorted({_inputs.pick_year(df, variable, y) for y in year})
        else:
            chosen = [_inputs.pick_year(df, variable, year)]
        rows = df[df[TIME].isin(chosen)]
        split, by_label = TIME, "Year"
        period = chosen[0] if len(chosen) == 1 else None
        default_title = f"Distribution of {label}, {period}" if period is not None else f"Distribution of {label} by year"

    keep = [variable] + ([split] if split is not None else [])
    rows = rows.dropna(subset=keep)
    if rows.empty:
        raise ValueError(f"No rows with data for {variable!r}" + (f" and {by!r}" if by else "") + _when(period))
    if kind == "ridgeline":
        if split is None:
            raise ValueError("kind='ridgeline' draws one density per year or group: the table needs a year "
                             "column, or pass by=")
        distinct = rows.groupby(split)[variable].nunique()
        thin = list(distinct.index[distinct < 2])
        if thin:
            notes.append(f"Without at least two different values, no density can be drawn for: "
                         f"{', '.join(str(t) for t in thin)}.")
            rows = rows[~rows[split].isin(thin)]
        if rows.empty:
            raise ValueError(f"kind='ridgeline' needs at least two different values of {variable!r} per "
                             f"{'year' if split == TIME else 'group'}")
    summary = _summary(rows, variable, split)
    levels = list(summary[split]) if split is not None else [None]
    if title is None:
        title = default_title

    values = rows[variable].to_numpy(dtype=float)
    if kind == "histogram":
        edges = np.histogram_bin_edges(values, bins=bins)
        centers, width = (edges[:-1] + edges[1:]) / 2, float(edges[1] - edges[0])
        fig = go.Figure()
        for k, level in enumerate(levels):
            part = values if level is None else rows.loc[rows[split] == level, variable].to_numpy(dtype=float)
            counts, _ = np.histogram(part, bins=edges)
            fig.add_trace(go.Bar(
                x=centers, y=counts, width=width, name=label if level is None else str(level),
                marker={"color": color_for(k), "line": {"width": 0}}, opacity=0.85 if len(levels) == 1 else 0.55,
                customdata=np.c_[edges[:-1], edges[1:]],
                hovertemplate="%{customdata[0]:.4~g} to %{customdata[1]:.4~g}<br>%{y} units<extra>%{fullData.name}</extra>"))
        apply_default_layout(fig, title=title, barmode="overlay", bargap=0, showlegend=len(levels) > 1,
                             legend={"title": {"text": by_label}})
        fig.update_xaxes(title_text=label)
        fig.update_yaxes(title_text="Units")
    elif kind in ("box", "violin"):
        fig = go.Figure()
        colour = color_for(0)
        for level in levels:
            part = rows if level is None else rows[rows[split] == level]
            common = {"y": part[variable], "name": label if level is None else str(level), "text": part[NAME],
                      "showlegend": False}
            if kind == "box":
                fig.add_trace(go.Box(**common, boxpoints="outliers", marker={"color": colour, "size": 5},
                                     line={"color": colour}, fillcolor=_rgba(colour, 0.35)))
            else:
                fig.add_trace(go.Violin(**common, box={"visible": True}, meanline={"visible": True}, points=False,
                                        line={"color": colour}, fillcolor=_rgba(colour, 0.35)))
        apply_default_layout(fig, title=title)
        fig.update_xaxes(title_text=by_label, type="category", showticklabels=split is not None)
        fig.update_yaxes(title_text=label)
    else:
        from ._engine.spacetime import explore_distribution_over_time
        ridge = rows[[ENTITY, split, variable]].copy()
        ridge.attrs = dict(df.attrs)
        fig = explore_distribution_over_time(ridge, variable, entity=ENTITY, time=split, title=title).fig
        fig.update_yaxes(title_text=by_label)

    return DistributionResult(df=summary, fig=fig, var=variable, kind=kind, by=by, period=period, label=label,
                              by_label=by_label if by is not None else None, notes=tuple(notes))


# --- scatter ----------------------------------------------------------------------------------

def scatter(data, x: str, y: str, year=None, *, color: str | None = None, size: str | None = None,
            fit: str | None = "ols", log_x: bool = False, log_y: bool = False, title: str | None = None,
            ref: str | None = None) -> ScatterResult:
    """Two variables against each other in one year, one point per unit.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load``
    x, y
        The numeric columns on the horizontal and the vertical axis
    year
        The year to plot (default: the last with data for ``x``), or ``"all"`` to pool
        every year (one point per unit and year)
    color
        Colour the points by a column (categories, or a numeric variable on a
        continuous scale) or by a coarser scale of the units, whose names are added
    size
        A non-negative numeric column that sets the area of the points
    fit
        The line drawn: ``"ols"`` (least squares, with its slope, R² and the correlation
        written on the figure), ``"lowess"`` (a local smooth) or ``None``
    log_x, log_y
        Logarithmic axes; the line and the numbers then use natural logarithms,
        and units with a value of zero or less are left out
    title
        The figure title

    Returns
    -------
    ScatterResult
        A result with ``.df`` (the units plotted: ``geo_id``, ``name`` and the columns used),
        ``.fig`` (the unit names show on hover), ``.slope``, ``.intercept``, ``.r2`` and
        ``.p_value`` (of the least-squares line of ``y`` on ``x``, whichever ``fit`` is drawn),
        ``.corr`` (Pearson), ``.n`` (units), ``.year``, ``.notes`` and ``.interpret()``.
    """
    if fit not in ("ols", "lowess", None):
        raise ValueError(f"fit must be 'ols', 'lowess' or None, not {fit!r}")
    df = _panel(data, [x, y] + ([size] if size else []), [color], ref=ref)
    labels = {c: resolve_label(df, c) for c in (x, y, color, size) if c}
    rows, period = _one_year(df, x, year)
    where = _pooled_text(df, year, period)
    notes: list[str] = []

    used = list(dict.fromkeys(c for c in (x, y, color, size) if c))
    sub = rows.dropna(subset=used)
    if sub.empty and TIME in df.columns:
        both = sorted(int(v) for v in df.dropna(subset=[x, y])[TIME].unique())
        raise ValueError(f"No units with data for both {x!r} and {y!r}{_when(period)}; the years with both are {both}")
    if len(sub) < len(rows):
        notes.append(f"{len(rows) - len(sub):,} of {len(rows):,} units lack data for a column used and were left out.")
    for column, logged in ((x, log_x), (y, log_y)):
        if logged and (sub[column] <= 0).any():
            notes.append(f"{int((sub[column] <= 0).sum()):,} units with {column} of zero or less cannot be on a "
                         "logarithmic axis and were left out.")
            sub = sub[sub[column] > 0]
    if size and (sub[size] < 0).any():
        raise ValueError(f"size= needs a non-negative column; {size!r} has negative values")
    n = len(sub)
    xv, yv = sub[x].to_numpy(dtype=float), sub[y].to_numpy(dtype=float)
    fx, fy = (np.log(xv) if log_x else xv), (np.log(yv) if log_y else yv)
    if n < 3 or np.ptp(fx) == 0:
        raise ValueError(f"scatter needs at least three units with data and different values of {x!r}; "
                         f"there are {n}{_when(period)}")
    from scipy.stats import linregress
    line = linregress(fx, fy)
    slope, intercept, corr = float(line.slope), float(line.intercept), float(line.rvalue)

    sub = sub[[c for c in (ENTITY, NAME, TIME) if c in sub.columns] + used].reset_index(drop=True)
    names = sub[NAME].astype(str) if period is not None or TIME not in sub.columns else (
        sub[NAME].astype(str) + ", " + sub[TIME].astype(str))
    hover = f"<b>%{{hovertext}}</b><br>{labels[x]}: %{{x:,.4~g}}<br>{labels[y]}: %{{y:,.4~g}}"
    base: dict = {"opacity": 0.75, "line": {"color": "rgba(255,255,255,0.6)", "width": 0.5}}
    if size:
        peak = float(sub[size].max())
        base.update(sizemode="area", sizeref=2.0 * peak / 24.0**2 if peak > 0 else 1.0, sizemin=3)
        hover += f"<br>{labels[size]}: %{{marker.size:,.4~g}}"
    else:
        base["size"] = 8

    def points(mask, name: str, **marker) -> go.Scatter:
        m = {**base, **marker}
        if size:
            m["size"] = sub.loc[mask, size].to_numpy(dtype=float)
        return go.Scatter(x=xv[mask], y=yv[mask], mode="markers", name=name, marker=m, hovertext=names[mask],
                          hovertemplate=hover + "<extra>%{fullData.name}</extra>")

    fig = go.Figure()
    everything = np.ones(n, dtype=bool)
    categories = bool(color) and not pd.api.types.is_numeric_dtype(sub[color])
    if categories:
        for k, level in enumerate(sorted(sub[color].astype(str).unique())):
            fig.add_trace(points((sub[color].astype(str) == level).to_numpy(), level, color=color_for(k)))
    elif color:
        fig.add_trace(points(everything, "", color=sub[color].to_numpy(dtype=float), colorscale=_point_scale(),
                             showscale=True, line={"color": "rgba(60,60,60,0.45)", "width": 0.6},
                             colorbar={"title": {"text": _wrap(labels[color], 18), "font": {"size": 13}}}))
        fig.data[-1].update(customdata=sub[color].to_numpy(dtype=float),
                            hovertemplate=hover + f"<br>{labels[color]}: %{{customdata:,.4~g}}<extra></extra>")
    else:
        fig.add_trace(points(everything, "", color=color_for(0)))

    if fit == "ols":
        gx = np.linspace(fx.min(), fx.max(), 100)
        gy = intercept + slope * gx
        fig.add_trace(go.Scatter(x=np.exp(gx) if log_x else gx, y=np.exp(gy) if log_y else gy, mode="lines",
                                 name="Least-squares line", line={"color": _NEUTRAL, "width": 2.5},
                                 hoverinfo="skip", showlegend=False))
        fig.add_annotation(text=f"slope = {_num(slope)}<br>R² = {corr ** 2:.2f}<br>r = {corr:.2f}<br>n = {n:,}",
                           xref="paper", yref="paper", showarrow=False, align="left", bgcolor=ANNOTATION_BG,
                           font={"size": 13}, **annotation_corner(fx, fy))
    elif fit == "lowess":
        from statsmodels.nonparametric.smoothers_lowess import lowess
        curve = lowess(fy, fx, frac=2 / 3, return_sorted=True)
        fig.add_trace(go.Scatter(x=np.exp(curve[:, 0]) if log_x else curve[:, 0],
                                 y=np.exp(curve[:, 1]) if log_y else curve[:, 1], mode="lines",
                                 name="LOWESS smooth", line={"color": _NEUTRAL, "width": 2.5}, hoverinfo="skip",
                                 showlegend=False))

    if title is None:
        title = f"{labels[y]} and {labels[x]}{where}"
    apply_default_layout(fig, title=title, showlegend=categories,
                         legend={"title": {"text": labels.get(color)}} if categories else {})
    fig.update_xaxes(title_text=labels[x], type="log" if log_x else None)
    fig.update_yaxes(title_text=labels[y], type="log" if log_y else None)

    return ScatterResult(df=sub, fig=fig, x=x, y=y, period=period, slope=slope, intercept=intercept, r2=corr ** 2,
                         corr=corr, p_value=float(line.pvalue), n=n, fit=fit, log_x=bool(log_x), log_y=bool(log_y),
                         labels=labels, notes=tuple(notes))


# --- trend ------------------------------------------------------------------------------------

def trend(data, variable: str, *, by: str | None = None, units: bool = True, stat: str = "mean",
          max_units: int = 400, title: str | None = None, ref: str | None = None) -> TrendResult:
    """A variable over time: its mean (or median) across units, with a band, and each unit's path.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to follow
    by
        One line per group: a column of the table, or a coarser scale of its units (e.g.
        the first-level administrative scale), whose names are added
    units
        Draw each unit's own trajectory as a thin grey line behind the summary
    stat
        ``"mean"`` (band: one standard error on each side) or ``"median"`` (band: the
        interquartile range)
    max_units
        Draw at most this many unit trajectories (a reproducible random sample
        when there are more); the statistics always use every unit
    title
        The figure title

    Notes
    -----
    The panel needs at least two years with data.

    Returns
    -------
    TrendResult
        A result with ``.df`` (one row per year and group: the statistic in a column named
        ``mean`` or ``median``, the band in ``lower`` and ``upper``, and ``n`` units),
        ``.fig``, ``.first`` and ``.last`` (years), ``.value_first``, ``.value_last`` and
        ``.change`` (the statistic across all units), ``.share_rising`` (share of units with
        data in both years that ended higher), ``.n_units``, ``.notes`` and ``.interpret()``.
    """
    if stat not in ("mean", "median"):
        raise ValueError(f"stat must be 'mean' or 'median', not {stat!r}")
    df = _panel(data, variable, [by], ref=ref)
    label = resolve_label(df, variable)
    by_label = resolve_label(df, by) if by is not None else None
    rows = df.dropna(subset=[variable] + ([by] if by is not None else []))
    have = _inputs.years(rows)
    if len(have) < 2:
        raise ValueError(f"trend needs at least two years with data for {variable!r}; the table has "
                         + (str(have) if TIME in df.columns else "no year column"))
    notes: list[str] = []
    first, last = have[0], have[-1]

    def stats(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        g = frame.groupby(keys, sort=True)[variable]
        if stat == "mean":
            centre, error = g.mean(), g.std() / np.sqrt(g.count())
            lower, upper = centre - error.fillna(0.0), centre + error.fillna(0.0)
        else:
            centre, lower, upper = g.median(), g.quantile(0.25), g.quantile(0.75)
        return pd.DataFrame({stat: centre, "lower": lower, "upper": upper, "n": g.count()}).reset_index()

    overall = stats(rows, [TIME]).set_index(TIME)[stat]
    if by is None:
        table = stats(rows, [TIME])
    else:
        table = stats(rows, [by, TIME])
        table = table[[TIME, by, stat, "lower", "upper", "n"]]
    counts = rows.groupby(TIME)[ENTITY].nunique()
    if counts.nunique() > 1:
        notes.append(f"The number of units with data changes over time (from {counts.min():,} to {counts.max():,}), "
                     "so part of the change may come from which units are observed.")
    wide = rows[rows[TIME].isin([first, last])].pivot_table(index=ENTITY, columns=TIME, values=variable).dropna()
    rising = float((wide[last] > wide[first]).mean()) if len(wide) and {first, last} <= set(wide.columns) else math.nan

    fig = go.Figure()
    if units:
        ids = rows[ENTITY].drop_duplicates().sort_values().to_numpy(dtype=object)
        legend = "Each unit"
        if len(ids) > int(max_units):
            notes.append(f"The grey lines are a random sample of {int(max_units):,} of the {len(ids):,} units.")
            ids = np.random.default_rng(_SEED).choice(ids, size=int(max_units), replace=False)
            legend = f"Units (sample of {int(max_units):,})"
        paths = rows[rows[ENTITY].isin(set(ids))].sort_values([ENTITY, TIME])
        xs: list = []
        ys: list = []
        text: list = []
        for _, part in paths.groupby(ENTITY, sort=False):
            xs += [*part[TIME].tolist(), None]
            ys += [*part[variable].tolist(), None]
            text += [*part[NAME].astype(str).tolist(), None]
        fig.add_trace(go.Scatter(x=xs, y=ys, text=text, mode="lines", name=legend, connectgaps=False,
                                 line={"color": _UNIT_LINES, "width": 1},
                                 hovertemplate="%{text}<br>%{x}: %{y:,.4~g}<extra></extra>"))
    groups = [None] if by is None else list(dict.fromkeys(table[by]))
    stat_name = stat.capitalize()
    for k, group in enumerate(groups):
        part = table if group is None else table[table[by] == group]
        name = stat_name if group is None else str(group)
        colour = color_for(k)
        years = part[TIME].tolist()
        fig.add_trace(go.Scatter(x=years + years[::-1], y=part["upper"].tolist() + part["lower"].tolist()[::-1],
                                 fill="toself", fillcolor=_rgba(colour, 0.2), line={"width": 0}, mode="lines",
                                 hoverinfo="skip", showlegend=False, legendgroup=name))
        fig.add_trace(go.Scatter(x=years, y=part[stat], mode="lines+markers", name=name, legendgroup=name,
                                 line={"color": colour, "width": 3}, marker={"size": 7},
                                 customdata=np.c_[part["lower"], part["upper"], part["n"]],
                                 hovertemplate=(f"<b>{name}</b>, %{{x}}<br>{stat}: %{{y:,.4~g}}<br>band: "
                                                "%{customdata[0]:,.4~g} to %{customdata[1]:,.4~g}<br>"
                                                "%{customdata[2]:,} units<extra></extra>")))
    band = "± one standard error" if stat == "mean" else "and interquartile range"
    subtitle = f"{stat_name} across units {band}" + (f", by {by_label}" if by is not None else "")
    if units:
        subtitle += "; grey lines: each unit"
    apply_default_layout(fig, title=title if title is not None else f"{label} over time", subtitle=subtitle,
                         legend={"title": {"text": by_label}} if by is not None else {})
    fig.update_xaxes(title_text="Year", tickformat="d",
                     **({"tickmode": "array", "tickvals": have} if len(have) <= 12 else {}))
    fig.update_yaxes(title_text=label)

    return TrendResult(df=table.reset_index(drop=True), fig=fig, var=variable, by=by, stat=stat, first=first,
                       last=last, value_first=float(overall.loc[first]), value_last=float(overall.loc[last]),
                       change=float(overall.loc[last] - overall.loc[first]), share_rising=rising,
                       n_units=int(rows[ENTITY].nunique()), label=label, by_label=by_label, notes=tuple(notes))


__all__ = ["correlation", "distribution", "extremes", "scatter", "trend"]
