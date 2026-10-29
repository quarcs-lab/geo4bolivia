# The CONTENT_REGISTRY entry

Copy an existing indicator entry in `site/src/content.js` (search for `type: 'indicator'`) and edit it.
Variables, sources, license and references come from the metadata; do not repeat them here.

```js
{
  id: 'municipalities339-ntl', type: 'indicator', section: 'indicators',
  title: 'Night-time lights per capita',
  scope: '339 municipalities · 2012–2020',                  // shown above the title
  summary: 'One sentence for the card and the header.',
  description: 'The About paragraph: what, where, when, how, why, caveats.',
  geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'Annual',
  key: 'geo_id', idExample: 'XX-01-02-03',                   // a real geo_id of the scale
  categories: ['Economy'], tags: ['night-time lights', 'VIIRS'],
  image: 'images/indicators/ntl.webp',                       // the 16:9 card (indicator_map.py)
  imageAlt: 'Map of ... in three natural-break classes: high in ..., low in ...',
  map: 'images/indicators/ntl-map.webp',                     // the page's map
  mapAlt: '<imageAlt>. Legend: High a to b (n units), Middle ..., Low ..., no data k.',
  date: '2026-10-29', pinned: false,
  dataset: 'ntl',                                            // or datasets: ['emb', 'embpw']
  notice: 'Optional warning shown under the description.',
  code: { python: `...`, pandas: `...` },
  examples: [                                                // optional: short recipes under the code tabs
    { title: 'Compute the index from its indicators', text: 'One sentence on what it shows.', code: `${PYTHON_SETUP}\n...` },
  ],
},
```

Do not add `files`, `folder`, `docs`, `variables`, `references`, `citation`, `related` or
download links: the page no longer uses them.

## Code snippets (rules from CLAUDE.md)

- **Two tabs.** `python` (the package) starts with `${PYTHON_SETUP}`, which holds the
  `!pip install -q <pkg>`, the import and `import plotly.express as px`. `pandas` (plain URLs)
  reads `BASE = "${RAW_URL}"` and needs no install line.
- **Runs in Colab as is.** Use `"<pkg>[raster]"` when it calls `geo.zonal()`; add `expdpy` or
  `geometrics` to the install line when used.
- **A Plotly Express figure** with the simplest syntax: data, `x`/`y`/`color`, and only
  `hover_name`, `labels={...}` and `title`. Use the variable's **label** in `labels`.
  - Maps: `px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index, color=..., hover_name="name", center=..., zoom=...)` with a continuous scale.
  - Use long tables (`groupby(..., as_index=False)`, names via `.map()`).
  - Add `.show()` to every figure except the last expression.
- **Lines of about 84 characters at most.**
- **Examples** (optional): 2–4 recipes of 8–20 lines that show how to use the dataset's
  variables (e.g. rebuild a composite index from its components, rank departments, relate two
  variables). Each starts with `${PYTHON_SETUP}` and ends with one Plotly Express figure.
- `CodeTabs` adds the "Open in Colab" button.

## JSON-LD

`site/build.mjs` writes the page's `Dataset` from the entry and the metadata: `name`,
`description`, `url` (the page), `license`, `temporalCoverage` (from `period`),
`spatialCoverage`, `keywords` (`tags`), `variableMeasured` (field titles) and `creator`.
**No `distribution`** (no download URLs). Check it in `_site/indicators/<id>/index.html`.

## QA checklist

- [ ] The page shows, in order: map, About (with the original source), Explore the map,
      Variables (every column), code, License, Cite this dataset, References, and the
      At-a-glance sidebar.
- [ ] No download links, and no links to `data/`, `geo/` or the GitHub folders.
- [ ] The metadata loads (no "could not be loaded" notice) and the console has no errors.
- [ ] No horizontal scroll at 390 px width.
- [ ] The card image appears in the Indicators section, and the Database architecture
      table lists the dataset.
- [ ] `build`, `validate` and `pytest` pass.
