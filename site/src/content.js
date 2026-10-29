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
// Retired pages ("<section>/<id>") and the page that replaced each one
export const REDIRECTS = {
  'indicators/municipalities339-sdg': 'indicators/municipalities339-sdg01',
};

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
    id: 'municipalities339-sdg01', type: 'indicator', section: 'indicators',
    title: 'SDG 1: No poverty',
    scope: '339 municipalities · 4 indicators and the SDG 1 index · 2012–2020',
    summary: 'The SDG 1 (No poverty) index of the Municipal Atlas of the SDGs and its four indicators, multidimensional poverty, unsatisfied basic needs, extreme energy poverty and access to basic services, for every municipality.',
    description: 'The SDG 1 (No poverty) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the four indicators behind it: the Alkire-Foster multidimensional poverty index (0–1, nine household deprivations), the share of the population with unsatisfied basic needs and the share of households with access to all three basic services (electricity, water and sanitation), all three from the 2012 Population and Housing Census (INE), and extreme energy poverty, the share of dwellings that consumed under 210 kWh a year or had no electricity, from electricity-meter records of 2016. The index runs from 0 (worst situation) to 100 (targets met): each indicator is rescaled linearly between a worst and a best value, capped, so that higher is always better, and the index is the simple mean of the available rescaled indicators. Extreme energy poverty is missing for 24 municipalities, whose index is the mean of the other three. Because its indicators refer to 2012 and 2016, the index is stored at 2016. The Atlas population (2020) and urbanization rate (2012) are included as context; they are not inputs of the index.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'poverty', 'multidimensional poverty', 'basic services', 'census'],
    image: 'images/indicators/sdg01.webp',
    imageAlt: 'Map of the No poverty index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high around Santa Cruz, in the Chiquitania, the Chaco of Tarija and the main cities, middle across most of Beni and Pando, low on the altiplano of La Paz and Oruro, in the northern Potosí and Chuquisaca valleys, the south-western corner of Potosí and northern Pando',
    mapAlt: 'Map of the No poverty index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high around Santa Cruz, in the Chiquitania, the Chaco of Tarija and the main cities, middle across most of Beni and Pando, low on the altiplano of La Paz and Oruro, in the northern Potosí and Chuquisaca valleys, the south-western corner of Potosí and northern Pando. Legend: High 57.0 to 90.5 (61 municipalities), Middle 31.0 to 57.0 (128), Low 0.1 to 31.0 (150).',
    map: 'images/indicators/sdg01-map.webp',
    date: '2026-10-30', pinned: true, dataset: 'sdg01',
    notice: 'Each variable has values only in its reference year: load the index with its year, geo.load("sdg01", variables="index_sdg1", years=2016), which is the latest year of its indicators (2012 and 2016). In DS4Bolivia the rows of three pairs of homonym municipalities (San Javier, El Puente, Santa Rosa) were attached to the wrong polygon of each pair; here every row is linked by INE code to its own municipality.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 1 index (0-100, higher is better), stored at 2016
gdf = geo.load("sdg01", variables="index_sdg1", years=2016, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg1", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg1": "No poverty index (0-100)"},
          title="SDG 1: No poverty index, 2016").show()

# Every variable at its own year: multidimensional poverty (2012) vs the index
df = geo.load("sdg01").groupby("geo_id", as_index=False).first()
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg1_2_mpi", y="index_sdg1", hover_name="name",
           labels={"sdg1_2_mpi": "Multidimensional poverty index",
                   "index_sdg1": "No poverty index (0-100)"},
           title="Multidimensional poverty (2012) and the SDG 1 index")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg01.csv")  # geo_id, year, mun_id, ...
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2016, ["geo_id", "index_sdg1"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg1", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg1": "No poverty index (0-100)"},
          title="SDG 1: No poverty index, 2016")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas bounds (worst, best), caps it to 0-100 and averages the available ones, which reproduces the published SDG 1 index.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg01").groupby("geo_id").first()  # each indicator at its year
bounds = {"sdg1_1_eepr": (94.9, 0), "sdg1_1_ubn": (96.7, 0),  # (worst, best)
          "sdg1_2_mpi": (0.391, 0), "sdg1_4_abs": (0, 100)}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)  # skips missing indicators
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="computed", y="index_sdg1", hover_name="name",
           labels={"computed": "Computed from the indicators",
                   "index_sdg1": "No poverty index (0-100)"},
           title="Recomputed vs published SDG 1 index")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Compares the mean rescaled score (0-100) of each indicator across municipalities: the lowest one is where the goal is furthest away.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg01").groupby("geo_id").first()
bounds = {"sdg1_1_eepr": (94.9, 0), "sdg1_1_ubn": (96.7, 0),
          "sdg1_2_mpi": (0.391, 0), "sdg1_4_abs": (0, 100)}
labels = geo.dictionary("sdg01").set_index("variable")["label"]
rows = [{"indicator": labels[v],
         "score": (100 * (df[v] - w) / (b - w)).clip(0, 100).mean()}
        for v, (w, b) in bounds.items()]
px.bar(pd.DataFrame(rows).sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 1 indicators: distance to the target")`,
      },
      {
        title: 'Rank the departments',
        text: 'Averages the index within each department, weighting municipalities by their 2016 gridded population.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg01", variables="index_sdg1", years=2016)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg1": "weighted_mean:pop"},
                    weights=geo.load("pop"))
dep["department"] = dep["geo_id"].map(
    geo.units("department").set_index("geo_id")["name"])
px.bar(dep.sort_values("index_sdg1"), x="index_sdg1", y="department",
       labels={"index_sdg1": "No poverty index (population-weighted)"},
       title="SDG 1 index by department, 2016")`,
      },
      {
        title: 'Poverty and night-time lights',
        text: 'Links multidimensional poverty in 2012 with the trend of night-time lights per capita in the same year from the observatory’s ntl dataset.',
        code: `${PYTHON_SETUP}

