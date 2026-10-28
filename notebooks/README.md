# Notebooks

Computational notebooks of the GeoDevelopment Observatory of Bolivia. Every notebook runs in Google Colab (no installation needed) and is paired with a MyST markdown file (`.md`) through [jupytext](https://jupytext.readthedocs.io/) for readable diffs. They load their data with the `geo4bolivia` package. The six ESDA notebooks are ports of [DS4Bolivia](https://github.com/quarcs-lab/ds4bolivia)'s notebooks, centred on the Multidimensional Poverty Index (`sdg1_2_mpi`, 2012) and night-time lights per capita in the same year.

| Notebook | Description | Data | Colab |
| --- | --- | --- | --- |
| [`geo4bolivia_quickstart.ipynb`](geo4bolivia_quickstart.ipynb) | Load data with and without the package, move it across scales, link your own table by name or INE code, build an indicator from a raster, interpolate to a grid and save | all datasets | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/geo4bolivia_quickstart.ipynb) |
| [`eda.ipynb`](eda.ipynb) | Exploratory data analysis of multidimensional poverty: departments, population, night-time lights | [`sdg`](../docs/datasets/sdg.md), [`ntl`](../docs/datasets/ntl.md), [`pop`](../docs/datasets/pop.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/eda.ipynb) |
| [`esda.ipynb`](esda.ipynb) | Spatial weights, Moran's I and LISA clusters of poverty | [`sdg`](../docs/datasets/sdg.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/esda.ipynb) |
| [`esda_dependence.ipynb`](esda_dependence.ipynb) | Box-plot and Fisher-Jenks maps, the spatial lag, Moran's I and LISA at two significance levels | [`sdg`](../docs/datasets/sdg.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/esda_dependence.ipynb) |
| [`esda_inequality.ipynb`](esda_inequality.ipynb) | Gini, Theil between and within departments, spatial Gini of poverty and lights | [`sdg`](../docs/datasets/sdg.md), [`ntl`](../docs/datasets/ntl.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/esda_inequality.ipynb) |
| [`esda_heterogeneity.ipynb`](esda_heterogeneity.ipynb) | OLS, GWR and MGWR of poverty on night-time lights | [`sdg`](../docs/datasets/sdg.md), [`ntl`](../docs/datasets/ntl.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/esda_heterogeneity.ipynb) |
| [`eda_esda.ipynb`](eda_esda.ipynb) | Extended workflow: infrastructure correlates, clusters, bivariate LISA, inequality and GWR | [`sdg`](../docs/datasets/sdg.md), [`ntl`](../docs/datasets/ntl.md), [`pop`](../docs/datasets/pop.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/eda_esda.ipynb) |
| [`embeddings_mpi_ml.ipynb`](embeddings_mpi_ml.ipynb) | Random forest and XGBoost predict poverty from satellite embeddings, with random and spatial cross-validation | [`emb`](../docs/datasets/emb.md), [`embpw`](../docs/datasets/embpw.md), [`sdg`](../docs/datasets/sdg.md), [`ntl`](../docs/datasets/ntl.md) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/embeddings_mpi_ml.ipynb) |

## Running locally

```bash
uv sync                                   # create the environment (includes geo4bolivia, scikit-learn, xgboost, mgwr, ...)
uv run jupyter lab                        # open notebooks
uv run jupytext --sync notebooks/*.ipynb  # keep .ipynb and .md in sync after editing
```

In Colab, every notebook installs what it needs (`geo4bolivia`, `mapclassify`, `esda`, `mgwr`, ...) only if it is missing. Outside the repository the package reads the data from GitHub.
