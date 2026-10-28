# Adding data

Every dataset is a **panel**: one row per spatial unit (`geo_id`) and `year`, with one column per variable. Datasets live by spatial scale in `data/<scale>/<dataset>.csv` (+ `.parquet`), are described by a Frictionless datapackage in `metadata/`, and are regenerated from untouched originals in `raw/` by `uv run geo4bolivia build`. How the pieces fit together is explained in [`docs/data-infrastructure.md`](docs/data-infrastructure.md).

> To build an indicator for your own analysis (in Colab, without contributing it), you need none of this. Use `geo.link()`, `geo.zonal()`, `geo.combine()` and `geo.save()`, described in [section 6 of the guide](docs/data-infrastructure.md#6-building-your-own-indicators-with-the-package).

## Add a dataset at an existing scale

1. **Put the originals in `raw/<dataset>/`** and list them in `raw/README.md`. Never edit them. If something must be fixed, fix it in the builder, so the fix is documented and reproducible.
2. **Describe it in `metadata/<dataset>.datapackage.json`.** Copy an existing package (e.g. `metadata/env.datapackage.json`), or the one `geo.save()` writes, and edit:
   - `name`, `title`, `description`, `licenses`, `sources`, `geo:categories`, `geo:citation`, `geo:notes`
   - one resource per scale with:
     - `path`: the public URL, `https://raw.githubusercontent.com/<repository>/main/<geo:path>`
     - `geo:scale` and `geo:period` (`[first, last]` year)
     - `geo:path` and `geo:parquet`
   - `schema.fields`, in output column order:
     - `geo_id`, with role `id` and the scale's ID pattern
     - `year`, with role `time`
     - optionally the original key, with role `source_key` and `geo:units_column` naming the matching column of `geo/units.csv`
     - the variables, each with `description`, `geo:unit`, `geo:source` and `geo:aggregation`

   Then add the dataset id to `metadata/index.json`.
3. **Write a builder.** Copy `src/geo4bolivia/build/_template.py` to `src/geo4bolivia/build/<dataset>.py`. It reads the raw file, maps its key to `geo_id`, and calls `publish()` and `write_docs()`:
   - map a source code with `ids_from_units(scale, "<units column>")`
   - map names with `geo4bolivia.link(df, scale, on=...)`

   Register the builder in `DATASETS` in `src/geo4bolivia/build/__init__.py`.
4. **Build and check:**
   ```bash
   uv run geo4bolivia build <dataset>
   uv run geo4bolivia validate <dataset>
   uv run pytest
   ```
   `publish()` writes the columns in schema order with schema types. `write_docs()` generates `docs/datasets/<dataset>.md`. `validate` reports any mismatch between the data, the metadata and `geo/`.
5. **Optional: add it to the website.** Add an `indicator` entry to `CONTENT_REGISTRY` in `index.html` (copy an existing one), a `Dataset` entry to the JSON-LD block, and an image in `images/indicators/`.

### Aggregation rules (`geo:aggregation`)

| Rule | Use for | Example |
| --- | --- | --- |
| `sum` | counts and totals that add up across units | population, GDP, zonal sums of lights |
| `weighted_mean:<field>` | rates and averages, weighted by another field of the dataset | HDI and GNI per capita, weighted by `POP` |
| `mean`, `min`, `max` | unweighted summaries (use with care) | — |
| `none` | values that cannot be aggregated without extra data | logs, HP trends, per-capita values without population |

`geo.aggregate()` and `geo.combine()` use these rules to move data up the hierarchy. `aggregate()` raises an error for `none` variables requested explicitly and otherwise leaves them out with a warning; `combine()` drops them with a warning. An explicit rule (`rules=`) keeps them.

## Add a new spatial scale

Scales are registered in [`geo/scales.yaml`](geo/scales.yaml). `commune` and `grid10k` are already reserved (`status: planned`).

- **Administrative scales** (e.g. communes, GADM level 3) nest by prefix: `KH-16-01-01` lies in district `KH-16-01`.
  1. Put the boundaries in `raw/boundaries/`.
  2. In `src/geo4bolivia/build/geo.py`, add their units (`geo_id`, `scale`, `name`, `parent_id`) and their layer. `build/gadm.py` (`from_gadm`) does this for any GADM file.
  3. Set `status: active`. `publish_geo()` then adds the `commune_id` column and the crosswalks to every coarser scale.
- **Groupings** (unions of whole units of another scale, like the Global Data Lab regions) set `children:` to the scale they group. They then nest exactly and work with `geo.aggregate()`.
- **Grids, custom zones and historical boundaries** do not nest. Give them an `id_pattern` such as `^KH-G10K-r\d{3}c\d{3}$` and boundaries in `geo/boundaries/<scale>.parquet`. Use `geo.overlay()` / `geo.overlay_weights()` to move data onto or off them with area weights.

After any change: `uv run geo4bolivia build && uv run geo4bolivia validate && uv run pytest`.
