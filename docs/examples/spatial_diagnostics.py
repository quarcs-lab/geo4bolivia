!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.spatial_diagnostics("sdg", "index_sdg", "urbanization")
print(res.interpret())
res.gt
