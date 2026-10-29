# geo4bolivia

**Subnational development data for Bolivia, ready to analyse, at every spatial scale.**

`geo4bolivia` is the Python package of the [GeoDevelopment Observatory of Bolivia](https://quarcs-lab.github.io/geo4bolivia/). It loads the observatory's indicators (population, night-time lights, the Municipal Atlas of the SDGs by goal, with each goal's index and indicators, satellite embeddings...) as tidy panels, with boundaries for every scale. It also lets you **build your own indicators**: link your tables to the same unit IDs, summarise rasters over units, move data across scales and combine datasets. It works out of the box in Google Colab: every example below runs in a new Colab notebook (replace the placeholder files, such as your own table or raster, with yours).

```python
!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px                         # interactive maps and charts (preinstalled in Colab)

geo.datasets()                                       # what is available, at which scale and years
gdf = geo.load("sdg01", variables="sdg1_2_mpi", years=2012, geometry=True)   # 339 municipalities
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color="sdg1_2_mpi",
                  hover_name="name", center={"lat": -16.3, "lon": -64}, zoom=4)
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## What it does

| Task | Functions |
| --- | --- |
| **Load** panels (one row per unit and year), names and boundaries | `datasets`, `dictionary`, `load`, `units`, `boundaries`, `crosswalk` |
| **Link** your own tables by unit names or codes (INE, DS4Bolivia), whatever the spelling | `link`, `check` |
| **Extract** indicators from rasters (Earth Engine exports, WorldPop, ...) | `zonal` |
| **Move** data up the hierarchy or onto grids and custom zones | `aggregate`, `overlay`, `overlay_weights` |
| **Combine** datasets at one scale and **save** new ones in the same format | `combine`, `save` |
| **Analyse** with [expdpy](https://cmg777.github.io/expdpy/) (panel exploration, fixed and random effects) and [geometrics](https://quarcs-lab.github.io/geometrics/) (convergence, spatial dependence, inequality) | `for_expdpy`, `for_geometrics` |

## One ID for every unit, at every scale

Every unit has a **geo ID** that nests by prefix (numbered as in GADM 4.1): municipality `BO-04-17-04` (La Paz) lies in province `BO-04-17` (Murillo), which lies in department `BO-04` (La Paz), which lies in Bolivia `BO`. INE codes and DS4Bolivia's `asdf_id` are kept as columns of `geo.units()`. The boundaries (`geometry=True`, `geo.boundaries()`) are geoBoundaries' public-domain municipalities from GeoBolivia. Each dataset is a long panel keyed by `geo_id` and `year`.

| Scale | Units | Example |
| --- | --- | --- |
| `country` | 1 | `BO` |
| `department` | 9 | `BO-04` |
| `province` | 112 | `BO-04-17` |
| `municipality` | 339 | `BO-04-17-04` |

## Build your own indicator in five lines

```python
!pip install -q geo4bolivia
import pandas as pd
import geo4bolivia as geo

mine = pd.read_csv("schools_by_municipality.csv")                 # e.g. columns mun_id (INE code), year, schools
mine = geo.link(mine, scale="municipality", on="mun_id", key="mun_id")   # 20101 -> BO-04-17-04
panel = geo.combine(["pop"], scale="municipality", extra=[mine])
panel["schools_per_10k"] = panel["schools"] / panel["pop"] * 1e4
geo.save(panel, "schools", scale="municipality", directory="my_data")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

From a raster:

```python
!pip install -q "geo4bolivia[raster]"             # [raster] adds rasterio
import geo4bolivia as geo

lights = geo.zonal("viirs_2020.tif", scale="municipality", stats=["sum", "mean"], name="ntl", year=2020)
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Then explore and model the panel with expdpy:

```python
!pip install -q geo4bolivia expdpy
import numpy as np
import geo4bolivia as geo
import expdpy as ex

panel = geo.combine(["ntl", "pop"], scale="municipality", years=(2012, 2020))
panel["ln_pop"] = np.log(panel["pop"])
df, df_def = geo.for_expdpy(panel, labels={"ln_pop": "Log of population"})
df = ex.set_labels(df, df_def, set_panel=True)
ex.analyze_panel_table(df, "ln_NTLpc", ["ln_pop"])        # pooled, between, fixed and random effects
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Or analyse it spatially with geometrics:

```python
!pip install -q geo4bolivia geometrics
import numpy as np
import geo4bolivia as geo
import geometrics as gm

ntl = geo.load("ntl")
ntl["NTLpc"] = np.exp(ntl["ln_NTLpc"])
gdf, df, df_dict = geo.for_geometrics(ntl, labels={"NTLpc": "Night-time lights per capita"})
df = gm.set_labels(df, df_dict, set_panel=True)
gm.analyze_beta_convergence(df, "NTLpc", gdf=gdf, w=gm.make_weights(gdf)).interpret()   # levels: logged internally
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Without the package

Every file is also a plain URL, readable with pandas alone (preinstalled in Colab, so nothing to install):

```python
import pandas as pd
df = pd.read_csv("https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/data/municipality/ntl.csv")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Installation

In a Google Colab cell:

```python
!pip install -q geo4bolivia                     # core: pandas, numpy, geopandas, pyarrow, requests, pyyaml (Colab has them)
!pip install -q "geo4bolivia[raster]"           # + rasterio, for zonal()
!pip install -q git+https://github.com/quarcs-lab/geo4bolivia   # development version
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Python 3.11 or later. The data are not inside the package. It reads them from the [GitHub repository](https://github.com/quarcs-lab/geo4bolivia), so installation is quick and you always get the files the website links to. For reproducible research, pin a release of the data with `geo.load(..., ref="v0.1.0")` or the environment variable `GEO4BOLIVIA_REF=v0.1.0`.

## Documentation

- [How the data infrastructure works](https://github.com/quarcs-lab/geo4bolivia/blob/main/docs/data-infrastructure.md): scales, IDs, metadata, aggregation rules, and recipes for building indicators
- [Dataset pages](https://github.com/quarcs-lab/geo4bolivia/tree/main/docs/datasets): variable dictionaries, coverage, sources and citations
- [Website](https://quarcs-lab.github.io/geo4bolivia/): indicators, notebooks, web apps and insights

## Citation

Mendez, C. (2026). *GeoDevelopment Observatory of Bolivia*. https://quarcs-lab.github.io/geo4bolivia/

MIT License. Original data sources are credited on each dataset page.
