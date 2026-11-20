!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg07", variables=["sdg7_1_cae", "sdg7_1_elc"], years=2024)
px.scatter(df, x="sdg7_1_cae", y="sdg7_1_elc", labels=geo.labels(df),
           title="Electricity and clean cooking, ~2024")
