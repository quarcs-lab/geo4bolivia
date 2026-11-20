!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

df = geo.load("sdg01", variables="sdg1_2_mpi", groups=["department"])
chg = geo.change(df, "sdg1_2_mpi")
px.scatter(chg, x="sdg1_2_mpi_2012", y="sdg1_2_mpi_change",
           color="department", hover_name="name", labels=geo.labels(chg),
           title="Poverty fell most where it was highest")
