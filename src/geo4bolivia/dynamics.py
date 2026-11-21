"""Distribution dynamics: how units move within the distribution, in the ranking and between spatial clusters.

``transitions`` and ``spatial_transitions`` follow every year of a panel (Markov chains);
``lisa_transitions`` and ``rank_mobility`` compare two years.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from . import _inputs
from ._engine.pedagogy import Interpretable

if TYPE_CHECKING:
    import plotly.graph_objects as go
    from great_tables import GT

ENTITY, TIME, NAME = _inputs.ENTITY, _inputs.TIME, _inputs.NAME

#: The local Moran types, in the order of the transition matrix (the four quadrants of
#: the Moran scatterplot, then the units without a significant local statistic).
LISA_TYPES = ("High-High", "Low-High", "Low-Low", "High-Low", "Not significant")

_NEUTRAL = "#8c8c8c"
_OUTLINE = "#1a1a1a"
_REFLINE = {"dash": "dash", "color": "rgba(0,0,0,0.35)", "width": 1}


# --- inputs -----------------------------------------------------------------------------------

def _with_data(df: pd.DataFrame, variable: str, func: str) -> tuple[pd.DataFrame, list[int]]:
    """The rows of a panel with a value of ``variable``, and their years (at least two)."""
    if TIME not in df.columns:
        raise ValueError(f"{func}() follows units over time: the table needs a {TIME!r} column; "
                         f"it has {list(df.columns)}")
    rows = df[np.isfinite(df[variable].astype(float))].reset_index(drop=True)
    rows.attrs = dict(df.attrs)
    have = _inputs.years(rows)
    if len(have) < 2:
        raise ValueError(f"{func}() needs at least two years of {variable!r}; the data have {have}")
    return rows, have


def _two_years(have: list[int], first, last) -> tuple[int, int]:
    """The two years to compare: those asked for (checked), else the first and last with data."""
    first = have[0] if first is None else int(first)
    last = have[-1] if last is None else int(last)
    for year in (first, last):
        if year not in have:
            raise ValueError(f"No rows for {year}; the years with data are {have}")
    if first >= last:
        raise ValueError(f"first must be earlier than last; got first={first} and last={last}")
    return first, last


def _in_every_year(rows: pd.DataFrame, have: list[int], notes: list[str], func: str) -> pd.DataFrame:
    """Keep the units observed in every year of ``have`` (a balanced panel), noting how many were left out."""
    when = f"all {len(have)} years" if len(have) > 2 else " and ".join(str(year) for year in have)
    counts = rows.groupby(ENTITY)[TIME].nunique()
    complete = set(counts.index[counts == len(have)])
    if not complete:
        raise ValueError(f"{func}() needs units with data in every year; no unit has data in {when}")
    if len(complete) < len(counts):
        notes.append(f"{func}: kept the {len(complete)} units with data in {when} "
                     f"({len(counts) - len(complete)} left out)")
    out = rows[rows[ENTITY].isin(complete)].reset_index(drop=True)
    out.attrs = dict(rows.attrs)
    return out


def _positive_means(df: pd.DataFrame, variable: str, func: str) -> None:
    """``relative=True`` divides by each year's mean: it keeps the order of the units only when positive."""
    means = df.groupby(TIME)[variable].mean()
    bad = means[means <= 0]
    if len(bad):
        raise ValueError(f"{func}(): relative=True divides the values by each year's mean, which must be positive; "
                         f"the mean of {variable!r} is {bad.iloc[0]:.4g} in {bad.index[0]}. Use relative=False")


def _finish(result, df: pd.DataFrame, notes: list[str]):
    """An engine result with the package's column names, unit names, integer years and our notes."""
    out = _inputs.finish(result, df)
    changes: dict[str, Any] = {}
    if TIME in out.df.columns and out.df[TIME].dtype != df[TIME].dtype:
        changes["df"] = out.df.assign(**{TIME: out.df[TIME].astype(df[TIME].dtype)})
    if notes:
        changes["notes"] = (*notes, *out.notes)
    return replace(out, **changes) if changes else out


def _clockwise(geometry):
    """A polygon (or its parts) with the exterior ring clockwise, as Plotly's vector maps expect."""
    from shapely.geometry import MultiPolygon
    from shapely.geometry.polygon import orient
    if geometry.geom_type == "Polygon":
        return orient(geometry, sign=-1.0)
    if geometry.geom_type == "MultiPolygon":
        return MultiPolygon([orient(part, sign=-1.0) for part in geometry.geoms])
    return geometry


