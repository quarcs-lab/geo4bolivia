!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.regression("sdg", "index_sdg",
                     [["urbanization"], ["urbanization", "population"]],
                     fixed_effects=[None, "department"])
print(res.interpret())
res.gt
