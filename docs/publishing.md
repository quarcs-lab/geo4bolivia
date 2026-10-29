# Releasing the package on PyPI

The package is built with [hatchling](https://hatch.pypa.io/) and published with [uv](https://docs.astral.sh/uv/). Only the code and `project.yaml` go into the package; the data stay in the GitHub repository, so every release is small.

## What a release contains

| Item | Where it is set |
| --- | --- |
| Name on PyPI and import name | `[project].name` in `pyproject.toml` = folder `src/geo4bolivia/` = `package` in `project.yaml` |
| Version | `version` in `pyproject.toml` **and** `__version__` in `src/geo4bolivia/__init__.py` (keep them equal) |
| PyPI page | `docs/python-package.md` (`readme =` in `pyproject.toml`). Use absolute links: relative links break on PyPI |
| Repository the installed package reads data from | `repository` and `default_ref` in `project.yaml`, bundled into the wheel |
| Optional extras | `[project.optional-dependencies]` (`raster` adds rasterio) |

## First release (one-time setup)

Do this once per project. If <https://pypi.org/project/geo4bolivia/> already shows the package, skip to [Every release](#every-release).

1. **Check the name is free:** <https://pypi.org/project/geo4bolivia/> should return "Not Found".
2. **Choose how to authenticate.** Use one of the two options below.
   - **Option A: an API token from your account (simplest).** On PyPI go to *Account settings → API tokens → Add API token*. Use scope "Entire account" for the very first upload, then replace it with a token scoped to `geo4bolivia`.
   - **Option B: Trusted Publishing from GitHub Actions (no token to store; recommended once it works).** Your geometrics package already uses it.
     1. On PyPI, go to *Your account → Publishing → Add a new pending publisher*.
     2. Fill in: PyPI project `geo4bolivia`, owner `quarcs-lab`, repository `geo4bolivia`, workflow `release.yml`, environment `pypi`.
     3. Add the workflow below to `.github/workflows/release.yml` (already in this repository).
     4. In the GitHub repository, go to *Settings → Environments* and create an environment called `pypi`. With the GitHub CLI: `gh api -X PUT repos/<owner>/<repo>/environments/pypi`.
3. **Optional: try TestPyPI first.** It is a separate account at <https://test.pypi.org>. Publish with `uv publish --publish-url https://test.pypi.org/legacy/ --token <testpypi-token>`, then install with `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ geo4bolivia`.

## Every release

```bash
# 1. Make sure everything passes
uv run geo4bolivia build && uv run geo4bolivia validate && uv run pytest

# 2. Bump the version in pyproject.toml and src/geo4bolivia/__init__.py (e.g. 0.1.0 -> 0.1.1)
#    Patch: fixes. Minor: new datasets or functions. Major: renamed IDs, columns or functions.

# 3. Build and inspect
rm -rf dist && uv build                       # dist/geo4bolivia-X.Y.Z.tar.gz and -py3-none-any.whl
unzip -l dist/*.whl                           # must list geo4bolivia/project.yaml and no data files

# 4. Test the wheel in a clean environment, outside the repository
cd /tmp && uv venv t && uv pip install -p t ~/path/to/geo4bolivia/dist/*.whl
t/bin/python -c "import geo4bolivia as geo; print(geo.load('pop').shape)"

# 5. Commit, tag and push (the tag also freezes the data: geo.load(..., ref="vX.Y.Z"))
git commit -am "Release X.Y.Z" && git tag vX.Y.Z && git push origin main --tags

# 6a. Option A: publish from your computer
uv publish --token pypi-XXXXXXXX              # or set UV_PUBLISH_TOKEN
# 6b. Option B: the tag push runs .github/workflows/release.yml, which publishes
```

Then check that it works in a fresh Google Colab notebook:

```python
!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px
gdf = geo.load("pop", years=2020, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color="pop",
                  hover_name="name", center={"lat": -16.3, "lon": -64}, zoom=4)
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

## Trusted Publishing workflow (option B)

The workflow is [`.github/workflows/release.yml`](../.github/workflows/release.yml). It runs only when you push a tag such as `vX.Y.Z`, and:

1. checks that the tag matches `version` in `pyproject.toml` (a mismatch stops the release)
2. builds the sdist and the wheel with `uv build`
3. publishes them to PyPI through the `pypi` environment, using OpenID Connect (no API token stored anywhere)

Follow the run in the repository's *Actions* tab. `scripts/new_project.py` copies the workflow into new `geo4<country>` projects with the package name already replaced.

## Keeping Colab installs smooth

- **Keep the core dependencies minimal and unpinned above.** Colab already ships pandas, numpy, geopandas, pyarrow, requests and pyyaml, so `pip install geo4bolivia` installs almost nothing and never downgrades Colab's own packages. Use lower bounds (`>=`) only.
- **Put heavy or optional libraries in extras**, e.g. `geo4bolivia[raster]`, never in the core.
- **Pure Python, one universal wheel** (`py3-none-any`): nothing to compile on any platform.
- **The data change without a release.** The package reads `main` by default, so new data reach users immediately. Release a new version only when the code changes. Tag the repository at every release so that `ref="vX.Y.Z"` reproduces past results.
- **Never rename a column, ID or function in a patch release.** Notebooks in Colab install the latest version.

## For a new `geo4<country>` project

The steps are identical with the new name. `scripts/new_project.py` already renames the package, the CLI, the environment variables and the URLs. Check that the name is free on PyPI before creating the project.
