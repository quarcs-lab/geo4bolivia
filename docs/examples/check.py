!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px
import pandas as pd

df = pd.DataFrame({"geo_id": ["BO-04-17-04", "BO-04-17-04", "BO-99"],
                   "year": [2024, 2024, 2024], "x": [1, 2, 3]})
geo.check(df, scale="municipality")        # unknown id, duplicate rows
