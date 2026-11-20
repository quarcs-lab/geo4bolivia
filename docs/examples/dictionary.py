!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

d = geo.dictionary("sdg03")
display(d[["variable", "label", "unit", "aggregation", "reference_years"]])
