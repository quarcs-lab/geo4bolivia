!pip install -q "geo4bolivia[panel]"
import geo4bolivia as geo

panel = geo.combine(["ntl", "pop"], scale="map339")
res = geo.panel_model(panel, "ln_NTLpc", "pop_density")
print(res.interpret())
res.gt
