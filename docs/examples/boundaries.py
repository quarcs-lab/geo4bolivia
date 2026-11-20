!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

dep = geo.boundaries("department")
px.choropleth_map(dep, geojson=dep.geometry, locations=dep.index,
                  color="name", hover_name="name",
                  center={"lat": -16.3, "lon": -64}, zoom=4,
                  title="Bolivia's nine departments")
