"""Regression models: least squares side by side, panel estimators, spatial models and their diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
import pandas as pd

from . import _inputs, project
from ._engine._labels import resolve_label
from ._engine.pedagogy import Interpretable

if TYPE_CHECKING:
    import plotly.graph_objects as go
    from great_tables import GT

ENTITY, TIME = _inputs.ENTITY, _inputs.TIME
_INTERCEPT = "Intercept"
_STARS_NOTE = "*** p<0.01, ** p<0.05, * p<0.10"
_TIDY = ["model", "term", "estimate", "std_error", "statistic", "p_value", "conf_low", "conf_high"]
_ESTIMATORS = {"pooled": "Pooled OLS", "between": "Between", "fe": "Fixed effects", "re": "Random effects"}
#: Regressors read one by one in an interpretation before it points to the table.
_MAX_TERMS = 4


# ---------------------------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------------------------

class Hausman(NamedTuple):
    """The Hausman test of fixed against random effects (chi-squared)."""

    statistic: float
    df: int
    p_value: float


@dataclass(frozen=True, repr=False)
class RegressionResult(Interpretable):
    """Result of ``regression``: least-squares specifications side by side.

    ``df`` is the tidy coefficient table (``model``, ``term``, ``estimate``, ``std_error``,
    ``statistic``, ``p_value``, ``conf_low``, ``conf_high``; fixed-effect dummies left out),
    ``summary`` has one row per model (``n``, ``r2``, ``r2_adj``, ``fixed_effects``,
    ``std_errors``), ``gt`` is the regression table, ``fig`` the coefficient plot and
    ``models`` the fitted statsmodels results, in the order of the specifications
    (model 1 is ``models[0]``). ``x`` and ``fixed_effects`` hold one tuple per model.
    """

    df: pd.DataFrame
    summary: pd.DataFrame
    gt: GT
    fig: go.Figure
    models: tuple[Any, ...]
    y: str
    x: tuple[tuple[str, ...], ...]
    years: tuple[int, ...]
    fixed_effects: tuple[tuple[str, ...], ...]
    cluster: str | None
    labels: dict[str, str]
    notes: tuple[str, ...] = ()

    @property
    def variable(self) -> str:
        """The outcome."""
        return self.y

    @property
    def year(self) -> int | None:
        """The year analysed (``None`` when several years are pooled, or without years)."""
        return self.years[0] if len(self.years) == 1 else None

    def interpret(self, *, lang: str = "en") -> str:
        """A plain-language reading of the coefficients, the fit and the standard errors (Markdown)."""
        return _read_regression(self)

    def tidy(self) -> pd.DataFrame:
        """The tidy coefficient table."""
        return self.df

    def glance(self) -> pd.DataFrame:
        """One row per model."""
        return self.summary


@dataclass(frozen=True, repr=False)
class PanelModelResult(Interpretable):
    """Result of ``panel_model``: the standard panel estimators side by side.

    ``df`` is the tidy coefficient table (``model`` is ``pooled``, ``between``, ``fe`` or
    ``re``), ``summary`` has one row per model (``n``, ``units``, ``years`` and the R²
    measures), ``gt`` is the comparison table, ``fig`` the coefficient plot, ``models`` the
    fitted linearmodels results keyed by estimator, and ``hausman`` the test of fixed
    against random effects (``statistic``, ``df``, ``p_value``; ``None`` when it was not
    computed, with the reason in ``notes``).
    """

    df: pd.DataFrame
    summary: pd.DataFrame
    gt: GT
    fig: go.Figure
    models: dict[str, Any]
    hausman: Hausman | None
    y: str
    x: tuple[str, ...]
    years: tuple[int, ...]
    n_obs: int
    n_units: int
    time_effects: bool
    cluster: bool
    labels: dict[str, str]
    notes: tuple[str, ...] = ()

    @property
    def variable(self) -> str:
        """The outcome."""
        return self.y

    @property
    def year(self) -> int | None:
        """``None``: a panel model uses every year (see ``years``)."""
        return None

    def interpret(self, *, lang: str = "en") -> str:
        """A plain-language reading of the between and within estimates and the Hausman test (Markdown)."""
        return _read_panel(self)

    def tidy(self) -> pd.DataFrame:
        """The tidy coefficient table."""
        return self.df

    def glance(self) -> pd.DataFrame:
        """One row per model."""
        return self.summary


# ---------------------------------------------------------------------------------------------
# shared: inputs
# ---------------------------------------------------------------------------------------------

def _unique(items) -> list:
    return list(dict.fromkeys(items))


def _is_all(year) -> bool:
    return isinstance(year, str) and year.lower() == "all"


def _known_scales(ref: str | None) -> set[str]:
    """The ids of the project's scales (none when the registry cannot be read)."""
    from .scales import scales as registry
    try:
        return set(registry(ref))
    except Exception:  # offline, or data that are not in the project
        return set()


def _source(data, variables: list[str], extras: list[str], ref: str | None, *, what: str):
    """Where the extra columns of a model (fixed effects, clusters) come from.

    Each one is a column of the table or a coarser scale, whose unit names are added as a
    column. Returns ``(data, groups)``: the data to prepare (a dataset id is loaded here
    when an extra is one of its own columns) and the scales to add as columns.
    """
    extras = [e for e in _unique(extras) if e not in (ENTITY, TIME)]
    if not extras:
        return data, []
    if isinstance(data, str):
        scales = _known_scales(ref)
        groups = [e for e in extras if e in scales]
        columns = [e for e in extras if e not in scales]
        if columns:
            from . import io
            data = io.load(data, variables=_unique([*variables, *columns]), names=True, groups=groups or None, ref=ref)
        return data, groups
    if not isinstance(data, pd.DataFrame):
        return data, []                                   # _inputs.panel raises the TypeError
    groups = [e for e in extras if e not in data.columns]
    unknown = [g for g in groups if g not in _known_scales(ref)]
    if unknown:
        raise ValueError(f"{what} {unknown}: neither a column of the table nor a coarser scale; "
                         f"the table has {[c for c in data.columns if c != ENTITY]}")
    return data, groups