def _outlines(geometries) -> tuple[list, list]:
    """The exterior rings of polygons as one line: longitudes and latitudes, separated by ``None``."""
    lon, lat = [], []
    for geometry in geometries:
        for part in getattr(geometry, "geoms", [geometry]):
            if part.geom_type == "Polygon":
                x, y = part.exterior.coords.xy
                lon.extend([*x, None])
                lat.extend([*y, None])
    return lon, lat


def _share_heatmap(shares: pd.DataFrame, text, *, hover: str, x_title: str, y_title: str, title: str,
                   subtitle: str) -> go.Figure:
    """A transition matrix as a heatmap: rows = the first year, coloured by the share of the row."""
    import plotly.graph_objects as go

    from ._engine._theme import active_sequential_scale, apply_default_layout
    fig = go.Figure(go.Heatmap(
        z=shares.fillna(0.0).to_numpy(), x=[str(c) for c in shares.columns], y=[str(i) for i in shares.index],
        text=text, texttemplate="%{text}", customdata=shares.fillna(0.0).to_numpy(), xgap=1, ygap=1,
        colorscale=active_sequential_scale(), zmin=0.0, zmax=1.0, colorbar={"title": "Share of the row"},
        hovertemplate=hover))
    fig.update_yaxes(autorange="reversed")
    return apply_default_layout(fig, title=title, subtitle=subtitle, xaxis={"title": x_title, "type": "category"},
                                yaxis={"title": y_title, "type": "category"})


# --- Markov chains ----------------------------------------------------------------------------

def transitions(data, variable: str, *, k: int = 5, scheme: str = "quantiles", bins=None, per_year: bool = True,
                relative: bool = False, title: str | None = None, ref: str | None = None):
    """Markov transitions between classes of a variable's distribution: how mobile are the units?

    Every unit is assigned to one of ``k`` classes in each year, and all the moves from
    one year to the next are counted in a transition matrix: the probability of being
    in each class next year, given this year's class. Needs the ``[dynamics]`` extra.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to follow, observed in at least two years; the units
        without a value in every year are left out
    k
        Number of classes
    scheme
        How classes are formed: ``"quantiles"`` (equal numbers of units),
        ``"equal_interval"`` or ``"fisher_jenks"``
    bins
        Upper bounds of fixed classes, the same in every year (replaces ``k``,
        ``scheme`` and ``per_year``)
    per_year
        Classify each year on its own, so a class is a position within that
        year's distribution (default); ``False`` classifies all years together, so
        classes are fixed levels
    relative
        Divide the values by each year's mean first
    title
        The figure title

    Returns
    -------
    result object
        A result with ``.p`` (the transition probabilities, rows = this year's class) and
        ``.counts``, ``.fig`` (the matrix as a heatmap), ``.gt`` (mobility indices,
        long-run shares and expected stays), ``.df`` (one row per unit and year with its
        ``state``), ``.states``, ``.steady_state`` (the long-run distribution),
        ``.sojourn`` (expected years in each class), the mobility indices ``.shorrocks``,
        ``.prais`` and ``.bartholomew``, ``.n_transitions`` and ``.interpret()``.
    """
    from ._engine.distribution_dynamics import analyze_markov_transitions
    func, notes = "transitions", []
    rows, have = _with_data(_inputs.panel(data, variable, ref=ref), variable, func)
    df = _in_every_year(rows, have, notes, func)
    if relative:
        _positive_means(df, variable, func)
    return _finish(analyze_markov_transitions(df, variable, k=k, scheme=scheme, bins=bins, per_period=per_year,
                                              relative=relative, title=title), df, notes)


