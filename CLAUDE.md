# Working with Claude on GDO-Bolivia

This guide helps you work effectively with Claude (AI assistant) on the GeoDevelopment Observatory of Bolivia: analysing the data, building indicators with the `geo4bolivia` package, extending the notebooks, and updating the website.

This repository was created from the **geo4cambodia template** (see `TEMPLATE.md`) and shares its design with the other `geo4<country>` projects. Keep generic code generic: it must never hard-code Bolivia, the repository or the package name. Improvements to generic files should be ported back to geo4cambodia (the list is in `TEMPLATE.md`).

## Read first

| File | What it explains |
| --- | --- |
| `docs/data-infrastructure.md` | How the indicators database works: scales, geo IDs, units, metadata, aggregation rules, loading with and without the package, recipes for building indicators, the package reference |
| `CONTRIBUTING_DATA.md` | Step by step: add a dataset, a spatial scale, or a municipality map of another vintage |
| `raw/README.md` | Every raw input, and DS4Bolivia's swapped homonyms |
| `TEMPLATE.md` | What is generic and what is project-specific |
| `docs/python-package.md` | The package's PyPI page (absolute links only) |
| `docs/publishing.md` | Releasing the package on PyPI |

## Quick start prompts

```
"Load multidimensional poverty (sdg1_2_mpi, 2012) and night-time lights per
capita (2012) with geo4bolivia, map both with a quantile classification and
compute the bivariate Moran's I."
```

```
"Use geo.for_geometrics on night-time lights per capita (levels) and geometrics
to test beta-convergence across the 339 municipalities, 2012-2020."
```

```
"Add a new dataset at the municipality scale from raw/<dataset>/, following
CONTRIBUTING_DATA.md, and register it on the website."
```

## Project structure

- **`project.yaml`**: project identity. Holds the name, the package name, the GitHub repository and default ref, the country codes (`BO`, `BOL`), the equal-area CRS (an Albers projection fitted to Bolivia) and the catalog file name. It is bundled into the wheel.
- **`index.html`**: the entire website (React 18 UMD + Babel standalone + Tailwind Play CDN, all pinned). There is no build step.
- **`raw/`**: original inputs. Never edit them; fixes belong in the builders.
- **`geo/`**: the spatial backbone.
  - `scales.yaml`: the scale registry, edited by hand.
  - `units.csv/.parquet`, `boundaries/<scale>.geojson/.parquet`, `crosswalks/<from>__<to>.csv`: generated.
