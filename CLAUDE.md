# Working on the geo4bolivia package

The Python package of the GeoDevelopment Observatory of Bolivia: it finds, loads and prepares the observatory's data and runs the fundamental analyses of spatial data science on them. The data, the builders and the observatory website live in the data repository, `quarcs-lab/gdo4bolivia`; this repository holds only the package, its tests and its documentation site.

## Environment

```bash
uv sync --all-extras                 # dependencies, extras, dev + docs + compare groups
uv run pytest -n 6 -p no:warnings    # tests (data tests need the data repository, see tests/conftest.py)
uv run ruff check src tests          # lint
```

- The package reads the data from a checkout of the data repository next to this one (`../gdo4bolivia`), from `GEO4BOLIVIA_DATA_DIR`, or from GitHub.
- Version: keep `pyproject.toml` and `__version__` in `src/geo4bolivia/__init__.py` equal.
- **Generic code.** Nothing in `src/` names Bolivia, a dataset, a variable, the repository or the package: the package name is `project.PACKAGE`, everything else comes from `project.yaml` and the metadata. Bolivian examples belong in `docs/` and `tests/` marked `data` must be driven by the registry and the metadata.

## Layout of `src/geo4bolivia/`

| Part | Modules |
| --- | --- |
| Data | `project`, `store`, `scales`, `metadata`, `io`, `discover`, `panel`, `create`, `aggregate`, `bridge`, `plot` |
| Maintainer tools | `build/` (generic helpers and the entry point; the project's builders are in the data repository), `validate`, `cli` |
| Analyses (public) | `spatial` (weights, connectivity, moran, lisa), `explore`, `convergence`, `dynamics`, `inequality`, `models`, `local` |
| Shared | `_inputs` (panel, boundaries, weights, labels, result finishing) |
| Engine | `_engine/`: estimators, figures, tables and interpretation texts ported from geometrics; it keeps geometrics' vocabulary (`var`, `period`, `entity`, `time`, `start`/`end`) and takes every input explicitly |

## Conventions of the analysis functions

Read `src/geo4bolivia/spatial.py`, `src/geo4bolivia/_inputs.py` and `tests/test_spatial.py` first: they are the model.

- **Names and arguments.** Short names (`moran`, `beta_convergence`). First argument `data`: a dataset id or a panel with `geo_id` (and `year`). Then the variable(s). The package's vocabulary: `variable` / `variables`, `year`, `first` / `last` (two years), `by` (a grouping column or a coarser scale). Options are keyword-only and end with `title=None, gdf=None, ref=None` where they apply; spatial functions take `w=None`.
- **Inputs.** `_inputs.panel()` turns `data` into a plain panel with names, panel ids and metadata labels declared; `_inputs.spatial()` also returns the boundaries and weights, restricted to the units with data. Explicit `gdf=` (a GeoDataFrame with `geo_id`) and `w=` always win, so every function also runs on data that are not in the project.
- **Results.** Every function returns a frozen result object (`@dataclass(frozen=True, repr=False)` mixing in `_engine.pedagogy.Interpretable`) with `.df`, `.fig` (Plotly), `.gt` (Great Tables, where a table helps), named numbers, `.notes` and `.interpret()`. Engine results go through `_inputs.finish(result, df)`, which renames the engine's `entity` / `period` columns to `geo_id` / `year` and adds unit names. The one exception is `map`, which returns a Plotly figure.
- **Figures.** Plotly only, styled with `_engine._theme.apply_default_layout` (colours from `color_for`, `active_sequential_scale`, `active_diverging_scale`); axis and legend text from `_engine._labels.resolve_label(df, column)`. Never call `.show()`; never change Plotly's default template.
- **Interpretation.** `.interpret()` returns Markdown that reads the numbers in words. It describes associations only (never "causes" or "effect of") and ends with `_engine.pedagogy._interpret._shared._ASSOC_NOTE`.
- **Errors.** `ValueError` for a missing column or year (say what the table has), `TypeError` for a non-numeric variable. When data are too short for a method (e.g. it needs three periods), say what the method needs and what the data have.
- **Docstrings.** NumPy sections in this package's compact style (`name : description`), a `Returns` section that names the result's attributes, and no `Examples` section: the documentation site adds a tested example per function from `docs/examples/`.
- **Optional libraries** (giddy, mgwr, linearmodels, rasterio) are imported inside the function, with an `ImportError` that gives the install line (`pip install "<package>[extra]"`, built from `project.PACKAGE`).
- **Tests.** Known-answer tests on the synthetic fixtures of `tests/conftest.py` (`units`, `field`, `growth_panel`: a lattice with planted spatial dependence and convergence), plus one `@pytest.mark.data` test that runs on the project's first dataset without naming it.