def spatial_transitions(data, variable: str, *, w=None, k: int = 5, m: int | None = None, per_year: bool = False,
                        relative: bool = True, title: str | None = None,
                        map: str | None = None, gdf=None, ref: str | None = None):
    """Spatial Markov transitions: does a unit's mobility depend on where its neighbours stand?

    Rey's spatial Markov chain splits the transition matrix of ``transitions`` by the
    class of each unit's neighbours (their weighted mean), and tests whether the
    matrices differ. Needs the ``[dynamics]`` extra.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to follow, observed in at least two years; the units
        without a value in every year are left out
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    k
        Number of quantile classes of the variable
    m
        Number of quantile classes of the neighbours' mean (default: ``k``)
    per_year
        Classify each year on its own; by default all years are classified
        together, so classes are fixed levels
    relative
        Divide the values by each year's mean first (default), so that classes
        are levels relative to the average unit; needs positive means
    title
        The figure title
    map
        The map (scale) the units are drawn on and their neighbours found, e.g. one of
        the project's municipal maps (default: the data's own map; needed only for a table
        whose units are on several maps and that does not record which, see ``geo.scales()``)
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.p_global`` (the transition probabilities of all units),
        ``.p_conditional`` (one matrix per class of the neighbours, from the lowest to the
        highest), ``.steady_states`` (the long-run distribution in each neighbourhood),
        ``.fig`` (the conditional matrices side by side), ``.gt`` (the tests of equal
        dynamics across neighbourhoods), ``.lr_stat``, ``.lr_p``, ``.q_stat``, ``.q_p``,
        ``.dof``, ``.df`` (one row per unit and year with its ``state`` and
        ``neighbor_state``) and ``.interpret()``.
    """
    from ._engine.distribution_dynamics import analyze_spatial_markov
    func, notes = "spatial_transitions", []
    rows, _ = _with_data(_inputs.panel(data, variable, gdf=gdf, scale=map, ref=ref), variable, func)
    df, geo, w = _inputs.spatial(rows, variable, year="all", gdf=gdf, scale=map, w=w, ref=ref)
    left_out = rows[ENTITY].nunique() - len(geo)
    if left_out:
        notes.append(f"{func}: kept the {len(geo)} units with data in every year and boundaries ({left_out} left out)")
    if relative:
        _positive_means(df, variable, func)
    return _finish(analyze_spatial_markov(df, variable, gdf=geo, w=w, k=k, m=m, fixed=not per_year,
                                          relative=relative, title=title), df, notes)


# --- LISA transitions -------------------------------------------------------------------------

@dataclass(frozen=True, repr=False)
class LisaTransitionsResult(Interpretable):
    """Result of ``lisa_transitions``: the local Moran type of each unit in two years.

    ``df`` has one row per unit (``geo_id``, ``name``, ``cluster_<first>``,
    ``cluster_<last>``, ``moved``, ``transition``); ``matrix`` counts the units by type
    in the first year (rows) and the last year (columns), ``shares`` divides each row
    by its total. ``fig`` is the matrix as a heatmap and ``fig_map`` the map of the
    types in the last year with the units that changed type outlined.
    """

    df: pd.DataFrame
    matrix: pd.DataFrame
    shares: pd.DataFrame
    fig: go.Figure
    fig_map: go.Figure
    n_units: int
    n_stayed: int
    n_moved: int
    share_stayed: float
    moran_i_first: float
    moran_i_last: float
    p_sim_first: float
    p_sim_last: float
    alpha: float
    permutations: int
    var: str
    first: Any
    last: Any
    w_spec: str
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """A plain-language reading of how the local clusters changed between the two years."""
        return self._read(_interpret_lisa_transitions(self))

    def tidy(self) -> pd.DataFrame:
        """The transition matrix as a long table: one row per pair of types."""
        long = self.matrix.reset_index().melt(id_vars=self.matrix.index.name, var_name=self.matrix.columns.name,
                                              value_name="units")
        long["share"] = self.shares.to_numpy().ravel(order="F")
        return long