mpi = geo.load("sdg01", variables="sdg1_2_mpi", years=2012)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2012)
df = mpi.merge(ntl, on=["geo_id", "year"])
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="ln_t400NTLpc", y="sdg1_2_mpi", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "sdg1_2_mpi": "Multidimensional poverty index"},
           title="Poverty and night-time lights, 2012")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg02', type: 'indicator', section: 'indicators',
    title: 'SDG 2: Zero hunger',
    scope: '339 municipalities · 4 indicators and the SDG 2 index · 2012–2020',
    summary: 'The Zero hunger index of the Municipal Atlas of the SDGs and its four indicators of child malnutrition, obesity in women, farm size and tractors, for every municipality.',
    description: 'The SDG 2 (Zero hunger) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the targets are met, with the four indicators behind it: chronic malnutrition among children under 5 and obesity among women aged 15–49 (2016 Demographic and Health Survey, EDSA), and the average farm size and tractors per 1,000 farms (2013 Agricultural Census, INE). Each indicator is rescaled linearly to 0–100 between a worst and a best value, so that higher is always better and values beyond the bounds are capped, and the index is the simple mean of the available rescaled indicators. The survey is not representative by municipality, so the two nutrition indicators are imputed by department and poverty level and municipalities in the same cell share one value. The two farm indicators are missing for 15 almost fully urban municipalities, where the index averages the two nutrition indicators. The index is stored at 2016, the latest year of its indicators; the Atlas population (2020) and urbanization rate (2012 census) are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social', 'Economy'], tags: ['SDGs', 'hunger', 'malnutrition', 'agriculture', 'municipalities'],
    image: 'images/indicators/sdg02.webp',
    imageAlt: 'Map of the Zero hunger index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high in the Santa Cruz lowlands, Pando and parts of Beni, low across the highland valleys of Cochabamba, northern Potosí, Chuquisaca and Tarija, the La Paz altiplano near Lake Titicaca and southern Potosí',
    map: 'images/indicators/sdg02-map.webp',
    mapAlt: 'Map of the Zero hunger index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high in the Santa Cruz lowlands, Pando and parts of Beni, low across the highland valleys of Cochabamba, northern Potosí, Chuquisaca and Tarija, the La Paz altiplano near Lake Titicaca and southern Potosí. Legend: High 51.4 to 71.4 (56 municipalities), Middle 38.7 to 51.4 (110), Low 21.4 to 38.7 (173).',
    date: '2026-10-30', pinned: false, dataset: 'sdg02',
    notice: 'Each variable has values only in its reference year: load the index with its year, geo.load("sdg02", variables="index_sdg2", years=2016), or every variable as a cross-section with geo.load("sdg02").groupby("geo_id").first(). The index is stored at 2016, the latest year of its indicators (the farm indicators are from 2013).',
    code: {
      python: `${PYTHON_SETUP}

# The Zero hunger index in 2016, with municipal boundaries
gdf = geo.load("sdg02", variables="index_sdg2", years=2016, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg2", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg2": "Zero hunger index (0-100)"},
          title="SDG 2: Zero hunger index, 2016").show()

# Every variable at its own year: one row per municipality
df = geo.load("sdg02").groupby("geo_id", as_index=False).first()
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg2_2_cmc", y="index_sdg2", hover_name="name",
           labels={"sdg2_2_cmc": "Child chronic malnutrition (%)",
                   "index_sdg2": "Zero hunger index (0-100)"},
           title="Child malnutrition and the Zero hunger index")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg02.csv")  # geo_id, year, mun_id, ...
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2016, ["geo_id", "index_sdg2"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg2", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg2": "Zero hunger index (0-100)"},
          title="SDG 2: Zero hunger index, 2016")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between its worst and best value, caps it at 0 and 100 and averages the available scores, which reproduces the published Zero hunger index.',
        code: `${PYTHON_SETUP}
import pandas as pd

# Worst and best value of each indicator (Atlas, Cuadro 17)
bounds = {"sdg2_2_cmc": (52.6, 0.0), "sdg2_2_oww": (32.8, 11.3),
          "sdg2_4_pual": (0.43, 30.0), "sdg2_4_td": (0.0, 673.4)}

df = geo.load("sdg02").groupby("geo_id").first()  # each variable at its year
scores = pd.DataFrame({v: 100 * (df[v] - worst) / (best - worst)
                       for v, (worst, best) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)  # skips missing farm indicators
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="index_sdg2", y="computed", hover_name="name",
           labels={"index_sdg2": "Zero hunger index (0-100), published",
                   "computed": "Zero hunger index (0-100), computed"},
           title="Recomputing the SDG 2 index")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Averages each indicator’s 0–100 score over the municipalities: the lowest bar is the indicator furthest from its target.',
        code: `${PYTHON_SETUP}
import pandas as pd

bounds = {"sdg2_2_cmc": (52.6, 0.0), "sdg2_2_oww": (32.8, 11.3),
          "sdg2_4_pual": (0.43, 30.0), "sdg2_4_td": (0.0, 673.4)}
labels = {"sdg2_2_cmc": "Child chronic malnutrition (%)",
          "sdg2_2_oww": "Obesity in women aged 15-49 (%)",
          "sdg2_4_pual": "Average farm size (ha)",
          "sdg2_4_td": "Tractors per 1,000 farms"}

df = geo.load("sdg02").groupby("geo_id").first()
score = pd.DataFrame({labels[v]: 100 * (df[v] - worst) / (best - worst)
                      for v, (worst, best) in bounds.items()}).clip(0, 100)
mean = score.mean().rename_axis("indicator").reset_index(name="score")
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean score (0-100)", "indicator": ""},
       title="Average distance to the SDG 2 targets")`,
      },
      {
        title: 'Rank the departments',
        text: 'Aggregates the index to the nine departments as population-weighted means, using the gridded population of 2016.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg02", variables="index_sdg2", years=2016)
dep = geo.aggregate(df, to="department", rules={"index_sdg2": "weighted_mean:pop"},
                    weights=geo.load("pop"))
dep["department"] = dep["geo_id"].map(
    geo.units("department").set_index("geo_id")["name"])
px.bar(dep.sort_values("index_sdg2"), x="index_sdg2", y="department",
       labels={"index_sdg2": "Zero hunger index (0-100), population-weighted",
               "department": ""},
       title="SDG 2 index by department, 2016")`,
      },
      {
        title: 'Zero hunger and night-time lights',
        text: 'Links the index with the observatory’s night-time lights per capita of the same year, a proxy for local economic activity.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg02", variables="index_sdg2", years=2016)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2016)
df = sdg.merge(ntl, on=["geo_id", "year"])
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="ln_t400NTLpc", y="index_sdg2", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "index_sdg2": "Zero hunger index (0-100)"},
           title="Zero hunger and night-time lights, 2016")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg03', type: 'indicator', section: 'indicators',
    title: 'SDG 3: Good health and well-being',
    scope: '339 municipalities · 9 indicators and the SDG 3 index · 2010–2018',
    summary: 'The SDG 3 index of the Municipal Atlas of the SDGs and its nine indicators of births, child mortality, infectious diseases and adolescent fertility.',
    description: 'The SDG 3 (Good health and well-being) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the nine indicators behind it: institutional birth coverage and adolescent fertility (2008–2012 averages from the 2012 census, stored at 2010), infant and under-five mortality (UDAPE estimates for 2016), Chagas infestation and tuberculosis incidence (2017), dengue incidence (2018), and malaria and HIV incidence (2014–2017 averages, stored at 2015), the last five from Ministry of Health programmes via the National Health Information System (SNIS). Each indicator is rescaled to 0–100 between a worst and a best value (higher is always better, values beyond the bounds capped), and the index, from 0 to 100 where 100 means the targets are met, is the simple mean of the rescaled indicators. Infant and under-five mortality are almost perfectly correlated (0.99), so child mortality carries double weight in the index. The Atlas population in 2020 and the urbanization rate in 2012 are included as context; no values are missing.',
    geography: 'Municipality', units: 339, period: '2010–2018', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'health', 'child mortality', 'infectious diseases', 'municipalities'],
    image: 'images/indicators/sdg03.webp',
    imageAlt: 'Map of the Good health index (0-100) in 2018 across 339 Bolivian municipalities in three natural-break classes: high across the eastern lowlands of Santa Cruz, Beni and the Chaco, low in Pando, the northern Potosí valleys and the southwest of Potosí',
    map: 'images/indicators/sdg03-map.webp',
    mapAlt: 'Map of the Good health index (0-100) in 2018 across 339 Bolivian municipalities in three natural-break classes: high across the eastern lowlands of Santa Cruz, Beni and the Chaco, low in Pando, the northern Potosí valleys and the southwest of Potosí. Legend: High 77.3 to 89.0 (154 municipalities), Middle 68.0 to 77.3 (124), Low 50.2 to 68.0 (61).',
    date: '2026-10-30', pinned: false, dataset: 'sdg03',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg03", variables="index_sdg3", years=2018), or every variable as a cross-section with geo.load("sdg03").groupby("geo_id").first(). The index is stored at 2018, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 3 index at its reference year, with municipal boundaries
gdf = geo.load("sdg03", variables="index_sdg3", years=2018, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg3", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg3": "Good health index (0-100)"},
          title="SDG 3: Good health and well-being, 2018").show()

# The index across the municipalities of each department
units = geo.units("municipality").set_index("geo_id")
names = geo.units("department").set_index("geo_id")["name"]
gdf["department"] = gdf["geo_id"].map(units["department_id"]).map(names)
px.box(gdf, x="department", y="index_sdg3", hover_name="name",
       labels={"index_sdg3": "Good health index (0-100)"},
       title="SDG 3 index by department, 2018")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg03.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2018, ["geo_id", "index_sdg3"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg3", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg3": "Good health index (0-100)"},
          title="SDG 3: Good health and well-being, 2018")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales the nine indicators between the Atlas bounds, averages them and reproduces the published SDG 3 index (correlation above 0.9999).',
        code: `${PYTHON_SETUP}

# Each indicator at its own reference year: one row per municipality
df = geo.load("sdg03").groupby("geo_id").first()
df["name"] = geo.units("municipality").set_index("geo_id")["name"]

# Atlas bounds [worst, best]: rescale to 0-100 (100 = best), cap, average
bounds = {"sdg3_1_idca": [15.7, 100.0], "sdg3_2_imr": [60.0, 12.0],
          "sdg3_2_mrc": [80.0, 25.0], "sdg3_3_cdir": [10.4, 0.0],
          "sdg3_3_di": [4.89, 0.0], "sdg3_3_imr": [25.8, 0.0],
          "sdg3_3_ti": [158.7, 0.0], "sdg3_3_hivi": [416.7, 0.0],
          "sdg3_7_afr": [156.7, 0.0]}
scores = df[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)
df["computed"] = scores.mean(axis=1)
print("correlation:", df["computed"].corr(df["index_sdg3"]))

px.scatter(df, x="index_sdg3", y="computed", hover_name="name",
           labels={"index_sdg3": "Good health index (0-100), published",
                   "computed": "Index computed from its 9 indicators"},
           title="Reproducing the SDG 3 index")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Shows the average rescaled score (0–100) of each indicator across the 339 municipalities: the lowest bars lower the index the most.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg03").groupby("geo_id").first()
labels = geo.dictionary("sdg03").set_index("variable")["label"]

# Atlas bounds [worst, best]
bounds = {"sdg3_1_idca": [15.7, 100.0], "sdg3_2_imr": [60.0, 12.0],
          "sdg3_2_mrc": [80.0, 25.0], "sdg3_3_cdir": [10.4, 0.0],
          "sdg3_3_di": [4.89, 0.0], "sdg3_3_imr": [25.8, 0.0],
          "sdg3_3_ti": [158.7, 0.0], "sdg3_3_hivi": [416.7, 0.0],
          "sdg3_7_afr": [156.7, 0.0]}
scores = df[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)

mean = scores.mean().rename("score").rename_axis("variable").reset_index()
mean["indicator"] = mean["variable"].map(labels)
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 3: average score of each indicator")`,
      },
      {
        title: 'Rank the departments',
        text: 'Ranks the nine departments by the population-weighted mean of the SDG 3 index, with WorldPop population as weights.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg03", variables="index_sdg3", years=2018)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg3": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg3"), x="index_sdg3", y="department",
       labels={"index_sdg3": "Good health index (0-100), population-weighted"},
       title="SDG 3 index by department, 2018")`,
      },
      {
        title: 'Births in health facilities and infant mortality',
        text: 'Plots infant mortality (2016) against institutional birth coverage (2008–2012 average) for every municipality, coloured by department.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg03").groupby("geo_id", as_index=False).first()
units = geo.units("municipality").set_index("geo_id")
names = geo.units("department").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(units["name"])
df["department"] = df["geo_id"].map(units["department_id"]).map(names)
px.scatter(df, x="sdg3_1_idca", y="sdg3_2_imr", color="department",
           hover_name="name",
           labels={"sdg3_1_idca": "Institutional birth coverage (%)",
                   "sdg3_2_imr": "Infant mortality (per 1,000 births)"},
           title="Births in health facilities and infant mortality")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg04', type: 'indicator', section: 'indicators',
    title: 'SDG 4: Quality education',
    scope: '339 municipalities · 6 indicators and the SDG 4 index · 2012–2020',
    summary: 'The Municipal Atlas’s SDG 4 index of quality education and its six indicators of school dropout, adult education, literacy and qualified teachers, each stored at the year it was measured.',
    description: 'The SDG 4 (Quality education) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the goal’s targets are met, together with the six indicators behind it: the secondary-school dropout rates of boys and girls (2017) and the shares of qualified pre-primary and secondary teachers (2016), from the Ministry of Education’s administrative records (SEIE), and the share of adults aged 19 or older with higher education and the literacy rate of people aged 15 or older, from the 2012 Population and Housing Census (INE). Each indicator is rescaled linearly to 0–100 between a worst and a best value, so that higher is always better and values beyond the bounds are capped, and the index is the simple mean of the available rescaled indicators. The Atlas does not define a “qualified” teacher. Because its indicators refer to 2012, 2016 and 2017, the index is stored at 2017, the latest of them. The Atlas’s 2020 population and 2012 urbanization rate are included as context; they are not inputs of the index.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'education', 'literacy', 'school dropout', 'municipalities'],
    image: 'images/indicators/sdg04.webp',
    imageAlt: 'Map of the Quality education index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high on the altiplano of La Paz, Oruro and southern Potosí and in the main cities, low in Pando, parts of Beni and the northern Potosí, Chuquisaca and southern Cochabamba valleys',
    map: 'images/indicators/sdg04-map.webp',
    mapAlt: 'Map of the Quality education index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high on the altiplano of La Paz, Oruro and southern Potosí and in the main cities, low in Pando, parts of Beni and the northern Potosí, Chuquisaca and southern Cochabamba valleys. Legend: High 57.1 to 85.8 (143 municipalities), Middle 41.7 to 57.1 (139), Low 12.4 to 41.7 (57).',
    date: '2026-10-30', pinned: false, dataset: 'sdg04',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg04", variables="index_sdg4", years=2017), or every variable as a cross-section with geo.load("sdg04").groupby("geo_id").first(). The index is stored at 2017, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 4 index in its reference year, with municipal boundaries
gdf = geo.load("sdg04", variables="index_sdg4", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg4", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg4": "Quality education index (0-100)"},
          title="SDG 4: Quality education, 2017").show()

# The index's spread within each department
units = geo.units("municipality").set_index("geo_id")
names = geo.units("department").set_index("geo_id")["name"]
gdf["department"] = gdf["geo_id"].map(units["department_id"]).map(names)
px.box(gdf, x="department", y="index_sdg4", hover_name="name",
       labels={"index_sdg4": "Quality education index (0-100)"},
       title="SDG 4 index by department, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg04.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg4"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg4", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg4": "Quality education index (0-100)"},
          title="SDG 4: Quality education, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas’s worst and best values, averages them and checks the result against the published SDG 4 index.',
        code: `${PYTHON_SETUP}

# Worst and best value of each indicator (Atlas, Cuadro 17)
bounds = {"sdg4_1_ssdrm": (9.7, 0), "sdg4_1_ssdrf": (9.7, 0),
          "sdg4_4_phe": (2.8, 36.9), "sdg4_6_lr": (71.2, 99.8),
          "sdg4_c_qti": (0, 100), "sdg4_c_qts": (0, 100)}

# Every variable at its own year, one row per municipality
df = geo.load("sdg04").groupby("geo_id").first()
scores = df[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)
df["computed"] = scores.mean(axis=1)   # mean of the available indicators

