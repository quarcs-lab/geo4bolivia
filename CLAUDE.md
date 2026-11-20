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
| Data | `project`, `store`, `scales`, `metadata`, `io`, `discover`, `panel`, `create`, `aggregate`, `bridge` |
| Maintainer tools | `build/` (generic helpers and the entry point; the project's builders are in the data repository), `validate`, `cli` |
| Analyses (public) | `explore` (correlation, extremes, distribution, scatter, trend), `plot` (map), `spatial` (weights, connectivity, moran, lisa), `convergence` (beta_convergence, sigma_convergence, convergence_clubs), `dynamics` (transitions, spatial_transitions, lisa_transitions, rank_mobility), `inequality` (inequality, theil_decomposition), `models` (regression, panel_model, spatial_model, spatial_diagnostics), `local` (mgwr) |
| Shared | `_inputs` (panel, boundaries, weights, labels, result finishing) |
| Engine | `_engine/`: estimators, figures, tables and interpretation texts ported from geometrics; it keeps geometrics' vocabulary (`var`, `period`, `entity`, `time`, `start`/`end`) and takes every input explicitly |

## Conventions of the analysis functions

Read `src/geo4bolivia/spatial.py`, `src/geo4bolivia/_inputs.py` and `tests/test_spatial.py` first: they are the model.

- **Names and arguments.** Short names (`moran`, `beta_convergence`). First argument `data`: a dataset id or a panel with `geo_id` (and `year`). Then the variable(s). The package's vocabulary: `variable` / `variables`, `year`, `first` / `last` (two years), `by` (a grouping column or a coarser scale). Options are keyword-only and end with `title=None, gdf=None, ref=None` where they apply; spatial functions take `w=None`.
- **Inputs.** `_inputs.panel()` turns `data` into a plain panel with names, panel ids and metadata labels declared; `_inputs.spatial()` also returns the boundaries and weights, restricted to the units with data. Explicit `gdf=` (a GeoDataFrame with `geo_id`) and `w=` always win, so every function also runs on data that are not in the project.
- **Results.** Every function returns a frozen result object (`@dataclass(frozen=True, repr=False)` mixing in `_engine.pedagogy.Interpretable`) with `.df`, `.fig` (Plotly), `.gt` (Great Tables, where a table helps), named numbers, `.notes` and `.interpret()`. Engine results go through `_inputs.finish(result, df)`, which renames the engine's `entity` / `period` columns to `geo_id` / `year` and adds unit names. The one exception is `map`, which returns a Plotly figure. `lisa`'s `.fig` is two panels in one figure (the Moran scatterplot and the cluster map, `_engine.dependence.lisa_panels`, one shared legend); `panels=` picks one, and `.fig_map` / `.fig_scatter` keep each. In the docs, a cell that shows it gets `#| classes: g4-wide` (a minimum width; `build_docs.py` adds it to the reference example).
- **Figures.** Plotly only, styled with `_engine._theme.apply_default_layout` (colours from `color_for`, `active_sequential_scale`, `active_diverging_scale`); axis and legend text from `_engine._labels.resolve_label(df, column)`. Never call `.show()`; never change Plotly's default template.
- **Interpretation.** `.interpret()` returns Markdown that reads the numbers in words. It describes associations only (never "causes" or "effect of") and ends with `_engine.pedagogy._interpret._shared._ASSOC_NOTE`.
- **Errors.** `ValueError` for a missing column or year (say what the table has), `TypeError` for a non-numeric variable. When data are too short for a method (e.g. it needs three periods), say what the method needs and what the data have.
- **Docstrings.** Standard NumPy sections (`name` on one line, its description indented below; types come from the signature), a `Returns` section that starts with the type and names the result's attributes, and no `Examples` section: the documentation site adds a tested example per function from `docs/examples/`, which keeps Bolivian names out of `src/`.
- **Optional libraries** (giddy: `[dynamics]`; mgwr: `[mgwr]`; linearmodels: `[panel]`; rasterio: `[raster]`) are imported inside the function, with an `ImportError` that gives the install line (`pip install "<package>[extra]"`, built from `project.PACKAGE`).
- **Tests.** Known-answer tests on the synthetic fixtures of `tests/conftest.py` (`units`, `field`, `growth_panel`: a lattice with planted spatial dependence and convergence), plus one `@pytest.mark.data` test that runs on the project's first dataset without naming it.

## Documentation site (`docs/`)

Quarto + quartodoc, deployed by `.github/workflows/docs.yml` to https://quarcs-lab.github.io/geo4bolivia/.

```bash
uv run python tools/build_docs.py              # reference, examples, notebooks, llms.txt, render to docs/_site
uv run python tools/run_page.py docs/articles/convergence.qmd --show   # run one page's code without rendering
uv run python tools/build_images.py            # process the pictures drawn in ChatGPT (prompts inside)
```

- **Generated, not committed:** `docs/reference/` (quartodoc), `docs/_site/`. **Generated and committed:** `docs/_freeze/` (the executed pages), `docs/llms.txt`, `notebooks/*.ipynb` (one Colab notebook per guide and article), `notebooks/reference/*.ipynb` (one per function, its example).
- **Reference.** Sections and their order are in `docs/_quarto.yml` (`quartodoc.sections`); every public function must be in one. Each function's example is `docs/examples/<function>.py`: Colab-ready code (first line `!pip install -q ...`), shown as written and run at build time.
- **Pages** (`get-started`, `explore`, `analyze`, `articles/*.qmd`). `docs/get-started.qmd` is the model. Rules:
  - Front matter: `title`, `description` (one sentence), `image` (the article's thumbnail, `../images/thumbs/<id>.webp`).
  - A "try-banner" with the Colab link of the page's notebook, then a first chunk with `#| eval: false` holding the `!pip install -q ...` line (with the extras the page needs).
  - Every chunk runs at build time on the observatory's data; keep each page under about two minutes. Lines of code within about 84 characters.
  - Show results as the package gives them: a result object as the last expression displays its figure and its reading; `.fig`, `.gt`, `.df` for a specific part. Other figures are Plotly Express with the simplest syntax (data, `x`/`y`/`color`, `hover_name`, `labels=geo.labels(df)`, `title`).
  - Write for a reader who knows some statistics but not the method: say what question the method answers, read every result in words using the actual numbers, and say what it does not show. Associations only, never causal claims. Plain sentences; no marketing language.
  - Datasets: `sdg` and `sdg01`...`sdg17` have two periods stored as 2012 and 2024 (343 units); `pop` (2001-2020) and `ntl` (2012-2020) have 333 units. Methods that need many years use `pop` or `ntl`.
- **Look.** Dark by default, like the observatory's website, with a light/dark toggle: `_quarto.yml` lists the `dark` theme first (`darkly` + `theme-dark.scss`) and then `light` (`cosmo` + `custom.scss`); the rules both share (buttons, cards, banners, tables, code boxes) are in `g4-common.scss`, which uses the `$g4-*` variables each theme defines. Altiplano palette and Inter font, as on the observatory's site. The page background is the Altiplano's night sky, fixed behind the content: faint stars (two SVG tiles) over a blue-to-teal gradient, `$g4-page-bg` in each theme (very faint on white in the light theme), drawn by `body::before` in `g4-common.scss`; the observatory's `site/src/styles.css` uses the same one.
- **Code boxes.** `docs/code-boxes.html` (added after every page's body) gives each box the observatory's `CodeBlock` look: window dots, a title and Copy on top; below, Open in Colab, which opens the page's own notebook (`notebooks/<page>.ipynb`; the home page opens `notebooks/home.ipynb`, which holds only the code of its first box, a reference page `notebooks/reference/<function>.ipynb`, any other page a blank notebook). Terminal boxes and the reference signatures get Copy only. Quarto's own `code-copy` is off.
- **Dark figures and tables.** The docs kernel starts with `docs/_ipython/profile_default/startup/00-dark.py` (`build_docs.py` registers it with `IPYTHONDIR`): a dark Plotly template, dark map tiles and dark Great Tables, for the site only. The package's figures keep their light default for users; never move this into `src/`. A change to it shows only after the pages are re-executed (`rm -rf docs/_freeze` and a full build).
- **Images.** The icon, the hero and the article thumbnails are AI-generated from the prompts in `tools/build_images.py` (Bolivian places and themes; no maps, borders, text or faces): `uv run python tools/build_images.py --generate` draws the missing ones with the Codex CLI (signed in to ChatGPT) into `docs/images/originals/` (not committed) and processes them. Every map on the site is drawn by the package from the official boundaries.
