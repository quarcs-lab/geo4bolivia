!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

dep = geo.combine(["sdg03", "sdg04"], scale="department", years=2024)
dep = geo.add_names(dep)
px.scatter(dep, x="index_sdg3", y="index_sdg4", text="name",
           labels=geo.labels(dep), title="Health and education, ~2024")
