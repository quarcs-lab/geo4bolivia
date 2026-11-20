!pip install -q "geo4bolivia[dynamics]"
import geo4bolivia as geo

res = geo.spatial_transitions("ntl", "ln_NTLpc", k=5)
print(res.interpret())
res.fig
