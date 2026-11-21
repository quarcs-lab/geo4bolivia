!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

m = geo.units("map343")              # names, parents, INE codes, areas
display(m[["geo_id", "name", "ine_code", "province_id", "department_id"]].head())
px.histogram(m, x="area_km2", log_y=True, title="Municipal areas (km²)")
