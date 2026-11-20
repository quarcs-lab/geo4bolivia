!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.connectivity("municipality")
print(res.interpret())
res.fig