df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="index_sdg4", y="computed", hover_name="name",
           labels={"index_sdg4": "Published SDG 4 index",
                   "computed": "Computed SDG 4 index"},
           title="Reproducing the SDG 4 index")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Compares the average rescaled score (0–100) of the six indicators across municipalities, showing which ones pull the SDG 4 index down most.',
        code: `${PYTHON_SETUP}

bounds = {"sdg4_1_ssdrm": (9.7, 0), "sdg4_1_ssdrf": (9.7, 0),
          "sdg4_4_phe": (2.8, 36.9), "sdg4_6_lr": (71.2, 99.8),
          "sdg4_c_qti": (0, 100), "sdg4_c_qts": (0, 100)}
df = geo.load("sdg04").groupby("geo_id").first()
scores = df[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)

# Mean score of each indicator, labelled from the dictionary
labels = geo.dictionary("sdg04").set_index("variable")["label"]
mean = scores.mean().rename(labels).rename_axis("indicator")
mean = mean.reset_index(name="score").sort_values("score")
px.bar(mean, x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 4 indicators: average score across municipalities")`,
      },
      {
        title: 'Boys’ and girls’ dropout',
        text: 'Plots the secondary dropout rates of boys and girls in 2017, municipality by municipality, coloured by the SDG 4 index.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg04", years=2017)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg4_1_ssdrf", y="sdg4_1_ssdrm", color="index_sdg4",
           hover_name="name",
           labels={"sdg4_1_ssdrf": "Secondary dropout rate, girls (%)",
                   "sdg4_1_ssdrm": "Secondary dropout rate, boys (%)",
                   "index_sdg4": "Quality education index (0-100)"},
           title="Secondary dropout of boys and girls, 2017")`,
      },
      {
        title: 'Rank the departments',
        text: 'Averages the SDG 4 index by department, weighting each municipality by its gridded population in 2017.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg04", variables="index_sdg4", years=2017)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg4": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg4"), x="index_sdg4", y="department",
       labels={"index_sdg4": "Quality education index (population-weighted)"},
       title="SDG 4 index by department, 2017")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg05', type: 'indicator', section: 'indicators',
    title: 'SDG 5: Gender equality',
    scope: '339 municipalities · 4 indicators and the SDG 5 index · 2012–2020',
    summary: 'The SDG 5 gender equality index of the Municipal Atlas of the SDGs and its four gender parity indicators in schooling, poverty and work, for every municipality.',
    description: 'The SDG 5 (Gender equality) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the four gender parity indicators behind it: parity in secondary-school dropout (2017, Ministry of Education records), and parity in years of schooling of people aged 25–35, in multidimensional poverty by sex of the household head and in labour-force participation (all 2012, from the Population and Housing Census, INE). Each indicator is rescaled to 0–100 between a worst and a best value (parity, or the average of the best municipalities), so that higher is always better and values beyond the bounds are capped, and the index is the simple mean of the available rescaled indicators: 100 means the targets are met. The index is stored at 2017, the latest year of its indicators. The parity indicators are published with one decimal only, so they reproduce the index only approximately. Labour participation parity is missing for Huachacalla. The Atlas’s 2020 population and 2012 urbanization rate are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'gender', 'gender parity', 'municipalities', 'census'],
    image: 'images/indicators/sdg05.webp',
    imageAlt: 'Map of the gender equality index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high across much of Beni, Tarija and the southern altiplano of Oruro and Potosí, middle across most of Santa Cruz, Pando and the Cochabamba and Chuquisaca valleys, low in clusters on the La Paz altiplano around Lake Titicaca and in the highlands of Oruro, Cochabamba and northern Potosí',
    map: 'images/indicators/sdg05-map.webp',
    mapAlt: 'Map of the gender equality index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high across much of Beni, Tarija and the southern altiplano of Oruro and Potosí, middle across most of Santa Cruz, Pando and the Cochabamba and Chuquisaca valleys, low in clusters on the La Paz altiplano around Lake Titicaca and in the highlands of Oruro, Cochabamba and northern Potosí. Legend: High 77.8 to 93.5 (109 municipalities), Middle 65.2 to 77.8 (162), Low 37.8 to 65.2 (68).',
    date: '2026-10-30', pinned: false, dataset: 'sdg05',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg05", variables="index_sdg5", years=2017). The index is stored at 2017, the latest reference year of its indicators (three of the four refer to 2012).',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 5 index in its reference year, with municipal boundaries
gdf = geo.load("sdg05", variables="index_sdg5", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg5", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg5": "Gender equality index (0-100)"},
          title="SDG 5: Gender equality, 2017").show()

# Municipal values by department
names = geo.units("department").set_index("geo_id")["name"]
gdf["department"] = gdf["geo_id"].str[:5].map(names)
px.box(gdf, x="department", y="index_sdg5", hover_name="name",
       labels={"index_sdg5": "Gender equality index (0-100)"},
       title="Gender equality index by department, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg05.csv")  # geo_id, year, indicators
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg5"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg5", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg5": "Gender equality index (0-100)"},
          title="SDG 5: Gender equality, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each parity indicator between its worst and best value, caps it at 0–100 and averages them, then compares the result with the published index; the match is close but approximate (r = 0.965, mean absolute difference 2.2 points), because the parity indicators are published with one decimal and the Atlas computed the index from unrounded values.',
        code: `${PYTHON_SETUP}
import pandas as pd

# Atlas bounds of each component: (worst, best)
bounds = {"sdg5_1_gpsd": (0, 1), "sdg5_1_gpyp": (0.6, 1),
          "sdg5_1_gpmpi": (0.623, 1), "sdg5_5_gpop": (0.42, 0.95)}

# Cross-section: each component at its own reference year
df = geo.load("sdg05").groupby("geo_id").first()
score = pd.DataFrame({v: (100 * (df[v] - w) / (b - w)).clip(0, 100)
                      for v, (w, b) in bounds.items()})
df["computed"] = score.mean(axis=1)    # missing components are skipped
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="computed", y="index_sdg5", hover_name="name",
           labels={"computed": "Computed index",
                   "index_sdg5": "Gender equality index (0-100)"},
           title="SDG 5 index: computed vs published")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Averages the rescaled score of each indicator over the municipalities: parity in labour participation is furthest from its target.',
        code: `${PYTHON_SETUP}
import pandas as pd

bounds = {"sdg5_1_gpsd": (0, 1), "sdg5_1_gpyp": (0.6, 1),
          "sdg5_1_gpmpi": (0.623, 1), "sdg5_5_gpop": (0.42, 0.95)}
df = geo.load("sdg05").groupby("geo_id").first()
labels = geo.dictionary("sdg05").set_index("variable")["label"]

scores = pd.DataFrame({
    "indicator": [labels[v] for v in bounds],
    "score": [(100 * (df[v] - w) / (b - w)).clip(0, 100).mean()
              for v, (w, b) in bounds.items()],
})
px.bar(scores.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 5 components: distance to target")`,
      },
      {
        title: 'Rank the departments',
        text: 'Aggregates the index to departments as population-weighted means.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg05", variables="index_sdg5", years=2017)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg5": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg5"), x="index_sdg5", y="department",
       labels={"index_sdg5": "Gender equality index (population-weighted)"},
       title="SDG 5 index by department, 2017")`,
      },
      {
        title: 'Women’s work and urbanization',
        text: 'Plots gender parity in labour participation against the urbanization rate, both from the 2012 census.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg05", variables=["sdg5_5_gpop", "urbano_2012"], years=2012)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="urbano_2012", y="sdg5_5_gpop", hover_name="name",
           labels={"urbano_2012": "Urbanization rate (%)",
                   "sdg5_5_gpop": "Gender parity in labour participation"},
           title="Gender parity in labour participation and urbanization, 2012")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg06', type: 'indicator', section: 'indicators',
    title: 'SDG 6: Clean water and sanitation',
    scope: '339 municipalities · 3 indicators and the SDG 6 index · 2012–2020',
    summary: 'The SDG 6 index of the Municipal Atlas of the SDGs and its three indicators of drinking water, sanitation and wastewater treatment in 2017, for every Bolivian municipality.',
    description: 'The SDG 6 (Clean water and sanitation) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the three indicators behind it, all for 2017: drinking water coverage and sanitation coverage (% of the population, unpublished official data of the Vice-Ministry of Drinking Water and Basic Sanitation, whose methodology the Atlas does not describe) and the share of wastewater treated (from the 2018 performance study of the regulated water and sewerage providers by the water regulator AAPS and the Ministry of Environment and Water). Each indicator is rescaled linearly to 0–100 between a worst and a best value, capped at both ends so that higher is always better, and the index (0–100, 100 = targets met) is the simple mean of the rescaled indicators. Treated wastewater is 0 in 311 municipalities and above 100 in six, as in the source. The Atlas population (2020) and urbanization rate (2012 census) are included as context; they are not inputs of the index.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social', 'Environment'], tags: ['SDGs', 'water', 'sanitation', 'wastewater', 'municipalities'],
    image: 'images/indicators/sdg06.webp',
    imageAlt: 'Map of the Clean water and sanitation index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high in Tarija and the Chaco and in a few municipalities of Santa Cruz and the main cities, middle across most of the lowlands of Santa Cruz, Beni and Pando, low across the altiplano and valleys of La Paz, Oruro, Cochabamba, Potosí and Chuquisaca and in parts of Beni and Pando',
    map: 'images/indicators/sdg06-map.webp',
    mapAlt: 'Map of the Clean water and sanitation index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high in Tarija and the Chaco and in a few municipalities of Santa Cruz and the main cities, middle across most of the lowlands of Santa Cruz, Beni and Pando, low across the altiplano and valleys of La Paz, Oruro, Cochabamba, Potosí and Chuquisaca and in parts of Beni and Pando. Legend: High 55.8 to 95.0 (27 municipalities), Middle 30.9 to 55.8 (179), Low 0.0 to 30.9 (133).',
    date: '2026-10-30', pinned: false, dataset: 'sdg06',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg06", variables="index_sdg6", years=2017). The index is stored at 2017, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 6 index in 2017, with municipal boundaries
gdf = geo.load("sdg06", variables="index_sdg6", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg6", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg6": "Clean water and sanitation index (0-100)"},
          title="SDG 6: Clean water and sanitation, 2017").show()

# Drinking water against sanitation coverage
df = geo.load("sdg06", years=2017)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg6_1_dwc", y="sdg6_2_sc", hover_name="name",
           labels={"sdg6_1_dwc": "Drinking water coverage (%)",
                   "sdg6_2_sc": "Sanitation coverage (%)"},
           title="Water and sanitation coverage, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg06.csv")   # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg6"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg6", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg6": "Clean water and sanitation index (0-100)"},
          title="SDG 6: Clean water and sanitation, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between its worst and best value, caps it at 0 and 100, averages the three and checks the result against the published SDG 6 index.',
        code: `${PYTHON_SETUP}
import pandas as pd

# Worst and best values of each indicator (Atlas, Cuadro 17)
bounds = {"sdg6_1_dwc": (28.4, 100), "sdg6_2_sc": (5.7, 100),
          "sdg6_3_wwt": (0, 100)}

df = geo.load("sdg06").groupby("geo_id").first()   # each variable at its year
scores = pd.DataFrame({v: (100 * (df[v] - w) / (b - w)).clip(0, 100)
                       for v, (w, b) in bounds.items()})
df["computed"] = scores.mean(axis=1)
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
print(df["computed"].corr(df["index_sdg6"]))

