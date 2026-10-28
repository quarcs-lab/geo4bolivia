# raw: original inputs

The untouched originals behind every published file. Never edit them: `uv run $package build` regenerates `geo/`, `data/` and `docs/datasets/` from them, and any correction belongs in a builder in `src/$package/build/`.

| Path | Source | Used by |
| --- | --- | --- |
| `boundaries/gadm41_${iso3}_${n_levels}.json` | GADM 4.1, level $n_levels (https://gadm.org/download_country.html) | `build/geo.py` |
