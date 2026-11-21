!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.convergence_clubs("ntl", "ln_NTLpc")       # 2012-2020, 322 units
print(res.interpret())
res.fig_map
