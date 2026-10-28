# Code

Data-preparation code for the observatory.

- **Building and validating the published data:** the `geo4bolivia` package in [`../src/geo4bolivia/`](../src/geo4bolivia/). Builders in [`../src/geo4bolivia/build/`](../src/geo4bolivia/build/) turn the originals in [`../raw/`](../raw/) into `data/`, `geo/` and `docs/datasets/`. Run `uv run geo4bolivia build && uv run geo4bolivia validate`. See [`../CONTRIBUTING_DATA.md`](../CONTRIBUTING_DATA.md) to add a dataset.
- **Matching DS4Bolivia to GADM:** [`../scripts/match_municipalities.py`](../scripts/match_municipalities.py) writes `raw/lookups/municipalities339_gadm.csv`.
- **Upstream preparation (DS4Bolivia):** the first datasets were prepared in [DS4Bolivia's `code/`](https://github.com/quarcs-lab/ds4bolivia/tree/master/code): Stata do-files that clean the SDG Atlas, night-time lights and population series, and Earth Engine scripts that aggregate the satellite embeddings to municipalities (`aggregate-satellite-embedings-to-adm.js`, `aggregate-satellite-embedings-to-adm-pop-weighted1.js`).
- **Earth Engine apps:** see [`../apps`](../apps/).
- **Analysis notebooks:** see [`../notebooks`](../notebooks/).