def lisa_transitions(data, variable: str, first=None, last=None, *, w=None, permutations: int = 999,
                     seed: int | None = 12345, alpha: float = 0.05, tiles: str | None = "carto-positron",
                     title: str | None = None,
                     map: str | None = None, gdf=None, ref: str | None = None):
    """Transitions between local Moran (LISA) types: did the hot spots and cold spots persist?

    Runs ``lisa`` in two years on the same units and the same weights, and counts how
    the units moved between the types High-High, Low-High, Low-Low, High-Low and
    Not significant.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to analyse
    first, last
        The two years to compare (default: the first and last with data);
        only the units with a value in both are used
    w
        Spatial weights from ``weights`` (default: queen contiguity among the units with data)
    permutations
        Random permutations behind each unit's pseudo p-value
    seed
        Makes the permutations reproducible
    alpha
        Significance level below which a unit is assigned to a cluster
    tiles
        The basemap style of the map (``None``: no basemap)
    title
        The title of the matrix figure
    map
        The map (scale) the units are drawn on and their neighbours found, e.g. one of
        the project's municipal maps (default: the data's own map; needed only for a table
        whose units are on several maps and that does not record which, see ``geo.scales()``)
    gdf
        Boundaries to use instead of the project's (a GeoDataFrame with ``geo_id``)

    Returns
    -------
    result object
        A result with ``.df`` (one row per unit: ``cluster_<first>``, ``cluster_<last>``,
        ``moved`` and the ``transition`` in words), ``.matrix`` (units by type in the first
        year, rows, and in the last year, columns; always the five types, in the same
        order), ``.shares`` (each row as shares of its total; empty rows are missing),
        ``.fig`` (the matrix as a heatmap: counts in the cells, coloured by the share of
        the row), ``.fig_map`` (the types in the last year, with the units that changed
        type outlined), ``.n_units``, ``.n_stayed``, ``.n_moved``, ``.share_stayed``, the
        global Moran's I of each year (``.moran_i_first``, ``.moran_i_last``, with
        ``.p_sim_first`` and ``.p_sim_last``) and ``.interpret()``.
    """
    import plotly.graph_objects as go

    from ._engine import dependence
    from ._engine._basemap import credit
    from ._engine._labels import resolve_label
    from ._engine._mapping import _wgs84_simplified, categorical_map
    from ._engine._theme import LISA_COLORS, apply_default_layout

    func, notes = "lisa_transitions", []
    rows, have = _with_data(_inputs.panel(data, variable, gdf=gdf, scale=map, ref=ref), variable, func)
    first, last = _two_years(have, first, last)
    rows = rows[rows[TIME].isin([first, last])]
    df, geo, w = _inputs.spatial(rows, variable, year="all", gdf=gdf, scale=map, w=w, ref=ref)
    left_out = rows[ENTITY].nunique() - len(geo)
    if left_out:
        notes.append(f"{func}: kept the {len(geo)} units with data in {first} and {last} and boundaries "
                     f"({left_out} left out)")
    runs = {year: dependence.explore_lisa_cluster_map(df, variable, gdf=geo, w=w, period=year,
                                                      permutations=permutations, seed=seed, alpha=alpha, tiles=None)
            for year in (first, last)}
    notes.extend(n for n in dict.fromkeys(n for run in runs.values() for n in run.notes))

    col_first, col_last = f"cluster_{first}", f"cluster_{last}"
    names = df.drop_duplicates(ENTITY).set_index(ENTITY)[NAME]
    ids = runs[first].df["entity"]
    table = pd.DataFrame({
        ENTITY: ids.to_numpy(),
        NAME: ids.map(names).to_numpy(),
        col_first: runs[first].df["cluster"].to_numpy(),
        col_last: runs[last].df.set_index("entity")["cluster"].reindex(ids).to_numpy(),
    })
    table["moved"] = table[col_first] != table[col_last]
    table["transition"] = table[col_first] + " → " + table[col_last]

    matrix = (pd.crosstab(table[col_first], table[col_last])
              .reindex(index=list(LISA_TYPES), columns=list(LISA_TYPES), fill_value=0).astype(int))
    totals = matrix.sum(axis=1)
    shares = matrix.div(totals.where(totals > 0), axis=0)
    n_units, n_moved = len(table), int(table["moved"].sum())
    w_spec = runs[last].w_spec

    label = resolve_label(df, variable)
    subtitle = f"{n_units:,} units; {w_spec}; p < {float(alpha):g} on {int(permutations)} permutations"
    fig = _share_heatmap(
        shares, matrix.to_numpy(), x_title=f"Type in {last}", y_title=f"Type in {first}",
        hover=(f"{first}: %{{y}}<br>{last}: %{{x}}<br>%{{text}} units (%{{customdata:.0%}} of the row)"
               "<extra></extra>"),
        title=title if title is not None else f"LISA transitions: {label}, {first} to {last}", subtitle=subtitle)

    # The types in the last year, drawn by the engine; then the outlines of the units that changed type
    drawn = _wgs84_simplified(geo, ENTITY, "auto").set_index(ENTITY).loc[table[ENTITY]].reset_index()
    if tiles is None:       # the vector backend fills the outside of a polygon whose exterior runs anticlockwise
        drawn[drawn.geometry.name] = drawn.geometry.apply(_clockwise)
    fig_map = categorical_map(drawn, table[col_last], entity=ENTITY, colors=LISA_COLORS,
                              category_order=list(LISA_TYPES), tiles=tiles, simplify=None)
    both_years = table.set_index(table[ENTITY].astype(str))[[NAME, col_first, col_last]].astype(str)
    for trace in fig_map.data:
        trace.customdata = both_years.loc[[str(i) for i in trace.locations]].to_numpy()
        trace.hovertemplate = (f"<b>%{{customdata[0]}}</b><br>{first}: %{{customdata[1]}}<br>"
                               f"{last}: %{{customdata[2]}}<extra></extra>")
    lon, lat = _outlines(drawn.geometry[table["moved"].to_numpy()])
    line = go.Scattermap if tiles is not None else go.Scattergeo
    fig_map.add_trace(line(lon=lon, lat=lat, mode="lines", line={"color": _OUTLINE, "width": 1.5},
                           hoverinfo="skip", name=f"Changed type since {first}"))
    apply_default_layout(fig_map, title=f"LISA clusters in {last} and changes since {first}: {label}",
                         subtitle=f"{n_moved:,} of {n_units:,} units changed type; {w_spec}",
                         legend_title_text=f"Type in {last}")

    table.attrs["geo_labels"] = dict(df.attrs.get("geo_labels") or {})   # the reading names the variable by its label
    credit(fig_map)
    return LisaTransitionsResult(
        df=table, matrix=matrix, shares=shares, fig=fig, fig_map=fig_map, n_units=n_units,
        n_stayed=n_units - n_moved, n_moved=n_moved, share_stayed=(n_units - n_moved) / n_units,
        moran_i_first=float(runs[first].moran_i), moran_i_last=float(runs[last].moran_i),
        p_sim_first=float(runs[first].p_sim_global), p_sim_last=float(runs[last].p_sim_global),
        alpha=float(alpha), permutations=int(permutations), var=variable, first=first, last=last, w_spec=w_spec,
        notes=tuple(notes))


