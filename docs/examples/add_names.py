!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg08", variables="index_sdg8", years=2024)
df = geo.add_names(df, groups=["department", "province"])
px.box(df, x="department", y="index_sdg8", hover_name="name",
       labels=geo.labels(df), title="Decent work index, ~2024")