- **`data/<scale>/<dataset>.csv/.parquet`**: published panels, one row per `geo_id` × `year`. Generated.
- **`metadata/<dataset>.datapackage.json`** + `metadata/index.json`: Frictionless metadata, the source of truth for variables (each field's `title` is its plot label, its `description` how it was built), units, sources (with their licenses and required credits), licenses, reference years, aggregation rules and the headline map (`geo:` properties). The website's indicator pages read it directly.
- **`docs/datasets/*.md`**, **`data/README.md`**, **`definitions_gdo-bolivia.csv`**: generated from the metadata.
- **`src/geo4bolivia/`**: the Python package.

  | Module | Kind | Contents |
  | --- | --- | --- |
  | `project.py` | generic | reads `project.yaml`, finds the local checkout |
  | `store.py` | generic | reads files locally or from GitHub |
  | `scales.py` | generic | the scale registry |
  | `metadata.py` | generic | reads the datapackages |
  | `io.py` | generic | `load`, `units`, `boundaries`, `crosswalk`, `datasets`, `dictionary` |
  | `create.py` | generic | `link`, `check`, `combine`, `zonal`, `save` |
  | `bridge.py` | generic | `for_expdpy`, `for_geometrics` |
  | `aggregate.py` | generic | `aggregate`, `overlay`, `overlay_weights` |
  | `validate.py` | generic | the validator |
  | `cli.py` | generic | the command line |
  | `build/common.py`, `build/gadm.py` | generic | writing data, docs and `geo/`; geography from any GADM file |
  | `build/geo.py`, `build/{pop,ntl,sdg,emb}.py` | Bolivia-specific | the builders |
  | `build/_template.py`, `build/_geo_template.py` | templates | starting points for new builders |

- **`tests/test_core.py`**: generic tests, driven by the registry and metadata. **`tests/test_project.py`**: Bolivia facts.
- **`scripts/match_municipalities.py`**: one-off matching of GADM municipalities to DS4Bolivia (`raw/lookups/municipalities339_gadm.csv`). **`scripts/indicator_map.py`** (generic): the indicator pages' headline maps and cards, three Fisher–Jenks classes over Esri's keyless World Dark Gray Canvas (settings in `project.yaml` `site:`). **`scripts/site_images.py`**: renders the website's other images. **`scripts/new_project.py`** + `scripts/template/*.tpl`: the template generator.
- **`notebooks/`**: Colab notebooks paired with MyST `.md` files through jupytext.
  - `geo4bolivia_quickstart`: load, link and build indicators.
  - `eda`, `esda`, `esda_dependence`, `esda_inequality`, `esda_heterogeneity`, `eda_esda`: ported from DS4Bolivia, on multidimensional poverty (`sdg1_2_mpi`, 2012) and night-time lights.
  - `embeddings_mpi_ml`: predicting poverty from satellite embeddings.
- **`apps/`**: Google Earth Engine app source (`.js`).
- **`code/`**: pointers to data-preparation code.
- **`media/`**, **`images/`**: site assets.
- **`.claude/skills/create-indicator-website/`**: the skill that turns a dataset and its information into an indicator page (generic; port it with the template).
- **Licenses**: code MIT (`LICENSE`), data CC BY 4.0 (`LICENSE-DATA`), except the GADM-derived `geo/boundaries/` (GADM: non-commercial, no redistribution without permission; a rebuild on geoBoundaries is planned) and where a source requires otherwise. The SDG Atlas states no open license and is used with SDSN Bolivia's permission.
- `geo4cambodia/` and `ds4bolivia/` at the root, if present, are local reference clones. They are ignored by git and pytest; never edit or commit them.

## Environment setup (uv)

```bash
uv sync                                    # dependencies + the package (editable) + analysis libs incl. expdpy, geometrics, scikit-learn, xgboost
uv run geo4bolivia build [geo|<dataset>]   # regenerate geo/, data/, docs/ from raw/
uv run geo4bolivia validate                # check IDs, schemas, nesting, URLs, CSV = Parquet
uv run geo4bolivia list                    # datasets x scales x years
uv run pytest                              # tests
uv run jupyter lab notebooks/              # open notebooks
uv run jupytext --sync notebooks/*.ipynb   # re-pair after editing a notebook
uv add <package>                           # add a dependency (commit uv.lock)
python3 -m http.server 8000                # preview the website locally
```

- Always use `uv run` for Python and Jupyter.
- After changing anything in `raw/`, `metadata/`, `geo/scales.yaml` or `src/geo4bolivia/build/`, run `build`, `validate` and `pytest`, and commit the regenerated files.
- **Keep the package's own dependencies minimal.** Today they are pandas, numpy, requests, geopandas, pyarrow and pyyaml, all preinstalled in Colab. Optional libraries go in extras (`[raster]` = rasterio); notebook and analysis libraries go in the `analysis` dependency group.
- Version: keep `pyproject.toml` and `__version__` in `src/geo4bolivia/__init__.py` equal. Releases: `docs/publishing.md`.
- Inside the package, import `scales` and `project` as modules (`from . import project`; `from .scales import scales as registry`). The public names `geo.scales()` (a table) and `geo.config()` shadow nothing, but `geo4bolivia.scales` resolves to the function, not the module.
- Commit `uv.lock` after changing dependencies. Never commit `.venv/`.
- The notebooks install packages only when they are missing, so they run unchanged in Colab and locally.

## Spatial scales and geo IDs

Every unit has one **geo ID** (`geo_id`). Administrative IDs follow the GADM 4.1 hierarchy and nest by prefix. Source keys are kept as columns in `geo/units.csv`.

| Scale | Units | geo ID | Source keys kept | Datasets |
| --- | --- | --- | --- | --- |
| `country` | 1 | `BO` | `gid` | — |
| `department` | 9 | `BO-04` (La Paz) | `gid` (GADM), `ine_code` (`02`) | — |
| `province` | 112 | `BO-04-17` (Murillo) | `gid`, `ine_code` (`0201`) | — |
| `municipality` | 339 | `BO-04-17-04` (La Paz) | `gid` (`GID_3`), `ine_code` (`020101`), `asdf_id` (DS4Bolivia polygon), `mun_id` (INE code as integer) | `pop`, `ntl`, `sdg`, `emb`, `embpw` |
| `municipality_ine`, `grid10k` | planned | `BO-INE-020101`, `BO-G10K-r012c034` | — | — |

- Every unit row carries `<scale>_id` columns for each scale it lies in (`department_id`, `province_id`, ...).
- Department and province numbers follow GADM order and **differ from INE codes** (La Paz is `BO-04` here and `02` in INE). GADM skips province index 1 in La Paz, so La Paz provinces run `BO-04-02` to `BO-04-21`.
- GADM level 3 has 5 Lake Titicaca polygons (`TYPE_3 == "Lago"`); they are not units.
- Harmonized names: municipalities and departments use DS4Bolivia's spelling; provinces come from `raw/lookups/province_names.csv` (hand-checked; GADM writes names without spaces). `name_gadm` keeps GADM's spelling.
- **Municipality vintages.** New municipalities are created over time. The `municipality` scale is the 339-unit GADM map and stays so. A newer map is a new scale (`municipality_ine` is reserved) linked by overlay; never relabel `municipality`. See `CONTRIBUTING_DATA.md`.
- **DS4Bolivia's swapped homonyms.** San Javier (Beni/Santa Cruz), El Puente (Tarija/Santa Cruz) and Santa Rosa (Beni/Pando): DS4Bolivia attaches each pair's attribute rows (names, INE codes, SDG Atlas values) to the other polygon. Polygon-based data (`pop`, `ntl`, `emb`, `embpw`) link by `asdf_id`; the SDG Atlas data link by INE code (`mun_id`). Evidence in `raw/README.md`; `swapped` flags them in the lookup.
- Municipality names repeat across departments (six pairs) and four provinces are called Cercado, so link municipal tables by code (`key="mun_id"`, `"ine_code"` or `"asdf_id"`) rather than by name. `geo.link()` refuses ambiguous names instead of guessing.

## Datasets

| Dataset | Years | Notes |
| --- | --- | --- |
| `pop` | 2001–2020 | gridded population (WorldPop 1 km, via DS4Bolivia); `sum`. `pop_density` (people per km² of the GADM area); `none` |
| `ntl` | 2012–2020 | `ln_NTLpc` = ln(10⁸ × EOG VIIRS radiance / WorldPop) and its HP trend `ln_t400NTLpc`; logs, so `none` |
| `sdg` | 2010–2020 | 64 SDG Atlas indicators, **each at its own reference year** (`geo:year`); period averages at the midpoint, rounded down. The composite indices (IMDS, `index_sdg*`) are deliberately not included |
| `emb`, `embpw` | 2017 | 64 satellite embedding dimensions (A00–A63), area- and population-weighted; `none` |

Load one SDG indicator at its year: `geo.load("sdg", variables="sdg1_2_mpi", years=2012)`. Population-weighted SDG averages: `geo.aggregate(df, to="department", rules={"sdg1_2_mpi": "weighted_mean:pop"}, weights=geo.load("pop"))`.

## Loading data and building indicators

```python
!pip install -q "geo4bolivia[raster]"              # Google Colab ([raster] for geo.zonal)
import geo4bolivia as geo
geo.datasets(); geo.dictionary("sdg")               # catalog; variables with label and description
df  = geo.load("ntl")                               # panel: geo_id, year, variables
gdf = geo.load("ntl", years=2020, geometry=True)    # with boundaries
wide = geo.load("pop", wide="pop")                  # one column per year
geo.units("municipality"); geo.boundaries("department"); geo.crosswalk("municipality", "province")
geo.aggregate(geo.load("pop"), to="department", dataset="pop")       # up the hierarchy (metadata rules)
geo.combine(["ntl", "pop"], scale="municipality", extra=[my_panel])  # datasets on one scale
geo.overlay(pop_2020, grid_gdf, extensive=["pop"], id_col="cell")    # non-nested units, area-weighted
mine = geo.link(table, scale="municipality", on="mun_id", key="mun_id")   # INE codes -> geo_id
geo.zonal("raster.tif", scale="municipality", stats=["sum", "mean"], name="ntl", year=2020)
geo.save(panel, "name", scale="municipality", directory="my_data", variables={...})
gdf, df, df_dict = geo.for_geometrics(ntl_panel)                     # geometrics: LEVELS for beta/sigma convergence (logged internally); LOGS for convergence clubs
df, df_def = geo.for_expdpy("ntl", groups=["department"])            # for expdpy: analyses variables as given
```

- **Location of the data.** Outside the repo, the package reads from GitHub: `ref=` or `GEO4BOLIVIA_REF` pins a tag or commit. Inside the repo it reads local files.
- **Without the package**, use the raw URLs, e.g. `https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/data/municipality/ntl.csv`.
- **Documentation must always show both ways** of loading: with the package and with plain URLs.

## Updating the website

All content is data in the `CONTENT_REGISTRY` array in `index.html`. To add an item:

1. Add an object with these fields, copying an existing entry of the same type for the type-specific fields:
   - `id`, `type` (`indicator` | `package` | `notebook` | `app` | `insight` | `event`), `section` (`indicators` | `tools` | `insights` | `events`)
   - `title`, `summary`, `description`, `tags`
   - `image`, `imageAlt`
   - `date`, `pinned`
2. Put images in `images/<section>/` as WebP, at most 1600 px wide. Indicator maps and cards are rendered by `uv run python scripts/indicator_map.py <dataset>`; the other cards by `uv run python scripts/site_images.py`.
3. The item automatically gets a card and a shareable detail page at `#/<section>/<id>`.
4. Type-specific fields:
   - **New indicator:** use the **`create-indicator-website` skill** (`.claude/skills/`), which runs the whole workflow: data, metadata, approved dictionary and licenses, map, page, checks, commit. By hand: add the data (see `CONTRIBUTING_DATA.md`) with a `title` (plot label) and a construction `description` for every column, the sources' licenses and a `geo:map` (headline variable and year). Run `scripts/indicator_map.py`. Then set `dataset` (or `datasets`), `key: 'geo_id'`, `idExample`, `map` and `mapAlt` (the page's map), `image` and `imageAlt` (the card), and `code` with the tabs `python` (package) and `pandas` (plain URL). Add a `Dataset` entry, without `distribution`, to the JSON-LD block in `<head>`.
   - **Indicator pages** (`IndicatorDetail`) show the map, About (with the original source), Variables (name, label, description), the code, License and References. Variables, sources, licenses and references are fetched from `metadata/<dataset>.datapackage.json`, so edit the metadata, not the page. There is deliberately no download section and no link to the data folders: redistribution rights are being cleared.
   - **Package:** `scope` (the pip command), `install`, `quickstart` (code tabs), optionally `build`, `features` (`{title, fns, text}`) and `links` (kinds `colab`, `docs`, `pypi`, `github`).
   - **Insight:** add only published work whose DOI and abstract you have checked, with its full citation. The Insights and Events sections (and their nav links) appear automatically once they have at least one item.

