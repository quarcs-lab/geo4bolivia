!pip install -q geo4bolivia
import geo4bolivia as geo

res = geo.distribution("sdg01", "sdg1_2_mpi", by="department", kind="box")
print(res.interpret())
res.fig
