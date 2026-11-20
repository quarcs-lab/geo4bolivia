!pip install -q geo4bolivia expdpy
import geo4bolivia as geo
import expdpy as ex

df, df_def = geo.for_expdpy("sdg", variables="index_sdg", groups=["department"])
df = ex.set_labels(df, df_def, set_panel=True)
ex.explore_trend_plot_by_group(df, group_var="department", var="index_sdg").fig
