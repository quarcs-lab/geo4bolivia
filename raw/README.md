# raw: original inputs

The untouched originals behind every published file. Never edit them: `uv run geo4bolivia build` regenerates `geo/`, `data/` and `docs/datasets/` from them, and any correction belongs in a builder in `src/geo4bolivia/build/`.

| Path | Source | Used by |
| --- | --- | --- |
| `boundaries/gadm41_BOL_3.json` | GADM 4.1, level 3 (https://gadm.org/download_country.html) | `build/geo.py` |
