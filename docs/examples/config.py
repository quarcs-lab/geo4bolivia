!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

cfg = geo.config()                         # project.yaml: repository, CRS...
print(cfg["repository"], cfg["equal_area_crs"])
