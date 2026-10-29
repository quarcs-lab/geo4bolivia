# Using this repository as a template

> **geo4bolivia** was created from [geo4cambodia](https://github.com/quarcs-lab/geo4cambodia), the reference implementation, with `scripts/new_project.py`. This page is kept as in geo4cambodia, so "this repository" in the steps below means geo4cambodia. What geo4bolivia adapted:
>
> - three admin levels from one GADM level-3 file (`--levels department,province,municipality`), with the 5 Lake Titicaca polygons dropped before `from_gadm()`
> - a scale per municipality map (`municipality_ine` planned, see [`CONTRIBUTING_DATA.md`](CONTRIBUTING_DATA.md))
> - a country-fitted equal-area projection in `project.yaml`
> - variables observed once stored at their reference year (`geo:year`, see `metadata/sdg.datapackage.json`)
>
> Small generic fixes made here and still to be copied back to geo4cambodia: `dissolve()` fills the sliver gaps between source polygons that used to remain as holes in every dissolved scale (thousands of them in Bolivia's departments); `link()` no longer links a name shared by several units to one of them at random (it reports them instead); `from_gadm()` also accepts a GeoDataFrame; `validate` compares source keys as text (an integer `asdf_id` equals the `"57"` stored in `geo/units`); `aggregate()` leaves numeric source keys and `*_id` columns out of the variables it aggregates by default (it warned about `asdf_id`); `zonal()` has no default `scale` (it was `"district"`, which not every project has); and `scripts/new_project.py` renames the package inside `TEMPLATE.md` too, which makes the new project call itself the reference implementation. Indicator pages: every field has a `title` (plot label) and a construction `description`, sources carry `geo:role`, `geo:creator`, `geo:homepage`, `geo:license` and `geo:attribution`, and packages a `geo:map` headline map and `geo:updated`, all checked by `validate` (the `geo:map` check is new); `dictionary()` returns a `label` column, `save()` writes field titles (`label` in `variables`), and the catalog CSV gains a `description` column; `scripts/indicator_map.py` draws the headline maps (Fisher–Jenks, keyless Esri basemap, `site:` block in `project.yaml`); the `create-indicator-website` skill (`.claude/skills/`); `IndicatorDetail` in `index.html` reads the metadata at runtime and has no download section; and `LICENSE-DATA` (CC BY 4.0 for data, with exceptions).

geo4cambodia is the reference implementation of a family of **geo4<country>** repositories. Each one has a Python package, a database of subnational indicators and (optionally) a website. They all share one design, so code, notebooks and skills transfer from one country to another:

- **geo IDs:** `<ISO2>`, `<ISO2>-NN`, `<ISO2>-NN-NN`, ... from GADM
- **datasets:** long panels keyed by `geo_id` and `year`, as CSV and Parquet
- **metadata:** Frictionless datapackages with `geo:` properties
- **the same package API:** `load`, `link`, `zonal`, `aggregate`, `overlay`, `combine`, `save`, `for_expdpy`, `for_geometrics`

How the database works is explained in [`docs/data-infrastructure.md`](docs/data-infrastructure.md). This page explains how to start a new project. The examples in `docs/data-infrastructure.md` and `docs/publishing.md` use geo4cambodia's own datasets (`gdppc`, `env`, `hdi`) and IDs; adapt them once your project has data.

## What is generic and what is project-specific

| Generic (shared by every project, copied as is) | Project-specific (rewritten for each project) |
| --- | --- |
| `src/<package>/`: `project.py`, `store.py`, `scales.py`, `metadata.py`, `io.py`, `create.py`, `bridge.py`, `aggregate.py`, `validate.py`, `cli.py` | `project.yaml`: name, package, repository, country codes, projection |
| `src/<package>/build/`: `common.py` (writing data, docs and geo/), `gadm.py` (geography from GADM), `_template.py`, `_geo_template.py` | `src/<package>/build/geo.py` and one builder per dataset; `DATASETS` in `build/__init__.py` |
| `tests/test_core.py` | `tests/test_project.py` |
| `docs/data-infrastructure.md`, `docs/publishing.md`, `CONTRIBUTING_DATA.md`, `TEMPLATE.md`, `scripts/`, `.claude/skills/` | `geo/scales.yaml`, `raw/`, `metadata/`, `docs/python-package.md`, `README.md`, `CLAUDE.md` |
| | Generated: `geo/units.*`, `geo/boundaries/`, `geo/crosswalks/`, `data/`, `docs/datasets/`, the catalog CSV |
| | Website (`index.html`, `images/`, `media/`) and notebooks: optional |

Generic code never names a country, a repository or a package. It reads them from `project.yaml` and from the folder name of the package. The environment variables take the package name as prefix (`GEO4LAOS_REF`, ...).

## Start a new project in 6 steps

**1. Create the skeleton** (Python standard library only):

```bash
python scripts/new_project.py ../geo4laos --package geo4laos --country Laos \
    --iso2 LA --iso3 LAO --repo my-org/geo4laos --levels province,district
```

The script:
- copies the generic files, renaming `geo4cambodia` to `geo4laos` everywhere (package folder, imports, CLI, environment variables, URLs)
- writes `project.yaml`, `geo/scales.yaml` (country, then one admin scale per `--levels` entry, plus a planned sub-level and a 10 km grid), `pyproject.toml`, `README.md`, `CLAUDE.md`, `docs/python-package.md`, `raw/README.md` and a stub `tests/test_project.py`
- creates an empty `metadata/index.json` and installs the GADM geography builder as `build/geo.py`

Options: `--name`, `--short-name` and `--website` (defaults: "GeoDevelopment Observatory of <country>", "GDO-<country>", and the repository's GitHub Pages URL). Run `python scripts/new_project.py --help` for the full list.

**2. Add the boundaries.** Download the country from [GADM 4.1](https://gadm.org/download_country.html) at the finest level in `--levels` (e.g. level 2, GeoJSON). Save it unedited as `raw/boundaries/gadm41_<ISO3>_<n>.json` (the file name `build/geo.py` expects; change `GADM_FILE` there if needed).

**3. Build and check the geography:**

```bash
cd ../geo4laos
git init && uv sync
uv run geo4laos build && uv run geo4laos validate && uv run pytest
```

This creates `geo/units.csv`, `geo/boundaries/{country,province,district}.*` and the crosswalks. With no dataset yet, the dataset tests are skipped.

**4. Add datasets**, one at a time, following [`CONTRIBUTING_DATA.md`](CONTRIBUTING_DATA.md): `raw/<dataset>/`, then `metadata/<dataset>.datapackage.json`, a builder, `build`, `validate`.

**5. Publish:**
- Push the repository to GitHub. The package reads data from the `repository` in `project.yaml`, so remote loading works after the first push.
- Release the package on PyPI with [`docs/publishing.md`](docs/publishing.md).

**6. Optional: a website.** Copy `index.html`, `404.html`, `robots.txt`, `sitemap.xml`, `site.webmanifest` and `.nojekyll` from geo4cambodia. Replace the `CONTENT_REGISTRY` entries, texts, images and the hero settings, and enable GitHub Pages on `main`.

## Adapting the design

| You want | Do this |
| --- | --- |
| Different scale names (e.g. `region`, `municipality`) | `--levels region,municipality`. Names are free; `<scale>_id` columns follow them |
| Three or more admin levels | `--levels province,district,commune` with a GADM level-3 file |
| More than 99 units under one parent | `digits: 3` for that scale in `geo/scales.yaml` (and `\d{3}` in its `id_pattern`) |
| Groupings (statistical regions, GDL regions) | A scale with `kind: grouping`, `children: <scale>`. Add its units and `<grouping>_id` on the child units in `build/geo.py`; see geo4cambodia's `build/geo.py` |
| Non-GADM boundaries (national statistics office) | Write `build/geo.py` yourself. Build `units` (`geo_id`, `scale`, `name`, `parent_id`, source keys) and `layers` (`{scale: GeoDataFrame}`), then call `publish_geo(units, layers)` |
| Grids or custom zones | Register them (`kind: grid` / `custom`, no parent) and publish their boundaries. Data move to and from them with `overlay()` |
| A country-fitted projection | Set `equal_area_crs` in `project.yaml` (default `EPSG:6933`, exact areas everywhere) |

## Keeping projects in sync

Improvements to the generic files should be made in geo4cambodia first, then copied to the other projects. Copy the files listed in the "Generic" column and replace `geo4cambodia` with the project's package name. Because generic code reads everything from `project.yaml`, it can be copied without other edits. `tests/test_core.py` checks that it still works with each project's data.