def _check_xy(y: str, xs: list[str]) -> None:
    if not isinstance(y, str):
        raise TypeError("y must be the name of one column (the outcome)")
    if not xs:
        raise ValueError("x needs at least one column")
    if any(not isinstance(v, str) for v in xs):
        raise TypeError("x must be a column name or a list of column names")
    if y in xs:
        raise ValueError(f"The outcome {y!r} cannot also be a regressor")
    if len(set(xs)) != len(xs):
        raise ValueError(f"x repeats a column: {xs}")


def _specifications(y: str, x) -> list[list[str]]:
    """``x`` as a list of specifications: a list of columns is one model, a list of lists one model each."""
    if isinstance(x, str):
        specs = [[x]]
    else:
        items = list(x) if x is not None else []
        specs = [_inputs.as_list(i) for i in items] if any(not isinstance(i, str) for i in items) else [items]
    for spec in specs:
        _check_xy(y, spec)
    return specs


def _fixed_effects(fixed_effects) -> list[list[str]]:
    """``fixed_effects`` as one list per specification (a single list applies to all of them)."""
    if fixed_effects is None or isinstance(fixed_effects, str):
        return [_inputs.as_list(fixed_effects)]
    items = list(fixed_effects)
    if any(not isinstance(i, str) for i in items):         # None or a list: one entry per specification
        return [_unique(_inputs.as_list(i)) for i in items]
    return [_unique(items)]


def _years_text(years: tuple[int, ...]) -> str:
    if not years:
        return ""
    if len(years) == 1:
        return str(years[0])
    return f"{years[0]}–{years[-1]} ({len(years)} years pooled)"


# ---------------------------------------------------------------------------------------------
# shared: table, figure, wording
# ---------------------------------------------------------------------------------------------

def _num(value: float) -> str:
    """A number for a regression table: three decimals, or scientific notation when that shows nothing."""
    if not np.isfinite(value):
        return "--"
    size = abs(value)
    if size == 0 or 0.001 <= size < 1000:
        return f"{value:.3f}"
    return f"{value:,.1f}" if size >= 1000 else f"{value:.2e}"


