!pip install -q "geo4bolivia[raster]"
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import geo4bolivia as geo
import plotly.express as px

# A small raster of rough distance to La Paz (km); use your own GeoTIFF instead
x0, y0, x1, y1 = geo.boundaries("country").total_bounds
lon, lat = np.meshgrid(np.linspace(x0, x1, 400), np.linspace(y1, y0, 400))
km = 111 * np.hypot(lon + 68.13, lat + 16.50)
with rasterio.open("dist.tif", "w", driver="GTiff", width=400, height=400,
                   count=1, dtype="float32", crs="EPSG:4326",
                   transform=from_bounds(x0, y0, x1, y1, 400, 400)) as f:
    f.write(km.astype("float32"), 1)

dist = geo.zonal("dist.tif", scale="map343", stats=["mean", "max"],
                 name="dist_lpz", year=2024)
geo.map(dist, "dist_lpz_mean", title="Mean distance to La Paz (km)")
