!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

print(geo.scale_of("BO-04-17"), geo.scale_of("BO-04"))   # province, department
try:
    geo.scale_of("BO-04-17-04")        # a municipality: on map343 and map339
except ValueError as error:
    print(error)