px.scatter(df, x="computed", y="index_sdg6", hover_name="name",
           labels={"computed": "Computed index",
                   "index_sdg6": "Clean water and sanitation index (0-100)"},
           title="Computed vs published SDG 6 index")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Shows the average rescaled score (0–100) of each indicator across the 339 municipalities: treated wastewater, zero in most of them, pulls the index down most.',
        code: `${PYTHON_SETUP}
import pandas as pd

bounds = {"sdg6_1_dwc": (28.4, 100), "sdg6_2_sc": (5.7, 100),
          "sdg6_3_wwt": (0, 100)}
labels = {"sdg6_1_dwc": "Drinking water coverage (%)",
          "sdg6_2_sc": "Sanitation coverage (%)",
          "sdg6_3_wwt": "Wastewater treated (%)"}

df = geo.load("sdg06", years=2017)
rows = [{"indicator": labels[v],
         "score": (100 * (df[v] - w) / (b - w)).clip(0, 100).mean()}
        for v, (w, b) in bounds.items()]
px.bar(pd.DataFrame(rows), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="Average score of each SDG 6 indicator, 2017")`,
      },
      {
        title: 'Rank the departments',
        text: 'Ranks the nine departments by their population-weighted SDG 6 index.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg06", variables="index_sdg6", years=2017)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg6": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg6"), x="index_sdg6", y="department",
       labels={"index_sdg6": "Clean water and sanitation index (0-100)"},
       title="SDG 6 index by department (population-weighted), 2017")`,
      },
      {
        title: 'Urbanization and sanitation',
        text: 'Plots sanitation coverage in 2017 against the 2012 urbanization rate, coloured by department.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg06").groupby("geo_id", as_index=False).first()
units = geo.units("municipality").set_index("geo_id")
departments = geo.units("department").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(units["name"])
df["department"] = df["geo_id"].map(units["department_id"]).map(departments)
px.scatter(df, x="urbano_2012", y="sdg6_2_sc", color="department",
           hover_name="name",
           labels={"urbano_2012": "Urbanization rate (%)",
                   "sdg6_2_sc": "Sanitation coverage (%)"},
           title="Urbanization (2012) and sanitation coverage (2017)")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg07', type: 'indicator', section: 'indicators',
    title: 'SDG 7: Affordable and clean energy',
    scope: '339 municipalities · 4 indicators and the SDG 7 index · 2012–2016',
    summary: 'The SDG 7 clean energy index and its four indicators of electricity coverage, residential electricity use, clean cooking energy and energy CO2 emissions per person.',
    description: 'The SDG 7 (Affordable and clean energy) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the goal’s targets are met, with the four indicators behind it: electricity coverage (% of the population) and clean cooking energy (% of households cooking with electricity, piped natural gas or LPG), both from the 2012 Population and Housing Census (INE), and residential electricity use (kWh per person) and energy-related CO2 emissions (t per person), both for 2016 from Andersen, Branisa & Calderón (2019). Each indicator is rescaled to 0–100 between a worst and a best value, with higher always better and values beyond the bounds capped, and the index is the simple mean of the rescaled indicators. Every municipality has all four indicators. The indicators refer to different years, so each is stored at its own reference year and the index at 2016, the latest of them. The Atlas population (2020) and urbanization rate (2012) are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2016', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Economy', 'Environment'], tags: ['SDGs', 'energy', 'electricity', 'CO2 emissions', 'municipalities'],
    image: 'images/indicators/sdg07.webp',
    imageAlt: 'Map of the Clean energy index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high in the departmental capitals and their metropolitan areas (Santa Cruz, La Paz and El Alto, the Cochabamba valley, Tarija, Trinidad, Cobija), low in the northern Potosí and Chuquisaca valleys, the rural altiplano of La Paz and Oruro and Charagua in the Chaco',
    map: 'images/indicators/sdg07-map.webp',
    mapAlt: 'Map of the Clean energy index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high in the departmental capitals and their metropolitan areas (Santa Cruz, La Paz and El Alto, the Cochabamba valley, Tarija, Trinidad, Cobija), low in the northern Potosí and Chuquisaca valleys, the rural altiplano of La Paz and Oruro and Charagua in the Chaco. Legend: High 63.4 to 96.5 (74 municipalities), Middle 45.5 to 63.4 (142), Low 24.9 to 45.5 (123).',
    date: '2026-10-30', pinned: false, dataset: 'sdg07',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg07", variables="index_sdg7", years=2016). The index is stored at 2016, the latest reference year of its indicators (two of them are from 2012).',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 7 index in 2016, with municipal boundaries
gdf = geo.load("sdg07", variables="index_sdg7", years=2016, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg7", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg7": "Clean energy index (0-100)"},
          title="SDG 7: Affordable and clean energy, 2016").show()

# Electricity coverage (2012) against clean cooking energy (2012)
df = geo.load("sdg07", years=2012)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg7_1_ec", y="sdg7_1_cce", hover_name="name",
           labels={"sdg7_1_ec": "Electricity coverage (%)",
                   "sdg7_1_cce": "Clean cooking energy (% of households)"},
           title="Electricity and clean cooking, 2012")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg07.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2016, ["geo_id", "index_sdg7"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg7", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg7": "Clean energy index (0-100)"},
          title="SDG 7: Affordable and clean energy, 2016")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas’s worst and best values, caps it at 0–100 and averages the four, which reproduces the published SDG 7 index to within 0.2 points.',
        code: `${PYTHON_SETUP}

# Every variable at its own reference year, one row per municipality
df = geo.load("sdg07").groupby("geo_id").first()
df["name"] = geo.units("municipality").set_index("geo_id")["name"]

# Worst and best values of each indicator (Atlas, Cuadro 17)
bounds = {"sdg7_1_ec": (25.6, 100), "sdg7_1_rec": (9, 563),
          "sdg7_1_cce": (6.9, 97), "sdg7_3_co2epc": (8, 0)}
scores = df[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)
df["computed"] = scores.mean(axis=1)    # missing indicators are skipped

px.scatter(df, x="computed", y="index_sdg7", hover_name="name",
           labels={"computed": "Computed index (0-100)",
                   "index_sdg7": "Clean energy index (0-100)"},
           title="SDG 7 index: computed vs published")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Averages each indicator’s 0–100 score over the municipalities: residential electricity use scores lowest, energy CO2 emissions highest.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg07").groupby("geo_id").first()
bounds = {"sdg7_1_ec": (25.6, 100), "sdg7_1_rec": (9, 563),
          "sdg7_1_cce": (6.9, 97), "sdg7_3_co2epc": (8, 0)}
labels = {"sdg7_1_ec": "Electricity coverage (%)",
          "sdg7_1_rec": "Residential electricity use (kWh per person)",
          "sdg7_1_cce": "Clean cooking energy (% of households)",
          "sdg7_3_co2epc": "Energy CO2 emissions (t per person)"}
rows = []
for var, (worst, best) in bounds.items():
    score = (100 * (df[var] - worst) / (best - worst)).clip(0, 100)
    rows.append({"indicator": labels[var], "score": score.mean()})
px.bar(pd.DataFrame(rows).sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean score (0-100)", "indicator": ""},
       title="SDG 7: mean score of each indicator")`,
      },
      {
        title: 'Rank the departments',
        text: 'Averages the index by department, weighting each municipality by its gridded population in 2016.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg07", variables="index_sdg7", years=2016)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg7": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg7"), x="index_sdg7", y="department",
       labels={"index_sdg7": "Clean energy index (0-100, population-weighted)"},
       title="SDG 7 index by department, 2016")`,
      },
      {
        title: 'Clean energy and night-time lights',
        text: 'Links the 2016 index with the observatory’s night-time lights per capita for the same year.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg07", variables="index_sdg7", years=2016)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2016)
df = sdg.merge(ntl, on=["geo_id", "year"])
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="ln_t400NTLpc", y="index_sdg7", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "index_sdg7": "Clean energy index (0-100)"},
           title="Clean energy and night-time lights, 2016")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg08', type: 'indicator', section: 'indicators',
    title: 'SDG 8: Decent work and economic growth',
    scope: '339 municipalities · 7 indicators and the SDG 8 index · 2012–2018',
    summary: 'The SDG 8 index of decent work and economic growth for the 339 municipalities, with its seven indicators of labour participation, youth inactivity, idle electricity meters, bank branches and migration intermediation.',
    description: 'The SDG 8 (Decent work and economic growth) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) and the seven indicators behind it, for all 339 municipalities. Four come from the 2012 Population and Housing Census (INE): the labour participation rates of men and women aged 10 or older and the shares of young men and women aged 15–24 who neither study nor take part in the labour market. The others are the share of residential electricity meters with zero consumption in May 2016 (Andersen, Branisa & Calderón, 2019), commercial bank branches per 100,000 people in 2018 (ASFI and INE projections) and an index of intermediation in internal migration built from the 2012 census (Rocha-Portugal, Vera-Cossío & Wanderley, 2020). The index runs from 0 to 100, where 100 means the targets are met: each indicator is rescaled linearly between a worst and a best value, capped at 0 and 100, and the index is the simple mean of the available rescaled indicators. The zero-consumption meters are missing for 23 municipalities, whose index averages the other six. Because the indicators refer to different years, the index is stored at 2018, the latest of them. The Atlas population (2020) and urbanization rate (2012) are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2018', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Economy'], tags: ['SDGs', 'employment', 'labour participation', 'financial inclusion', 'municipalities'],
    image: 'images/indicators/sdg08.webp',
    imageAlt: 'Map of the Decent work and growth index (0-100) in 2018 across 339 Bolivian municipalities in three natural-break classes: high in the Yungas of La Paz, the Chapare and the cities of La Paz, El Alto, Cochabamba, Santa Cruz de la Sierra and Tarija, low in Pando, the western altiplano of Oruro, southwestern Potosí and the Chaco and Chiquitanía of Santa Cruz',
    map: 'images/indicators/sdg08-map.webp',
    mapAlt: 'Map of the Decent work and growth index (0-100) in 2018 across 339 Bolivian municipalities in three natural-break classes: high in the Yungas of La Paz, the Chapare and the cities of La Paz, El Alto, Cochabamba, Santa Cruz de la Sierra and Tarija, low in Pando, the western altiplano of Oruro, southwestern Potosí and the Chaco and Chiquitanía of Santa Cruz. Legend: High 51.8 to 72.5 (85 municipalities), Middle 38.5 to 51.8 (162), Low 14.9 to 38.5 (92).',
    date: '2026-10-30', pinned: false, dataset: 'sdg08',
    notice: 'Each variable has values only in its reference year: load one with its year, e.g. geo.load("sdg08", variables="index_sdg8", years=2018). The index is stored at 2018, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 8 index (stored at 2018), with municipal boundaries
gdf = geo.load("sdg08", variables="index_sdg8", years=2018, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg8", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg8": "Decent work and growth index (0-100)"},
          title="SDG 8: Decent work and economic growth, 2018").show()

# Every variable at its own year: bank branches and the index
df = geo.load("sdg08").groupby("geo_id", as_index=False).first()
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg8_10_dbb", y="index_sdg8", hover_name="name",
           labels={"sdg8_10_dbb": "Bank branches per 100,000 people",
                   "index_sdg8": "Decent work and growth index (0-100)"},
           title="Bank branches (2018) and the SDG 8 index")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg08.csv")   # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2018, ["geo_id", "index_sdg8"]].dropna()
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg8", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg8": "Decent work and growth index (0-100)"},
          title="SDG 8: Decent work and economic growth, 2018")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales the seven indicators between the Atlas bounds and averages them, which reproduces the published SDG 8 index.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg08").groupby("geo_id").first()   # each variable at its year
bounds = {"sdg8_4_rem": (39.1, 0.3), "sdg8_5_oprm": (61.2, 83.0),
          "sdg8_5_ofrm": (30.6, 75.2), "sdg8_6_mlm": (40.0, 8.0),
          "sdg8_6_wlm": (40.0, 8.0), "sdg8_10_dbb": (0.0, 60.0),
          "sdg8_11_idi": (0.01, 13.26)}            # (worst, best) per indicator
scores = pd.DataFrame({v: (100 * (df[v] - w) / (b - w)).clip(0, 100)
                       for v, (w, b) in bounds.items()})
df["computed"] = scores.mean(axis=1)              # missing indicators skipped
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="computed", y="index_sdg8", hover_name="name",
           labels={"computed": "Computed index (0-100)",
                   "index_sdg8": "Decent work and growth index (0-100)"},
           title="SDG 8 index: computed vs published")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Averages each indicator’s 0–100 score over the municipalities to show which ones pull the SDG 8 index down most.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg08").groupby("geo_id").first()
bounds = {"sdg8_4_rem": (39.1, 0.3), "sdg8_5_oprm": (61.2, 83.0),
          "sdg8_5_ofrm": (30.6, 75.2), "sdg8_6_mlm": (40.0, 8.0),
          "sdg8_6_wlm": (40.0, 8.0), "sdg8_10_dbb": (0.0, 60.0),
          "sdg8_11_idi": (0.01, 13.26)}
scores = pd.DataFrame({v: (100 * (df[v] - w) / (b - w)).clip(0, 100)
                       for v, (w, b) in bounds.items()})
