"""Project-specific tests: facts about Bolivia's units and datasets.

Generic behaviour is tested in tests/test_core.py. Add checks here that only
someone who knows the data could write (unit counts, known values, spellings).
"""

import geo4bolivia as geo


def test_country_unit():
    country = geo.units("country")
    assert country["geo_id"].tolist() == ["BO"]
    assert country["name"].item() == "Bolivia"
