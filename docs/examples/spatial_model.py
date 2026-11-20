!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.spatial_model("sdg", "index_sdg", "urbanization", model="durbin")
print(res.interpret())
res.gt
