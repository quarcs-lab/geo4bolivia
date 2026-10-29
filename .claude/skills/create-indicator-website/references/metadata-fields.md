# Metadata the indicator page needs

`metadata/<dataset>.datapackage.json` is a Frictionless Data Package with `geo:` extensions
(the full list is in `src/<pkg>/metadata.py` and `docs/data-infrastructure.md`). The page
reads the properties below at runtime; the validator enforces the starred ones.

## Package

| Property | Use on the page |
| --- | --- |
| `name`*, `title`*, `description`* | Heading of the variable table when a page shows several datasets |
| `licenses`* | License section: the license of the published files. Usually CC BY 4.0, or the source's license if that is stricter. Each entry has a `name`* (SPDX id or `LicenseRef-...`), `title` and `path` (URL) |
| `sources`* | About (the `original` ones), License and References. See below |
| `geo:map` | Headline map: `{"variable": "...", "year": 2020}`, optionally `"scale"` and `"classify": "log"` |
| `geo:updated` | "Last updated" in the License section (ISO date) |
| `geo:citation`, `geo:notes`, `geo:notebooks` | Generated docs only |

## Source

```json
{
  "title": "Full citation, APA style (the paper if there is one, else the dataset).",
  "path": "https://doi.org/...",
  "geo:role": "original",
  "geo:creator": "Organisation or authors who produced the data",
  "geo:homepage": "https://provider.example/data",
  "geo:license": {"name": "CC-BY-4.0", "title": "Creative Commons Attribution 4.0 International License",
                  "path": "URL of the page that states the license"},
  "geo:attribution": "The credit sentence the provider asks for, verbatim"
}
```

- **Roles.**
  - `original`: whoever produced the measurements.
  - `intermediary`: tools, repositories and boundary files the data passed through. These
    appear under References and License, not in About.
- **No open license.** Use a `LicenseRef-...` name and state the facts in the `title`, e.g.
  "No open license stated (© Publisher); used and shared with the permission of ...".

## Field (every column, keys included)

| Property | Use |
| --- | --- |
| `name`* | Variable name |
| `title`* | **Label**: a readable plot label (sentence case, spaces, no codes or year, ≤ 45 characters) |
| `description`* | **How it was built**: definition, unit, original source, reference year or period |
| `geo:unit`, `geo:aggregation`, `geo:source`, `geo:role`, `geo:year` | Package and docs (`geo:source` also goes in the map's data credit) |

`geo.dictionary(dataset)` returns `variable, label, description, unit, role, aggregation, source`.
