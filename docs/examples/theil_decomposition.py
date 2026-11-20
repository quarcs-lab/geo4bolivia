!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.theil_decomposition("sdg", "index_sdg", by="department")
print(res.interpret())
res.fig
