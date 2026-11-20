!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg05", variables=["index_sdg5"], years=[2012, 2024],
              groups=["department"])
px.histogram(df, x="index_sdg5", color="year", barmode="overlay",
             labels=geo.labels(df), title="Gender equality index")
