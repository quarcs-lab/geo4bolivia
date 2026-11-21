!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

print(geo.ancestors("map343"))       # province, department, country
