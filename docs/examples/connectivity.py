!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.connectivity("map343")
print(res.interpret())
res.fig