def _interpret_lisa_transitions(result) -> str:
    """Markdown reading of a ``LisaTransitionsResult``."""
    from ._engine.pedagogy._format import fmt_num
    from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE

    first, last, n = result.first, result.last, int(result.n_units)
    counts = result.matrix.to_numpy()
    types = list(result.matrix.index)
    ns = types.index("Not significant")
    change = result.moran_i_last - result.moran_i_first
    trend = ("changed little" if abs(change) < 0.05 else "strengthened" if change > 0 else "weakened")
    lines = [
        f"Local Moran statistics (LISA) of **{result.var}** were computed in {first} and in {last} for the same "
        f"{n:,} units, under {result.w_spec}, and each unit was assigned to a type at the {result.alpha:g} level. "
        f"Global Moran's I is {fmt_num(result.moran_i_first)} in {first} (pseudo p = "
        f"{fmt_num(result.p_sim_first)}) and {fmt_num(result.moran_i_last)} in {last} (pseudo p = "
        f"{fmt_num(result.p_sim_last)}): the overall clustering of similar values {trend}.",
        f"**{result.n_stayed:,} of {n:,} units ({result.share_stayed:.0%}) are of the same type in both years** "
        f"and {result.n_moved:,} changed type.",
    ]

    significant_first = int(counts.sum()) - int(counts[ns].sum())
    if significant_first:
        kept = int(np.trace(counts)) - int(counts[ns, ns])
        faded = int(counts[:, ns].sum()) - int(counts[ns, ns])
        lines[-1] += (f" Of the {significant_first:,} units in a significant cluster or outlier in {first}, "
                      f"{kept:,} kept their type, {faded:,} are no longer significant in {last} and "
                      f"{significant_first - kept - faded:,} switched to another type.")
    entered = int(counts[ns].sum()) - int(counts[ns, ns])
    lines[-1] += (f" {entered:,} units that were not significant in {first} belong to a cluster or are an outlier "
                  f"in {last}.")

    parts = []
    for kind, word in (("High-High", "hot spots (high values surrounded by high values)"),
                       ("Low-Low", "cold spots (low values surrounded by low values)")):
        i = types.index(kind)
        was, now = int(counts[i].sum()), int(counts[:, i].sum())
        if was:
            parts.append(f"Of the {was:,} **{kind}** {word} of {first}, {int(counts[i, i]):,} are still "
                         f"{kind} in {last}, a year with {now:,} of them.")
        else:
            parts.append(f"There were no **{kind}** {word} in {first}; there are {now:,} in {last}.")
    off = counts.copy()
    np.fill_diagonal(off, 0)
    if off.sum():
        i, j = np.unravel_index(int(off.argmax()), off.shape)
        parts.append(f"The most common change is from {types[i]} to {types[j]} ({int(off[i, j]):,} units).")
    lines.append(" ".join(parts))

    lines.append(
        "Read the changes with care. A unit's type depends on whether its pseudo p-value is below the threshold, "
        "computed unit by unit without a multiple-testing adjustment, so moves to and from Not significant can "
        "come from borderline p-values. High and low are relative to the mean of each year, and a unit can change "
        "type because its neighbours' values changed while its own did not.")
    return "\n\n".join([*lines, _ASSOC_NOTE])


# --- rank mobility ----------------------------------------------------------------------------