labels = geo.dictionary("sdg08").set_index("variable")["label"]
mean = scores.mean().rename("score").rename_axis("variable").reset_index()
mean["indicator"] = mean["variable"].map(labels)
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean score (0-100, 100 = target met)", "indicator": ""},
       title="SDG 8: mean score of each indicator")`,
      },
      {
        title: 'Women’s and men’s labour participation',
        text: 'Compares the labour participation rates of women and men in 2012, municipality by municipality and by department.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg08", variables=["sdg8_5_oprm", "sdg8_5_ofrm"], years=2012)
units = geo.units("municipality").set_index("geo_id")
departments = geo.units("department").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(units["name"])
df["department"] = df["geo_id"].map(units["department_id"]).map(departments)
px.scatter(df, x="sdg8_5_oprm", y="sdg8_5_ofrm", color="department",
           hover_name="name",
           labels={"sdg8_5_oprm": "Male labour participation rate (%)",
                   "sdg8_5_ofrm": "Female labour participation rate (%)"},
           title="Labour participation of women and men, 2012")`,
      },
      {
        title: 'Rank the departments',
        text: 'Averages the SDG 8 index over each department’s municipalities, weighted by their population in 2018.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg08", variables="index_sdg8", years=2018)
dep = geo.aggregate(df, to="department", rules={"index_sdg8": "weighted_mean:pop"},
                    weights=geo.load("pop"))
dep["department"] = dep["geo_id"].map(geo.units("department")
                                      .set_index("geo_id")["name"])
px.bar(dep.sort_values("index_sdg8"), x="index_sdg8", y="department",
       labels={"index_sdg8": "Decent work and growth index (population-weighted)"},
       title="SDG 8 index by department, 2018")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg09', type: 'indicator', section: 'indicators',
    title: 'SDG 9: Industry, innovation and infrastructure',
    scope: '339 municipalities · 5 indicators and the SDG 9 index · 2012–2019',
    summary: 'The SDG 9 index of the Municipal Atlas of the SDGs and its five indicators of road and rail links, phone access, mobile antennas and school technology, for every municipality.',
    description: 'The SDG 9 (Industry, innovation and infrastructure) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) and the five indicators behind it, for all 339 municipalities: the number of railways and primary roads of the national trunk network entering or leaving the municipality (2019, Conservación Internacional Bolivia), the share of households with a fixed or mobile phone (2012 census, INE), and three AGETIC measures for 2016: mobile radio base stations per 1,000 people, Kuaa laptops per 100 school-age people and the share of public schools with technology floors. The index runs from 0 (worst) to 100 (targets met): each indicator is rescaled linearly between a worst and a best value, capped at 0 and 100, and the index is the simple mean of the available rescaled indicators. Schools with technology floors is missing for 16 municipalities, whose index averages the other four. The components refer to different years, so the index is stored at 2019, the latest of them. The Atlas population (2020) and urbanization rate (2012) are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2019', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Economy'], tags: ['SDGs', 'infrastructure', 'roads', 'telecommunications', 'municipalities'],
    image: 'images/indicators/sdg09.webp',
    imageAlt: 'Map of the Industry and infrastructure index (0-100) in 2019 across 339 Bolivian municipalities in three natural-break classes: high in Tarija and along the La Paz–Oruro–Cochabamba–Santa Cruz corridor, low in Pando, the rural valleys of Chuquisaca, northern Potosí and Cochabamba, and parts of northern La Paz',
    map: 'images/indicators/sdg09-map.webp',
    mapAlt: 'Map of the Industry and infrastructure index (0-100) in 2019 across 339 Bolivian municipalities in three natural-break classes: high in Tarija and along the La Paz–Oruro–Cochabamba–Santa Cruz corridor, low in Pando, the rural valleys of Chuquisaca, northern Potosí and Cochabamba, and parts of northern La Paz. Legend: High 46.8 to 78.9 (80 municipalities), Middle 28.6 to 46.8 (136), Low 0.6 to 28.6 (123).',
    date: '2026-10-30', pinned: false, dataset: 'sdg09',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg09", variables="index_sdg9", years=2019). The index is stored at 2019, the latest reference year of its indicators (2012, 2016 and 2019).',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 9 index at its reference year, with municipal boundaries
gdf = geo.load("sdg09", variables="index_sdg9", years=2019, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg9", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg9": "Industry and infrastructure index (0-100)"},
          title="SDG 9 index, 2019").show()

# The index by department
names = geo.units("department").set_index("geo_id")["name"]
gdf["department"] = gdf["geo_id"].str[:5].map(names)    # BO-DD
px.box(gdf, x="department", y="index_sdg9", hover_name="name",
       labels={"index_sdg9": "Industry and infrastructure index (0-100)"},
       title="SDG 9 index by department, 2019")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg09.csv")
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2019, ["geo_id", "index_sdg9"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg9", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg9": "Industry and infrastructure index (0-100)"},
          title="SDG 9 index, 2019")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas worst and best values, averages them and checks the result against the published SDG 9 index.',
        code: `${PYTHON_SETUP}

import pandas as pd

# Every variable at its own reference year: one row per municipality
df = geo.load("sdg09").groupby("geo_id").first()
names = geo.units("municipality").set_index("geo_id")["name"]
df["name"] = df.index.map(names)

# Atlas bounds of each indicator: [worst, best]
bounds = {"sdg9_1_routes": [0.0, 2.0], "sdg9_5_cd": [0.0, 6.5],
          "sdg9_5_eutf": [0.0, 80.0], "sdg9_c_mnc": [8.4, 100.0],
          "sdg9_c_drb": [0.3, 11.4]}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)    # missing indicators are skipped

px.scatter(df, x="computed", y="index_sdg9", hover_name="name",
           labels={"computed": "Computed index (0-100)",
                   "index_sdg9": "Industry and infrastructure index (0-100)"},
           title="SDG 9 index: computed vs published")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Averages each indicator’s 0–100 score across municipalities to show where the goal is furthest from its target.',
        code: `${PYTHON_SETUP}

import pandas as pd

df = geo.load("sdg09").groupby("geo_id").first()
bounds = {"sdg9_1_routes": [0.0, 2.0], "sdg9_5_cd": [0.0, 6.5],
          "sdg9_5_eutf": [0.0, 80.0], "sdg9_c_mnc": [8.4, 100.0],
          "sdg9_c_drb": [0.3, 11.4]}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)

labels = geo.dictionary("sdg09").set_index("variable")["label"]
mean = scores.mean().rename_axis("variable").reset_index(name="score")
mean["indicator"] = mean["variable"].map(labels)
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean score (0-100)", "indicator": ""},
       title="Mean SDG 9 indicator scores across municipalities")`,
      },
      {
        title: 'Departments ranked by population-weighted index',
        text: 'Aggregates the municipal index to departments, weighting each municipality by its 2019 population.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg09", variables="index_sdg9", years=2019)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg9": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg9"), x="index_sdg9", y="department",
       labels={"index_sdg9": "Industry and infrastructure index (0-100)"},
       title="SDG 9 index by department (population-weighted), 2019")`,
      },
      {
        title: 'Infrastructure and night-time lights',
        text: 'Links the SDG 9 index to the trend of night-time lights per capita in 2019, a satellite proxy for economic activity.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg09", variables="index_sdg9", years=2019)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2019)
df = sdg.merge(ntl, on=["geo_id", "year"])
names = geo.units("municipality").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(names)
px.scatter(df, x="ln_t400NTLpc", y="index_sdg9", hover_name="name",
           labels={"ln_t400NTLpc": "Log lights per capita (trend)",
                   "index_sdg9": "Industry and infrastructure index (0-100)"},
           title="SDG 9 index and night-time lights, 2019")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg10', type: 'indicator', section: 'indicators',
    title: 'SDG 10: Reduced inequalities',
    scope: '339 municipalities · 3 indicators and the SDG 10 index · 2012–2020',
    summary: 'The Atlas’s SDG 10 index for every municipality, built from inequality in schooling, inequality in household electricity use and the share of people who do not speak Spanish.',
    description: 'The SDG 10 (Reduced inequalities) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the goal’s targets are met, with the three indicators behind it: the Gini coefficient of years of schooling of people aged 25–65 and the share of the population aged 3 or older who do not speak Spanish, both from the 2012 Population and Housing Census (INE), and the inequality of residential electricity consumption per household in 2016, a generalised entropy index GE(-1) from electricity-meter records (Andersen, Branisa & Calderón, 2019). Each indicator is rescaled linearly to 0–100 between a worst and a best value, capped at both ends, and the index is the simple mean of the available rescaled indicators. Electricity inequality is missing for 24 municipalities, whose index averages the other two, and its values are on the Atlas’s own scale (apparently GE(-1) × 100). The index is stored at 2016, the latest year of its indicators; the Atlas’s 2020 population and 2012 urbanization rate are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'inequality', 'education', 'electricity', 'language'],
    image: 'images/indicators/sdg10.webp',
    imageAlt: 'Map of the Reduced inequalities index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high on the altiplano of La Paz and Oruro and in southwestern Potosí, low in the valleys of Cochabamba, northern Potosí and Chuquisaca and in central Santa Cruz',
    map: 'images/indicators/sdg10-map.webp',
    mapAlt: 'Map of the Reduced inequalities index (0-100) in 2016 across 339 Bolivian municipalities in three natural-break classes: high on the altiplano of La Paz and Oruro and in southwestern Potosí, low in the valleys of Cochabamba, northern Potosí and Chuquisaca and in central Santa Cruz. Legend: High 73.4 to 95.7 (107 municipalities), Middle 55.1 to 73.4 (154), Low 10.3 to 55.1 (78).',
    date: '2026-10-30', pinned: false, dataset: 'sdg10',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg10", variables="index_sdg10", years=2016). The index is stored at 2016, the latest year of its indicators (two of them refer to 2012).',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 10 index in its year, with municipal boundaries
gdf = geo.load("sdg10", variables="index_sdg10", years=2016, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg10", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg10": "Reduced inequalities index (0-100)"},
          title="SDG 10: Reduced inequalities, 2016").show()

# Schooling inequality against the index (each variable at its own year)
cs = geo.load("sdg10").groupby("geo_id", as_index=False).first()
cs["name"] = cs["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(cs, x="sdg10_2_gcye", y="index_sdg10", hover_name="name",
           labels={"sdg10_2_gcye": "Gini of years of schooling",
                   "index_sdg10": "Reduced inequalities index (0-100)"},
           title="Schooling inequality and the SDG 10 index")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg10.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2016, ["geo_id", "index_sdg10"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg10", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg10": "Reduced inequalities index (0-100)"},
          title="SDG 10: Reduced inequalities, 2016")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas’s worst and best values, averages the available scores and compares the result with the published index (they match to within 0.7 points, from the rounding of the published Gini).',
        code: `${PYTHON_SETUP}

# Atlas bounds for each indicator: [worst, best]
bounds = {"sdg10_2_gcye": [0.578, 0.214],
          "sdg10_2_iec": [228.0, 11.0],
          "sdg10_2_nssp": [51.8, 1.1]}
cs = geo.load("sdg10").groupby("geo_id").first()   # each variable at its year
scores = cs[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (cs[var] - worst) / (best - worst)).clip(0, 100)
cs["computed"] = scores.mean(axis=1)               # missing indicators skipped
cs["name"] = geo.units("municipality").set_index("geo_id")["name"]
print(cs["computed"].corr(cs["index_sdg10"]))
px.scatter(cs, x="index_sdg10", y="computed", hover_name="name",
           labels={"index_sdg10": "Published index (0-100)",
                   "computed": "Computed index (0-100)"},
           title="SDG 10 index: computed vs published")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Shows the average rescaled score (0–100) of each indicator across municipalities: the lower the score, the further the municipalities are from the target.',
        code: `${PYTHON_SETUP}
import pandas as pd

