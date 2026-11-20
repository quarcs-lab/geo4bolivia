# Releasing the package on PyPI

The package is built with [hatchling](https://hatch.pypa.io/) and published by GitHub Actions through PyPI Trusted Publishing. Only the code and `project.yaml` go into the package; the data stay in the data repository ([quarcs-lab/gdo4bolivia](https://github.com/quarcs-lab/gdo4bolivia)), so every release is small.

## What a release contains

| Item | Where it is set |
| --- | --- |
| Name on PyPI and import name | `[project].name` in `pyproject.toml` = folder `src/geo4bolivia/` = `package` in `project.yaml` |
| Version | `version` in `pyproject.toml` **and** `__version__` in `src/geo4bolivia/__init__.py` (keep them equal) |
| PyPI page | `README.md`. Use absolute links and image URLs: relative ones break on PyPI |
| Repository the installed package reads data from | `repository` and `default_ref` in `project.yaml`, bundled into the wheel |
| Extras | `[project.optional-dependencies]`: `dynamics` (giddy), `gwr` (mgwr), `panel` (linearmodels), `raster` (rasterio), `all` |

## Every release

```bash
# 1. Make sure everything passes, here and in the data repository
uv run ruff check src tests && uv run pytest -n 6 -p no:warnings
(cd ../gdo4bolivia && uv run geo4bolivia validate && uv run pytest)

# 2. Bump the version in pyproject.toml and src/geo4bolivia/__init__.py, and add the
#    release to docs/changelog.qmd.
#    Patch: fixes. Minor: new functions. Major: renamed functions, arguments or columns.

# 3. Rebuild the documentation and commit what changed (docs/_freeze, docs/llms.txt, notebooks/)
uv run python tools/build_docs.py

# 4. Build and inspect
rm -rf dist && uv build                       # dist/geo4bolivia-X.Y.Z.tar.gz and -py3-none-any.whl
unzip -l dist/*.whl                           # must list geo4bolivia/project.yaml and no data files

# 5. Test the wheel in a clean environment, outside both repositories
cd /tmp && uv venv t && uv pip install -p t "$OLDPWD/dist/"*.whl
t/bin/python -c "import geo4bolivia as geo; print(geo.moran('sdg', 'index_sdg').moran_i)"

# 6. Commit, tag and push: the tag runs .github/workflows/release.yml, which publishes
git commit -am "Release X.Y.Z" && git tag vX.Y.Z && git push origin main --tags

# 7. Tag the data repository with the same version, so ref="vX.Y.Z" freezes the data
(cd ../gdo4bolivia && git tag vX.Y.Z && git push origin vX.Y.Z)
```

Then check that it works in a fresh Google Colab notebook:

```python
!pip install -q geo4bolivia
import geo4bolivia as geo
geo.lisa("sdg", "index_sdg").fig
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## The release workflow

[`.github/workflows/release.yml`](.github/workflows/release.yml) runs only when a tag such as `vX.Y.Z` is pushed, and:

1. checks that the tag matches `version` in `pyproject.toml` (a mismatch stops the release)
2. builds the sdist and the wheel with `uv build`
3. publishes them to PyPI through the `pypi` environment, using OpenID Connect (no API token stored anywhere)

The trusted publisher on PyPI is: project `geo4bolivia`, owner `quarcs-lab`, repository `geo4bolivia`, workflow `release.yml`, environment `pypi`. The GitHub repository needs an environment called `pypi` (*Settings → Environments*, or `gh api -X PUT repos/quarcs-lab/geo4bolivia/environments/pypi`).

## Keeping Colab installs smooth

- **Lower bounds only** (`>=`) on dependencies, so installing the package never downgrades Colab's own libraries.
- **The default install covers the core analyses.** Colab already ships pandas, numpy, scipy, geopandas, statsmodels and plotly; the package adds the light PySAL libraries (libpysal, esda, spreg, inequality, mapclassify) and great-tables.
- **Heavier or fragile libraries are extras**: giddy (which needs numba) for Markov transitions, mgwr for geographically weighted regression, linearmodels for panel models, rasterio for zonal statistics. Each function that needs one imports it when called and says how to install it.
- **Pure Python, one universal wheel** (`py3-none-any`): nothing to compile on any platform.
- **The data change without a release.** The package reads the data repository's `main` by default, so new data reach users immediately. Release a new version only when the code changes.
- **Never rename a function, argument or result column in a patch release.** Notebooks in Colab install the latest version.
