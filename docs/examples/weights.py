!pip install -q geo4bolivia
import geo4bolivia as geo

w = geo.weights("municipality")                    # queen contiguity, 343 units
w6 = geo.weights("municipality", method="knn", k=6)   # the six nearest
print(w.n, round(w.mean_neighbors, 2), w6.n, w6.mean_neighbors)
geo.moran("sdg", "index_sdg", w=w6).fig
