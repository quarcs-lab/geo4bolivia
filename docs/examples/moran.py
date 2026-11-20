!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.moran("sdg", "index_sdg", year=2024)
print(res.interpret())
print(geo.moran("sdg", "index_sdg", year="all").df)   # Moran's I in each year
res.fig
