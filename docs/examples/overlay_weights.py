!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px

w = geo.overlay_weights("map343", "department")
px.histogram(w, x="share_of_from", log_y=True,
             title="Share of each municipality inside each department")
