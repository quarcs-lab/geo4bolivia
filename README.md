# GeoDevelopment Observatory of Bolivia (GDO-Bolivia)

Open subnational development data for Bolivia, at every spatial scale, with a Python package to load them, link your own data to them and build new indicators.

- **Website:** https://quarcs-lab.github.io/geo4bolivia/
- **Package:** `!pip install -q geo4bolivia` in Google Colab ([guide](docs/python-package.md))
- **How the data infrastructure works:** [docs/data-infrastructure.md](docs/data-infrastructure.md)

## Data

Every spatial unit has a **geo ID** that nests by prefix (GADM 4.1 hierarchy): `BO` (country) › `BO-01` (department) › `BO-01-01` (municipality). Datasets are panels with one row per unit (`geo_id`) and year, published as CSV and Parquet in `data/<scale>/`. Each dataset is described in `metadata/` and on a generated page in `docs/datasets/`.

| Dataset | Title | Scale | Period |
| --- | --- | --- | --- |
| — | *No datasets yet: see [CONTRIBUTING_DATA.md](CONTRIBUTING_DATA.md)* | | |

### Load the data, with or without the package

```python
# With the package (every snippet runs as-is in Google Colab)
!pip install -q geo4bolivia
import geo4bolivia as geo
geo.datasets()
df = geo.load("<dataset>", geometry=True)

# Without it: every file is a plain URL
import pandas as pd
df = pd.read_csv("https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/data/<scale>/<dataset>.csv")
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Repository structure

```
project.yaml            # project identity: name, package, repository, country codes
geo/                    # scales.yaml, units, boundaries/, crosswalks/
data/<scale>/           # published panels (generated)
metadata/               # one Frictionless datapackage per dataset
docs/                   # guides and generated dataset pages
raw/                    # original inputs, never edited
src/geo4bolivia/           # Python package: load, link, zonal, aggregate, overlay, build, validate
tests/                  # test_core.py (generic) + test_project.py
```

## Run locally

```bash
uv sync                            # environment + the package (editable)
uv run geo4bolivia build              # regenerate geo/, data/, docs/ from raw/
uv run geo4bolivia validate           # check IDs, schemas, nesting and file consistency
uv run pytest
```

Created from the [geo4cambodia](https://github.com/quarcs-lab/geo4cambodia) template ([TEMPLATE.md](TEMPLATE.md)).
