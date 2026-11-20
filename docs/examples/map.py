!pip install -q geo4bolivia
import geo4bolivia as geo

# Multidimensional poverty in both periods, in common natural-break classes
geo.map("sdg01", "sdg1_2_mpi", year=[2012, 2024], scheme="fisher_jenks")
