# $package

**Subnational development data for $country, ready to analyse, at every spatial scale.**

`$package` is the Python package of the [$name]($website). It loads the observatory's indicators as tidy panels with boundaries for every scale. It also lets you build your own indicators: link your tables to the same unit IDs, summarise rasters over units, move data across scales and combine datasets. It works out of the box in Google Colab.

```python
!pip install -q $package          # every example runs as-is in Google Colab
import $package as geo

geo.datasets()                    # what is available, at which scale and years
gdf = geo.load("<dataset>", geometry=True)
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/notebooks/empty.ipynb)

| Task | Functions |
| --- | --- |
| Load panels, names and boundaries | `datasets`, `dictionary`, `load`, `units`, `boundaries`, `crosswalk` |
| Link your own tables by unit names or codes | `link`, `check` |
| Extract indicators from rasters | `zonal` |
| Move data across scales | `aggregate`, `overlay`, `overlay_weights` |
| Combine and save datasets | `combine`, `save` |
| Analyse with [expdpy](https://cmg777.github.io/expdpy/) (panel econometrics) and [geometrics](https://quarcs-lab.github.io/geometrics/) (spatial analysis) | `for_expdpy`, `for_geometrics` |

Without the package, every file is a plain URL: `https://raw.githubusercontent.com/$repository/main/<path>`.

Documentation: [how the data infrastructure works](https://github.com/$repository/blob/main/docs/data-infrastructure.md).
