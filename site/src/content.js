// Site content: constants, every indicator, tool, insight and event, the team and the citation.
// Plain data (no JSX): the app renders it and site/build.mjs pre-renders a page for every item.
// ====================================================================
// Site constants
// ====================================================================
export const SITE_URL = 'https://quarcs-lab.github.io/geo4bolivia/';
export const REPO_URL = 'https://github.com/quarcs-lab/geo4bolivia';
export const RAW_URL = 'https://raw.githubusercontent.com/quarcs-lab/geo4bolivia/main/';
export const COLAB_URL = 'https://colab.research.google.com/github/quarcs-lab/geo4bolivia/blob/main/notebooks/';
export const COLAB_EMPTY = 'https://colab.research.google.com/notebooks/empty.ipynb';
export const DEFAULT_TITLE = 'GeoDevelopment Observatory of Bolivia | GDO-Bolivia';
export const SITE_NAME = 'GeoDevelopment Observatory of Bolivia';
export const SHORT_NAME = 'GDO-Bolivia';
export const SITE_DESCRIPTION = 'GDO-Bolivia is a public-access platform of open subnational indicators, notebooks, web apps, and research insights for monitoring sustainable regional development in Bolivia with satellite data and AI.';
// Authors of the observatory's own citations (the site's, and each dataset's on its page)
export const CITE_AUTHORS = { apa: 'Mendez, C.', bibtex: 'Mendez, Carlos' };
// Center and zoom of the interactive indicator maps
export const MAP_VIEW = { center: [-16.3, -64.6], zoom: 5 };

// ====================================================================
// Content registry: every indicator, tool, insight and event
// ====================================================================
// Every code box runs as-is in Google Colab: the first line installs what Colab lacks.
export const PYTHON_SETUP = `!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px`;

