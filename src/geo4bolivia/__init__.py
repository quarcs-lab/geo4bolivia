"""Find, load, map and analyse geo-referenced development data across spatial scales.

>>> import geo4bolivia as geo
>>> geo.datasets()                                   # the catalog: datasets, scales, years, units
>>> geo.search("poverty")                            # variables matching words, in every dataset
>>> df = geo.load(dataset, variables=variable, groups=[scale])     # a panel: geo_id, year, names
>>> geo.describe(df); geo.change(df, variable)       # summaries; first-to-last change per unit
>>> geo.map(df, variable, year=[first, last], scheme="fisher_jenks")   # maps in common classes
>>> res = geo.moran(df, variable)                    # one call per analysis ...
>>> res.fig; res.df; res.interpret()                 # ... and a result with figure, table and reading

Every analysis function takes a dataset id or a panel with ``geo_id`` (and ``year``),
finds the boundaries, the spatial weights and the labels itself, and returns a result
object. The families: explore (``correlation``, ``extremes``, ``distribution``,
``scatter``, ``trend``), spatial dependence (``weights``, ``connectivity``, ``moran``,
``lisa``), convergence (``beta_convergence``, ``sigma_convergence``,
``convergence_clubs``), transitions (``transitions``, ``spatial_transitions``,
``lisa_transitions``, ``rank_mobility``), inequality (``inequality``,
``theil_decomposition``), models (``regression``, ``panel_model``, ``spatial_model``,
``spatial_diagnostics``) and spatial heterogeneity (``mgwr``).

The documentation site (``config()["documentation"]``) has a guide, articles and an
example for every function.
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
__version__ = "0.7.2"
