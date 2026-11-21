!pip install -q geo4bolivia
import geo4bolivia as geo
import plotly.express as px
import pandas as pd

mine = pd.DataFrame({"municipio": ["SUCRE", "el alto", "Cobija"],
                     "clinics": [41, 63, 12]})        # made-up values
mine = geo.link(mine, scale="map343", on="municipio")
by_code = geo.link(pd.DataFrame({"cod": [20101]}), scale="map343",
                   on="cod", key="mun_id")            # INE code -> geo_id
geo.add_names(mine)
