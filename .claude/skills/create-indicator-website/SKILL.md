---
name: create-indicator-website
description: Turn a new dataset plus its information (source, citation, license, variables) into a finished indicator page on the observatory's website, end to end — raw files, builder, metadata with a full variable dictionary and licenses, a static Fisher–Jenks headline map on a keyless basemap, the CONTENT_REGISTRY entry with code snippets, validation, commit and push. Use when the user hands over data for a new indicator ("add this dataset", "create the indicator page for ...", "/create-indicator-website"), or asks to rebuild an existing indicator page with the same workflow.
---

# Create an indicator page

One run takes a dataset from `raw/` to a published page at `<website>indicators/<id>/`. The project is
a geo4<country> repository: read `project.yaml` first (name, `package`, repository, country,
`site` map settings) and `CLAUDE.md`; never hard-code the country, the repository or the package.
Below, `<pkg>` is the `package` in `project.yaml` (the CLI and the import name).

The page is drawn by `IndicatorDetail` in `site/src/app.jsx` and has, in order: title and summary,
the headline map, **About the dataset** (description, notice, original source with its
citation), **Explore the map** (interactive: any variable and year, from the published data),
**Variables** (name, label, description of every column), **Use it in your code**
(package and plain-URL tabs), **License**, **Cite this dataset**, **References**, plus an
*At a glance* sidebar. `site/build.mjs` pre-renders it at `indicators/<id>/` with its own
preview image and JSON-LD, and adds it to the sitemap and the search.
Variables, original source, license, citations and references are read at runtime from
`metadata/<dataset>.datapackage.json`, so the metadata is the single source of truth.
There is no download section, and the page links to no data files.

## Hard rules

- **Never guess** a source, a citation, a license or how a variable was built. Research
  it, cite where it came from, flag what you could not confirm, and ask.
- **Ask before writing** the variable dictionary and the license: show the drafts and
  wait for approval (step 4 and step 5).
- `raw/` files are never edited; fixes go in the builder.
- Keep generic files generic (`TEMPLATE.md` lists them).
- Finish with `build`, `validate` and `pytest` all green before committing.

## Workflow

### 1. Preflight

```bash
git fetch && git status -sb        # on the default branch, up to date, clean
```

If the tree is dirty or behind, stop and ask (other sessions may be working in parallel).

### 2. Intake

Look for a brief at `raw/<dataset>/indicator.yaml` (template:
[references/indicator.yaml](references/indicator.yaml)). Interview the user for anything
missing. Ask everything in a single round, with `AskUserQuestion` where options exist:

- dataset id, scale (an active scale in `geo/scales.yaml`), source key to link units
- title, one-line summary, description, categories, tags
- original source(s): creator, citation (paper and/or dataset), DOI or URL, data homepage
- any intermediary (e.g. a repository the data passed through)
- license hints, or the user's permission arrangements
- headline map: variable and year (propose the main variable at its latest year)
- related notebooks or apps, if any

### 3. Data

Follow `CONTRIBUTING_DATA.md`:

1. `raw/<dataset>/`
2. `metadata/<dataset>.datapackage.json` and `metadata/index.json`
3. a builder from `src/<pkg>/build/_template.py`, registered in `DATASETS`

Metadata properties are listed in [references/metadata-fields.md](references/metadata-fields.md).

### 4. Variable dictionary (approval required)

For **every** column, keys included, draft:

- `title`: the label. A human-readable plot label in sentence case, with spaces, no codes and no year, and a short unit in parentheses if useful (≤ 45 characters).
- `description`: how the variable was **constructed**. Give the definition (numerator and denominator, or the method), the unit, the original data source and the reference year or period.

Work from the source's methodology (paper, technical annex, catalog page, the provider's
code). For many variables, delegate the research to a subagent that returns a CSV
`name,label,description,confidence,evidence`.

Write all drafts to a review file in the scratchpad: a Markdown table, ⚠ on the rows that
are not high confidence, and the evidence for them. Ask the user to approve it or send edits.
Write the dictionary into the metadata only after approval.

### 5. License (approval required)

Research each source's license and the credit it asks for, following
[references/license-guide.md](references/license-guide.md). Show the user a table with:

- source
- license, with the URL of the statement
- required credit text
- whether it is compatible with the observatory's CC BY 4.0

Flag blockers (no license, non-commercial, share-alike, no redistribution).
After the user confirms, set:

- the package's `licenses`: CC BY 4.0, or the source's license if that is stricter
- for each source: `geo:license`, `geo:attribution`, `geo:creator`, `geo:role`, `geo:homepage`
- `geo:updated`

### 6. Build and check

```bash
uv run <pkg> build <dataset>
uv run <pkg> validate <dataset>
uv run pytest
```

The validator checks:
- every field has a `title` and a `description`
- every license has a `name`
- `geo:map` names a variable that has data in its year

### 7. Headline map

Set `geo:map` (`{"variable", "year"}`) in the datapackage, then:

```bash
uv run python scripts/indicator_map.py <dataset>
```

It draws three Fisher–Jenks natural-break classes (Low, Middle, High), plus "No data", over a
keyless basemap whose labels sit above the units, and writes two images:
`images/indicators/<dataset>-map.webp` (the page, 1600×1000) and `images/indicators/<dataset>.webp`
(the card, 1600×900).

- **Skewed variable:** if one class swallows almost every unit (e.g. densities), show the
  user both versions and ask. `--log`, or `"classify": "log"` in `geo:map`, finds the breaks
  on the log scale; the legend stays in the original units.
- **Check:** open both images (Read) and check the title (the label and year), the legend
  ranges and counts, the No data class, readable labels and the attribution.
- **Alt text:** the script prints the class counts and the top units; use them to write the
  `imageAlt` and `mapAlt` (the pattern and the legend ranges).

### 8. Page entry

Add the `CONTENT_REGISTRY` entry in `site/src/content.js`; the fields and the snippet rules
are in [references/page-entry.md](references/page-entry.md). The build writes the JSON-LD
`Dataset` and the map data. Do not add download links or links to the data folders. Then preview:

```bash
npm ci --prefix site                # once
npm run --prefix site preview       # open http://localhost:8765/indicators/<id>/
```

Check in the browser (claude-in-chrome):
- the section order
- every variable row
- the interactive map (every variable and year draws; the legend and highest/lowest lists make sense)
- the search finds the page and its variables
- the License text
- no console errors
- no horizontal scroll at 390 px (measure inside a 390 px iframe if the window cannot be resized)
- the card on the Indicators section

### 9. Ship

Update `CLAUDE.md`'s dataset table and anything else that lists datasets, run `build`,
`validate` and `pytest` once more, then commit everything the build regenerated (data, docs,
catalog, images) with the attribution lines, and push to the default branch. If the user
asked for a branch and PR instead, do that.

Report back:
- the page URL (`<website>indicators/<id>/`)
- the license verdicts and any blockers
- the ⚠ rows the user approved
- anything left to do