bounds = {"sdg10_2_gcye": [0.578, 0.214],
          "sdg10_2_iec": [228.0, 11.0],
          "sdg10_2_nssp": [51.8, 1.1]}
labels = geo.dictionary("sdg10").set_index("variable")["label"]
cs = geo.load("sdg10").groupby("geo_id").first()
rows = []
for var, (worst, best) in bounds.items():
    score = (100 * (cs[var] - worst) / (best - worst)).clip(0, 100)
    rows.append({"indicator": labels[var], "score": score.mean()})
px.bar(pd.DataFrame(rows).sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 10: average score by indicator")`,
      },
      {
        title: 'Rank the departments',
        text: 'Ranks the nine departments by the population-weighted mean of the SDG 10 index in 2016.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg10", variables="index_sdg10", years=2016)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg10": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg10"), x="index_sdg10", y="department",
       labels={"index_sdg10": "Reduced inequalities index (population-weighted)",
               "department": ""},
       title="SDG 10 index by department, 2016")`,
      },
      {
        title: 'Language and schooling inequality',
        text: 'Compares the share of people who do not speak Spanish with the Gini of years of schooling in 2012, by department.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg10", variables=["sdg10_2_nssp", "sdg10_2_gcye"], years=2012)
units = geo.units("municipality").set_index("geo_id")
names = geo.units("department").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(units["name"])
df["department"] = df["geo_id"].map(units["department_id"]).map(names)
px.scatter(df, x="sdg10_2_nssp", y="sdg10_2_gcye", color="department",
           hover_name="name",
           labels={"sdg10_2_nssp": "Non-Spanish speakers, age 3+ (%)",
                   "sdg10_2_gcye": "Gini of years of schooling"},
           title="Language and schooling inequality, 2012")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg11', type: 'indicator', section: 'indicators',
    title: 'SDG 11: Sustainable cities and communities',
    scope: '339 municipalities · 3 indicators and the SDG 11 index · 2012–2020',
    summary: 'The SDG 11 index of the Municipal Atlas of the SDGs for every municipality, with its three indicators of housing, sanitation and public transport.',
    description: 'The SDG 11 (Sustainable cities and communities) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the targets are met. It summarises three indicators: the overcrowding rate and the share of households without a toilet, both from the 2012 Population and Housing Census (INE), and public transport seats per 1,000 people, from the municipal vehicle register (RUAT) and the cable car and municipal bus fleets, labelled 2017 by the Atlas. Each indicator is rescaled to 0–100 between a worst and a best value, capped at the bounds, and the index is the simple mean of the rescaled indicators. Every municipality has all three, but 184 have no registered public transport seats, so that component scores 0 for most of the country. The index is stored at 2017, the latest year of its indicators; the Atlas population (2020) and urbanization rate (2012) are included as context.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Social'], tags: ['SDGs', 'cities', 'housing', 'public transport', 'municipalities'],
    image: 'images/indicators/sdg11.webp',
    imageAlt: 'Map of the Sustainable cities index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high in La Paz and El Alto, the Cochabamba valley, the cities of Oruro and Potosí, around Santa Cruz and in much of Tarija, low across the western Oruro altiplano, northern Potosí, the Chuquisaca valleys and Charagua in the Chaco',
    map: 'images/indicators/sdg11-map.webp',
    mapAlt: 'Map of the Sustainable cities index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high in La Paz and El Alto, the Cochabamba valley, the cities of Oruro and Potosí, around Santa Cruz and in much of Tarija, low across the western Oruro altiplano, northern Potosí, the Chuquisaca valleys and Charagua in the Chaco. Legend: High 47.6 to 94.8 (58 municipalities), Middle 31.1 to 47.6 (183), Low 3.0 to 31.1 (98).',
    date: '2026-10-30', pinned: false, dataset: 'sdg11',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg11", variables="index_sdg11", years=2017). The index is stored at 2017, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 11 index in 2017, with municipal boundaries
gdf = geo.load("sdg11", variables="index_sdg11", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg11", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg11": "Sustainable cities index (0-100)"},
          title="SDG 11: Sustainable cities and communities, 2017").show()

# Overcrowding and households without a toilet (both 2012)
df = geo.load("sdg11", years=2012)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg11_1_hno", y="sdg11_1_hocr", hover_name="name",
           labels={"sdg11_1_hno": "Households without a toilet (%)",
                   "sdg11_1_hocr": "Overcrowding rate (% of households)"},
           title="Overcrowding and sanitation, 2012")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg11.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg11"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg11", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg11": "Sustainable cities index (0-100)"},
          title="SDG 11: Sustainable cities and communities, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator to 0–100 between the Atlas bounds, averages them and recovers the published SDG 11 index.',
        code: `${PYTHON_SETUP}

# Each indicator at its own year: one row per municipality
cs = geo.load("sdg11").groupby("geo_id").first()
bounds = {"sdg11_1_hocr": (55.0, 10.0),   # (worst, best)
          "sdg11_1_hno": (94.8, 5.5),
          "sdg11_2_samt": (0.0, 843.8)}
scores = cs[list(bounds)].copy()
for var, (worst, best) in bounds.items():
    scores[var] = (100 * (cs[var] - worst) / (best - worst)).clip(0, 100)
cs["computed"] = scores.mean(axis=1)
cs["name"] = geo.units("municipality").set_index("geo_id")["name"]
print(cs[["computed", "index_sdg11"]].corr().iloc[0, 1])
px.scatter(cs, x="index_sdg11", y="computed", hover_name="name",
           labels={"index_sdg11": "Sustainable cities index (0-100)",
                   "computed": "Computed index (0-100)"},
           title="SDG 11 index: computed vs published")`,
      },
      {
        title: 'Which indicator holds the index back',
        text: 'Shows the average rescaled score of each indicator: public transport scores far below housing and sanitation.',
        code: `${PYTHON_SETUP}
import pandas as pd

cs = geo.load("sdg11").groupby("geo_id").first()
bounds = {"sdg11_1_hocr": (55.0, 10.0), "sdg11_1_hno": (94.8, 5.5),
          "sdg11_2_samt": (0.0, 843.8)}
labels = {"sdg11_1_hocr": "Overcrowding rate",
          "sdg11_1_hno": "Households without a toilet",
          "sdg11_2_samt": "Public transport seats"}
rows = []
for var, (worst, best) in bounds.items():
    score = (100 * (cs[var] - worst) / (best - worst)).clip(0, 100)
    rows.append({"indicator": labels[var], "score": score.mean()})
px.bar(pd.DataFrame(rows), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 11 components: mean score across municipalities")`,
      },
      {
        title: 'Rank the departments',
        text: 'Averages the SDG 11 index by department, weighting each municipality by its population.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg11", variables="index_sdg11", years=2017)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg11": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg11"), x="index_sdg11", y="department",
       labels={"index_sdg11": "Sustainable cities index (population-weighted)"},
       title="SDG 11 index by department, 2017")`,
      },
      {
        title: 'Link the index with night-time lights',
        text: 'Compares the SDG 11 index with log night-time lights per capita in the same year.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg11", variables="index_sdg11", years=2017)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2017)
df = sdg.merge(ntl, on=["geo_id", "year"])
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="ln_t400NTLpc", y="index_sdg11", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "index_sdg11": "Sustainable cities index (0-100)"},
           title="SDG 11 index and night-time lights, 2017")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg13', type: 'indicator', section: 'indicators',
    title: 'SDG 13: Climate action',
    scope: '339 municipalities · 3 indicators and the SDG 13 index · 2012–2020',
    summary: 'The SDG 13 (Climate action) index of the Municipal Atlas of the SDGs 2020 and its three indicators, climate change vulnerability, CO₂ emissions per person and deforestation, for every municipality.',
    description: 'The SDG 13 (Climate action) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the three indicators behind it: the climate change vulnerability index (2015, from Conservación Internacional Bolivia’s Climate Change Atlas), total CO₂ emissions per person from deforestation and from burning natural gas, gasoline and diesel (2016), and the annual deforestation rate as a share of the 2015 forest area (average of 2016–2018, stored at 2017). The Atlas population in 2020 and the 2012 census urbanization rate are included as context. Each indicator is rescaled to 0–100 between a worst and a best value, capped at the bounds so that higher is always better, and the index is the simple mean of the rescaled indicators. The index is stored at 2017, the latest reference year of its indicators. The vulnerability index is published with one decimal, which leaves small residuals when the index is recomputed.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Environment'], tags: ['SDGs', 'climate change', 'CO₂ emissions', 'deforestation', 'municipalities'],
    image: 'images/indicators/sdg13.webp',
    imageAlt: 'Map of the Climate action index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high around Lake Titicaca, the La Paz altiplano and the Cochabamba valley, middle across the rest of the altiplano, the southern valleys and the Chaco, low across the lowlands of Pando, Beni, northern La Paz, Santa Cruz and the Cochabamba tropics',
    map: 'images/indicators/sdg13-map.webp',
    mapAlt: 'Map of the Climate action index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high around Lake Titicaca, the La Paz altiplano and the Cochabamba valley, middle across the rest of the altiplano, the southern valleys and the Chaco, low across the lowlands of Pando, Beni, northern La Paz, Santa Cruz and the Cochabamba tropics. Legend: High 80.6 to 99.8 (95 municipalities), Middle 61.2 to 80.6 (166), Low 11.9 to 61.2 (78).',
    date: '2026-10-30', pinned: false, dataset: 'sdg13',
    notice: 'Each variable has values only in its reference year: load one with its year, e.g. geo.load("sdg13", variables="index_sdg13", years=2017). The index is stored at 2017, the latest reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 13 index in 2017, with municipal boundaries
gdf = geo.load("sdg13", variables="index_sdg13", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg13", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg13": "Climate action index (0-100)"},
          title="SDG 13: Climate action, 2017").show()

# Deforestation rate against the index
df = geo.load("sdg13", variables=["sdg13_2_dra", "index_sdg13"], years=2017)
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg13_2_dra", y="index_sdg13", hover_name="name",
           labels={"sdg13_2_dra": "Deforestation rate (% of forest)",
                   "index_sdg13": "Climate action index (0-100)"},
           title="Deforestation and the SDG 13 index, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg13.csv")    # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg13"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg13", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg13": "Climate action index (0-100)"},
          title="SDG 13: Climate action, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas’s worst and best values, caps it at 0–100 and averages, reproducing the published SDG 13 index (small residuals come from the one-decimal vulnerability index).',
        code: `${PYTHON_SETUP}
import pandas as pd

