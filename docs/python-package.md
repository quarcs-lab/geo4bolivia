# geo4bolivia

**Find, load and understand Bolivia's subnational development data, at every spatial scale.**

`geo4bolivia` is the Python package of the [GeoDevelopment Observatory of Bolivia](https://quarcs-lab.github.io/geo4bolivia/) and the way into its data: the SDG Atlas of Bolivia 2026 of SDSN Bolivia (the Sustainable Development Index, 15 goal indices and 81 indicators near 2012 and near 2024), population, night-time lights and satellite embeddings, for Bolivia's 343 municipalities and indigenous autonomies, its provinces and departments. It knows every dataset's documentation, so it can tell you what a variable means, where it comes from, under which license, how to cite it and which years really lie behind each period. It loads any indicator as a labelled panel with names and boundaries, compares periods, aggregates to coarser scales, draws maps, links your own data to the same units and hands everything to the companion packages [expdpy](https://cmg777.github.io/expdpy/) (panel econometrics) and [geometrics](https://quarcs-lab.github.io/geometrics/) (spatial analysis).

It works out of the box in Google Colab: every example below runs in a new Colab notebook.

- **Tutorial:** https://quarcs-lab.github.io/geo4bolivia/tools/geo4bolivia-package/
- **Function reference, with an example per function:** https://quarcs-lab.github.io/geo4bolivia/tools/geo4bolivia-reference/
- **Tutorial notebook:** [Open in Colab](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/geo4bolivia_quickstart.ipynb)
- **The three packages on one question:** [Open in Colab](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/three_packages.ipynb)

```python
!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px                          # preinstalled in Colab

geo.search("poverty")                                # which variables, in which datasets and years
mpi = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])   # 343 units, ~2012 and ~2024
chg = geo.change(mpi, "sdg1_2_mpi")                  # per municipality: change and rank change
geo.map(mpi, "sdg1_2_mpi", year=2024).show()         # interactive, labelled map
px.scatter(chg, x="sdg1_2_mpi_2012", y="sdg1_2_mpi_2024", color="department",
           hover_name="name", labels=geo.labels(chg))
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## What it does

| Task | Functions |
| --- | --- |
| **Discover** datasets and variables, their sources, licenses, actual years and citation | `datasets`, `search`, `info`, `dictionary`, `reference_years`, `cite` |
| **Load** panels (one row per unit and year) with names, parent units and boundaries | `load`, `add_names`, `units`, `boundaries`, `crosswalk`, `scales`, `ancestors`, `scale_of` |
| **Understand** variables: labelled summaries, change between periods, interactive maps | `describe`, `labels`, `change`, `map` |
| **Move** data up the hierarchy (with each variable's rule and coverage) or onto grids and other maps | `aggregate`, `combine`, `overlay`, `overlay_weights` |
| **Build** your own indicators: link tables by names or codes, summarise rasters, check and save | `link`, `check`, `zonal`, `save` |
| **Analyse** with [expdpy](https://cmg777.github.io/expdpy/) and [geometrics](https://quarcs-lab.github.io/geometrics/) | `for_expdpy`, `for_geometrics` |

## One ID for every unit, at every scale

Every unit has a **geo ID** that nests by prefix (numbered as in GADM 4.1): municipality `BO-04-17-04` (Nuestra Señora de La Paz) lies in province `BO-04-17` (Murillo), which lies in department `BO-04` (La Paz), which lies in Bolivia `BO`. INE codes and DS4Bolivia's `asdf_id` are kept as columns of `geo.units()`. The municipalities are the 343 municipalities and indigenous autonomies of SDSN Bolivia's municipal map of 2025, used with SDSN Bolivia's permission. Each dataset is a long panel keyed by `geo_id` and `year`.

| Scale | Units | Example |
| --- | --- | --- |
| `country` | 1 | `BO` |
| `department` | 9 | `BO-04` |
| `province` | 113 | `BO-04-17` |
| `municipality` | 343 | `BO-04-17-04` |

## Tutorial

### 1. Discover what is available

```python
!pip install -q geo4bolivia
import geo4bolivia as geo

geo.datasets()                             # dataset, scale, years ("2012, 2024"), units with data
geo.search("poverty")                      # variables matching words, ignoring accents and case
geo.info("sdg03")                          # description, coverage, sources, licenses, citation, notes
geo.dictionary("sdg03")                    # label, definition, unit, aggregation rule, reference years
geo.reference_years("sdg03")               # e.g. infant mortality: stored 2012/2024, surveys of 2008/2023
print(geo.cite("sdg03"))                   # APA, then the credits its sources require
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

The SDG Atlas stores its initial values at 2012 and its final values at 2024; `geo.reference_years()` gives the actual years behind each indicator. Population, lights and embeddings cover the 333 municipalities whose territory is unchanged since the 2015 map they were computed on; `geo.datasets()` shows it.

### 2. Load a panel

```python
!pip install -q geo4bolivia
import geo4bolivia as geo

mpi = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])  # + name, department
ids = geo.load("sdg", years=2024, geometry=True)                         # a GeoDataFrame
pop = geo.load("pop", variables="pop", wide="pop")                        # one column per year
geo.units("municipality")                                                # names, parents, INE codes, areas
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

### 3. Understand a variable and compare the periods

```python
!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

ids = geo.load("sdg", variables="index_sdg", groups=["department"])
geo.describe(ids)                                  # per period, with labels and units
chg = geo.change(ids, "index_sdg")                 # first, last, change, % change, annual change, ranks
geo.map(chg, "index_sdg_change").show()            # interactive map (plotly; geo4bolivia[plot] outside Colab)
px.scatter(chg, x="index_sdg_2012", y="index_sdg_change", color="department",
           hover_name="name", labels=geo.labels(chg),
           title="Did the municipalities that started lower gain more?")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

### 4. Move across scales

```python
!pip install -q geo4bolivia
import geo4bolivia as geo

mpi = geo.load("sdg01", variables="sdg1_2_mpi")
geo.aggregate(mpi, to=["department", "country"], dataset="sdg01")   # census-population weighted
geo.combine(["sdg01", "sdg04"], scale="department")                  # two goals, one panel
geo.aggregate(geo.load("ntl"), to="department", rules={"ln_NTLpc": "mean"},
              variables="ln_NTLpc")                                   # coverage: 333 of 343 have lights
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Each variable carries an aggregation rule in the metadata: `sum` for counts, `weighted_mean:<field>` for rates, `none` for logs and ranks. The SDG indicators average with census-population weights (the 2012 census for ~2012, the 2024 census for ~2024), which the package loads from the `sdg` dataset itself; the results approximate, but are not, the Atlas's own department figures. Every result has `n_units` and `coverage`, the share of the target's units with data.

### 5. Build your own indicator

```python
!pip install -q geo4bolivia
import pandas as pd
import geo4bolivia as geo

mine = pd.read_csv("schools_by_municipality.csv")                 # e.g. columns mun_id (INE code), year, schools
mine = geo.link(mine, scale="municipality", on="mun_id", key="mun_id")   # 20101 -> BO-04-17-04
panel = geo.combine(["sdg"], scale="municipality", years=2024, extra=[mine])
panel["schools_per_10k"] = panel["schools"] / panel["population"] * 1e4
geo.save(panel, "schools", scale="municipality", directory="my_data")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

`geo.link()` also matches names in any spelling (ignoring accents, case and spacing) and refuses to guess between municipalities that share a name. From a raster, such as a Google Earth Engine export:

```python
!pip install -q "geo4bolivia[raster]"             # [raster] adds rasterio
import geo4bolivia as geo

lights = geo.zonal("viirs_2020.tif", scale="municipality", stats=["sum", "mean"], name="ntl", year=2020)
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

### 6. Analyse with expdpy and geometrics

The three packages work as one workflow: geo4bolivia finds and prepares the data, [expdpy](https://quarcs-lab.github.io/geo4bolivia/tools/expdpy-package/) explores and models it as a panel, [geometrics](https://quarcs-lab.github.io/geo4bolivia/tools/geometrics-package/) analyses its geography.

```python
!pip install -q geo4bolivia expdpy geometrics
import numpy as np
import geo4bolivia as geo
import expdpy as ex
import geometrics as gm

ids = geo.load("sdg", variables=["index_sdg", "population"], groups=["department"])
ids["ln_pop"] = np.log(ids["population"])
df, df_def = geo.for_expdpy(ids, labels={"ln_pop": "Log of census population"})
df = ex.set_labels(df, df_def, set_panel=True)
ex.explore_xtsum_table(df, var=["index_sdg"])                     # between vs within variation
print(ex.analyze_hausman_test(df, "index_sdg", ["ln_pop"]).interpret())

gdf, sp, sp_dict = geo.for_geometrics("sdg", variables="index_sdg")
sp = gm.set_labels(sp, sp_dict, set_panel=True)
w = gm.make_weights(gdf, method="queen")
print(gm.analyze_beta_convergence(sp, "index_sdg").interpret())  # ~2012 -> ~2024
gm.explore_lisa_cluster_map(sp, "index_sdg", gdf=gdf, w=w, period=2024).fig
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Without the package

Every file is also a plain URL, readable with pandas alone (preinstalled in Colab, so nothing to install):

```python
import pandas as pd
df = pd.read_csv("https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/data/municipality/sdg01.csv")
units = pd.read_csv("https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/geo/units.csv")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Installation

In a Google Colab cell:

```python
!pip install -q geo4bolivia                     # core: pandas, numpy, geopandas, pyarrow, requests, pyyaml (Colab has them)
!pip install -q "geo4bolivia[raster]"           # + rasterio, for zonal()
!pip install -q "geo4bolivia[plot]"             # + plotly, for map() (Colab has it)
!pip install -q git+https://github.com/quarcs-lab/geo4bolivia   # development version
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Python 3.11 or later. The data are not inside the package. It reads them from the [GitHub repository](https://github.com/quarcs-lab/geo4bolivia), so installation is quick and you always get the files the website links to. For reproducible research, pin a release of the data with `geo.load(..., ref="v0.5.0")` or the environment variable `GEO4BOLIVIA_REF=v0.5.0`. From the command line: `geo4bolivia list`, `geo4bolivia search poverty`, `geo4bolivia info sdg01`.

## Documentation

- [Tutorial](https://quarcs-lab.github.io/geo4bolivia/tools/geo4bolivia-package/) and [function reference](https://quarcs-lab.github.io/geo4bolivia/tools/geo4bolivia-reference/) on the website
- [How the data infrastructure works](https://github.com/quarcs-lab/geo4bolivia/blob/main/docs/data-infrastructure.md): scales, IDs, metadata, aggregation rules, and recipes for building indicators
- [Dataset pages](https://github.com/quarcs-lab/geo4bolivia/tree/main/docs/datasets): variable dictionaries, coverage, sources and citations
- [Website](https://quarcs-lab.github.io/geo4bolivia/): indicators, notebooks, web apps and insights

## Citation

Mendez, C. (2026). *GeoDevelopment Observatory of Bolivia*. https://quarcs-lab.github.io/geo4bolivia/

MIT License. Original data sources are credited on each dataset page; `geo.cite()` prints them.
