# What is generic, and how to reuse this package for another country

geo4bolivia belongs to a family of **geo4\<country\>** projects that share one design (the reference implementation is [geo4cambodia](https://github.com/quarcs-lab/geo4cambodia)): geo IDs that nest by prefix, long panels keyed by `geo_id` and `year`, Frictionless metadata with `geo:` properties, and the same package API. Since version 0.6 a project is **two repositories**:

| Repository | Holds | Here |
| --- | --- | --- |
| The package | `src/<package>/` (generic code), `project.yaml` (identity), tests, the documentation site | [quarcs-lab/geo4bolivia](https://github.com/quarcs-lab/geo4bolivia) |
| The data repository | `raw/`, `builders/` (project-specific), `geo/`, `data/`, `metadata/`, generated dataset docs, notebooks and the observatory website | [quarcs-lab/gdo4bolivia](https://github.com/quarcs-lab/gdo4bolivia) |

The package reads the data repository named in `project.yaml` (`repository`, `default_ref`): from GitHub by default, or from a local checkout (found from the working directory, or `<PREFIX>_DATA_DIR`). The data repository depends on the package and runs its commands (`<package> build`, `<package> validate`).

## What is generic and what is project-specific

| Generic: copied as is | Project-specific: rewritten |
| --- | --- |
| Everything in `src/<package>/`: the data layer (`project`, `store`, `scales`, `metadata`, `io`, `discover`, `panel`, `create`, `aggregate`, `bridge`, `plot`), the maintainer tools (`build/common.py`, `build/gadm.py`, `build/geoboundaries.py`, the build entry point, `validate`, `cli`), the analyses (`explore`, `spatial`, `convergence`, `dynamics`, `inequality`, `models`, `local`, `_inputs`) and the engine (`_engine/`) | `project.yaml`: name, package, data repository, country codes, projection, default map view |
| `tests/` (the analyses are tested on synthetic data; `tests/test_data.py` is driven by the registry and the metadata) | `pyproject.toml` (name, description, URLs), `README.md`, `CITATION.cff`, `CLAUDE.md` |
| `tools/` (documentation build, page runner, image processing), `.github/workflows/`, `docs/_quarto.yml` structure and `docs/custom.scss` | `docs/` pages, articles and `docs/examples/` (they use the country's datasets), the prompts in `tools/build_images.py` |
| In the data repository: nothing in `builders/` is generic except its contract (below) | In the data repository: `builders/`, `raw/`, `geo/scales.yaml`, `metadata/`, the website and notebooks |

Generic code never names a country, a dataset, a variable, a repository or a package. It reads them from `project.yaml`, from the metadata and from the name of the package's folder. The environment variables take the package name as prefix (`GEO4LAOS_REF`, ...).

## The contract between the two repositories

- **Files the package reads:** `geo/scales.yaml`, `geo/units.parquet`, `geo/boundaries/<scale>.parquet`, `geo/crosswalks/<from>__<to>.csv`, `metadata/index.json`, `metadata/<dataset>.datapackage.json`, and each resource's `geo:parquet`.
- **A checkout is recognised** by a `project.yaml` whose `package` is this package and a `geo/scales.yaml` (`project._is_root`). Its `project.yaml` is read on top of the package's own, so it can add website settings.
- **Builders:** `builders/__init__.py` in the data repository defines `build_geo` (a function that writes `geo/`) and `DATASETS` (`{dataset id: function}`), and optionally `after_build(target)`, run last for the project's own finishing steps. `<package> build [geo|<dataset>]` loads and runs them; they import the generic helpers from `<package>.build`. `build/_template.py` and `build/_geo_template.py` are starting points.
- **Versions:** the data repository is tagged with the package's version at each release, so `ref="vX.Y.Z"` freezes the data.

## Porting to geo4cambodia (not done yet)

geo4cambodia still has the one-repository layout of version 0.5. To bring it to this design:

1. **Split the repository** as here: the package with its history (`git filter-repo` on `src/`, `tests/`, `pyproject.toml`, `project.yaml`), the country's builders into `builders/` of the data repository, and `[tool.uv.sources]` or a PyPI dependency from the data repository to the package.
2. **Copy the generic code of 0.6:** `_engine/`, `_inputs.py`, `explore.py`, `spatial.py`, `convergence.py`, `dynamics.py`, `inequality.py`, `models.py`, `local.py`, the extended `plot.py`, `build/__init__.py` (the entry point that loads `builders/`), `project.py` (own and local `project.yaml`), the tests (`tests/conftest.py`, `tests/dgp.py`, `tests/engine/`, `tests/test_*_api.py`, `tests/test_spatial.py`), `tools/` and the workflows, renaming the package.
3. **Dependencies:** core gains scipy, libpysal, esda, spreg, inequality, mapclassify, statsmodels, plotly and great-tables; extras `dynamics` (giddy), `mgwr`, `panel` (linearmodels), `raster`, `all`; and the uv constraints for numba and quantecon.
4. **Documentation site:** `docs/_quarto.yml`, `docs/custom.scss` (palette), then the pages, articles and `docs/examples/` rewritten on the country's datasets.
5. **`scripts/new_project.py`** (in the data repository) still generates the one-repository layout and needs the same split.