# Each variable at its own reference year, one row per municipality
df = geo.load("sdg13").groupby("geo_id").first()
bounds = {"sdg13_1_ccvi": (2.97, 0), "sdg13_2_tco2e": (23.7, 0.02),
          "sdg13_2_dra": (5.44, 0)}                      # (worst, best)
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)
df["name"] = geo.units("municipality").set_index("geo_id")["name"]
px.scatter(df, x="computed", y="index_sdg13", hover_name="name",
           labels={"computed": "Computed index",
                   "index_sdg13": "Climate action index (0-100)"},
           title="SDG 13 index: computed vs published")`,
      },
      {
        title: 'Which indicator holds the index down',
        text: 'Averages the rescaled score of each indicator across municipalities to show where the goal is furthest from its target.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg13").groupby("geo_id").first()
bounds = {"sdg13_1_ccvi": (2.97, 0), "sdg13_2_tco2e": (23.7, 0.02),
          "sdg13_2_dra": (5.44, 0)}                      # (worst, best)
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
labels = {"sdg13_1_ccvi": "Climate change vulnerability index",
          "sdg13_2_tco2e": "Total CO2 emissions (t per person)",
          "sdg13_2_dra": "Deforestation rate (% of forest)"}
mean = scores.mean().rename(labels).reset_index()
mean.columns = ["indicator", "score"]
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="SDG 13: mean score of each indicator")`,
      },
      {
        title: 'Rank the departments',
        text: 'Aggregates the index to the nine departments as a population-weighted mean, using the observatory’s gridded population.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg13", variables="index_sdg13", years=2017)
dep = geo.aggregate(df, to="department", rules={"index_sdg13": "weighted_mean:pop"},
                    weights=geo.load("pop"))
dep["department"] = dep["geo_id"].map(
    geo.units("department").set_index("geo_id")["name"])
px.bar(dep.sort_values("index_sdg13"), x="index_sdg13", y="department",
       labels={"index_sdg13": "Climate action index (population-weighted)"},
       title="SDG 13 index by department, 2017")`,
      },
      {
        title: 'Emissions and deforestation',
        text: 'Plots each municipality’s deforestation rate against its CO₂ emissions per person, which include the emissions from burning cleared forest.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg13").groupby("geo_id", as_index=False).first()
units = geo.units("municipality").set_index("geo_id")
df["name"] = df["geo_id"].map(units["name"])
df["department"] = df["geo_id"].map(units["department_id"]).map(
    geo.units("department").set_index("geo_id")["name"])
px.scatter(df, x="sdg13_2_dra", y="sdg13_2_tco2e", color="department",
           hover_name="name",
           labels={"sdg13_2_dra": "Deforestation rate (% of forest)",
                   "sdg13_2_tco2e": "Total CO2 emissions (t per person)"},
           title="Deforestation and CO2 emissions per person")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg15', type: 'indicator', section: 'indicators',
    title: 'SDG 15: Life on land',
    scope: '339 municipalities · 2 indicators and the SDG 15 index · 2012–2020',
    summary: 'The Life on land index of the Municipal Atlas of the SDGs for 339 municipalities, built from the share of protected area and biodiversity loss from deforestation.',
    description: 'The SDG 15 (Life on land) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) and the two indicators behind it, for all 339 municipalities: the legally declared protected area as a share of the municipal area (2019, computed by Conservación Internacional Bolivia) and a biodiversity loss index due to deforestation that weights deforested habitat by the number of species living there (average of 2016–2018, stored at 2017). Each indicator is rescaled linearly to 0–100 between a worst and a best value (higher is always better, values beyond the bounds capped), and the index, on a 0–100 scale where 100 means the targets are met, is the simple mean of the two scores; it is stored at 2019, the latest of its indicators’ years. With only two components the index bunches at a few values: 147 municipalities have no protected area and no measured biodiversity loss, which gives a score of 0 and one of 100 and an index of exactly 50, while 4 municipalities reach 100 and 2 score 0. The dataset also holds the Atlas population for 2020 and the 2012 urbanization rate as context; they are not inputs of the index.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Environment'], tags: ['SDGs', 'protected areas', 'deforestation', 'biodiversity', 'municipalities'],
    image: 'images/indicators/sdg15.webp',
    imageAlt: 'Map of the Life on land index (0-100) in 2019 across 339 Bolivian municipalities in three natural-break classes: high in northern La Paz, the Cochabamba tropics and Tunari range, the Chaco and the Pantanal, low along the Santa Cruz agricultural frontier, Alto Beni, Colomi and Cobija; most of the highlands and valleys sit in the middle class at an index of 50',
    map: 'images/indicators/sdg15-map.webp',
    mapAlt: 'Map of the Life on land index (0-100) in 2019 across 339 Bolivian municipalities in three natural-break classes: high in northern La Paz, the Cochabamba tropics and Tunari range, the Chaco and the Pantanal, low along the Santa Cruz agricultural frontier, Alto Beni, Colomi and Cobija; most of the highlands and valleys sit in the middle class at an index of 50. Legend: High 68.9 to 100.0 (53 municipalities), Middle 33.3 to 68.9 (259), Low 0.0 to 33.3 (27).',
    date: '2026-10-30', pinned: false, dataset: 'sdg15',
    notice: 'Each variable has values only in its reference year: load the index with geo.load("sdg15", variables="index_sdg15", years=2019), or every variable as a cross-section with geo.load("sdg15").groupby("geo_id").first(). The index is stored at 2019, the latest year of its two indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The Life on land index in 2019, with municipal boundaries
gdf = geo.load("sdg15", variables="index_sdg15", years=2019, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg15", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg15": "Life on land index (0-100)"},
          title="SDG 15: Life on land, 2019").show()

# Its distribution: many municipalities score exactly 50
px.histogram(gdf, x="index_sdg15", nbins=40,
       labels={"index_sdg15": "Life on land index (0-100)"},
       title="Distribution of the SDG 15 index, 2019")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg15.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2019, ["geo_id", "index_sdg15"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg15", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg15": "Life on land index (0-100)"},
          title="SDG 15: Life on land, 2019")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales the two indicators between the Atlas’s worst and best values, caps them at 0 and 100, averages them and reproduces the published index.',
        code: `${PYTHON_SETUP}

import pandas as pd

# Each indicator at its own reference year
df = geo.load("sdg15").groupby("geo_id").first()
names = geo.units("municipality").set_index("geo_id")["name"]

# Worst and best values of each indicator (Atlas)
bounds = {"sdg15_1_pa": (0, 50), "sdg15_5_blr": (1.117, 0)}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)
df["name"] = df.index.map(names)
print(df[["computed", "index_sdg15"]].corr())

