# Researching licenses

The observatory publishes its derived data under **CC BY 4.0, unless a source requires
otherwise** (`LICENSE-DATA`). Before a dataset is published, every source in its chain needs a
verified license: the producer, any extraction tool, and the boundaries it was computed on.

## Where to look, in order

1. **The provider's own terms page.** For example, EOG's "Data Access and Licensing" PDF, WorldPop's DOI pages, or
   a portal's "Terms of use".
2. **The DOI landing page** of the dataset: Zenodo, Dryad, Figshare, a DataCite record.
3. **The Google Earth Engine catalog page** ("Terms of Use" tab) if the data came through GEE.
4. **The paper's data availability statement**, and the copyright page of a report or PDF.
5. **The files themselves**: a cover sheet, a README, a LICENSE file in the repository.

Quote the statement verbatim and keep its URL. "Free to download" or "available to
researchers" is not a license. Without a grant, default copyright applies, so ask the user
whether they have permission.

## Common cases

| License | Compatible with our CC BY 4.0? | What to do |
| --- | --- | --- |
| CC0, public domain, PDDL | Yes | Credit anyway (good practice) |
| CC BY 4.0, ODC-BY, OGL, Etalab | Yes | Copy the provider's credit sentence into `geo:attribution` |
| CC BY 3.0 or 2.0 | Yes, with attribution | Same as above |
| CC BY-SA, ODbL | No (share-alike) | Publish the dataset under the source's license instead; tell the user |
| CC BY-NC, CC BY-NC-SA, "non-commercial use" | No | The source's terms prevail; tell the user, and ask before publishing |
| "No redistribution without permission" (e.g. GADM) | No | Do not publish the files without written permission; tell the user |
| No license stated | Unclear | Ask the user. With documented permission, record it in `geo:license.title` |
| Software licenses (MIT, Apache) on data | Usually yes | They permit reuse with notice; the copyright holder can relicense |

Remember the **intermediaries**. Tools such as AidData GeoQuery (ODC-BY 1.0) and the
polygons the statistics were computed on (geoBoundaries CC BY 4.0; GADM non-commercial,
no redistribution) carry terms too.

## The License section

The page composes it from the metadata, so all that's needed is accurate fields:

- **This dataset:** the package's `licenses[0]`, with the CC BY 4.0 summary: share and adapt
  for any purpose, give credit, link to the license, indicate changes.
- **Created by:** the `geo:creator` of the `original` sources.
- **Curated by:** the observatory.
- **Last updated:** `geo:updated`.
- **Licenses of the sources:** each source's `geo:license` link and its `geo:attribution`
  ("Required credit").
- **Boundary note:** a fixed sentence in `site/src/app.jsx` (`BOUNDARY_NOTE`): every boundary
  (maps, `geometry=True`, `geo/boundaries/`) is geoBoundaries' public-domain polygons from
  GeoBolivia; check the license of each country's geoBoundaries file when porting.

Show the user the table of verdicts before writing, and say plainly when something blocks
publication.
