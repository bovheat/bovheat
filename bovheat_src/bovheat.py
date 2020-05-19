#!/usr/bin/env python3

# %%
# Mandatory column with named headers in input SCR files:
# 'Activity Change'
# 'Cow Number'
# 'Date'
# 'Time'
# 'Days in Lactation' - for estrus results and calving date determination
# 'Lactation Number'


# %%

import itertools
import os
from datetime import datetime

import pandas as pd

from bovheat_src import output_creation


# %%
def ask_constants():
    while True:
        language = input("Column header language, type either eng or ger: ")
        start_dim = int(input("Choose DIM to start, e.g. 0: "))
        stop_dim = int(input("Choose DIM to stop, e.g. 30: "))
        threshold = int(input("Threshold between 0 and 100 to use, e.g. 35: "))

        print(
            f"# You selected: \
            \nStart Dim is day {start_dim} \
            \nStop Dim is day {stop_dim} \
            \nDetection threshold of {threshold}"
        )

        userchoice = input("Please type c to continue or r to retry: ")

        if userchoice == "c":
            return (language, start_dim, stop_dim, threshold)


# %%
def read_sourcedata(language, relative_path=""):
    """Reads all .xslx files in current directory and merges into one dataframe
    Unnamend columns and empty rows are dismissed.

    Returns:
        pd.dataframe
    """

    folderpath = os.path.join(os.getcwd(), relative_path)

    # right hand side are mandatory column headers
    # left hand side can be edited, to comply with differenct column header languages
    translation_table = {
        "Cow Number": "Cow Number",
        "Date": "Date",
        "Time": "Time",
        "Activity Change": "Activity Change",
        "Lactation Number": "Lactation Number",
        "Days in Lactation": "Days in Lactation",
    }

    translation_german = {
        "Kuhnummer": "Cow Number",
        "Termin": "Date",
        "Zeit": "Time",
        "Aktivität ändern": "Activity Change",
        "Laktationnummer": "Lactation Number",
        "Laktationstage": "Days in Lactation",
    }

    if language == "ger":
        translation_table = translation_german

    sum_df = pd.DataFrame()
    print(f"Reading directory {folderpath}:")
    for root, _, files in os.walk(folderpath):
        for name in files:
            if name.endswith((".xlsx", ".xls")) and not name.startswith(
                    (".", "~", "BovHEAT")
            ):
                print("\r Reading file", name, end="")

                data = pd.read_excel(
                    os.path.join(root, name),
                    usecols=list(translation_table.keys()),
                    sheet_name=0,
                    index=True,
                )

                data.rename(columns=translation_table, inplace=True)

                # removes empty rows, including possible footers rows
                data.dropna(subset=["Cow Number", "Time"], inplace=True)

                data["foldername"] = os.path.basename(root)

                data["datetime"] = pd.to_datetime(
                    data["Date"].astype(str) + " " + data["Time"].astype(str)
                )
                sum_df = pd.concat([sum_df, data], axis=0, sort=False)
    assert len(sum_df) > 0, "No XLSX or XLS files found."

    return sum_df


# %%
def get_cleaned_copy(cowdf):
    """Creates a cleaned and sorted copy of the cow dataframe

    Arguments:
        cowdf_orginal {pd.dataframe} -- original cow dataframe

    Returns:
        pd.dateframe -- cleaned cow dataframe
    """

    print(
        "\r Cleaning data for",
        cowdf["foldername"].iloc[0],
        cowdf["Cow Number"].iloc[0],
        end="",
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
    """Tries to find calving date from days in lacation based on lactation number received

    Arguments:
        cowdf {[type]} -- [description]
        cowdf_results {[type]} -- [description]
        lactation {[type]} -- [description]
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
def cut_time_window(cowdf, start_dim, stop_dim):
    timeframe_dfs = pd.DataFrame()

    calving_dates = [
        date for date in cowdf["calving_date"].unique() if not pd.isnull(date)
    ]
    for calving_date in calving_dates:
        type(calving_date)
        date_start = calving_date + pd.Timedelta(days=start_dim)
        date_end = calving_date + pd.Timedelta(days=stop_dim)

        # ToDo: This excludes the date of date_end, ok?
        datetime_range = pd.date_range(date_start, date_end, freq="2H", closed="left")
        base_df = pd.DataFrame(data={"datetime": datetime_range})

        timeframe_df = pd.merge(
            base_df, cowdf, on="datetime", how="left", validate="one_to_one"
        )

        # interpolates, especially over 10:00pm missing values
        timeframe_df["Activity Change"] = timeframe_df["Activity Change"].interpolate(
            limit_area="inside", limit=2
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


# %%


def get_usable(cowdf_cut):
    if cowdf_cut is not None:
        return cowdf_cut["Activity Change"].notnull().sum() / len(cowdf_cut) * 100
    return 0


def calc_heats(cowdf, threshold):
    # ToDo: Implement peaks-touching

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
            "abnormal_flag",
        ]
    )

    heat_df = heat_df.append(pd.Series(dtype=object), ignore_index=True)

    peak_groups = []  # Example: [[2, 3, 4, 5], [8, 9, 10, 11]]
    gte_threshold_indexes = cowdf[cowdf["Activity Change"] >= threshold].index

    for _, group in itertools.groupby(
            enumerate(gte_threshold_indexes), lambda x: x[1] - x[0]
    ):
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

    heat_df["calving_date"] = cowdf["calving_date"].iloc[0]
    heat_df["heat_count"] = heat_df["heat_no"].nunique()
    heat_df["act_usable"] = act_usable
    heat_df["act_max"] = heat_df["max_act_heat"].max()
    heat_df["abnormal_flag"] = None

    return heat_df


# %%
def main():
    language, start_dim, stop_dim, threshold = ask_constants()

    # Scan all file root and subfolders for xls and xslx files.
    # Raise exception and exit if none are found.

    try:
        print("Reading source")
        source_df = read_sourcedata(language, relative_path="../")
    except Exception as e:
        print("Error: ", e)
        input("Press Enter to exit.")
        raise SystemExit

    print("\nProcessing ...")
    out_filename = f"BovHEAT_start{start_dim}_stop{stop_dim}_t{threshold}_" + datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    source_df_cleaned = source_df.groupby(
        ["foldername", "Cow Number"], group_keys=False
    ).apply(get_cleaned_copy)

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
        cut_time_window, start_dim=start_dim, stop_dim=stop_dim
    )
    sections_df = sections_df.reset_index().drop(columns="level_2")

    heats_df = sections_df.groupby(["foldername", "Cow Number", "lactation_adj"]).apply(
        calc_heats, threshold=threshold
    )
    heats_df = heats_df.reset_index().drop(columns="level_3")
    heats_filtered_df = heats_df[heats_df["act_usable"] > 0]

    print("\nCalculation finished - Writing pdf and xlsx files...")

    output_creation.write_pdf(
        heats_filtered_df,
        sections_df=sections_df,
        threshold=threshold,
        filename=out_filename,
    )
    output_creation.write_xlsx(heats_filtered_df, filename=out_filename)

    input("Hit Enter to close.")


if __name__ == "__main__":
    main()
