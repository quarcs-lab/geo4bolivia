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
from .create import check, combine, link, save, zonal
from .discover import cite, describe, info, labels, reference_years, search
from .io import add_names, boundaries, crosswalk, datasets, dictionary, load, units
from .panel import change
from .plot import map
from .project import PACKAGE, config
from .scales import ancestors, scale_of
from .scales import table as scales

__all__ = ["add_names", "aggregate", "ancestors", "boundaries", "change", "check", "cite", "combine", "config",
           "crosswalk", "datasets", "describe", "dictionary", "for_expdpy", "for_geometrics", "info", "labels",
           "link", "load", "map", "overlay", "overlay_weights", "reference_years", "save", "scale_of", "scales",
           "search", "units", "zonal"]
__version__ = "0.5.0"
