!pip install -q "geo4bolivia[panel]"
import geo4bolivia as geo

panel = geo.combine(["ntl", "pop"], scale="municipality")
res = geo.panel_model(panel, "ln_NTLpc", "pop_density")
print(res.interpret())
res.gt