px.scatter(df, x="index_sdg15", y="computed", hover_name="name",
           labels={"index_sdg15": "Life on land index (0-100)",
                   "computed": "Computed index"},
           title="SDG 15 index: computed vs published")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Compares the mean 0–100 score of the two indicators in each department, showing that the protected-area score (19 on average) pulls the index down far more than biodiversity loss (89).',
        code: `${PYTHON_SETUP}

df = geo.load("sdg15").groupby("geo_id", as_index=False).first()
bounds = {"sdg15_1_pa": (0, 50), "sdg15_5_blr": (1.117, 0)}
labels = {"sdg15_1_pa": "Protected areas (% of area)",
          "sdg15_5_blr": "Biodiversity loss from deforestation"}
for v, (w, b) in bounds.items():
    df[labels[v]] = (100 * (df[v] - w) / (b - w)).clip(0, 100)

units = geo.units("municipality").set_index("geo_id")
deps = geo.units("department").set_index("geo_id")["name"]
df["department"] = df["geo_id"].map(units["department_id"]).map(deps)
long = df.melt(id_vars="department", value_vars=list(labels.values()),
               var_name="indicator", value_name="score")
mean = long.groupby(["department", "indicator"], as_index=False)["score"].mean()
px.bar(mean, x="score", y="department", color="indicator", barmode="group",
       labels={"score": "Mean score (0-100)"},
       title="SDG 15 indicator scores by department")`,
      },
      {
        title: 'Rank departments by population-weighted index',
        text: 'Averages the municipal index within each department, weighting by population in 2019.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg15", variables="index_sdg15", years=2019)
dep = geo.aggregate(df, to="department",
                    rules={"index_sdg15": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg15"), x="index_sdg15", y="department",
       labels={"index_sdg15": "Life on land index (population-weighted)"},
       title="SDG 15 index by department, 2019")`,
      },
      {
        title: 'Protected areas against biodiversity loss',
        text: 'Plots the two indicators against each other, coloured by the index, to see which combination of protection and deforestation sets each municipality’s score.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg15").groupby("geo_id").first()
df["name"] = df.index.map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="sdg15_1_pa", y="sdg15_5_blr", color="index_sdg15",
           hover_name="name",
           labels={"sdg15_1_pa": "Protected areas (% of area)",
                   "sdg15_5_blr": "Biodiversity loss from deforestation",
                   "index_sdg15": "Life on land index (0-100)"},
           title="Protected areas and biodiversity loss")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg16', type: 'indicator', section: 'indicators',
    title: 'SDG 16: Peace, justice and strong institutions',
    scope: '339 municipalities · 3 indicators and the SDG 16 index · 2012–2017',
    summary: 'The SDG 16 index of the 339 municipalities, built from homicide rates, municipal budget execution and birth registration of children under 5.',
    description: 'The SDG 16 (Peace, justice and strong institutions) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, on a 0–100 scale where 100 means the targets are met, with its three indicators: the homicide rate per 100,000 inhabitants (average of 2015–2017, from police statistics compiled by the Bolivian Observatory of Citizen Security and Fight against Drugs, stored at 2016), the municipal government’s budget execution in 2017 (executed over programmed budget, from the Ministry of Economy and Public Finance) and the share of children under 5 whose birth is registered (2012 census, INE). Each indicator is rescaled linearly to 0–100 between a worst and a best value, with values beyond the bounds capped, and the index is the simple mean of the rescaled indicators. The indicators refer to different years, so the index is stored at 2017, the latest of them. No values are missing; 253 municipalities recorded no homicide over 2015–2017, and one reports a budget execution above 100%, capped in the index. The dataset also holds the Atlas’s 2020 population and 2012 urbanization rate as context.',
    geography: 'Municipality', units: 339, period: '2012–2017', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Institutions'], tags: ['SDGs', 'SDG 16', 'homicides', 'municipal finance', 'birth registration', 'municipalities'],
    image: 'images/indicators/sdg16.webp',
    imageAlt: 'Map of the Peace, justice, institutions index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high across most of Chuquisaca and highland La Paz, low in scattered municipalities of Beni and Pando, the Cochabamba valley, El Alto, the eastern Santa Cruz border and the salt-flat municipalities of western Oruro and Potosí',
    map: 'images/indicators/sdg16-map.webp',
    mapAlt: 'Map of the Peace, justice, institutions index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high across most of Chuquisaca and highland La Paz, low in scattered municipalities of Beni and Pando, the Cochabamba valley, El Alto, the eastern Santa Cruz border and the salt-flat municipalities of western Oruro and Potosí. Legend: High 76.9 to 93.7 (141 municipalities), Middle 63.8 to 76.9 (148), Low 32.7 to 63.8 (50).',
    date: '2026-10-30', pinned: false, dataset: 'sdg16',
    notice: 'Each variable has values only in its reference year: load the index with its year, e.g. geo.load("sdg16", variables="index_sdg16", years=2017), or every variable as a cross-section with geo.load("sdg16").groupby("geo_id").first(). The index is stored at 2017, the latest year of its indicators (homicides 2015–2017, budget execution 2017, birth registration 2012).',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 16 index (stored at 2017), with municipal boundaries
gdf = geo.load("sdg16", variables="index_sdg16", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg16", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg16": "Peace, justice, institutions index (0-100)"},
          title="SDG 16 index, 2017").show()

# The index by department
deps = geo.units("department").set_index("geo_id")["name"]
gdf["department"] = gdf["geo_id"].str[:5].map(deps)
px.box(gdf, x="department", y="index_sdg16", hover_name="name",
       labels={"index_sdg16": "Peace, justice, institutions index (0-100)"},
       title="SDG 16 index by department, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg16.csv")   # geo_id, year, mun_id, ...
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg16"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg16", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg16": "Peace, justice, institutions index (0-100)"},
          title="SDG 16 index, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas’s worst and best values, caps it at 0 and 100, averages the three scores and compares the result with the published SDG 16 index.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg16").groupby("geo_id").first()    # each variable at its own year
names = geo.units("municipality").set_index("geo_id")["name"]
df["name"] = df.index.map(names)

# Worst and best values of each indicator (Atlas, Cuadro 17)
bounds = {"sdg16_1_rhr": (8.3, 0), "sdg16_6_pbec": (34.8, 100),
          "sdg16_9_cr": (50, 100)}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)
df["computed"] = scores.mean(axis=1)

px.scatter(df, x="computed", y="index_sdg16", hover_name="name",
           labels={"computed": "Computed index (0-100)",
                   "index_sdg16": "Peace, justice, institutions index (0-100)"},
           title="Computed vs published SDG 16 index")`,
      },
      {
        title: 'Which indicator pulls the index down',
        text: 'Shows the average 0–100 score of each indicator across the 339 municipalities: the lower the bar, the further municipalities are from that target.',
        code: `${PYTHON_SETUP}
import pandas as pd

df = geo.load("sdg16").groupby("geo_id").first()
bounds = {"sdg16_1_rhr": (8.3, 0), "sdg16_6_pbec": (34.8, 100),
          "sdg16_9_cr": (50, 100)}
scores = pd.DataFrame({v: 100 * (df[v] - w) / (b - w)
                       for v, (w, b) in bounds.items()}).clip(0, 100)

labels = {"sdg16_1_rhr": "Homicide rate (per 100,000)",
          "sdg16_6_pbec": "Budget execution (%)",
          "sdg16_9_cr": "Birth registration, under 5 (%)"}
mean = scores.mean().rename(labels).reset_index()
mean.columns = ["indicator", "score"]
px.bar(mean.sort_values("score"), x="score", y="indicator",
       labels={"score": "Mean score (0-100)", "indicator": ""},
       title="Average SDG 16 score by indicator")`,
      },
      {
        title: 'Rank the departments by population-weighted index',
        text: 'Averages the municipal SDG 16 index within each department, weighting each municipality by its 2017 gridded population.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg16", variables="index_sdg16", years=2017)
dep = geo.aggregate(df, to="department", rules={"index_sdg16": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg16"), x="index_sdg16", y="department",
       labels={"index_sdg16": "Peace, justice, institutions index (0-100)"},
       title="SDG 16 index by department (population-weighted), 2017")`,
      },
      {
        title: 'Budget execution and night-time lights',
        text: 'Plots municipal budget execution in 2017 against the trend of log night-time lights per capita in the same year, to see whether brighter, richer municipalities execute more of their budget.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg16", variables="sdg16_6_pbec", years=2017)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2017)
df = sdg.merge(ntl, on=["geo_id", "year"])
names = geo.units("municipality").set_index("geo_id")["name"]
df["name"] = df["geo_id"].map(names)
px.scatter(df, x="ln_t400NTLpc", y="sdg16_6_pbec", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "sdg16_6_pbec": "Budget execution (%)"},
           title="Budget execution and night-time lights, 2017")`,
      },
    ],
  },
  {
    id: 'municipalities339-sdg17', type: 'indicator', section: 'indicators',
    title: 'SDG 17: Partnerships for the goals',
    scope: '339 municipalities · 2 indicators and the SDG 17 index · 2012–2020',
    summary: 'The SDG 17 index of the Municipal Atlas of the SDGs and its two indicators of municipal finance, local tax revenue and public investment per capita, in 2017.',
    description: 'The SDG 17 (Partnerships for the goals) index of the Municipal Atlas of the Sustainable Development Goals in Bolivia 2020 (SDSN Bolivia) for all 339 municipalities, with the two indicators behind it, both for 2017 and from Ministry of Economy and Public Finance data: the share of municipal revenue that comes from local taxes (the rest comes mainly from central-government transfers) and public investment per capita in bolivianos. The index runs from 0 (worst) to 100 (targets met): each indicator is rescaled linearly between a worst and a best value, capped at 0 and 100, and the index is their simple mean. Local taxes are a small share of revenue in most municipalities (median 0.6%), so the index is low across most of the country. The Atlas does not state which population divides public investment. The Atlas population (2020) and urbanization rate (2012) are included as context; they are not inputs of the index.',
    geography: 'Municipality', units: 339, period: '2012–2020', frequency: 'One reference year per indicator', key: 'geo_id', idExample: 'BO-04-17-04',
    categories: ['Institutions'], tags: ['SDGs', 'municipal finance', 'local taxes', 'public investment', 'municipalities'],
    image: 'images/indicators/sdg17.webp',
    imageAlt: 'Map of the Partnerships index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high around Santa Cruz de la Sierra, La Paz and Cochabamba, in Puerto Quijarro and in a few municipalities of the southwestern altiplano of Oruro and Potosí; middle in parts of Tarija, southern Potosí and Pando; low across most of the country',
    mapAlt: 'Map of the Partnerships index (0-100) in 2017 across 339 Bolivian municipalities in three natural-break classes: high around Santa Cruz de la Sierra, La Paz and Cochabamba, in Puerto Quijarro and in a few municipalities of the southwestern altiplano of Oruro and Potosí; middle in parts of Tarija, southern Potosí and Pando; low across most of the country. Legend: High 36.9 to 65.2 (14 municipalities), Middle 16.3 to 36.9 (85), Low 0.0 to 16.3 (240).',
    map: 'images/indicators/sdg17-map.webp',
    date: '2026-10-30', pinned: false, dataset: 'sdg17',
    notice: 'Each variable has values only in its reference year: load the index with geo.load("sdg17", variables="index_sdg17", years=2017). The index is stored at 2017, the latest (here the only) reference year of its indicators.',
    code: {
      python: `${PYTHON_SETUP}

# The SDG 17 index in 2017, with municipal boundaries
gdf = geo.load("sdg17", variables="index_sdg17", years=2017, geometry=True)
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg17", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg17": "Partnerships index (0-100)"},
          title="SDG 17: Partnerships for the goals, 2017").show()

# Its two indicators: local taxes and public investment
df = geo.load("sdg17", years=2017, geometry=True)
px.scatter(df, x="sdg17_5_pipc", y="sdg17_1_pmtax", hover_name="name",
           labels={"sdg17_5_pipc": "Public investment per capita (Bs)",
                   "sdg17_1_pmtax": "Revenue from local taxes (%)"},
           title="Local taxes and public investment, 2017")`,
      pandas: `import pandas as pd
import geopandas as gpd
import plotly.express as px

# No geo4bolivia needed: every file is a plain URL
BASE = "${RAW_URL}"
df = pd.read_csv(BASE + "data/municipality/sdg17.csv")  # geo_id, year, variables
municipalities = gpd.read_file(BASE + "geo/boundaries/municipality.geojson")

index = df.loc[df["year"] == 2017, ["geo_id", "index_sdg17"]]
gdf = municipalities.merge(index, on="geo_id")
px.choropleth_map(gdf, geojson=gdf.geometry, locations=gdf.index,
          color="index_sdg17", hover_name="name",
          center={"lat": -16.3, "lon": -64}, zoom=4,
          labels={"index_sdg17": "Partnerships index (0-100)"},
          title="SDG 17: Partnerships for the goals, 2017")`,
    },
    examples: [
      {
        title: 'Compute the index from its indicators',
        text: 'Rescales each indicator between the Atlas worst and best values, caps it at 0 and 100, averages the two and checks the result against the published index.',
        code: `${PYTHON_SETUP}
import pandas as pd

# Every variable at its own reference year, one row per municipality
df = geo.load("sdg17").groupby("geo_id").first()
bounds = {"sdg17_1_pmtax": (0.0, 40.5),     # (worst, best) of each indicator
          "sdg17_5_pipc": (144.0, 3563.0)}
scores = pd.DataFrame({v: (100 * (df[v] - w) / (b - w)).clip(0, 100)
                       for v, (w, b) in bounds.items()})
df["computed"] = scores.mean(axis=1)        # missing indicators are skipped
df["name"] = df.index.map(geo.units("municipality").set_index("geo_id")["name"])
r = df["computed"].corr(df["index_sdg17"])
px.scatter(df, x="index_sdg17", y="computed", hover_name="name",
           labels={"index_sdg17": "Partnerships index (0-100)",
                   "computed": "Computed index (0-100)"},
           title=f"Computed vs published SDG 17 index (r = {r:.4f})")`,
      },
      {
        title: 'Which indicator holds the index down',
        text: 'Averages the rescaled score of each indicator over the 339 municipalities: local tax revenue scores far lower than public investment.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg17", years=2017)
bounds = {"sdg17_1_pmtax": (0.0, 40.5), "sdg17_5_pipc": (144.0, 3563.0)}
labels = {"sdg17_1_pmtax": "Revenue from local taxes (%)",
          "sdg17_5_pipc": "Public investment per capita (Bs)"}
rows = [{"indicator": labels[v],
         "score": (100 * (df[v] - w) / (b - w)).clip(0, 100).mean()}
        for v, (w, b) in bounds.items()]
px.bar(rows, x="score", y="indicator",
       labels={"score": "Mean rescaled score (0-100)", "indicator": ""},
       title="Mean score of each SDG 17 indicator, 2017")`,
      },
      {
        title: 'Rank the departments',
        text: 'Ranks the nine departments by the population-weighted mean of the SDG 17 index.',
        code: `${PYTHON_SETUP}

df = geo.load("sdg17", variables="index_sdg17", years=2017)
dep = geo.aggregate(df, to="department", rules={"index_sdg17": "weighted_mean:pop"},
                    weights=geo.load("pop"))
names = geo.units("department").set_index("geo_id")["name"]
dep["department"] = dep["geo_id"].map(names)
px.bar(dep.sort_values("index_sdg17"), x="index_sdg17", y="department",
       labels={"index_sdg17": "Partnerships index (0-100), population-weighted"},
       title="SDG 17 index by department, 2017")`,
      },
      {
        title: 'Link with night-time lights',
        text: 'Plots the share of revenue from local taxes against night-time lights per capita in 2017, a proxy for local economic activity.',
        code: `${PYTHON_SETUP}

sdg = geo.load("sdg17", variables="sdg17_1_pmtax", years=2017)
ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2017)
df = sdg.merge(ntl, on=["geo_id", "year"])
df["name"] = df["geo_id"].map(geo.units("municipality").set_index("geo_id")["name"])
px.scatter(df, x="ln_t400NTLpc", y="sdg17_1_pmtax", hover_name="name",
           labels={"ln_t400NTLpc": "Log night-time lights per capita (trend)",
                   "sdg17_1_pmtax": "Revenue from local taxes (%)"},
           title="Local taxes and night-time lights, 2017")`,
      },
    ],
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
mpi = geo.load("sdg01", variables="sdg1_2_mpi", years=2012)
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
    related: ['expdpy-package', 'geometrics-package', 'geo4bolivia-quickstart', 'municipalities339-sdg01', 'municipalities339-ntl'],
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
    related: ['geo4bolivia-package', 'municipalities339-sdg01', 'municipalities339-pop'],
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
    related: ['municipalities339-sdg01', 'municipalities339-ntl', 'mpi-esda'],
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
    related: ['municipalities339-sdg01', 'mpi-esda-dependence', 'geometrics-package'],
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
    related: ['mpi-esda', 'municipalities339-sdg01'],
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
    related: ['municipalities339-sdg01', 'municipalities339-ntl', 'geometrics-package'],
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
    related: ['municipalities339-ntl', 'municipalities339-sdg01', 'geometrics-package'],
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
    related: ['municipalities339-sdg01', 'mpi-esda', 'mpi-esda-heterogeneity'],
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
    related: ['municipalities339-emb', 'municipalities339-sdg01', 'mpi-eda'],
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
    description: 'This study maps five constraints on human capital across Bolivia’s 339 municipalities: chronic malnutrition in children, the share of the population that does not speak Spanish, the secondary-school dropout rates of boys and girls, and inequality in years of education. It summarises them with principal components, finds where high and low values cluster in space (hot spots and cold spots), and groups municipalities that are both similar and contiguous into regions. All five indicators are in the observatory’s SDG goal datasets (sdg02, sdg04 and sdg10).',
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
      { h: 'Reproduce it', p: 'The five indicators are sdg2_2_cmc, sdg10_2_nssp, sdg4_1_ssdrm, sdg4_1_ssdrf and sdg10_2_gcye in the sdg02, sdg10 and sdg04 datasets, each at its own reference year.' },
    ],
    related: ['municipalities339-sdg02', 'municipalities339-sdg04', 'municipalities339-sdg10', 'mpi-esda'],
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

