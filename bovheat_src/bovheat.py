#!/usr/bin/env python3

import itertools
import multiprocessing
import sys
import textwrap
import warnings
from datetime import datetime

# Hide MatplotlibDeprecationWarning in PyInstaller executable
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

import pandas as pd

from bovheat_src import bh_input, bh_output


# %%
def print_welcome():
    welcome_message = """
    Bovine Heat Analysis Tool (BovHEAT) - Version 1.0.0
    https://github.com/bovheat/bovheat
    """

    print(textwrap.dedent(welcome_message))


# %%
def get_cleaned_copy(cowdf):
    """Creates a cleaned and sorted copy of the cow dataframe

    Arguments:
        cowdf_orginal {pd.dataframe} -- original cow dataframe

    Returns:
        pd.dateframe -- cleaned cow dataframe
    """

    print(
        "\r Cleaning data for", cowdf["foldername"].iloc[0], cowdf["Cow Number"].iloc[0], end="",
    )

    cowdf = cowdf.copy()

    cowdf.dropna(subset=["Lactation Number"], inplace=True)

    # makes sure df is sorted
    cowdf.sort_values(by="datetime", inplace=True)
    cowdf.reset_index(drop=True, inplace=True)

    # Weekly schema creates overlapping empty 12:00am rows. Removing.
    duplicate_mask = cowdf.duplicated("datetime", keep=False)
    overlap_rows = cowdf[duplicate_mask & cowdf["Activity Change"].isna()]
    cowdf.drop(overlap_rows.index, inplace=True)

    # Drop complete duplicates. Same cow information found in multiple files.
    cowdf.drop_duplicates(inplace=True, ignore_index=True)
    cowdf.reset_index(inplace=True, drop=True)

    # If duplicates continue to remain, cow number is not unique in folder. Skipping cow.
    remaining_duplicates = cowdf.duplicated(["datetime", "Cow Number"]).sum()

    if remaining_duplicates:
        print(" # Cow Number is not unique within folder, skipping")
        return pd.DataFrame()

    return cowdf


# %%
def calc_calving_date(cowdf):
    """Tries to find calving date from days in lacation (DIM)

    Arguments:
        cowdf {[type]} -- [description]
    """
    print(
        "\r Calculating calving date for",
        cowdf["foldername"].iloc[0],
        cowdf["Cow Number"].iloc[0],
        end="",
    )

    cowdf.reset_index(drop=True, inplace=True)

    if cowdf["Days in Lactation"].min() >= 0:
        min_dim_row = cowdf.loc[cowdf["Days in Lactation"].idxmin()]
        min_dim_value = min_dim_row["Days in Lactation"]
        min_dim_date = min_dim_row["datetime"]

        calving_datetime = min_dim_date - pd.Timedelta(days=min_dim_value)
        return calving_datetime.normalize()

    # ToDo: Log warning and errors
    print(" # NOT FOUND", end="")

    return None


# %%
def cut_time_window(cowdf, start_dim, stop_dim, interpolation_limit):
    timeframe_dfs = pd.DataFrame()

    calving_dates = [date for date in cowdf["calving_date"].unique() if not pd.isnull(date)]
    for calving_date in calving_dates:
        type(calving_date)
        date_start = calving_date + pd.Timedelta(days=start_dim)
        date_end = calving_date + pd.Timedelta(days=stop_dim)

        datetime_range = pd.date_range(date_start, date_end, freq="2H", closed="left")
        base_df = pd.DataFrame(data={"datetime": datetime_range})

        timeframe_df = pd.merge(base_df, cowdf, on="datetime", how="left", validate="one_to_one")

        # interpolates, especially over 10:00pm missing values
        timeframe_df["Activity Change"] = timeframe_df["Activity Change"].interpolate(
            limit_area="inside", limit=interpolation_limit
        )
        timeframe_df["lactation_adj"] = cowdf[cowdf["calving_date"] == calving_date][
            "Lactation Number"
        ].iloc[0]
        timeframe_df["calving_date"] = calving_date

        # columns can remain empty, dropping them insures the use of the index from outer groupby
        # apply
        timeframe_df.drop(columns=["Cow Number", "foldername"], inplace=True)
        timeframe_dfs = pd.concat([timeframe_dfs, timeframe_df], axis=0, sort=False)

    return timeframe_dfs


