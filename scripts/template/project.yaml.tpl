# Project identity. See TEMPLATE.md and docs/data-infrastructure.md.
# Everything generic in the package reads its settings from here.

name: $name
short_name: $short_name

# Python package (import name), CLI command and prefix of the environment
# variables (${package_upper}_DATA_DIR, ${package_upper}_BASE_URL, ${package_upper}_REF).
package: $package

# GitHub repository holding the published files, and the git ref an installed
# package reads from by default (a release tag freezes the data).
repository: $repository
default_ref: main

website: $website

country:
  name: $country
  iso2: $iso2     # prefix of every geo_id
  iso3: $iso3    # GADM country code (GID_0)

# Equal-area projection for areas, crosswalk weights and overlays.
# EPSG:6933 gives exact areas anywhere; a country-fitted Albers also keeps shapes.
equal_area_crs: "EPSG:6933"

# Generated table listing every variable of every dataset.
catalog: definitions.csv
