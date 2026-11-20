!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg06", groups=["department"])
display(geo.describe(df))                          # per period
s = geo.describe(df, variables="index_sdg6", by="department")
px.bar(s, x="department", y="mean", error_y="std", labels={"mean": s["label"][0]},
       title="Clean water and sanitation index by department (both periods)")