def _stars(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def _terms(tidy: pd.DataFrame) -> list[str]:
    """The terms of a tidy table in order of first appearance, the intercept last."""
    terms = _unique(tidy["term"])
    return [t for t in terms if t != _INTERCEPT] + [t for t in terms if t == _INTERCEPT]


def _tidy(model, terms: list[str], params, std_errors, statistics, p_values, intervals) -> pd.DataFrame:
    """The tidy rows of one fitted model for ``terms`` (labels of ``params``)."""
    low, high = intervals.iloc[:, 0], intervals.iloc[:, 1]
    return pd.DataFrame({
        "model": model, "term": terms,
        "estimate": [float(params[t]) for t in terms], "std_error": [float(std_errors[t]) for t in terms],
        "statistic": [float(statistics[t]) for t in terms], "p_value": [float(p_values[t]) for t in terms],
        "conf_low": [float(low[t]) for t in terms], "conf_high": [float(high[t]) for t in terms],
    }).replace({"term": {"const": _INTERCEPT}})[_TIDY]


def _comparison_table(tidy: pd.DataFrame, headers: dict, labels: dict[str, str], footer: list[tuple[str, list[str]]], *,
                      title: str, subtitle: str, spanner: str, notes: list[str]) -> GT:
    """A regression table: per term the estimate with stars and, below it, the standard error; then ``footer`` rows.

    ``headers`` maps each model id of ``tidy`` to its column header, in column order.
    """
    from great_tables import GT, loc, style

    cells = tidy.set_index(["model", "term"])
    rows: list[list[str]] = []
    for term in _terms(tidy):
        estimates, errors = [labels.get(term, term)], [""]
        for model in headers:
            if (model, term) in cells.index:
                row = cells.loc[(model, term)]
                estimates.append(f"{_num(row['estimate'])}{_stars(row['p_value'])}")
                errors.append(f"({_num(row['std_error'])})")
            else:
                estimates.append("")
                errors.append("")
        rows += [estimates, errors]
    first_footer = len(rows)
    rows += [[label, *values] for label, values in footer]
    columns = [str(h) for h in headers.values()]
    table = (GT(pd.DataFrame(rows, columns=["term", *columns]))
             .tab_header(title=title, subtitle=subtitle)
             .tab_spanner(label=spanner, columns=columns)
             .cols_label(term="")
             .cols_align(align="center", columns=columns)
             .tab_style(style=style.borders(sides="top", color="#7f7f7f", weight="1px"),
                        locations=loc.body(rows=[first_footer])))
    for note in notes:
        table = table.tab_source_note(note)
    return table


def _coefficient_figure(tidy: pd.DataFrame, legend: dict, labels: dict[str, str], *, title: str, subtitle: str,
                        legend_title: str) -> go.Figure:
    """Estimates with their 95% intervals, one colour per model, the intercept left out.

    ``legend`` maps each model id of ``tidy`` to its legend name, in drawing order.
    """
    import plotly.graph_objects as go

    from ._engine._theme import apply_default_layout, color_for

    shown = tidy[tidy["term"] != _INTERCEPT]
    terms = _unique(shown["term"])
    position = {term: i for i, term in enumerate(terms)}
    n = len(legend)
    step = 0.0 if n == 1 else min(0.6 / n, 0.18)
    fig = go.Figure()
    for j, (model, name) in enumerate(legend.items()):
        sub = shown[shown["model"] == model]
        if sub.empty:
            continue
        offset = (j - (n - 1) / 2) * step
        fig.add_trace(go.Scatter(
            x=sub["estimate"], y=[position[t] + offset for t in sub["term"]], mode="markers", name=str(name),
            showlegend=n > 1, marker={"color": color_for(j), "size": 9},
            error_x={"type": "data", "symmetric": False, "array": (sub["conf_high"] - sub["estimate"]).to_numpy(),
                     "arrayminus": (sub["estimate"] - sub["conf_low"]).to_numpy(), "thickness": 1.5,
                     "color": color_for(j)},
            customdata=np.column_stack([[labels.get(t, t) for t in sub["term"]], sub["conf_low"], sub["conf_high"],
                                        sub["p_value"]]),
            hovertemplate=("<b>%{customdata[0]}</b><br>" + str(name) + ": %{x:.4g}"
                           "<br>95% interval: %{customdata[1]:.4g} to %{customdata[2]:.4g}"
                           "<br>p = %{customdata[3]:.3g}<extra></extra>"),
        ))
    fig.add_vline(x=0, line_dash="dash", line_color="rgba(0,0,0,0.4)")
    apply_default_layout(
        fig, title=title, subtitle=subtitle, legend_title_text=legend_title,
        xaxis={"title": "Coefficient, with its 95% confidence interval"},
        yaxis={"tickmode": "array", "tickvals": list(position.values()), "ticktext": [labels.get(t, t) for t in terms],
               "title": "", "autorange": "reversed", "automargin": True},
    )
    return fig


def _coefficient_phrase(row, outcome: str) -> str:
    """One coefficient in words: size, direction, significance and interval."""
    from ._engine.pedagogy._format import direction_word, fmt_num, significance_phrase
    return (f"a one-unit higher value goes with {outcome} that is {fmt_num(abs(row['estimate']))} "
            f"{direction_word(row['estimate'])} ({significance_phrase(row['p_value'])}; 95% interval "
            f"{fmt_num(row['conf_low'])} to {fmt_num(row['conf_high'])})")


def _notes_block(notes: tuple[str, ...]) -> list[str]:
    return ["", *[f"- Note: {note}" for note in notes]] if notes else []


# ---------------------------------------------------------------------------------------------
# regression
# ---------------------------------------------------------------------------------------------

def _fixed_effect_label(column: str, labels: dict[str, str]) -> str:
    if column == TIME:
        return "Year"
    return "Unit" if column == ENTITY else labels.get(column, column)


def _fit_ols(df: pd.DataFrame, y: str, xs: list[str], effects: list[str], cluster: str | None, robust: bool):
    """One least-squares model on the rows complete in its columns.

    Returns ``(fitted, shown, errors, n_clusters)``: the statsmodels result, the terms to
    report (the regressors, and the intercept unless fixed effects absorb it) and a
    description of the standard errors.
    """
    import statsmodels.api as sm

    sample = df.dropna(subset=_unique([y, *xs, *effects, *([cluster] if cluster else [])]))
    design = pd.DataFrame({_INTERCEPT: 1.0}, index=sample.index)
    design[xs] = sample[xs].astype(float)
    for column in effects:
        levels = sample[column].nunique()
        if levels < 2:
            hint = ' Pool the years (year="all") to use year fixed effects.' if column == TIME else ""
            raise ValueError(f"The fixed effect {column!r} has {levels} value(s) in the {len(sample)} rows used, "
                             f"so there is nothing to absorb.{hint}")
        dummies = pd.get_dummies(sample[column].astype(str), prefix=column, prefix_sep=" = ", drop_first=True,
                                 dtype=float)
        design = pd.concat([design, dummies], axis=1)
    n, k = design.shape
    if n <= k:
        raise ValueError(f"Only {n} complete row(s) for {k} coefficients (regressors, intercept and fixed-effect "
                         "dummies): not enough to estimate")
    scaled = design.to_numpy() / np.linalg.norm(design.to_numpy(), axis=0)
    rank = np.linalg.matrix_rank(scaled)
    if rank < k:                                           # dummies may overlap (nested scales); regressors may not
        redundant = [v for v in xs
                     if np.linalg.matrix_rank(np.delete(scaled, design.columns.get_loc(v), axis=1)) == rank]
        if redundant:
            other = "the other regressors or the fixed effects" if effects else "the other regressors"
            raise ValueError(f"{redundant} cannot be told apart from {other} (constant or collinear), "
                             "so the coefficient(s) cannot be estimated")
    model = sm.OLS(sample[y].astype(float), design)
    n_clusters = None
    if cluster:
        codes = pd.factorize(sample[cluster])[0]
        n_clusters = int(codes.max()) + 1
        if n_clusters < 2:
            raise ValueError(f"cluster={cluster!r} has a single value in the rows used; clustering needs several")
        fitted = model.fit(cov_type="cluster", cov_kwds={"groups": codes}, use_t=True)
        errors = f"clustered by {cluster} ({n_clusters} clusters)"
    elif robust:
        fitted = model.fit(cov_type="HC1", use_t=True)
        errors = "heteroskedasticity-robust (HC1)"
    else:
        fitted = model.fit()
        errors = "classical"
    shown = [*xs] if effects else [*xs, _INTERCEPT]
    return fitted, shown, errors, n_clusters


def regression(data, y: str, x, year=None, *, fixed_effects=None, cluster: str | None = None, robust: bool = True,
               title: str | None = None, ref: str | None = None) -> RegressionResult:
    """Ordinary least squares, with several specifications side by side.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load`` or ``combine``
    y
        The outcome column
    x
        The regressors: a column or a list of columns (one model), or a list of lists
        (one model per list, e.g. adding controls step by step)
    year
        The year to use (default: the last with data for ``y`` and every regressor),
        a list of years, or ``"all"`` to pool every year
    fixed_effects
        A column, a coarser scale (e.g. the scale above the units'),
        ``"year"``, or a list of them: absorbed as dummies and reported as Yes/No rows
        instead of coefficients. A list with one entry per model, where an entry is
        ``None`` or a list, sets them model by model
    cluster
        A column or a coarser scale: standard errors clustered by it (p-values and
        intervals then use a t distribution with one degree of freedom less than clusters)
    robust
        Heteroskedasticity-robust standard errors (HC1) when there is no
        ``cluster``; ``False``: classical standard errors
    title
        The title of the table and of the figure

    Returns
    -------
    RegressionResult
        A result with ``.gt`` (the regression table: coefficients with stars, standard
        errors in parentheses, the fixed effects, N and R²), ``.fig`` (the coefficients with
        95% confidence intervals across models), ``.df`` (tidy: ``model``, ``term``,
        ``estimate``, ``std_error``, ``statistic``, ``p_value``, ``conf_low``,
        ``conf_high``), ``.summary`` (one row per model: ``n``, ``r2``, ``r2_adj``,
        ``fixed_effects``, ``std_errors``), ``.models`` (the fitted statsmodels results)
        and ``.interpret()``.
    """
    specs, effects = _specifications(y, x), _fixed_effects(fixed_effects)
    n_models = max(len(specs), len(effects))
    if {len(specs), len(effects)} - {1, n_models}:
        raise ValueError(f"x has {len(specs)} specifications but fixed_effects has {len(effects)} entries")
    specs = specs * n_models if len(specs) == 1 else specs
    effects = effects * n_models if len(effects) == 1 else effects
    if cluster is not None and not isinstance(cluster, str):
        raise TypeError("cluster must be the name of one column or scale")
    variables = _unique([y, *[v for spec in specs for v in spec]])
    extras = _unique([*[e for fe in effects for e in fe], *([cluster] if cluster else [])])
    source, groups = _source(data, variables, extras, ref, what="fixed_effects / cluster")
    df = _inputs.panel(source, variables, groups=groups, ref=ref)

    notes: list[str] = []
    years: tuple[int, ...] = ()
    if TIME in df.columns:
        complete = df.dropna(subset=variables)
        if _is_all(year):
            years = tuple(_inputs.years(complete))
            if not years:
                raise ValueError(f"No rows with data for all of {variables}")
        elif isinstance(year, list | tuple):
            years = tuple(sorted({_inputs.pick_year(complete, y, v) for v in year}))
        else:
            years = (_inputs.pick_year(complete, y, year),)
        attrs = dict(df.attrs)
        df = df[df[TIME].isin(years)].reset_index(drop=True)
        df.attrs = attrs
    elif year is not None and not _is_all(year):
        raise ValueError("The table has no year column, so year= cannot be used")
    if TIME in extras and TIME not in df.columns:
        raise ValueError("The table has no year column, so year fixed effects (or clusters) cannot be used")

    labels = {c: resolve_label(df, c) for c in _unique([*variables, *extras])}
    y_label = labels[y]
    fitted, tidies, rows = [], [], []
    for i, (xs, fe) in enumerate(zip(specs, effects, strict=True), start=1):
        res, shown, errors, n_clusters = _fit_ols(df, y, xs, fe, cluster, robust)
        fitted.append(res)
        tidies.append(_tidy(i, shown, res.params, res.bse, res.tvalues, res.pvalues, res.conf_int()))
        rows.append({"model": i, "n": int(res.nobs), "r2": float(res.rsquared), "r2_adj": float(res.rsquared_adj),
                     "fixed_effects": ", ".join(fe) if fe else "none", "std_errors": errors})
    tidy = pd.concat(tidies, ignore_index=True)
    summary = pd.DataFrame(rows)

    sizes = sorted(set(summary["n"]))
    if len(sizes) > 1:
        notes.append(f"The models use different rows (n from {sizes[0]:,} to {sizes[-1]:,}) because each one keeps "
                     "the rows complete in its own columns")
    if cluster and n_clusters is not None and n_clusters < 30:
        notes.append(f"Only {n_clusters} clusters: cluster-robust standard errors tend to be too small with few clusters")
    if len(years) > 1 and cluster is None and df[ENTITY].duplicated().any():
        notes.append(f"The years are pooled, so the same units appear several times; cluster={ENTITY!r} allows for "
                     "the dependence between a unit's rows")

    when = _years_text(years)
    all_effects = _unique([e for fe in effects for e in fe])
    footer = [(f"{_fixed_effect_label(e, labels)} fixed effects", ["Yes" if e in fe else "No" for fe in effects])
              for e in all_effects]
    footer += [("Observations", [f"{n:,}" for n in summary["n"]]),
               ("R²", [f"{v:.3f}" for v in summary["r2"]]),
               ("Adjusted R²", [f"{v:.3f}" for v in summary["r2_adj"]])]
    errors_text = summary["std_errors"].iloc[0]
    gt = _comparison_table(
        tidy, {i: f"({i})" for i in summary["model"]}, labels, footer,
        title=title or f"Regression of {y_label}", subtitle=", ".join(t for t in ("Ordinary least squares", when) if t),
        spanner=y_label, notes=[f"{_STARS_NOTE}. Standard errors in parentheses: {errors_text}."])
    fig = _coefficient_figure(
        tidy, {i: f"({i})" for i in summary["model"]}, labels, title=title or f"{y_label}: regression coefficients",
        subtitle=", ".join(t for t in ("Ordinary least squares", when, f"standard errors: {errors_text}") if t),
        legend_title="Model")
    return RegressionResult(df=tidy, summary=summary, gt=gt, fig=fig, models=tuple(fitted), y=y,
                            x=tuple(tuple(s) for s in specs), years=years,
                            fixed_effects=tuple(tuple(fe) for fe in effects), cluster=cluster, labels=labels,
                            notes=tuple(notes))


def _read_regression(result: RegressionResult) -> str:
    from ._engine.pedagogy._format import fmt_num
    from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE

    labels, tidy, summary = result.labels, result.df, result.summary
    outcome = labels.get(result.y, result.y)
    n_models = len(result.models)
    last = summary.iloc[-1]
    xs, effects = result.x[-1], result.fixed_effects[-1]
    when = _years_text(result.years)
    head = f"**Ordinary least squares** of **{outcome}**" + (f", {when}" if when else "")
    head += (f": {n_models} specifications side by side. Model ({n_models}), the last one, reads as follows."
             if n_models > 1 else f" on {len(xs)} regressor{'s' if len(xs) != 1 else ''}.")
    lines = [head, ""]

    held = []
    if len(xs) > 1:
        held.append("the other regressors held constant")
    if effects:
        held.append("within the same " + " and ".join(_fixed_effect_label(e, labels).lower() for e in effects))
    rows = tidy[(tidy["model"] == last["model"]) & (tidy["term"] != _INTERCEPT)]
    for _, row in rows.head(_MAX_TERMS).iterrows():
        lines.append(f"- **{labels.get(row['term'], row['term'])}**: {_coefficient_phrase(row, outcome)}"
                     + (f", {', '.join(held)}." if held else "."))
    if len(rows) > _MAX_TERMS:
        lines.append(f"- (The other {len(rows) - _MAX_TERMS} regressors are in `.df` and `.gt`.)")
    lines.append("")

    if effects:
        names = ", ".join(f"*{_fixed_effect_label(e, labels)}*" for e in effects)
        lines.append(f"Fixed effects for {names} absorb every difference between their groups, so the coefficients "
                     "compare observations of the same group only.")
    fit = (f"The model has {int(last['n']):,} observations and R² = {fmt_num(last['r2'])} "
           f"(adjusted {fmt_num(last['r2_adj'])}): the regressors"
           f"{' and the fixed effects' if effects else ''} account for {last['r2']:.1%} of the variation "
           f"in {outcome}.")
    lines.append(fit)
    lines.append(f"Standard errors are {last['std_errors']}.")

    focus = result.x[0][0]
    path = tidy[tidy["term"] == focus]
    if n_models > 1 and len(path) > 1:
        steps = ", ".join(f"({int(m)}) {fmt_num(e)}" for m, e in zip(path["model"], path["estimate"], strict=True))
        first, final = float(path["estimate"].iloc[0]), float(path["estimate"].iloc[-1])
        if first * final < 0:
            move = "It changes sign"
        elif abs(final) < 0.8 * abs(first):
            move = "It shrinks"
        elif abs(final) > 1.25 * abs(first):
            move = "It grows"
        else:
            move = "It is stable"
        lines += ["", f"Across the models, the coefficient on **{labels.get(focus, focus)}** is {steps}. {move}: a "
                      "coefficient that moves when regressors or fixed effects are added was partly picking up what "
                      "they measure; one that stays put does not depend on them."]
    lines += _notes_block(result.notes)
    lines += ["", _ASSOC_NOTE]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------
# panel_model
# ---------------------------------------------------------------------------------------------

def _linearmodels():
    """``linearmodels.panel``, or an ImportError with the install line."""
    try:
        import linearmodels.panel as lmp
    except ImportError as exc:
        raise ImportError('panel_model needs the linearmodels library; install it with: '
                          f'pip install "{project.PACKAGE}[panel]"') from exc
    return lmp


def _hausman_test(lmp, outcome, within_x, random_x, xs: list[str], time_effects: bool) -> tuple[Hausman | None, list[str]]:
    """Hausman's chi-squared test on the regressors' coefficients, with classical covariances.

    Both covariance matrices use the residual variance of the fixed-effects model, which is
    also the idiosyncratic variance of the random-effects model. With each model's own
    residual variance their difference is often not positive definite, and the statistic
    negative, precisely when the random-effects assumption fails.
    """
    from scipy import stats

    fe = lmp.PanelOLS(outcome, within_x, entity_effects=True, time_effects=time_effects).fit()
    re = lmp.RandomEffects(outcome, random_x).fit()
    gap = (fe.params[xs] - re.params[xs]).to_numpy()
    variance = fe.cov.loc[xs, xs].to_numpy() - re.cov.loc[xs, xs].to_numpy() * float(fe.s2) / float(re.s2)
    statistic = float(gap @ np.linalg.pinv(variance) @ gap)
    if not np.isfinite(statistic) or statistic < 0:
        return None, ["The Hausman test could not be computed: the difference between the fixed- and random-effects "
                      "covariance matrices is not positive definite in this sample"]
    return Hausman(statistic, len(xs), float(stats.chi2.sf(statistic, len(xs)))), []


def panel_model(data, y: str, x, *, models=("pooled", "between", "fe", "re"), time_effects: bool = False,
                cluster: bool = True, title: str | None = None, ref: str | None = None) -> PanelModelResult:
    """The standard panel estimators side by side, and the Hausman test of fixed against random effects.

    The units are ``geo_id`` and the periods ``year``; every year with data is used.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load`` or ``combine``
    y
        The outcome column
    x
        The regressors: a column or a list of columns
    models
        The estimators to compare, in order: ``"pooled"`` (least squares on all
        rows), ``"between"`` (on the units' averages over the years), ``"fe"`` (fixed
        effects: each unit's deviations from its own average) and ``"re"`` (random effects)
    time_effects
        Add year effects (to every estimator but ``"between"``)
    cluster
        Standard errors clustered by unit; ``False``: heteroskedasticity-robust.
        The between estimator, with one row per unit, is always heteroskedasticity-robust
    title
        The title of the table and of the figure

    Returns
    -------
    PanelModelResult
        A result with ``.gt`` (the comparison table), ``.fig`` (the coefficients with 95%
        confidence intervals across estimators), ``.df`` (tidy: ``model``, ``term``,
        ``estimate``, ``std_error``, ``statistic``, ``p_value``, ``conf_low``,
        ``conf_high``), ``.summary`` (one row per model: ``n``, ``units``, ``years``,
        ``r2``, ``r2_within``, ``r2_between``, ``r2_overall``), ``.models`` (the fitted
        linearmodels results, keyed by estimator), ``.hausman`` (``statistic``, ``df``,
        ``p_value``; ``None`` unless both ``"fe"`` and ``"re"`` are estimated and the test
        can be computed) and ``.interpret()``.

        The Hausman test compares the fixed- and random-effects coefficients of the regressors
        with classical covariance matrices that share the residual variance of the
        fixed-effects model, so that their difference is positive semi-definite.

        Needs the ``linearmodels`` library (the ``[panel]`` extra).
    """
    lmp = _linearmodels()
    xs = _inputs.as_list(x)
    _check_xy(y, xs)
    kinds = _unique([str(m).lower() for m in _inputs.as_list(models)])
    unknown = [k for k in kinds if k not in _ESTIMATORS]
    if unknown or not kinds:
        raise ValueError(f"Unknown model(s) {unknown}; choose from {list(_ESTIMATORS)}")
    df = _inputs.panel(data, [y, *xs], ref=ref)
    if TIME not in df.columns:
        raise ValueError("panel_model needs a panel: the table has no year column")
    sample = df.dropna(subset=[y, *xs, TIME])
    years = tuple(sorted(int(v) for v in sample[TIME].unique()))
    if len(years) < 2:
        raise ValueError(f"panel_model needs at least two years; the rows with data for {[y, *xs]} cover {list(years)}")
    if sample.duplicated([ENTITY, TIME]).any():
        raise ValueError(f"panel_model needs one row per {ENTITY} and {TIME}; the table repeats some")
    per_unit = sample.groupby(ENTITY)[TIME].size()
    n_units, repeated = len(per_unit), int((per_unit > 1).sum())
    if repeated == 0:
        raise ValueError(f"No unit has data for {[y, *xs]} in more than one year, so there is no variation within "
                         "units to estimate from")
    if "fe" in kinds:
        values = sample[[y, *xs]].astype(float)
        within = values - values.groupby(sample[ENTITY]).transform("mean")
        flat = [c for c in [y, *xs] if np.allclose(within[c], 0.0, atol=1e-10 * max(1.0, float(values[c].abs().max())))]
        if flat:
            raise ValueError(f"{flat} do(es) not change within units over the years, so fixed effects have nothing to "
                             "estimate from; drop the column(s) or leave 'fe' out of models")
    if "between" in kinds and n_units <= len(xs) + 1:
        raise ValueError(f"The between estimator needs more units than coefficients; there are {n_units} units "
                         f"for {len(xs) + 1} coefficients")

    notes: list[str] = []
    if repeated < n_units:
        notes.append(f"Units with data in a single year ({n_units - repeated} of {n_units}) do not inform the "
                     "fixed-effects estimates")
    indexed = sample.assign(**{TIME: sample[TIME].astype(int)}).set_index([ENTITY, TIME])
    outcome, within_x = indexed[y].astype(float), indexed[xs].astype(float)
    pooled_x = within_x.assign(const=1.0)
    timed_x = pooled_x
    if time_effects:
        dummies = pd.get_dummies(indexed.index.get_level_values(TIME).astype(str), prefix=TIME, prefix_sep=" = ",
                                 drop_first=True, dtype=float).set_index(indexed.index)
        timed_x = pd.concat([pooled_x, dummies], axis=1)
        if "between" in kinds:
            notes.append("Year effects do not apply to the between estimator, which averages each unit over the years")
    cov = {"cov_type": "clustered", "cluster_entity": True} if cluster else {"cov_type": "robust"}
    errors = f"clustered by {ENTITY}" if cluster else "heteroskedasticity-robust"

    fitted: dict[str, Any] = {}
    tidies, rows = [], []
    for kind in kinds:
        try:
            if kind == "pooled":
                res = lmp.PooledOLS(outcome, timed_x).fit(**cov)
            elif kind == "between":
                res = lmp.BetweenOLS(outcome, pooled_x).fit(cov_type="robust")
            elif kind == "fe":
                res = lmp.PanelOLS(outcome, within_x, entity_effects=True, time_effects=time_effects).fit(**cov)
            else:
                res = lmp.RandomEffects(outcome, timed_x).fit(**cov)
        except Exception as exc:
            if type(exc).__name__ != "AbsorbingEffectError":
                raise
            raise ValueError(f"The {_ESTIMATORS[kind].lower()} model cannot be estimated: a regressor is fully "
                             "explained by the unit and year effects (it changes by the same amount in every unit)"
                             ) from exc
        fitted[kind] = res
        shown = [*xs, *(["const"] if "const" in res.params.index else [])]
        tidies.append(_tidy(kind, shown, res.params, res.std_errors, res.tstats, res.pvalues, res.conf_int()))
        rows.append({"model": kind, "estimator": _ESTIMATORS[kind], "n": int(res.nobs),
                     "units": int(res.entity_info["total"]), "years": int(res.time_info["total"]),
                     "r2": float(res.rsquared), "r2_within": float(res.rsquared_within),
                     "r2_between": float(res.rsquared_between), "r2_overall": float(res.rsquared_overall),
                     "time_effects": bool(time_effects and kind != "between"),
                     "std_errors": "heteroskedasticity-robust" if kind == "between" else errors})
    tidy = pd.concat(tidies, ignore_index=True)
    summary = pd.DataFrame(rows)

    hausman = None
    if {"fe", "re"} <= set(kinds):
        hausman, test_notes = _hausman_test(lmp, outcome, within_x, timed_x, xs, time_effects)
        notes += test_notes
    else:
        notes.append("The Hausman test compares fixed and random effects: it needs both 'fe' and 're' in models")

    labels = {c: resolve_label(df, c) for c in [y, *xs]}
    y_label = labels[y]
    span = f"{years[0]}–{years[-1]}"
    unit_effects = {"pooled": "No", "between": "No", "fe": "Fixed", "re": "Random"}
    footer = [("Unit effects", [unit_effects[k] for k in kinds]),
              ("Year effects", ["Yes" if t else "No" for t in summary["time_effects"]]),
              ("Observations", [f"{n:,}" for n in summary["n"]]),
              ("Units", [f"{n:,}" for n in summary["units"]]),
              ("R²", [f"{v:.3f}" for v in summary["r2"]]),
              ("R² within", [f"{v:.3f}" for v in summary["r2_within"]]),
              ("R² between", [f"{v:.3f}" for v in summary["r2_between"]])]
    table_notes = [f"{_STARS_NOTE}. Standard errors in parentheses: {errors} (between: heteroskedasticity-robust)."]
    if hausman is not None:
        p_text = "p < 0.0001" if hausman.p_value < 0.0001 else f"p = {hausman.p_value:.4f}"
        table_notes.append(f"Hausman test of fixed against random effects: χ²({hausman.df}) = {hausman.statistic:.2f}, "
                           f"{p_text}")
    subtitle = f"{len(sample):,} observations of {n_units:,} units, {span} ({len(years)} years)"
    headers = {k: _ESTIMATORS[k] for k in kinds}
    gt = _comparison_table(tidy, headers, labels, footer, title=title or f"Panel models of {y_label}",
                           subtitle=subtitle, spanner=y_label, notes=table_notes)
    fig = _coefficient_figure(tidy, headers, labels, title=title or f"{y_label}: panel estimates", subtitle=subtitle,
                              legend_title="Estimator")
    return PanelModelResult(df=tidy, summary=summary, gt=gt, fig=fig, models=fitted, hausman=hausman, y=y,
                            x=tuple(xs), years=years, n_obs=len(sample), n_units=n_units,
                            time_effects=bool(time_effects), cluster=bool(cluster), labels=labels, notes=tuple(notes))


def _read_panel(result: PanelModelResult) -> str:
    from ._engine.pedagogy._format import direction_word, fmt_num, significance_phrase
    from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE

    labels, tidy, years = result.labels, result.df, result.years
    outcome = labels.get(result.y, result.y)
    kinds = list(result.models)
    lines = [f"**Panel models** of **{outcome}**: {result.n_obs:,} observations of {result.n_units:,} units over "
             f"{len(years)} years ({years[0]}–{years[-1]}), estimated as "
             f"{', '.join(_ESTIMATORS[k][0].lower() + _ESTIMATORS[k][1:] for k in kinds)}"
             f"{', with year effects' if result.time_effects else ''}.", ""]
    words = {
        "pooled": "pooling all rows",
        "between": "between units (comparing the units' averages over the years)",
        "fe": "within units (fixed effects: each unit compared with itself over the years)",
        "re": "with random effects (a weighted mix of the between and within comparisons)",
    }
    cells = tidy.set_index(["model", "term"])
    for term in result.x[:_MAX_TERMS]:
        lines.append(f"- **{labels.get(term, term)}**, a one-unit higher value goes with {outcome} that is:")
        for kind in kinds:
            row = cells.loc[(kind, term)]
            lines.append(f"    - {fmt_num(abs(row['estimate']))} {direction_word(row['estimate'])} {words[kind]} "
                         f"({significance_phrase(row['p_value'])});")
        lines[-1] = lines[-1][:-1] + "."
    if len(result.x) > _MAX_TERMS:
        lines.append(f"- (The other {len(result.x) - _MAX_TERMS} regressors are in `.df` and `.gt`.)")
    lines.append("")

    if {"between", "fe"} <= set(kinds):
        lines.append("The between estimate asks whether units with a higher regressor have a higher or lower outcome "
                     "than other units; the within (fixed-effects) estimate asks whether a unit's outcome moves when "
                     "its own regressor moves, which leaves out every lasting difference between units. When the two "
                     "disagree, the units that differ in the regressor also differ in other lasting ways that go with "
                     "the outcome.")
    elif "fe" in kinds:
        lines.append("The fixed-effects estimate uses only each unit's changes over the years, which leaves out every "
                     "lasting difference between units.")
    if "fe" in kinds and len(years) == 2 and not result.time_effects:
        lines.append(f"With only two years ({years[0]} and {years[1]}), the fixed-effects estimate rests on one change "
                     "per unit, and without year effects it also absorbs the changes common to all units between the "
                     "two years (a shift that every unit shares counts as association); `time_effects=True` removes "
                     "them.")
    test = result.hausman
    if test is not None:
        reading = (f"**Hausman test**: χ²({test.df}) = {fmt_num(test.statistic)}, p = {fmt_num(test.p_value)}. ")
        if test.p_value < 0.05:
            reading += ("The fixed- and random-effects estimates differ by more than chance allows, so the lasting "
                        "differences between units are related to the regressors: random effects are not reliable "
                        "here and **fixed effects** are the estimates to read.")
        else:
            reading += ("The fixed- and random-effects estimates do not differ by more than chance allows, so "
                        "**random effects**, the more precise of the two, are admissible. This is a lack of evidence "
                        "against them, not a proof that they are right.")
        lines += ["", reading]
    lines += _notes_block(tuple(n for n in result.notes if test is None or "Hausman test compares" not in n))
    lines += ["", _ASSOC_NOTE]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------
# spatial models
# ---------------------------------------------------------------------------------------------

def _cross_section(data, y: str, x, year, fixed_effects, gdf, w, ref: str | None, *, what: str):
    """The inputs of a spatial model of one year: panel, boundaries, weights, regressors, fixed-effect column."""
    xs = _inputs.as_list(x)
    _check_xy(y, xs)
    if _is_all(year) or isinstance(year, list | tuple):
        raise ValueError(f"{what} analyses one year: give a single year (default: the last with data)")
    effects = _inputs.as_list(fixed_effects)
    if len(effects) > 1:
        raise ValueError(f"{what} takes one fixed_effects column or scale, got {effects}")
    if TIME in effects or ENTITY in effects:
        raise ValueError(f"{what} analyses one row per unit, so {effects[0]!r} cannot be a fixed effect")
    variables = [y, *xs]
    source, groups = _source(data, variables, effects, ref, what="fixed_effects")
    df = _inputs.panel(source, variables, groups=groups, gdf=gdf, ref=ref)
    if TIME in df.columns:                                  # the last year with data for every variable
        year = _inputs.pick_year(df.dropna(subset=variables), y, year)
    df, geo, w = _inputs.spatial(df, variables, year=year, gdf=gdf, w=w, groups=groups, ref=ref)
    return df, geo, w, xs, (effects[0] if effects else None)


def spatial_model(data, y: str, x, year=None, *, model: str = "durbin", method: str = "ml", w=None,
                  fixed_effects: str | None = None, impacts: bool = True, n_draws: int = 10_000,
                  seed: int | None = 12345, title: str | None = None, gdf=None, ref: str | None = None):
    """A spatial regression for one year, with direct, indirect (spillover) and total impacts.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load`` or ``combine``
    y
        The outcome column
    x
        The regressors: a column or a list of columns
    year
        The year to model (default: the last with data for ``y`` and every regressor)
    model
        ``"ols"`` (no spatial term), ``"lag"`` (neighbours' outcome), ``"error"``
        (spatially correlated errors), ``"slx"`` (neighbours' regressors), ``"durbin"``
        (neighbours' outcome and regressors) or ``"durbin_error"`` (neighbours'
        regressors and spatially correlated errors)
    method
        ``"ml"`` (maximum likelihood) or ``"gm"`` (generalized method of moments;
        not for ``"durbin_error"``)
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    fixed_effects
        A column or a coarser scale, added as dummies
    impacts
        Compute the direct, indirect and total impacts where the model has them
    n_draws
        Simulation draws behind the standard errors of the impacts
    seed
        Makes the draws reproducible
    title
        The title of the table
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.df`` (tidy coefficients: ``variable``, the column name, with
        ``const`` for the intercept and ``W_<column>`` for a spatial lag; ``term``, its
        label; ``estimate``, ``se``, ``z``, ``p``), ``.gt`` (the coefficient table),
        ``.impacts`` (one row per regressor: ``variable``, ``term``,
        ``direct``, ``indirect``, ``total`` and their standard errors; ``None`` for
        ``"ols"`` and ``"error"``), the spatial parameters ``.rho`` (lag) and ``.lam``
        (error), ``.r2``, ``.aic``, ``.log_likelihood``, ``.n_obs``, ``.model_obj`` (the
        fitted spreg model) and ``.interpret()``.
    """
    from ._engine.spatial_models import analyze_spatial_model
    df, geo, w, xs, effect = _cross_section(data, y, x, year, fixed_effects, gdf, w, ref, what="spatial_model")
    return _with_columns(_inputs.finish(analyze_spatial_model(
        df, y, xs, gdf=geo, w=w, model=model, method=method, period=_inputs.one_year(df), fixed_effects=effect,
        impacts=impacts, n_draws=n_draws, seed=seed, title=title), df), df)


def _with_columns(result, df: pd.DataFrame):
    """A spatial model's tables with the column name of each term (``variable``) next to its label (``term``).

    The engine names terms by label, which reads well in a table; ``variable`` is the
    stable key: the column name, ``const`` for the intercept and ``W_<column>`` for a
    spatial lag.
    """
    from dataclasses import replace

    back = {label: name for name, label in (df.attrs.get("geo_labels") or {}).items()}

    def column(term: str) -> str:
        if term == "CONSTANT":
            return "const"
        if term.startswith("W_"):
            return "W_" + back.get(term[2:], term[2:])
        return back.get(term, term)

    changes = {}
    for field in ("df", "impacts"):
        frame = getattr(result, field, None)
        if isinstance(frame, pd.DataFrame) and "term" in frame.columns and "variable" not in frame.columns:
            frame = frame.copy()
            frame.insert(0, "variable", frame["term"].map(column))
            changes[field] = frame
    return replace(result, **changes) if changes else result


def spatial_diagnostics(data, y: str, x, year=None, *, w=None, fixed_effects: str | None = None, alpha: float = 0.05,
                        gdf=None, ref: str | None = None):
    """Tests for spatial dependence left in a least-squares regression, and the spatial model they point to.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` (and ``year``), e.g. from ``load`` or ``combine``
    y
        The outcome column
    x
        The regressors: a column or a list of columns
    year
        The year to test (default: the last with data for ``y`` and every regressor)
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    fixed_effects
        A column or a coarser scale, added as dummies
    alpha
        Significance level of the decision rule
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.df`` (one row per test: Moran's I of the residuals, the Lagrange
        multiplier tests for a lag and for an error model, their robust forms and the joint
        test, with ``statistic``, ``df`` and ``p``), ``.gt`` (the same as a table),
        ``.recommendation`` (``"ols"``, ``"lag"`` or ``"error"``), ``.reasoning``,
        ``.moran_i_resid``, ``.ols_model`` (the fitted spreg model) and ``.interpret()``.
    """
    from ._engine.spatial_models import analyze_spatial_diagnostics
    df, geo, w, xs, effect = _cross_section(data, y, x, year, fixed_effects, gdf, w, ref, what="spatial_diagnostics")
    return _inputs.finish(analyze_spatial_diagnostics(df, y, xs, gdf=geo, w=w, period=_inputs.one_year(df),
                                                      fixed_effects=effect, alpha=alpha), df)


__all__ = ["panel_model", "regression", "spatial_diagnostics", "spatial_model"]
