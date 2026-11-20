!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

xw = geo.crosswalk("municipality", "department")
n = xw.groupby("geo_id_to", as_index=False).size()
n["department"] = n["geo_id_to"].map(geo.units("department")
                                     .set_index("geo_id")["name"])
px.bar(n, x="department", y="size", title="Municipalities per department")