export const CONTENT_REGISTRY = [
  // ---------------------------------------------------------------- Indicators
  {
    id: 'municipalities339-sdg', type: 'indicator', section: 'indicators',
    title: 'SDG indicators: the Municipal Atlas of the SDGs',
    scope: '339 municipalities · 64 indicators · 2010–2020',
    summary: 'Sixty-four municipal indicators of poverty, health, education, gender, water, energy, work, infrastructure and institutions, each stored at the year it was measured.',
    description: 'The indicators behind the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities: multidimensional poverty and unsatisfied basic needs, child malnutrition and mortality, school dropout and literacy, gender parity, water, sanitation and electricity coverage, CO₂ emissions, labour participation, connectivity, inequality, deforestation, protected areas, homicides and municipal finance. The Atlas gathers them from different sources and years (poverty from the 2012 census, health from 2016, education from 2017...), so each indicator is stored at its own reference year and the panel is sparse: load an indicator with its year. Indicators averaged over a period are stored at its midpoint, rounded down. The Atlas’s composite indices are not included.',
    geography: 'Municipality', units: 339, period: '2010–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social', 'Economy', 'Environment', 'Institutions'], tags: ['SDGs', 'poverty', 'municipalities', 'census'],
    image: 'images/indicators/sdg.webp',
    imageAlt: 'Map of the Multidimensional Poverty Index in 2012 across 339 Bolivian municipalities in three natural-break classes: high in Pando, northern La Paz and the Chuquisaca and Potosí valleys, low around Santa Cruz, the Chaco and the southern altiplano',
    map: 'images/indicators/sdg-map.webp',
    mapAlt: 'Map of the Multidimensional Poverty Index in 2012 across 339 Bolivian municipalities in three natural-break classes: high in Pando, northern La Paz and the Chuquisaca and Potosí valleys, low around Santa Cruz, the Chaco and the southern altiplano. Legend: High 0.283 to 0.520 (45 municipalities), Middle 0.150 to 0.283 (148), Low 0.007 to 0.150 (146).',
    date: '2026-10-28', pinned: true, dataset: 'sdg',
    notice: 'Each indicator has values only in its reference year: load one with its year, e.g. geo.load("sdg", variables="sdg1_2_mpi", years=2012). In DS4Bolivia the rows of three pairs of homonym municipalities (San Javier, El Puente, Santa Rosa) were attached to the wrong polygon of each pair; here every row is linked by INE code to its own municipality.',
    code: {
      python: `${PYTHON_SETUP}

# Multidimensional poverty in its census year, with municipal boundaries
gdf = geo.load("sdg", variables="sdg1_2_mpi", years=2012, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="sdg1_2_mpi", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"sdg1_2_mpi": "MPI"},
          title="Multidimensional poverty, 2012").show()

# Population-weighted poverty by department
dep = geo.aggregate(gdf, to="department", rules={"sdg1_2_mpi": "weighted_mean:pop"},
            weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("sdg1_2_mpi"), x="sdg1_2_mpi", y="department",
       labels={"sdg1_2_mpi": "MPI (population-weighted)"},
       title="Poverty by department, 2012").show()`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg.csv")    # geo_id, year, mun_id, 64 indicators
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

mpi = df.loc[df["year"] == 2012, ["geo_id", "sdg1_2_mpi"]]
gdf = municipalities.merge(mpi, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="sdg1_2_mpi", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"sdg1_2_mpi": "MPI"},
          title="Multidimensional poverty, 2012")`,
    },
  },
  {
    id: 'municipalities339-ntl', type: 'indicator', section: 'indicators',
    title: 'Night-time lights per capita',
    scope: '339 municipalities · 2012–2020',
    summary: 'Nine years of VIIRS night-time lights per person for every municipality, with a long-run trend: a satellite proxy for local economic activity.',
    description: 'Annual night-time lights per capita for Bolivia’s 339 municipalities from 2012 to 2020: the summed radiance of the Earth Observation Group’s annual VIIRS night-time lights (version 2, background masked) over each municipality, divided by its WorldPop population, in natural logs. A Hodrick–Prescott trend (λ = 400) of the same series separates the long-run path from year-to-year noise; it is complete for every municipality, while the raw log is missing where a municipality had no measurable light. Night-time lights track electrification and economic activity where official local statistics are scarce.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'Annual', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Economy'], tags: ['night-time lights', 'VIIRS', 'remote sensing', 'panel data'],
    image: 'images/indicators/ntl.webp',
    imageAlt: 'Map of log night-time lights per capita in 2020 across 339 Bolivian municipalities in three natural-break classes: highest across Santa Cruz, the Chaco and the southern altiplano, lowest in northern La Paz, parts of Pando and clusters in the Potosí and Chuquisaca valleys',
    map: 'images/indicators/ntl-map.webp',
    mapAlt: 'Map of log night-time lights per capita in 2020 across 339 Bolivian municipalities in three natural-break classes: highest across Santa Cruz, the Chaco and the southern altiplano, lowest in northern La Paz, parts of Pando and clusters in the Potosí and Chuquisaca valleys. Legend: High 14.5 to 17.9 (109 municipalities), Middle 13.0 to 14.5 (147), Low 10.5 to 13.0 (78), no data 5.',
    date: '2026-10-28', pinned: false, dataset: 'ntl',
    code: {
      python: `${PYTHON_SETUP}

df = geo.load("ntl")
df = df.merge(geo.units("municipality")[["geo_id", "department_id"]], on="geo_id")

# Long-run trend of lights per capita: mean by department
trend = df.groupby(["year", "department_id"], as_index=False)["ln_t400NTLpc"].mean()
names = geo.units("department").set_index("geo_id")["name"]
trend["department"] = trend["department_id"].map(names)
px.line(trend, x="year", y="ln_t400NTLpc", color="department",
labels={"ln_t400NTLpc": "Log lights per capita (trend)"},
title="Night-time lights by department")`,
      pandas: `import pandas as pd
import plotly.express as px

BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/ntl.csv")
units = pd.read_csv(BASE + "geo/units.csv")
df = df.merge(units[["geo_id", "department_id"]], on="geo_id")

# Long-run trend of lights per capita: mean by department
trend = df.groupby(["year", "department_id"], as_index=False)["ln_t400NTLpc"].mean()
trend["department"] = trend["department_id"].map(units.set_index("geo_id")["name"])
px.line(trend, x="year", y="ln_t400NTLpc", color="department",
labels={"ln_t400NTLpc": "Log lights per capita (trend)"},
title="Night-time lights by department")`,
    },
  },
  {
    id: 'municipalities339-pop', type: 'indicator', section: 'indicators',
    title: 'Population',
    scope: '339 municipalities · 2001–2020',
    summary: 'Two decades of gridded population estimates and population density for every municipality: the denominator for per-capita indicators and population-weighted averages.',
    description: 'Annual population estimates for Bolivia’s 339 municipalities from 2001 to 2020, computed by summing WorldPop’s 1 km gridded population over each municipality, and the population density (people per km²) of each municipality. Population sums up the hierarchy, so it gives provincial, departmental and national totals directly, and it is the weight for population-weighted averages of rates such as poverty. These are gridded estimates, not INE’s official projections.',
    geography: 'Municipality', units: 339, period: '2001–2020', frequency: 'Annual', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['population', 'WorldPop', 'demography', 'panel data'],
    image: 'images/indicators/pop.webp',
    imageAlt: 'Map of population density in 2020 across 339 Bolivian municipalities in three natural-break classes on a log scale: densest in the La Paz–El Alto, Cochabamba, Santa Cruz, Sucre and Tarija urban areas, intermediate across the altiplano and valleys, sparsest in the northern and eastern lowlands',
    map: 'images/indicators/pop-map.webp',
    mapAlt: 'Map of population density in 2020 across 339 Bolivian municipalities in three natural-break classes on a log scale: densest in the La Paz–El Alto, Cochabamba, Santa Cruz, Sucre and Tarija urban areas, intermediate across the altiplano and valleys, sparsest in the northern and eastern lowlands. Legend: High 42 to 2,860 people per km² (55 municipalities), Middle 4 to 42 (202), Low 0 to 4 (82).',
    date: '2026-10-28', pinned: false, dataset: 'pop',
    code: {
      python: `${PYTHON_SETUP}

pop = geo.load("pop")

# Totals by department, 2001-2020 (population sums up the hierarchy)
dep = geo.aggregate(pop, to="department", dataset="pop")
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.line(dep, x="year", y="pop", color="department",
labels={"pop": "Population"}, title="Population by department, 2001-2020")`,
      pandas: `import pandas as pd
import plotly.express as px

BASE = "${RAW_URL}"
pop = pd.read_csv(BASE + "data/municipality/pop.csv")
units = pd.read_csv(BASE + "geo/units.csv")
pop = pop.merge(units[["geo_id", "department_id"]], on="geo_id")

# Totals by department, 2001-2020
dep = pop.groupby(["year", "department_id"], as_index=False)["pop"].sum()
dep["department"] = dep["department_id"].map(units.set_index("geo_id")["name"])
px.line(dep, x="year", y="pop", color="department",
labels={"pop": "Population"}, title="Population by department, 2001-2020")`,
    },
  },
  {
    id: 'municipalities339-emb', type: 'indicator', section: 'indicators',
    title: 'Satellite embeddings',
    scope: '339 municipalities · 64 dimensions · 2017',
    summary: 'What every municipality looks like from space, compressed by a deep-learning model into 64 numbers: features for machine learning.',
    description: 'Sixty-four satellite embedding dimensions (A00–A63) for each of Bolivia’s 339 municipalities in 2017, averaged from the annual 10 m Google Satellite Embedding dataset (AlphaEarth Foundations). The model summarises Sentinel-2, Landsat and other imagery into abstract features that capture land cover, texture, roads and buildings. Two versions are published: `emb`, the area-weighted mean over each municipality, and `embpw`, weighted by population so that it describes where people live. The dimensions are not interpretable one by one; they are inputs to models, for example to predict poverty.',
    geography: 'Municipality', units: 339, period: '2017', frequency: 'One year', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Environment', 'Economy'], tags: ['satellite embeddings', 'AlphaEarth', 'machine learning', 'remote sensing'],
    image: 'images/indicators/emb.webp',
    imageAlt: 'Map of satellite embedding dimension A00 (area-weighted) in 2017 across 339 Bolivian municipalities in three natural-break classes: low across the altiplano and western valleys, middle across Beni and Pando, high across Santa Cruz and the Chaco',
    map: 'images/indicators/emb-map.webp',
    mapAlt: 'Map of satellite embedding dimension A00 (area-weighted) in 2017 across 339 Bolivian municipalities in three natural-break classes: low across the altiplano and western valleys, middle across Beni and Pando, high across Santa Cruz and the Chaco. Legend: High 0.046 to 0.164 (49 municipalities), Middle −0.055 to 0.046 (97), Low −0.165 to −0.055 (193).',
    date: '2026-10-28', pinned: false, dataset: 'emb', datasets: ['emb', 'embpw'],
    code: {
      python: `${PYTHON_SETUP}
from sklearn.decomposition import PCA

emb = geo.load("embpw")                           # or "emb", area-weighted
X = emb.filter(regex=r"^A\\d{2}$")                # 64 dimensions
emb["pc1"] = PCA(1).fit_transform(X)[:, 0]

# How the first component relates to multidimensional poverty (2012)
mpi = geo.load("sdg", variables="sdg1_2_mpi", years=2012)
names = geo.units("municipality")[["geo_id", "name"]]
df = emb[["geo_id", "pc1"]].merge(mpi, on="geo_id").merge(names, on="geo_id")
px.scatter(df, x="pc1", y="sdg1_2_mpi", hover_name="name", trendline="ols",
   labels={"pc1": "First principal component", "sdg1_2_mpi": "MPI, 2012"},
   title="Satellite embeddings and poverty")`,
      pandas: `import pandas as pd
import plotly.express as px

BASE = "${RAW_URL}"
emb = pd.read_csv(BASE + "data/municipality/embpw.csv")   # geo_id, year, asdf_id, A00-A63

# Distribution of each of the 64 dimensions across municipalities
px.box(emb.filter(regex=r"^A\\d{2}$"),
       labels={"variable": "Dimension", "value": "Value"},
       title="Satellite embeddings, 2017")`,
    },
  },

  // ---------------------------------------------------------------- Tools: packages
  {
    id: 'geo4bolivia-package', type: 'package', section: 'tools',
    title: 'geo4bolivia: load, link and build subnational data',
    scope: '!pip install -q geo4bolivia',
    summary: 'The observatory’s Python package. Load every indicator as a tidy panel with boundaries, link your own data to the same units, and build new indicators across municipalities, provinces and departments.',
    description: 'geo4bolivia is the data engine of the observatory. One line loads any dataset as a panel (one row per unit and year) with names and boundaries. Every spatial unit has one geo ID that nests by prefix (municipality BO-04-17-04 lies in province BO-04-17, in department BO-04, in Bolivia BO), so the package can move data up the hierarchy with each variable’s own aggregation rule, interpolate it onto grids or newer municipality maps, and combine datasets. To build your own indicators, it links tables that identify units by name in any spelling or by INE and DS4Bolivia codes (and refuses to guess between municipalities that share a name), summarizes rasters such as Earth Engine exports over units, and saves the result with the same documented format as the published data. It is small, works out of the box in Google Colab, and hands its data in one line to two companion packages: expdpy for panel exploration and econometrics, and geometrics for spatial analysis.',
    tags: ['Python', 'data loading', 'multi-scale', 'Colab', 'open data'],
    image: 'images/tools/geo4bolivia-package.webp',
    imageAlt: 'Three stacked map layers of Bolivia, 9 departments, 112 provinces and 339 municipalities, linked by geo IDs, beside a code snippet that loads the data',
    date: '2026-10-28', pinned: true,
    installNote: 'Colab already has its other dependencies, so installing takes seconds.',
    install: `!pip install -q geo4bolivia
!pip install -q "geo4bolivia[raster]"      # + rasterio, for zonal statistics from rasters (geo.zonal)`,
    quickstart: {
      python: `${PYTHON_SETUP}

geo.datasets()                                        # datasets x scales x years
geo.dictionary("sdg")                                 # variables, units, reference years
gdf = geo.load("ntl", years=2020, geometry=True)      # 339 municipalities with boundaries
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="ln_t400NTLpc", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"ln_t400NTLpc": "Log lights per capita"},
          title="Night-time lights, 2020").show()

# Across scales: municipalities -> provinces -> departments -> Bolivia
panel = geo.combine(["ntl", "pop"], scale="municipality")   # two datasets, one panel
dep = geo.aggregate(geo.load("pop", years=2020), to="department", dataset="pop")
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep, x="department", y="pop", labels={"pop": "Population"},
       title="Population by department, 2020").show()`,
      pandas: `import pandas as pd
import plotly.express as px

# The same files without the package: plain URLs
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/ntl.csv")
units = pd.read_csv(BASE + "geo/units.csv")           # names, parents, INE and DS4Bolivia codes
df = df.merge(units[["geo_id", "name", "department_id"]], on="geo_id")
df["department"] = df["department_id"].map(units.set_index("geo_id")["name"])

# One line per municipality, coloured by department
px.line(df, x="year", y="ln_t400NTLpc", color="department",
line_group="geo_id", hover_name="name",
labels={"ln_t400NTLpc": "Log lights per capita (trend)"},
title="Night-time lights, 339 municipalities")`,
    },
    build: `!pip install -q "geo4bolivia[raster]"
import geo4bolivia as geo
import plotly.express as px

# 1. Your table, with INE municipality codes (or names) -> geo IDs
mine = geo.link(my_table, scale="municipality", on="mun_id", key="mun_id")   # 20101 -> BO-04-17-04
geo.check(mine, scale="municipality")                                      # [] = valid panel

# 2. A raster (e.g. an Earth Engine export) -> municipal indicator
ntl = geo.zonal("viirs_2020.tif", scale="municipality", stats=["sum", "mean"], name="ntl", year=2020)

# 3. Combine with published data, derive, and save in the same format
panel = geo.combine(["pop"], scale="municipality", extra=[mine])
panel["clinics_per_10k"] = panel["clinics"] / panel["pop"] * 1e4
geo.save(panel, "clinics", scale="municipality", directory="my_data")

# 4. Hand it to expdpy (panel econometrics) or geometrics (spatial analysis)
df, df_def = geo.for_expdpy(panel)
gdf, df, df_dict = geo.for_geometrics(panel)

# 5. Map your indicator
gdf = geo.boundaries("municipality").merge(panel.query("year == 2020"), on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="clinics_per_10k", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"clinics_per_10k": "Clinics per 10,000 people"},
          title="Clinics, 2020")`,
    features: [
      { title: 'Load', fns: ['datasets', 'dictionary', 'load', 'units', 'boundaries', 'crosswalk'], text: 'Panels with filters, wide reshaping and boundaries; names, parents and INE, GADM and DS4Bolivia codes of every unit.' },
      { title: 'Link', fns: ['link', 'check'], text: 'Attach geo IDs to any table by names or codes, ignoring accents, case and spacing, with spelling suggestions; shared names are reported, never guessed.' },
      { title: 'Extract', fns: ['zonal'], text: 'Summarize rasters (sum, mean, max, count, ...) over municipalities or any scale, for one year or a series.' },
      { title: 'Move across scales', fns: ['aggregate', 'overlay', 'overlay_weights'], text: 'Up the hierarchy with metadata rules, or onto grids and newer municipality maps by area weights.' },
      { title: 'Combine & save', fns: ['combine', 'save'], text: 'Several datasets as one panel at one scale; your result as CSV, Parquet and a documented datapackage.' },
      { title: 'Analyze', fns: ['for_expdpy', 'for_geometrics'], text: 'Labeled inputs for expdpy (panel econometrics) and geometrics (spatial analysis), built from the metadata.' },
    ],
    links: [
      { label: 'Quickstart in Colab', url: COLAB_URL + 'geo4bolivia_quickstart.ipynb', kind: 'colab' },
      { label: 'How the database works', url: REPO_URL + '/blob/main/docs/data-infrastructure.md', kind: 'docs' },
      { label: 'Package guide', url: REPO_URL + '/blob/main/docs/python-package.md', kind: 'docs' },
      { label: 'PyPI', url: 'https://pypi.org/project/geo4bolivia/', kind: 'pypi' },
      { label: 'Source code', url: REPO_URL + '/tree/main/src/geo4bolivia', kind: 'github' },
    ],
    related: ['expdpy-package', 'geometrics-package', 'geo4bolivia-quickstart', 'municipalities339-sdg', 'municipalities339-ntl'],
  },
  {
    id: 'geometrics-package', type: 'package', section: 'tools',
    title: 'geometrics: regional growth, convergence and inequality',
    scope: '!pip install -q geo4bolivia geometrics',
    summary: 'A companion package for spatial analysis: maps, spatial dependence, β-, σ- and club convergence, spatial regressions, distribution dynamics and inequality, each with a plain-language reading.',
    description: 'geometrics turns the standard analyses of regional growth into single functions built on the PySAL stack. Explore functions map variables, build spatial weights and test spatial dependence (Moran’s I, LISA clusters). Analyze functions estimate β-convergence (OLS and spatial models with LeSage–Pace impacts), σ-convergence, Phillips–Sul convergence clubs, Markov and spatial Markov transitions, Gini and Theil decompositions, and geographically weighted regressions. Learn functions simulate each concept from a known truth. Every result carries an interactive figure, a table and an interpret() method that explains it in words. geo4bolivia prepares Bolivian data for it in one line: geo.for_geometrics().',
    tags: ['Python', 'spatial econometrics', 'convergence', 'inequality', 'PySAL'],
    image: 'images/tools/geometrics-package.webp',
    imageAlt: 'A LISA cluster map of night-time lights per capita across Bolivian municipalities in 2012 and its Moran scatterplot',
    date: '2026-10-28', pinned: true,
    install: `!pip install -q geo4bolivia geometrics`,
    quickstart: {
      python: `!pip install -q geo4bolivia geometrics
import numpy as np
import geo4bolivia as geo
import geometrics as gm

ntl = geo.load("ntl")                                   # 339 municipalities, 2012-2020
ntl["NTLpc"] = np.exp(ntl["ln_NTLpc"])                  # levels, for convergence
gdf, df, df_dict = geo.for_geometrics(ntl, labels={"NTLpc": "Night-time lights per capita"})
df = gm.set_labels(df, df_dict, set_panel=True)
w = gm.make_weights(gdf, method="queen")

gm.explore_lisa_cluster_map(df, "ln_t400NTLpc", gdf=gdf, w=w, period=2020).fig
res = gm.analyze_beta_convergence(df, "NTLpc", gdf=gdf, w=w)   # levels: logged internally
print(res.interpret())`,
    },
    features: [
      { title: 'Explore', fns: ['explore_choropleth_map', 'explore_moran_plot', 'explore_lisa_cluster_map'], text: 'Maps, spatial weights, Moran’s I and local clusters, over time.' },
      { title: 'Converge', fns: ['analyze_beta_convergence', 'analyze_sigma_convergence', 'analyze_convergence_clubs'], text: 'β-, σ- and club convergence, including spatial models.' },
      { title: 'Model', fns: ['analyze_spatial_model', 'analyze_gwr', 'analyze_mgwr'], text: 'SAR, SEM, SLX and SDM with impacts; local regressions.' },
      { title: 'Inequality & dynamics', fns: ['analyze_inequality_over_time', 'analyze_theil_decomposition', 'analyze_markov_transitions'], text: 'Gini and Theil (between and within groups), Markov and spatial Markov chains.' },
      { title: 'Learn', fns: ['learn_beta_convergence', 'explain'], text: 'Simulations from a known truth and plain-language explainers for 30 topics.' },
    ],
    links: [
      { label: 'Documentation', url: 'https://quarcs-lab.github.io/geometrics/', kind: 'docs' },
      { label: 'PyPI', url: 'https://pypi.org/project/geometrics/', kind: 'pypi' },
      { label: 'Source code', url: 'https://github.com/quarcs-lab/geometrics', kind: 'github' },
    ],
    related: ['geo4bolivia-package', 'expdpy-package', 'mpi-esda', 'mpi-esda-heterogeneity'],
  },
  {
    id: 'expdpy-package', type: 'package', section: 'tools',
    title: 'expdpy: explore and model panel data',
    scope: '!pip install -q geo4bolivia expdpy',
    summary: 'A companion package for panel data: within/between variation, trajectories and transitions, then pooled, fixed and random effects, Hausman tests and clustered standard errors, each with a plain-language reading.',
    description: 'expdpy (a Python port of ExPanDaR) turns the everyday steps of panel-data research into single functions. Explore functions describe a panel’s structure, decompose variation into between and within components (xtsum), and chart trajectories, distributions, transitions, missing values and correlations. Analyze functions estimate pooled, between, fixed-effects, random-effects and correlated-random-effects models, run Hausman and joint tests, fit fixest-style regressions with fixed effects and clustered or Driscoll–Kraay standard errors, and cover IV, event studies and β-, σ- and club convergence. Learn functions simulate each concept from a known truth. Every result has an interactive figure or table and an interpret() method. The observatory’s datasets are exactly the long panels expdpy expects: geo.for_expdpy() hands them over, labeled, in one line.',
    tags: ['Python', 'panel data', 'econometrics', 'fixed effects', 'ExPanDaR'],
    image: 'images/tools/expdpy-package.webp',
    imageAlt: 'Night-time lights per capita trajectories of 339 Bolivian municipalities, 2012–2020, with department means and the between/within split of their variation',
    date: '2026-10-28', pinned: true,
    install: `!pip install -q geo4bolivia expdpy`,
    quickstart: {
      python: `!pip install -q geo4bolivia expdpy
import numpy as np
import geo4bolivia as geo
import expdpy as ex

df, df_def = geo.for_expdpy("ntl", groups=["department"])   # 339 municipalities, 2012-2020
df = ex.set_labels(df, df_def, set_panel=True)              # geo_id x year panel
ex.explore_xtsum_table(df, var=["ln_t400NTLpc"]).gt         # within vs between variation
ex.explore_trend_plot_by_group(df, group_var="department", var="ln_t400NTLpc").fig

# Lights and population: pooled, between, fixed and random effects
panel = geo.combine(["ntl", "pop"], scale="municipality")
panel["ln_pop"] = np.log(panel["pop"])
panel, panel_def = geo.for_expdpy(panel, labels={"ln_pop": "Log of population"})
panel = ex.set_labels(panel, panel_def, set_panel=True)
ex.analyze_panel_table(panel, "ln_NTLpc", ["ln_pop"]).etable
print(ex.analyze_hausman_test(panel, "ln_NTLpc", ["ln_pop"]).interpret())`,
    },
    features: [
      { title: 'Explore', fns: ['explore_panel_structure', 'explore_xtsum_table', 'explore_spaghetti_plot', 'explore_transition_matrix'], text: 'Panel structure, within/between variation, trajectories, distributions and transitions.' },
      { title: 'Panel models', fns: ['analyze_panel_table', 'analyze_hausman_test', 'analyze_cre_table'], text: 'Pooled, between, fixed, random and correlated random effects, side by side.' },
      { title: 'Regressions & inference', fns: ['analyze_regression_table', 'analyze_coefficient_plot', 'analyze_robust_inference'], text: 'Fixed effects, clustered and Driscoll–Kraay errors, wild bootstrap, IV and event studies.' },
      { title: 'Convergence & Kuznets', fns: ['analyze_beta_convergence', 'analyze_sigma_convergence', 'analyze_kuznets_waves'], text: 'Non-spatial β-, σ- and club convergence; inequality–development waves.' },
      { title: 'Learn', fns: ['learn_pooled_vs_fixed_effects', 'explain'], text: 'Sandboxes that simulate from a known truth, and plain-language explainers.' },
    ],
    links: [
      { label: 'Documentation', url: 'https://cmg777.github.io/expdpy/', kind: 'docs' },
      { label: 'PyPI', url: 'https://pypi.org/project/expdpy/', kind: 'pypi' },
      { label: 'Source code', url: 'https://github.com/cmg777/expdpy', kind: 'github' },
      { label: 'No-code Analyze app', url: 'https://expdpy-analyze.streamlit.app', kind: 'launch' },
    ],
    related: ['geo4bolivia-package', 'geometrics-package', 'municipalities339-ntl', 'municipalities339-pop'],
  },

  // ---------------------------------------------------------------- Tools: notebooks
  {
    id: 'geo4bolivia-quickstart', type: 'notebook', section: 'tools',
    title: 'Load, link and build Bolivian indicators with geo4bolivia',
    summary: 'A hands-on tour of the observatory’s data: load it with and without the package, move it across scales, link your own table by name or INE code, and build an indicator from a raster.',
    description: 'This Colab notebook walks through the observatory’s data for Bolivia’s 339 municipalities. It loads files as plain URLs and then with geo4bolivia; maps multidimensional poverty in its census year; sums population to departments and computes population-weighted poverty; combines lights, population and poverty in one panel; links a table by department names in any spelling and by INE municipality codes, and shows how shared municipality names and typos are reported; builds a market-access indicator (distance to La Paz, Cochabamba and Santa Cruz) from a raster with zonal statistics; interpolates population onto a 25 km grid; and saves the result in the observatory’s format.',
    tags: ['geo4bolivia', 'quickstart', 'Python', 'Colab'],
    image: 'images/tools/geo4bolivia-quickstart.webp',
    imageAlt: 'Map of population-weighted multidimensional poverty by Bolivian department in 2012',
    date: '2026-10-28', pinned: true,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'geo4bolivia_quickstart.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/geo4bolivia_quickstart.ipynb', kind: 'github' },
    ],
    related: ['geo4bolivia-package', 'municipalities339-sdg', 'municipalities339-pop'],
  },
  {
    id: 'mpi-eda', type: 'notebook', section: 'tools',
    title: 'Exploratory data analysis of multidimensional poverty',
    summary: 'How poverty varies across 339 municipalities and 9 departments, and how it relates to population and night-time lights.',
    description: 'This Colab notebook explores the Multidimensional Poverty Index of 2012 across Bolivia’s municipalities: summary statistics, the poorest and least poor municipalities, distributions and box plots by department, a treemap of population and poverty, and the links with population and night-time lights. Poverty averages 0.18 and runs from 0.007 to 0.52; Pando and Chuquisaca are the poorest departments and Tarija and Santa Cruz the least poor, but poverty varies more within departments than between them. Brighter municipalities are less poor (correlation −0.54), and the slope is negative in all nine departments.',
    tags: ['EDA', 'poverty', 'night-time lights', 'Python'],
    image: 'images/tools/eda.webp',
    imageAlt: 'Scatter plot of multidimensional poverty against log night-time lights per capita for Bolivian municipalities in 2012, with a negative fitted line',
    date: '2026-10-28', pinned: false,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'eda.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/eda.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-sdg', 'municipalities339-ntl', 'mpi-esda'],
  },
  {
    id: 'mpi-esda', type: 'notebook', section: 'tools',
    title: 'Exploratory spatial data analysis of poverty',
    summary: 'Is a municipality as poor as its neighbours? Spatial weights, Moran’s I and LISA clusters of multidimensional poverty.',
    description: 'This Colab notebook asks whether poverty in one municipality resembles poverty in its neighbours. It maps the Multidimensional Poverty Index of 2012, builds six-nearest-neighbour weights and spatial lags, and tests global and local spatial dependence. Poverty is strongly clustered (Moran’s I = 0.46, p = 0.001). The LISA map finds poverty hot spots in Pando and the Chuquisaca and Potosí valleys, low-poverty clusters around Santa Cruz, the Cochabamba valley, La Paz–El Alto and Tarija, and less poor capitals such as Sucre and Cobija surrounded by poorer municipalities.',
    tags: ['ESDA', 'spatial autocorrelation', 'LISA', 'PySAL'],
    image: 'images/tools/esda.webp',
    imageAlt: 'LISA cluster map of multidimensional poverty in 2012: high-poverty clusters in Pando and the Chuquisaca and Potosí valleys, low-poverty clusters around Santa Cruz, Cochabamba, La Paz and Tarija',
    date: '2026-10-28', pinned: true,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'esda.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/esda.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-sdg', 'mpi-esda-dependence', 'geometrics-package'],
  },
  {
    id: 'mpi-esda-dependence', type: 'notebook', section: 'tools',
    title: 'Spatial distribution and dependence of poverty',
    summary: 'Two ways to classify a poverty map, then spatial weights, the spatial lag, Moran’s I and local clusters.',
    description: 'This Colab notebook first maps the Multidimensional Poverty Index of 2012 with box-plot breaks, which flag three high outliers (El Sena, San Pedro and Poroma), and with three Fisher–Jenks natural breaks. It then builds six-nearest-neighbour weights, shows that Moran’s I (0.46) is the slope of the spatial-lag regression, and maps local clusters and outliers, comparing the 10% and 5% significance levels and how many clusters would be expected by chance.',
    tags: ['ESDA', 'map classification', 'Moran’s I', 'PySAL'],
    image: 'images/tools/esda-dependence.webp',
    imageAlt: 'Map of multidimensional poverty in Bolivian municipalities classified with box-plot breaks',
    date: '2026-10-28', pinned: false,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'esda_dependence.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/esda_dependence.ipynb', kind: 'github' },
    ],
    related: ['mpi-esda', 'municipalities339-sdg'],
  },
  {
    id: 'mpi-esda-inequality', type: 'notebook', section: 'tools',
    title: 'Spatial inequality of poverty and night-time lights',
    summary: 'Gini, Theil between and within departments, and the spatial Gini: how much of Bolivia’s inequality is regional?',
    description: 'This Colab notebook measures inequality across the 339 municipalities in multidimensional poverty and in night-time lights per capita (2012). Poverty has a Gini of 0.31; the Theil index shows that only about a quarter of it lies between the nine departments, and the rest within them. The spatial Gini confirms that neighbouring municipalities are more alike than distant ones. A department table compares simple and population-weighted poverty.',
    tags: ['inequality', 'Theil', 'Gini', 'spatial Gini'],
    image: 'images/tools/esda-inequality.webp',
    imageAlt: 'Quintile map of multidimensional poverty in 2012 across Bolivian municipalities, with the borders of the nine departments used to decompose inequality',
    date: '2026-10-28', pinned: false,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'esda_inequality.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/esda_inequality.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-sdg', 'municipalities339-ntl', 'geometrics-package'],
  },
  {
    id: 'mpi-esda-heterogeneity', type: 'notebook', section: 'tools',
    title: 'Where do lights predict poverty? GWR and MGWR',
    summary: 'Geographically weighted regressions let the link between night-time lights and poverty vary across Bolivia.',
    description: 'This Colab notebook regresses multidimensional poverty on night-time lights per capita (2012) across the 339 municipalities. A single national regression explains 29% of the variation. A geographically weighted regression, with a bandwidth of 46 neighbours, raises that to 62%: every local slope is negative, but it is steepest in Cochabamba, Chuquisaca and Potosí and weakest in La Paz, Beni and Pando. A multiscale GWR lets the intercept and the slope vary at different scales and fits best of the three.',
    tags: ['GWR', 'MGWR', 'spatial heterogeneity', 'night-time lights'],
    image: 'images/tools/esda-heterogeneity.webp',
    imageAlt: 'Map of significant local GWR slopes of poverty on night-time lights across Bolivian municipalities, steepest in Cochabamba, Chuquisaca and Potosí',
    date: '2026-10-28', pinned: false,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'esda_heterogeneity.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/esda_heterogeneity.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-ntl', 'municipalities339-sdg', 'geometrics-package'],
  },
  {
    id: 'mpi-eda-esda', type: 'notebook', section: 'tools',
    title: 'Poverty in Bolivia: an extended EDA and ESDA',
    summary: 'One workflow from descriptive statistics to infrastructure correlates, spatial clusters, bivariate LISA, inequality and GWR.',
    description: 'This Colab notebook combines exploratory and spatial data analysis of multidimensional poverty (2012). Electricity and network coverage are its strongest correlates (Spearman −0.91 and −0.89), ahead of clean cooking energy, child malnutrition and night-time lights. Poverty clusters strongly in space (Moran’s I = 0.46), and a bivariate LISA relates each municipality’s poverty to its neighbours’ lights: less poor places in bright neighbourhoods around Santa Cruz, Cochabamba and Tarija, and poor places in dark ones in La Paz, Potosí, Pando and Beni. It closes with inequality measures and a geographically weighted regression.',
    tags: ['EDA', 'ESDA', 'bivariate LISA', 'infrastructure'],
    image: 'images/tools/eda-esda.webp',
    imageAlt: 'Bivariate LISA map of Bolivian municipalities relating each one’s poverty to its neighbours’ night-time lights',
    date: '2026-10-28', pinned: false,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'eda_esda.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/eda_esda.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-sdg', 'mpi-esda', 'mpi-esda-heterogeneity'],
  },
  {
    id: 'embeddings-mpi-ml', type: 'notebook', section: 'tools',
    title: 'Predicting poverty from satellite embeddings',
    summary: 'Random forest and XGBoost predict multidimensional poverty from 64 satellite embedding dimensions, with random and spatial cross-validation.',
    description: 'This Colab notebook trains random forests and XGBoost to predict the Multidimensional Poverty Index of 2012 from the 64 satellite embedding dimensions of 2017, and compares them with a baseline of night-time lights and population. Population-weighted embeddings beat area-weighted ones, and adding lights helps: the best models reach an out-of-fold R² of about 0.55–0.58 with random 5-fold cross-validation. When whole departments are held out, R² falls to about 0.2, a reminder that models struggle to extrapolate to new regions. A map of residuals shows where they fail: Pando is under-predicted. The text discusses the 2017/2012 timing mismatch.',
    tags: ['machine learning', 'satellite embeddings', 'random forest', 'XGBoost'],
    image: 'images/tools/embeddings-mpi-ml.webp',
    imageAlt: 'Scatter plot of out-of-fold predicted against observed multidimensional poverty from XGBoost on satellite embeddings, random 5-fold cross-validation, R² 0.58',
    date: '2026-10-28', pinned: true,
    links: [
      { label: 'Open in Colab', url: COLAB_URL + 'embeddings_mpi_ml.ipynb', kind: 'colab' },
      { label: 'View on GitHub', url: REPO_URL + '/blob/main/notebooks/embeddings_mpi_ml.ipynb', kind: 'github' },
    ],
    related: ['municipalities339-emb', 'municipalities339-sdg', 'mpi-eda'],
  },

  // ---------------------------------------------------------------- Tools: apps
  {
    id: 'geoexplorer', type: 'app', section: 'tools',
    title: 'GeoExplorer v1.0: Bolivia from outer space',
    summary: 'Swipe between 2013 and 2019 to see how population, night-time lights, land cover and GDP changed across Bolivia’s municipalities.',
    description: 'An Earth Engine app, “Exploring regional development in Bolivia: a view from outer space”. Choose a layer (population density from WorldPop, VIIRS night-time lights, land cover, or gridded GDP), then drag the slider to compare 2013 with 2019 side by side. Click any municipality to chart its change. Cities such as Santa Cruz de la Sierra show how fast urban lights have spread. Built for DS4Bolivia by Carlos Mendez (Nagoya University).',
    tags: ['Earth Engine', 'night-time lights', 'population', 'interactive map'],
    image: 'images/tools/geoexplorer.webp',
    imageAlt: 'Earth Engine app comparing night-time lights over Santa Cruz de la Sierra in 2013 and 2019 with a swipe slider',
    date: '2026-01-15', pinned: true,
    links: [
      { label: 'Launch app', url: 'https://carlos-mendez.projects.earthengine.app/view/geoexplorer1v100bolivia', kind: 'launch' },
      { label: 'Source code', url: REPO_URL + '/blob/main/apps/geoexplorer1v100bolivia.js', kind: 'github' },
    ],
    related: ['municipalities339-ntl', 'municipalities339-pop'],
  },

  // ---------------------------------------------------------------- Insights
  {
    id: 'human-capital-paper', type: 'insight', subtype: 'Paper', section: 'insights',
    title: 'Human capital constraints and the regions of Bolivia',
    summary: 'Where malnutrition, language barriers, school dropout and unequal education cluster across 339 municipalities, and how they divide Bolivia into seven or eight regions.',
    description: 'This study maps five constraints on human capital across Bolivia’s 339 municipalities: chronic malnutrition in children, the share of the population that does not speak Spanish, the secondary-school dropout rates of boys and girls, and inequality in years of education. It summarises them with principal components, finds where high and low values cluster in space (hot spots and cold spots), and groups municipalities that are both similar and contiguous into regions. All five indicators are in the observatory’s sdg dataset.',
    citation: 'Mendez, C., & Gonzales, E. (2021). Human capital constraints, spatial dependence, and regionalization in Bolivia: A spatial clustering approach. Economía, 44(87), 115–145.',
    doi: 'https://doi.org/10.18800/economia.202101.007',
    tags: ['human capital', 'education', 'spatial clustering', 'regionalization'],
    image: 'images/insights/human-capital-paper.webp',
    imageAlt: 'Five maps of Bolivian municipalities: chronic child malnutrition, non-Spanish speakers, male and female secondary dropout, and inequality in years of education',
    date: '2021-05-06', pinned: true,
    media: [],
    links: [
      { label: 'Read the paper', url: 'https://doi.org/10.18800/economia.202101.007', kind: 'paper' },
    ],
    summarySections: [
      { h: 'Data', p: 'Five indicators of the Municipal Atlas of the SDGs for 339 municipalities: chronic malnutrition in children, non-Spanish-speaking population, secondary dropout of males and of females, and the inequality of years of education.' },
      { h: 'Method', p: 'Principal components summarise the five constraints; measures of spatial dependence find hot spots and cold spots; a regionalization analysis groups municipalities that are similar in their constraints and close in space.' },
      { h: 'Findings', p: 'Human capital constraints are spatially clustered, and Bolivia can be divided into seven or eight geographic regions that share similar constraints.' },
      { h: 'Reproduce it', p: 'The five indicators are sdg2_2_cmc, sdg10_2_nssp, sdg4_1_ssdrm, sdg4_1_ssdrf and sdg10_2_gcye in the sdg dataset, each at its own reference year.' },
    ],
    related: ['municipalities339-sdg', 'mpi-esda'],
  },
];


