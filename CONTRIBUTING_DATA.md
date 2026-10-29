# Adding data

Every dataset is a **panel**: one row per spatial unit (`geo_id`) and `year`, with one column per variable. Datasets live by spatial scale in `data/<scale>/<dataset>.csv` (+ `.parquet`), are described by a Frictionless datapackage in `metadata/`, and are regenerated from untouched originals in `raw/` by `uv run geo4bolivia build`. How the pieces fit together is explained in [`docs/data-infrastructure.md`](docs/data-infrastructure.md).

> To build an indicator for your own analysis (in Colab, without contributing it), you need none of this. Use `geo.link()`, `geo.zonal()`, `geo.combine()` and `geo.save()`, described in [section 6 of the guide](docs/data-infrastructure.md#6-building-your-own-indicators-with-the-package).

## Add a dataset at an existing scale

1. **Put the originals in `raw/<dataset>/`** and list them in `raw/README.md`. Never edit them. If something must be fixed, fix it in the builder, so the fix is documented and reproducible.
2. **Describe it in `metadata/<dataset>.datapackage.json`.** Copy an existing package (e.g. `metadata/pop.datapackage.json`), or the one `geo.save()` writes, and edit:
   - `name`, `title`, `description`, `geo:categories`, `geo:citation`, `geo:notes`, `geo:updated`
   - `licenses`: the license of the published files. CC BY 4.0 (`LICENSE-DATA`), unless a source requires otherwise
   - `sources`: one entry per source with its full citation (`title`, `path`) and `geo:role` (`original` or `intermediary`). Add `geo:creator`, `geo:homepage`, `geo:license` (`{name, title, path}`, the source's own license) and `geo:attribution` (the credit sentence it asks for)
   - `geo:map`: the headline map of the website, `{"variable": ..., "year": ...}` (add `"classify": "log"` for very skewed variables)
   - one resource per scale with:
     - `path`: the public URL, `https://raw.githubusercontent.com/<repository>/main/<geo:path>`
     - `geo:scale` and `geo:period` (`[first, last]` year)
     - `geo:path` and `geo:parquet`
   - `schema.fields`, in output column order:
     - `geo_id`, with role `id` and the scale's ID pattern
     - `year`, with role `time`
     - optionally the original key, with role `source_key` and `geo:units_column` naming the matching column of `geo/units.csv`
     - every field, keys included, with a `title` (a readable label for plots) and a `description` that says how it was built (definition, unit, source, year)
     - the variables, also with `geo:unit`, `geo:source` and `geo:aggregation`
     - for a variable observed in one year only, `geo:year` (see `metadata/sdg.datapackage.json`)

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
5. **Optional: add it to the website.** The `create-indicator-website` skill (`.claude/skills/`) does this end to end. By hand:
   - render the headline map and the card with `uv run python scripts/indicator_map.py <dataset>`
   - add an `indicator` entry to `CONTENT_REGISTRY` in `site/src/content.js` (copy an existing one)
   - preview it with `npm run --prefix site preview`

   The page reads the variables, sources and licenses from the metadata; the build writes its JSON-LD `Dataset` (without download URLs), its interactive-map data and its search entry.

### Aggregation rules (`geo:aggregation`)

| Rule | Use for | Example |
| --- | --- | --- |
| `sum` | counts and totals that add up across units | population, GDP, zonal sums of lights |
| `weighted_mean:<field>` | rates and averages, weighted by another field of the dataset | a poverty rate weighted by a `pop` field |
| `mean`, `min`, `max` | unweighted summaries (use with care) | — |
| `none` | values that cannot be aggregated without extra data | logs, HP trends, per-capita values without population |

`geo.aggregate()` and `geo.combine()` use these rules to move data up the hierarchy. `aggregate()` raises an error for `none` variables requested explicitly and otherwise leaves them out with a warning; `combine()` drops them with a warning. An explicit rule (`rules=`) keeps them.

## Add a new spatial scale

Scales are registered in [`geo/scales.yaml`](geo/scales.yaml). `municipality_ine` and `grid10k` are already reserved (`status: planned`).

- **Administrative scales** nest by prefix: `BO-04-17-04` lies in province `BO-04-17`.
  1. Put the boundaries in `raw/boundaries/`.
  2. In `src/geo4bolivia/build/geo.py`, add their units (`geo_id`, `scale`, `name`, `parent_id`) and their layer. `build/gadm.py` (`from_gadm`) does this for any GADM file.
  3. Set `status: active`. `publish_geo()` then adds the `<scale>_id` column and the crosswalks to every coarser scale.
- **Groupings** (unions of whole units of another scale, e.g. statistical regions made of whole departments) set `children:` to the scale they group. They then nest exactly and work with `geo.aggregate()`.
- **Grids, custom zones and historical boundaries** do not nest. Give them an `id_pattern` such as `^BO-G10K-r\d{3}c\d{3}$` and boundaries in `geo/boundaries/<scale>.parquet`. Use `geo.overlay()` / `geo.overlay_weights()` to move data onto or off them with area weights.

### Add a municipality map of another vintage

Bolivia keeps creating municipalities, so a new dataset may come on a map with more units than GADM's 339 (e.g. the current INE map). Never relabel the `municipality` scale: data published on it would silently move to different units. Add the map as its own scale instead. `municipality_ine` is reserved for the INE map, with IDs `BO-INE-DDPPMM` built from the 6-digit INE codes.

1. **Boundaries.** Put the official map in `raw/boundaries/` unedited, with its INE code per polygon.
2. **Register it.** Set `status: active` for `municipality_ine` in `geo/scales.yaml` (or add a scale with its own prefix and name, e.g. `municipality2024` with `^BO-M24-\d{6}$`). Keep `parent: null` unless every new municipality lies at least 99.5% inside one GADM province; then set `parent: province`, and `validate` checks it.
3. **Units and layer.** In `build/geo.py`, add its units (`geo_id`, `scale`, `name`, `ine_code`, and `parent_id` if it nests) and its layer to `publish_geo(units, layers)`.
4. **Links to the 339-unit map.** For a non-nested scale, `geo.overlay_weights("municipality", new_map, id_col="geo_id")` gives the area shares that move data between the maps with `geo.overlay()`. Where new municipalities were only carved out of old ones, publish a hand-checked lookup in `raw/lookups/` (old `geo_id` → new `geo_id`, with the population or area share) so the split is documented.
5. **Datasets on the new map** get a resource with `geo:scale: municipality_ine` and geo IDs matching its pattern. The same dataset can have resources on both maps.

After any change: `uv run geo4bolivia build && uv run geo4bolivia validate && uv run pytest`.
