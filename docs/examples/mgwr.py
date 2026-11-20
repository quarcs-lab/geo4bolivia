!pip install -q "geo4bolivia[mgwr]"
import geo4bolivia as geo

res = geo.mgwr("sdg", "index_sdg", "urbanization")   # about half a minute
print(res.interpret())
res.figs["urbanization"]
