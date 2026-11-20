!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.correlation("sdg01", year=2024)
print(res.interpret())
res.fig
