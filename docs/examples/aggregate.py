!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg04", variables="index_sdg4")
up = geo.aggregate(df, to=["department", "country"], dataset="sdg04")
up = geo.add_names(up[up["scale"] == "department"])
px.bar(up, x="name", y="index_sdg4", color="year", barmode="group",
       labels=geo.labels(up), title="Education index by department (weighted)")
