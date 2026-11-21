<p align="center">
  <img src="https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/docs/images/hero.webp" alt="geo4bolivia: spatial data science for Bolivia's subnational development data" width="100%">
</p>

# geo4bolivia

**Find, load, map and analyse Bolivia's subnational development data, in Python.**

[![PyPI](https://img.shields.io/pypi/v/geo4bolivia.svg)](https://pypi.org/project/geo4bolivia/)
[![Python](https://img.shields.io/pypi/pyversions/geo4bolivia.svg)](https://pypi.org/project/geo4bolivia/)
[![CI](https://github.com/quarcs-lab/geo4bolivia/actions/workflows/ci.yml/badge.svg)](https://github.com/quarcs-lab/geo4bolivia/actions/workflows/ci.yml)
[![Docs](https://github.com/quarcs-lab/geo4bolivia/actions/workflows/docs.yml/badge.svg)](https://quarcs-lab.github.io/geo4bolivia/)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/get-started.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](https://github.com/quarcs-lab/geo4bolivia/blob/main/LICENSE)

geo4bolivia is the Python package of the [GeoDevelopment Observatory of Bolivia](https://quarcs-lab.github.io/gdo4bolivia/). It gives you the observatory's data for 343 municipalities, 113 provinces and 9 departments, and the standard analyses of spatial data science, each in one call.

**Documentation: <https://quarcs-lab.github.io/geo4bolivia/>**

## Install

```python
!pip install -q geo4bolivia          # Google Colab, or any Python 3.11+ environment
import geo4bolivia as geo
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

The default install covers loading, maps and the core analyses. Extras add the libraries of a few methods: `geo4bolivia[dynamics]` (Markov transitions), `[mgwr]` (multiscale GWR), `[panel]` (panel models), `[raster]` (zonal statistics), or `[all]`.

## At a glance

```python
!pip install -q geo4bolivia
import geo4bolivia as geo

geo.search("poverty")                                  # find variables in every dataset
mpi = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])   # a panel with names
geo.map(mpi, "sdg1_2_mpi", year=[2012, 2024], scheme="fisher_jenks")     # both periods, common classes

res = geo.lisa(mpi, "sdg1_2_mpi", year=2024)           # where are the clusters of poverty?
print(res.interpret())                                 # a reading of the numbers in words
res.fig                                                # Moran scatterplot and cluster map, side by side
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

Every analysis function takes a dataset id or a table with a `geo_id` column, finds the boundaries, the spatial weights and the labels itself, and returns a result object with `.fig` (Plotly), `.df`, `.gt` (a formatted table where one helps), the numbers by name and `.interpret()`.

## What it does

| You want to know | Functions |
| --- | --- |
| What data are there, and what do they mean? | `datasets`, `search`, `info`, `dictionary`, `reference_years`, `cite` |
| Load them, with names, boundaries and coarser scales | `load`, `units`, `boundaries`, `change`, `aggregate`, `combine` |
| What does a variable look like? | `describe`, `distribution`, `extremes`, `correlation`, `scatter`, `trend` |
| Is it clustered in space, and where? | `map`, `weights`, `connectivity`, `moran`, `lisa` |
| Are the units that started lower catching up? | `beta_convergence`, `sigma_convergence`, `convergence_clubs` |
| Who moved, and do neighbours matter? | `rank_mobility`, `lisa_transitions`, `transitions`, `spatial_transitions` |
| How unequal are the units, between or within which groups? | `inequality`, `theil_decomposition` |
| What goes with what, once space is accounted for? | `regression`, `panel_model`, `spatial_diagnostics`, `spatial_model` |
| Does an association change from place to place? | `mgwr` |
| Bring your own table or raster | `link`, `check`, `zonal`, `overlay`, `save` |

The [articles](https://quarcs-lab.github.io/geo4bolivia/articles/) take one question each and work it through on Bolivia's data; the [function reference](https://quarcs-lab.github.io/geo4bolivia/reference/) has an example for every function.

## The data

The package reads the observatory's published files from [quarcs-lab/gdo4bolivia](https://github.com/quarcs-lab/gdo4bolivia); `ref="v0.8.0"` freezes them at a release.

| Dataset | What | Units and years |
| --- | --- | --- |
| `sdg`, `sdg01` to `sdg17` | [Atlas de los ODS en Bolivia 2026](https://atlasods.sdsnbolivia.org/) (Andersen & Argandoña, SDSN Bolivia): the Sustainable Development Index, 15 goal indices and 81 indicators | 343 municipalities (map343, 2025 map), about 2012 and about 2024 |
| `pop` | Population (WorldPop) and density | 339 municipalities (map339, 2015 map), 2001 to 2020 |
| `ntl` | Night-time lights per capita (VIIRS) | 339 municipalities (map339), 2012 to 2020 |
| `emb`, `embpw` | Satellite embeddings, 64 dimensions | 339 municipalities (map339), 2017 |

`geo.info(dataset)` gives each dataset's sources and licenses and `geo.cite(dataset)` the citation and the credits they require. The SDG data are on SDSN Bolivia's municipal map of 2025 (`map343`, used with its permission), `pop`, `ntl` and the embeddings on the map of 2015 (`map339`); the two maps share their geo IDs, and the spatial functions take `map=` when a table does not say which one it is on.

Without the package, the same files are plain CSV and Parquet:

```python
import pandas as pd

BASE = "https://raw.githubusercontent.com/quarcs-lab/gdo4bolivia/main/"
pd.read_csv(BASE + "data/map343/sdg.csv")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Sister packages

geo4bolivia covers the fundamentals. For specialised methods, `geo.for_expdpy()` and `geo.for_geometrics()` hand any panel to its sister packages: [expdpy](https://cmg777.github.io/expdpy/) (panel econometrics) and [geometrics](https://quarcs-lab.github.io/geometrics/) (regional convergence and spatial econometrics), from which geo4bolivia's analysis engine is ported.

## Development

```bash
uv sync --all-extras                 # environment
uv run pytest -n 6 -p no:warnings    # tests (the data tests read a checkout of gdo4bolivia next to this repo, or GitHub)
uv run ruff check src tests          # lint
uv run python tools/build_docs.py    # documentation site, into docs/_site
```

`CLAUDE.md` describes the layout and conventions, `RELEASING.md` how to publish, and `TEMPLATE.md` what is generic and can be reused for another country.

## Cite

Mendez, C. (2026). *geo4bolivia: spatial data science for Bolivia's subnational development data* (version 0.8.0). <https://quarcs-lab.github.io/geo4bolivia/>

Please also cite the sources of the datasets you use (`geo.cite(dataset)`).

## License

Code: [MIT](https://github.com/quarcs-lab/geo4bolivia/blob/main/LICENSE). The data have their own licenses, documented per dataset in the [data repository](https://github.com/quarcs-lab/gdo4bolivia). Parts of the package are ported from [geometrics](https://github.com/quarcs-lab/geometrics) and follow the design of [expdpy](https://github.com/cmg777/expdpy), a Python port of [ExPanDaR](https://github.com/joachim-gassen/ExPanDaR), all MIT.
