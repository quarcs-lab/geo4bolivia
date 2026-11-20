!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

hits = geo.search("education women")       # every word must match
display(hits[["dataset", "variable", "label", "years"]])
df = geo.load(hits["dataset"][0], variables=hits["variable"][0], names=True)
px.box(df, x="year", y=hits["variable"][0], hover_name="name",
       labels=geo.labels(df), title=hits["label"][0])
