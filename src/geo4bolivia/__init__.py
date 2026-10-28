"""Load, link, aggregate and create geo-referenced development data across spatial scales.

>>> import geo4bolivia as geo
>>> geo.datasets()                               # what is available, at which scales and years
>>> df = geo.load("gdppc")                       # panel: geo_id, year, variables
>>> gdf = geo.load("env", geometry=True)         # with boundaries
>>> geo.aggregate(geo.load("env"), to="gdl", dataset="env")   # up the hierarchy
>>> mine = geo.link(my_table, scale="province", on="Province")  # your data -> geo_id
>>> geo.combine(["env", "hdi"], scale="gdl", extra=[mine])     # one panel, one scale
>>> gdf, df, df_dict = geo.for_geometrics("gdppc")             # ready for the geometrics package
>>> df, df_def = geo.for_expdpy("env", groups=["gdl"])          # ready for the expdpy package

See docs/data-infrastructure.md in the repository for the full guide.
"""

from .aggregate import aggregate, overlay, overlay_weights
from .bridge import for_expdpy, for_geometrics
from .create import check, combine, link, save, zonal
from .io import boundaries, crosswalk, datasets, dictionary, load, units
from .project import PACKAGE, config
from .scales import ancestors, scale_of
from .scales import table as scales

__all__ = ["aggregate", "ancestors", "boundaries", "check", "combine", "config", "crosswalk", "datasets", "dictionary",
           "for_expdpy", "for_geometrics", "link", "load", "overlay", "overlay_weights", "save", "scale_of", "scales", "units", "zonal"]
__version__ = "0.1.0"
