!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px
import geopandas as gpd
import numpy as np
from shapely.geometry import box

crs = geo.config()["equal_area_crs"]       # metres, equal area
x0, y0, x1, y1 = geo.boundaries("country").to_crs(crs).total_bounds
size = 50_000                              # 50 km cells
cells = [box(x, y, x + size, y + size) for x in np.arange(x0, x1, size)
         for y in np.arange(y0, y1, size)]
grid = gpd.GeoDataFrame({"cell": range(len(cells))}, geometry=cells, crs=crs)
grid = grid.to_crs("EPSG:4326")
pop = geo.load("sdg", variables="population", years=2024)
cells = geo.overlay(pop, grid, extensive=["population"], id_col="cell")
px.histogram(cells, x="population", title="Population on a 50 km grid")
