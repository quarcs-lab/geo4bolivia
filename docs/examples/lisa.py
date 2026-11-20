!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.lisa("sdg", "index_sdg", year=2024)
print(res.interpret())
res.fig
