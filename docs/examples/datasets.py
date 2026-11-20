!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

cat = geo.datasets()
display(cat[["dataset", "scale", "title", "years", "units", "variables"]])
px.bar(cat, x="dataset", y="units", color="years", hover_name="title",
       title="Units with data per dataset")
