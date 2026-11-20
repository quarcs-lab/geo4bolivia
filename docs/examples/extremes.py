!pip install -q geo4bolivia
import geo4bolivia as geo

mpi = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])
res = geo.extremes(mpi, "sdg1_2_mpi", year=2024, n=5)
print(res.interpret())
res.fig
