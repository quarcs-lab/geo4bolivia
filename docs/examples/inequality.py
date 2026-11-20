!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.inequality("sdg", "index_sdg")
print(res.interpret())
res.fig_lorenz
