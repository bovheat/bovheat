import pytest
import pandas as pd
from bovheat_src import bovheat as bh


@pytest.mark.parametrize("data, output",
                         # 1 Basic Example
                         [(pd.DataFrame({"foldername": ["1"], "Cow Number": ["1"],
                                         "Days in Lactation": [2],
                                         "datetime": [pd.to_datetime("2015-02-20 10:00:00")]}),
                           pd.to_datetime("2015-02-18 00:00:00")),
                          # 2 datetime and DIM completely mixed, ordering should not matter
                          (pd.DataFrame({"foldername": ["1", "1"], "Cow Number": ["1", "1"],
                                         "Days in Lactation": [100, 20],
                                         "datetime": [pd.to_datetime("2015-02-20 10:00:00"),
                                                      # Should ignore smaller datetime
                                                      pd.to_datetime("2015-02-23 10:00:00")]}),
                           pd.to_datetime("2015-02-03 00:00:00")),
                          # Test Missing Days in Lactation
                          (pd.DataFrame({"foldername": ["1"], "Cow Number": ["1"],
                                         "Days in Lactation": [None]}),
                           None),
                          ])
def test_calc_calving_date(data, output):
    assert bh.calc_calving_date(data) == output