export const PEOPLE = {
  core: [
    { name: 'Carlos Mendez', affiliation: 'Nagoya University, Japan', avatar: 'images/people/carlos-mendez.webp', website: 'https://carlos-mendez.org' },
  ],
  associates: [
    { name: 'Favio Leiva', affiliation: 'Nagoya University, Japan', avatar: 'images/people/favio-leiva.webp', website: 'https://favioleiva.github.io/' },
    { name: 'Laura Prieto', affiliation: 'Nagoya University, Japan', avatar: 'images/people/laura-prieto.webp', website: 'https://lauraprieto.my.canva.site/' },
  ],
};

export const CONTACTS = [
  { name: 'Carlos Mendez', email: 'carlos.mendez.n9 [at] f.mail.nagoya-u.ac.jp' },
];

export const CITATION_APA = 'Mendez, C. (2026). GeoDevelopment Observatory of Bolivia. https://quarcs-lab.github.io/geo4bolivia/';
export const CITATION_BIB = `@misc{gdobolivia2026,
  author       = {Mendez, Carlos},
  title        = {{GeoDevelopment Observatory of Bolivia}},
  year         = {2026},
  howpublished = {\\url{https://quarcs-lab.github.io/geo4bolivia/}},
  note         = {Data and code: https://github.com/quarcs-lab/geo4bolivia}
}`;