# %%
def calc_heats(cowdf, threshold):
    MINIMUM_HOURS_APART = 10

    act_usable = cowdf["Activity Change"].count() / (len(cowdf)) * 100
    cowdf.reset_index(drop=True, inplace=True)

    heat_df = pd.DataFrame(
        columns=[
            "calving_date",
            "act_usable",
            "act_max",
            "heat_count",
            "heat_no",
            "start_dt_heat",
            "stop_dt_heat",
            "duration_heat",
            "max_act_heat",
            "max_dim_heat",
            "max_dt_heat",
            "short_inter_estrus",
        ]
    )

    heat_df = heat_df.append(pd.Series(dtype=object), ignore_index=True)

    peak_groups = []  # Example: [[2, 3, 4, 5], [8, 9, 10, 11]]
    gte_threshold_indexes = cowdf[cowdf["Activity Change"] >= threshold].index

    for _, group in itertools.groupby(enumerate(gte_threshold_indexes), lambda x: x[1] - x[0]):
        peak_groups.append(list(map(lambda x: x[1], group)))

    for index, heat_group in enumerate(peak_groups):
        heat_no = index + 1
        start_dt_heat = cowdf.loc[heat_group[0]]["datetime"]
        stop_dt_heat = cowdf.loc[heat_group[-1]]["datetime"]
        duration_heat = len(heat_group) * 2
        max_act_heat = cowdf.loc[heat_group]["Activity Change"].max()
        maxid = cowdf.loc[heat_group]["Activity Change"].idxmax()
        max_dim_heat = cowdf.loc[maxid]["Days in Lactation"]
        max_dt_heat = cowdf.loc[maxid]["datetime"]

        heat_df.loc[index, "heat_no"] = heat_no
        heat_df.loc[index, "start_dt_heat"] = start_dt_heat
        heat_df.loc[index, "stop_dt_heat"] = stop_dt_heat
        heat_df.loc[index, "duration_heat"] = duration_heat
        heat_df.loc[index, "max_act_heat"] = max_act_heat
        heat_df.loc[index, "max_dim_heat"] = max_dim_heat
        heat_df.loc[index, "max_dt_heat"] = max_dt_heat

        if index > 0:
            if (heat_group[0] - peak_groups[index - 1][-1]) * 2 < MINIMUM_HOURS_APART:
                heat_df.loc[index, "short_inter_estrus"] = 1

    heat_df["calving_date"] = cowdf["calving_date"].iloc[0]
    heat_df["heat_count"] = heat_df["heat_no"].nunique()
    heat_df["act_usable"] = act_usable
    heat_df["act_max"] = heat_df["max_act_heat"].max()

    return heat_df


# %%
def main():
    print_welcome()
    args = bh_input.get_args()
    start_parameters = bh_input.get_start_parameters(args)

    # Scan all file root and subfolders for xls and xslx files.
    # Raise exception and exit if none are found.
    try:
        print("Reading source")
        source_df = bh_input.get_source_data(
            start_parameters["language"], core_count=args.cores, relative_path=args.relative_path,
        )
    except Exception as e:
        print("Error:", e)
        input("Press Enter to exit.")
        raise SystemExit

    print("\nProcessing ...")

    source_df_cleaned = source_df.groupby(["foldername", "Cow Number"], group_keys=False).apply(
        get_cleaned_copy
    )

    calving_dates = source_df_cleaned.groupby(
        ["foldername", "Cow Number", "Lactation Number"]
    ).apply(calc_calving_date)

    source_df_calved = pd.merge(
        source_df_cleaned,
        calving_dates.rename("calving_date"),
        on=calving_dates.index.names,
        how="left",
    )

    sections_df = source_df_calved.groupby(["foldername", "Cow Number"]).apply(
        cut_time_window,
        start_dim=start_parameters["start_dim"],
        stop_dim=start_parameters["stop_dim"],
        interpolation_limit=args.interpolation_limit,
    )
    sections_df = sections_df.reset_index().drop(columns="level_2")

    heats_df = sections_df.groupby(["foldername", "Cow Number", "lactation_adj"]).apply(
        calc_heats, threshold=start_parameters["threshold"]
    )

    heats_df = heats_df.reset_index().drop(columns="level_3")
    heats_filtered_df = heats_df[heats_df["act_usable"] > 0]

    if args.outputname:
        out_filename = args.outputname
    else:
        out_filename = (
            f"BovHEAT_start{start_parameters['start_dim']}"
            + f"_stop{start_parameters['stop_dim']}_t{start_parameters['threshold']}_"
            + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )

    print("\nCalculation finished - Writing xlsx file...")
    bh_output.write_xlsx(heats_filtered_df, filename=out_filename)

    print("\nWriting visualisation to pdf file...")
    bh_output.write_pdf(
        heats_filtered_df,
        sections_df=sections_df,
        threshold=start_parameters["threshold"],
        filename=out_filename,
    )

    input("Hit Enter to close.")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # adds support for multiprocessing in pyinstaller executables
    main()
