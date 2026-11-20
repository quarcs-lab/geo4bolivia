!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.lisa_transitions("sdg", "index_sdg")       # ~2012 to ~2024
print(res.interpret())
res.fig
