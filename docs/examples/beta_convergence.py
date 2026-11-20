!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.beta_convergence("sdg", "index_sdg")       # ~2012 to ~2024
print(res.interpret())
res.fig