@dataclass(frozen=True, repr=False)
class RankMobilityResult(Interpretable):
    """Result of ``rank_mobility``: the position of each unit in two years.

    ``df`` has one row per unit (``geo_id``, ``name``, ``<variable>_<first>``,
    ``<variable>_<last>``, ``rank_<first>``, ``rank_<last>``, ``rank_change``,
    ``group_<first>``, ``group_<last>``), ordered by the rank in the last year.
    ``matrix`` holds the shares of each quantile group of the first year (rows) found
    in each group of the last year (columns) and ``counts`` the units behind them.
    """

    df: pd.DataFrame
    matrix: pd.DataFrame
    counts: pd.DataFrame
    climbers: pd.DataFrame
    fallers: pd.DataFrame
    fig: go.Figure
    fig_matrix: go.Figure
    gt: GT
    spearman: float
    kendall: float
    mean_abs_change: float
    median_abs_change: float
    share_same_group: float
    n_units: int
    n_climbed: int
    n_fell: int
    k: int
    top: int
    ascending: bool
    var: str
    first: Any
    last: Any
    notes: tuple[str, ...] = ()

    def interpret(self, *, lang: str = "en") -> str:
        """A plain-language reading of how much the ranking changed between the two years."""
        return self._read(_interpret_rank_mobility(self))

    def tidy(self) -> pd.DataFrame:
        """The table with one row per unit."""
        return self.df

    def glance(self) -> pd.DataFrame:
        """The summary numbers as a one-row table."""
        return pd.DataFrame([{name: getattr(self, name) for name in (
            "var", "first", "last", "n_units", "spearman", "kendall", "mean_abs_change", "median_abs_change",
            "share_same_group", "n_climbed", "n_fell")}]).rename(columns={"var": "variable"})


def _quantile_groups(values: pd.Series, k: int) -> np.ndarray:
    """The quantile group of each value, 0 (lowest values) to ``k`` - 1, as ``transitions`` forms its classes."""
    import warnings

    import mapclassify
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)        # fewer distinct values than classes: noted by the caller
        return np.asarray(mapclassify.Quantiles(values.to_numpy(dtype=float), k=k).yb, dtype=int)


