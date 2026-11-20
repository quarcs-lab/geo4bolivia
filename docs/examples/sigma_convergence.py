!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.sigma_convergence("pop", "pop")            # 20 years, 333 units
print(res.interpret())
res.fig
