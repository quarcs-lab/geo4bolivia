"""Find, load, understand, aggregate and build geo-referenced development data across spatial scales.

>>> import geo4bolivia as geo
>>> geo.datasets()                                   # the catalog: datasets, scales, years, units
>>> geo.search("poverty")                            # variables matching words, in every dataset
>>> geo.info("sdg01")                                # coverage, sources, licenses, citation, notes
>>> df = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])   # panel with names
>>> geo.describe(df)                                 # summary statistics per year, with labels
>>> geo.change(df, "sdg1_2_mpi")                     # first-to-last change and rank change per unit
>>> geo.aggregate(df, to=["department", "country"], dataset="sdg01")   # up the hierarchy
>>> geo.map(df, "sdg1_2_mpi", year=2024)             # interactive map (needs plotly)
>>> mine = geo.link(my_table, scale="municipality", on="mun_id", key="mun_id")  # your data -> geo_id
>>> geo.combine(["ntl", "pop"], scale="municipality", extra=[mine])  # one panel, one scale
>>> gdf, df, df_dict = geo.for_geometrics("sdg", variables="index_sdg")   # for geometrics
>>> df, df_def = geo.for_expdpy("sdg", groups=["department"])            # for expdpy

The website documents every function: https://quarcs-lab.github.io/geo4bolivia/tools/geo4bolivia-reference/
"""

from .aggregate import aggregate, overlay, overlay_weights
from .bridge import for_expdpy, for_geometrics
from .convergence import beta_convergence, convergence_clubs, sigma_convergence
from .create import check, combine, link, save, zonal
from .discover import cite, describe, info, labels, reference_years, search
from .dynamics import lisa_transitions, rank_mobility, spatial_transitions, transitions
from .explore import correlation, distribution, extremes, scatter, trend
from .inequality import inequality, theil_decomposition
from .io import add_names, boundaries, crosswalk, datasets, dictionary, load, units
from .local import mgwr
from .models import panel_model, regression, spatial_diagnostics, spatial_model
from .panel import change
from .plot import map
from .project import PACKAGE as PACKAGE
from .project import config
from .scales import ancestors, scale_of
from .scales import table as scales
from .spatial import connectivity, lisa, moran, weights

__all__ = [
    # find and understand the data
    "datasets", "search", "info", "dictionary", "reference_years", "cite", "labels", "describe",
    # load data, units and boundaries
    "load", "add_names", "units", "boundaries", "crosswalk", "scales", "ancestors", "scale_of", "config",
    # work with panels and scales
    "change", "aggregate", "combine", "overlay", "overlay_weights",
    # build your own indicators
    "link", "check", "zonal", "save",
    # explore
    "correlation", "extremes", "distribution", "scatter", "trend",
    # maps and spatial dependence
    "map", "weights", "connectivity", "moran", "lisa",
    # convergence
    "beta_convergence", "sigma_convergence", "convergence_clubs",
    # transitions and mobility
    "transitions", "spatial_transitions", "lisa_transitions", "rank_mobility",
    # inequality
    "inequality", "theil_decomposition",
    # models
    "regression", "panel_model", "spatial_model", "spatial_diagnostics",
    # spatial heterogeneity
    "mgwr",
    # companion packages
    "for_expdpy", "for_geometrics",
]
__version__ = "0.6.0"
