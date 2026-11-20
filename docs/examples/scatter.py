!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.scatter("sdg", "urbanization", "index_sdg",
                  color="department", size="population")
print(res.interpret())
res.fig