def rank_mobility(data, variable: str, first=None, last=None, *, k: int = 5, top: int = 10, ascending: bool = False,
                  title: str | None = None, ref: str | None = None):
    """Rank mobility between two years: how much did the units change position?

    Ranks the units in each year, compares the two rankings (rank correlations, the
    change of position of every unit) and follows the units between the quantile
    groups of the two years.

    Parameters
    ----------
    data
        A dataset id, or a panel with ``geo_id`` and ``year``, e.g. from ``load``
    variable
        The numeric column to rank
    first, last
        The two years to compare (default: the first and last with data);
        only the units with a value in both are ranked
    k
        Number of quantile groups of the transition matrix (``Q1``: the lowest values)
    top
        Number of units in ``.climbers`` and ``.fallers``
    ascending
        ``False`` (default): rank 1 is the highest value; ``True``: the lowest,
        for variables where less is better
    title
        The title of the rank figure

    Returns
    -------
    result object
        A result with ``.df`` (one row per unit, ordered by the last rank:
        ``<variable>_<first>``, ``<variable>_<last>``, ``rank_<first>``, ``rank_<last>``,
        ``rank_change``, positive when the unit climbed, and its quantile ``group_`` in
        each year), ``.fig`` (the rank in the first year against the rank in the last,
        with the line of no change), ``.matrix`` (the shares of each group of the first
        year, rows, found in each group of the last year, columns; rows sum to one),
        ``.counts`` and ``.fig_matrix`` (its heatmap), ``.climbers`` and ``.fallers`` (the
        ``top`` units by rank change), ``.gt`` (both as one table), ``.spearman`` and
        ``.kendall`` (rank correlations of the two years), ``.mean_abs_change`` and
        ``.median_abs_change`` (positions moved by a unit), ``.share_same_group``,
        ``.n_units``, ``.n_climbed``, ``.n_fell`` and ``.interpret()``.
    """
    import plotly.graph_objects as go
    from great_tables import GT
    from scipy import stats

    from ._engine._labels import resolve_label
    from ._engine._theme import apply_default_layout, color_for

    func, notes = "rank_mobility", []
    panel = _inputs.panel(data, variable, ref=ref)
    rows, have = _with_data(panel, variable, func)
    first, last = _two_years(have, first, last)
    k, top = int(k), int(top)
    if k < 2:
        raise ValueError(f"{func}(): k={k} needs to be at least 2")
    if top < 1:
        raise ValueError(f"{func}(): top={top} needs to be at least 1")
    rows = _in_every_year(rows[rows[TIME].isin([first, last])].drop_duplicates([ENTITY, TIME]), [first, last],
                          notes, func)
    a = rows[rows[TIME] == first].set_index(ENTITY)
    b = rows[rows[TIME] == last].set_index(ENTITY).reindex(a.index)
    n = len(a)
    if n < k:
        raise ValueError(f"{func}() needs at least as many units as groups; there are {n} units with data in "
                         f"{first} and {last}, and k={k}")
    for year, values in ((first, a[variable]), (last, b[variable])):
        if values.nunique() < 2:
            raise ValueError(f"{func}(): {variable!r} is the same in every unit in {year}, so they cannot be ranked")

    v0, v1, r0, r1 = f"{variable}_{first}", f"{variable}_{last}", f"rank_{first}", f"rank_{last}"
    g0, g1 = f"group_{first}", f"group_{last}"
    groups = [f"Q{i + 1}" for i in range(k)]
    table = pd.DataFrame({ENTITY: a.index.to_numpy(), NAME: a[NAME].to_numpy(),
                          v0: a[variable].to_numpy(), v1: b[variable].to_numpy()})
    table[r0] = table[v0].rank(ascending=ascending, method="min").astype(int)
    table[r1] = table[v1].rank(ascending=ascending, method="min").astype(int)
    table["rank_change"] = table[r0] - table[r1]
    for column, values in ((g0, table[v0]), (g1, table[v1])):
        codes = _quantile_groups(values, k)
        if len(np.unique(codes)) < k:
            notes.append(f"{func}: {column.split('_')[-1]} has too many equal values to fill {k} quantile groups")
        table[column] = [groups[c] for c in codes]
    table = table.sort_values([r1, r0, ENTITY]).reset_index(drop=True)

    counts = pd.crosstab(table[g0], table[g1]).reindex(index=groups, columns=groups, fill_value=0).astype(int)
    totals = counts.sum(axis=1)
    matrix = counts.div(totals.where(totals > 0), axis=0)
    moves = table["rank_change"]
    climbers = table[moves > 0].sort_values(["rank_change", r1], ascending=[False, True]).head(top)
    fallers = table[moves < 0].sort_values(["rank_change", r1], ascending=[True, False]).head(top)
    climbers, fallers = climbers.reset_index(drop=True), fallers.reset_index(drop=True)
    n_climbed, n_fell = int((moves > 0).sum()), int((moves < 0).sum())
    spearman = float(stats.spearmanr(table[v0], table[v1]).statistic)
    kendall = float(stats.kendalltau(table[v0], table[v1]).statistic)

    label = resolve_label(panel, variable)
    best = "lowest" if ascending else "highest"
    subtitle = f"{n:,} units; rank 1 = the {best} value; Spearman correlation {spearman:.2f}"
    fig = go.Figure(go.Scatter(x=[1, n], y=[1, n], mode="lines", line=dict(_REFLINE), name="No change",
                               hoverinfo="skip"))
    for name, mask, color in ((f"Climbed ({n_climbed:,})", moves > 0, color_for(0)),
                              (f"Fell ({n_fell:,})", moves < 0, color_for(3)),
                              (f"Same rank ({n - n_climbed - n_fell:,})", moves == 0, _NEUTRAL)):
        part = table[mask]
        fig.add_trace(go.Scatter(
            x=part[r0], y=part[r1], mode="markers", name=name,
            marker={"color": color, "size": 8, "opacity": 0.8, "line": {"color": "white", "width": 0.5}},
            customdata=part[[NAME, "rank_change", v0, v1]].to_numpy(),
            hovertemplate=(f"<b>%{{customdata[0]}}</b><br>Rank in {first}: %{{x}} (%{{customdata[2]:.4g}})<br>"
                           f"Rank in {last}: %{{y}} (%{{customdata[3]:.4g}})<br>"
                           "Change: %{customdata[1]:+d}<extra></extra>")))
    apply_default_layout(fig, title=title if title is not None else f"Rank mobility: {label}, {first} to {last}",
                         subtitle=subtitle,
                         xaxis={"title": f"Rank in {first}", "autorange": "reversed"},
                         yaxis={"title": f"Rank in {last} (above the line: climbed)", "autorange": "reversed"})

    fig_matrix = _share_heatmap(
        matrix, matrix.fillna(0.0).map("{:.2f}".format).to_numpy(),
        x_title=f"Quantile group in {last}", y_title=f"Quantile group in {first}",
        hover=f"{first}: %{{y}}<br>{last}: %{{x}}<br>%{{customdata:.1%}} of the row<extra></extra>",
        title=f"Moves between quantile groups: {label}, {first} to {last}",
        subtitle=f"{n:,} units in {k} groups per year (Q1: the lowest values)")

    listed = pd.concat([climbers.assign(_part="Climbed the most"), fallers.assign(_part="Fell the most")])
    gt = (GT(listed[["_part", NAME, r0, r1, "rank_change", v0, v1]], groupname_col="_part")
          .tab_header(title=f"Rank mobility: {label}", subtitle=f"{first} to {last}; {subtitle}")
          .cols_label(**{NAME: "Unit", r0: f"Rank {first}", r1: f"Rank {last}", "rank_change": "Change",
                         v0: f"Value {first}", v1: f"Value {last}"})
          .fmt_number(columns=[v0, v1], n_sigfig=4)
          .fmt_integer(columns="rank_change", force_sign=True))

    table.attrs["geo_labels"] = dict(panel.attrs.get("geo_labels") or {})   # the reading names the variable by its label
    return RankMobilityResult(
        df=table, matrix=matrix, counts=counts, climbers=climbers, fallers=fallers, fig=fig, fig_matrix=fig_matrix,
        gt=gt, spearman=spearman, kendall=kendall, mean_abs_change=float(moves.abs().mean()),
        median_abs_change=float(moves.abs().median()), share_same_group=float(np.trace(counts.to_numpy()) / n),
        n_units=n, n_climbed=n_climbed, n_fell=n_fell, k=k, top=top, ascending=bool(ascending), var=variable,
        first=first, last=last, notes=tuple(notes))


