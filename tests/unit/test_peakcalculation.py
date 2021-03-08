# pylint: disable-all
import pandas as pd
import pytest

from bovheat_src import bovheat as bh

input_data = {
    "Activity Change": [5, 11, 11, 22, 35, 11, 5, 25, 44, 66, 55, 44, 4, 2, 2],
    "Days in Lactation": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 0, 2],
    "datetime": pd.date_range("2015-02-24 00:00:00", periods=15, freq="2H"),
    "calving_date": [pd.to_datetime("2015-02-20 00:00:00")] * 15,
    "foldername": ["testfarm"] * 15,
    "Cow Number": [12345] * 15,
}

input_df = pd.DataFrame(data=input_data)


@pytest.mark.parametrize(
    "minheatlength, input_df, heat_df",
    [
        # Test 1 - Minimum heat length of 1 observation
        (
            1,
            input_df,
            pd.DataFrame(
                data=[
                    dict(
                        heat_no=1,
                        start_dt_heat=pd.to_datetime("2015-02-24 08:00:00"),
                        stop_dt_heat=pd.to_datetime("2015-02-24 08:00:00"),
                        duration_heat=2,
                        max_act_heat=35,
                        max_dim_heat=8,
                        max_dt_heat=pd.to_datetime("2015-02-24 08:00:00"),
                        short_inter_estrus=None,
                    ),
                    dict(
                        heat_no=2,
                        start_dt_heat=pd.to_datetime("2015-02-24 16:00:00"),
                        stop_dt_heat=pd.to_datetime("2015-02-24 22:00:00"),
                        duration_heat=8,
                        max_act_heat=66,
                        max_dim_heat=18,
                        max_dt_heat=pd.to_datetime("2015-02-24 18:00:00"),
                        short_inter_estrus=1,
                    ),
                ]
            ),
        ),
        # Test 2 - Minimum heat length of 2 observation
        (
            2,
            input_df,
            pd.DataFrame(
                data=[
                    dict(
                        heat_no=1,
                        start_dt_heat=pd.to_datetime("2015-02-24 16:00:00"),
                        stop_dt_heat=pd.to_datetime("2015-02-24 22:00:00"),
                        duration_heat=8,
                        max_act_heat=66,
                        max_dim_heat=18,
                        max_dt_heat=pd.to_datetime("2015-02-24 18:00:00"),
                        short_inter_estrus=None,
                    ),
                ]
            ),
        ),
    ],
)
def test_peakcalculation(minheatlength, input_df, heat_df):
    cowdf_results = bh.calc_heats(input_df, threshold=35, minheatlength=minheatlength)

    pd.testing.assert_frame_equal(
        cowdf_results[
            [
                "heat_no",
                "start_dt_heat",
                "stop_dt_heat",
                "duration_heat",
                "max_act_heat",
                "max_dim_heat",
                "max_dt_heat",
                "short_inter_estrus",
            ]
        ],
        heat_df,
        check_dtype=False,
    )