**Every code box assumes Google Colab.**
- Each Python snippet on the website (indicator tabs, package quickstarts, the build example) starts with a runnable `!pip install -q <what it needs>`. The same goes for code blocks in README and docs.
- Install `geo4bolivia` (plus `expdpy` or `geometrics` when used), and use `"geo4bolivia[raster]"` when it calls `geo.zonal()`.
- Plain-URL snippets that only use pandas, geopandas or plotly need no install line, since Colab has them.
- **Every snippet shows its result as an interactive Plotly Express figure** (`import plotly.express as px`), with the simplest syntax: data, `x`/`y`/`color`, plus only `hover_name` (unit names), `labels={...}` and `title`; no custom colours or templates. Maps use `px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color=..., hover_name="name", center={"lat": -16.3, "lon": -64}, zoom=4)` with a continuous scale. Use long tables (`groupby(..., as_index=False)`, department names via `.map()`) rather than `unstack()`. Only the last expression of a Colab cell displays, so add `.show()` to any other figure. Keep lines within about 84 characters so they fit the website's code box. The geometrics and expdpy quickstarts keep their own `.fig`, which is already Plotly.
- There are no R or Stata examples.
- Maintainer commands (`uv ...`, releasing) stay as terminal commands.
- Every Python code box links to a blank notebook, `https://colab.research.google.com/notebooks/empty.ipynb`. On the website it is an "Open in Colab" button in the box's footer bar (`CodeBlock`'s `colab` prop; `CodeTabs` sets it). In README and docs (including generated dataset docs) it is the Colab badge below each Python block. Not for BibTeX or terminal commands.

