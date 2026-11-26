!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

print(geo.cite("sdg01"))                   # the Atlas, the observatory, the boundaries
print(geo.cite("sdg01", style="bibtex"))
