!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.trend("ntl", "ln_NTLpc")
print(res.interpret())
res.fig