Design tokens are defined in `tailwind.config`, in the **Altiplano palette** (the night over the Salar de Uyuni, Laguna Verde, Laguna Colorada's flamingos): `lagoon-950…500` backgrounds, `salt-100…700` text greys, `brand-rose` (#d1405a, buttons, with white text), `brand-flamingo` (#ff8597, accent text), `brand-turquoise` (#5ad6c6, highlights and links) and `sand-200…400` (packages). Content types have their own hues: indicators teal, packages sand, notebooks violet, apps orange, insights rose, events emerald. `scripts/site_images.py` uses the same colours: `SITE_PALETTE` is the maps' lagoon-to-flamingo ramp. The emblem (`images/logo/`) is drawn by the same script: the nine departments shaded by multidimensional poverty inside a satellite's orbit. Keep text contrast at WCAG AA or better, keep `prefers-reduced-motion` working, and give every image meaningful `alt` text.

## Preferred libraries

pandas, geopandas, libpysal, esda, splot, mapclassify, mgwr, inequality, statsmodels, scikit-learn, xgboost, matplotlib, seaborn, plotly, **expdpy** (https://cmg777.github.io/expdpy/) for panel exploration and econometrics (FE/RE, Hausman, clustered SEs), and **geometrics** (https://quarcs-lab.github.io/geometrics/) for convergence, spatial dependence and inequality analysis.
