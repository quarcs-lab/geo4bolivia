"""Project-specific tests: facts about $country's units and datasets.

Generic behaviour is tested in tests/test_core.py. Add checks here that only
someone who knows the data could write (unit counts, known values, spellings).
"""

import $package as geo


def test_country_unit():
    country = geo.units("country")
    assert country["geo_id"].tolist() == ["$iso2"]
    assert country["name"].item() == "$country"
