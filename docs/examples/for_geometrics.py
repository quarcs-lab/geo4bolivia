!pip install -q geo4bolivia geometrics
import geo4bolivia as geo
import geometrics as gm

gdf, df, df_dict = geo.for_geometrics("sdg", variables="index_sdg")
df = gm.set_labels(df, df_dict, set_panel=True)
w = gm.make_weights(gdf, method="queen")
gm.explore_moran_plot(df, "index_sdg", gdf=gdf, w=w, period=2024).fig
