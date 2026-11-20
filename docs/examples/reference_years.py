!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

ry = geo.reference_years("sdg03")          # stored year -> actual years
ry[ry["year"] == 2024]