def _interpret_rank_mobility(result) -> str:
    """Markdown reading of a ``RankMobilityResult``."""
    from ._engine.pedagogy._format import fmt_num
    from ._engine.pedagogy._interpret._shared import _ASSOC_NOTE

    first, last, n, k = result.first, result.last, int(result.n_units), int(result.k)
    rho, tau = float(result.spearman), float(result.kendall)
    if rho >= 0.9:
        reading = "the ordering of the units is **very stable**"
    elif rho >= 0.7:
        reading = "the ordering is **broadly preserved**, with visible reshuffling"
    elif rho >= 0.4:
        reading = "the two orderings are **moderately related**: many units changed position substantially"
    elif rho > -0.4:
        reading = "the two orderings are **weakly related**: the ranking was largely reshuffled"
    else:
        reading = "the ordering was largely **reversed**"
    lines = [
        f"The {n:,} units with data in {first} and {last} were ranked by **{result.var}** in each year (rank 1 = "
        f"the {'lowest' if result.ascending else 'highest'} value). The Spearman correlation of the two rankings "
        f"is {fmt_num(rho)} and Kendall's tau is {fmt_num(tau)}: {reading}. Of all pairs of units, about "
        f"{(1 + tau) / 2:.0%} are in the same order in both years.",
        f"A unit moved {fmt_num(result.mean_abs_change)} positions on average (median "
        f"{fmt_num(result.median_abs_change)}), {result.mean_abs_change / n:.0%} of the length of the ranking; "
        f"two unrelated rankings would differ by about {fmt_num(n / 3)} positions. {result.n_climbed:,} units "
        f"climbed, {result.n_fell:,} fell and {n - result.n_climbed - result.n_fell:,} kept their rank.",
    ]

    stay = pd.Series(np.diag(result.matrix.to_numpy(dtype=float)), index=result.matrix.index).dropna()
    groups = (f"**{result.share_same_group:.0%} of the units are in the same quantile group in both years**, out "
              f"of {k} groups (about {1 / k:.0%} would be if the two years were unrelated).")
    if len(stay):
        groups += (f" The group that kept most of its units is {stay.idxmax()} ({stay.max():.0%} stayed) and the "
                   f"one that kept fewest is {stay.idxmin()} ({stay.min():.0%}); Q1 holds the lowest values and "
                   f"Q{k} the highest.")
    lines.append(groups)

    extremes = []
    for frame, verb in ((result.climbers, "climb"), (result.fallers, "fall")):
        if len(frame):
            unit = frame.iloc[0]
            extremes.append(f"the largest {verb} is **{unit[NAME]}**, from rank {int(unit[f'rank_{first}']):,} to "
                            f"{int(unit[f'rank_{last}']):,}")
    if extremes:
        sentence = "; ".join(extremes) + "."
        lines.append(sentence[0].upper() + sentence[1:])
    lines.append(
        "Ranks are relative: a unit can fall while its value rises, when the others rose more. Where values are "
        "close together, often in the middle of the distribution, small differences move a unit many positions.")
    return "\n\n".join([*lines, _ASSOC_NOTE])


__all__ = ["LisaTransitionsResult", "RankMobilityResult", "lisa_transitions", "rank_mobility",
           "spatial_transitions", "transitions"]
