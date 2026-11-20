!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.rank_mobility("sdg", "index_sdg")
print(res.interpret())
res.fig
