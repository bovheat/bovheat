import argparse
import multiprocessing
import os
from itertools import starmap

import pandas as pd


def get_start_parameters(args):
    # interactive mode
    if args.startstop is None:
        return get_userinput()

    # non-interactive mode
    return {
        "language": args.language,
        "start_dim": args.startstop[0],
        "stop_dim": args.startstop[1],
        "threshold": args.threshold,
        "minheatlength": args.minheatlength,
    }


def get_args():
    parser = argparse.ArgumentParser(
        description="# Bovine Heat Detection and Analysis Tool (BovHEAT) #  \
        \n\nBovHEAT starts in interactive mode, if startstop is not provided",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # positional argument
    parser.add_argument(
        "relative_path",
        type=str,
        nargs="?",
        default="",
        help="relative path to folder containing SCR xls(x) files",
    )

    parser.add_argument(
        "-c",
        "--cores",
        type=int,
        default="0",
        help="specify amount of logical cores to use,\
        default 0: auto (max available -1), 1: disable multiprocessing, >1: fixed core amount",
    )

    parser.add_argument(
        "-i",
        "--interpolation_limit",
        type=int,
        metavar="[0-n]",
        default=2,
        help="Maximum number of consecutive missing values to fill. 0 disables interpolation",
    )

    parser.add_argument(
        "-l",
        "--language",
        type=str,
        choices=["ger", "eng"],
        default="eng",
        help="language of column headings, default=eng",
    )

    parser.add_argument(
        "-x",
        "--x_axis_type",
        type=str,
        choices=["dt", "dim"],
        default="dim",
        help="show x-axis as datetime or dim in PDF, default=dim",
    )

    parser.add_argument(
        "-m",
        "--minheatlength",
        type=int,
        choices=range(1, 101),
        metavar="[0-100]",
        default=1,
        help="minimum number of heat observations required to count as a heat, default=1",
    )

    parser.add_argument(
        "-o",
        "--outputname",
        type=str,
        default="",
        help="specify output filename for result xlsx and pdf",
    )

    parser.add_argument(
        "-s",
        "--startstop",
        nargs=2,
        type=int,
        metavar=("start-dim", "stop-dim"),
        help="negative values are allowed",
    )

    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        choices=range(0, 101),
        metavar="[0-100]",
        default=35,
        help="threshold for heat detection, default=35",
    )

    args = parser.parse_args()

    if args.cores > multiprocessing.cpu_count():
        parser.error("Core count too high for this system.")

    if args.interpolation_limit is not None:
        if args.interpolation_limit < 0:
            parser.error("Please choose a value greater or equal 0")
        if args.interpolation_limit == 0:
            args.interpolation_limit = None

    if args.startstop:
        if args.startstop[0] > args.startstop[1]:
            parser.error("Please choose start < stop.")

    return args


# %%
def get_userinput():
    while True:
        language = input("Column header language, type either eng or ger: ")
        start_dim = int(input("Choose DIM to start, e.g. 0: "))
        stop_dim = int(input("Choose DIM to stop, e.g. 30: "))
        threshold = int(input("Threshold between 0 and 100 to use, e.g. 35: "))
        minheatlength = int(input("Minimum numbers of heat observations required to count as a heat: "))

        print(
            f"# You selected: \
            \nStart Dim is day {start_dim} \
            \nStop Dim is day {stop_dim} \
            \nDetection threshold of {threshold} \
            \nMinimum heat observations number of {minheatlength}"
        )

        userchoice = input("Please type c to continue or r to retry: ")

        if userchoice == "c":
            return {
                "language": language,
                "start_dim": start_dim,
                "stop_dim": stop_dim,
                "threshold": threshold,
                "minheatlength": minheatlength,
            }


def read_clean_file(root, file_name, translation_table):
    try:
        data = pd.read_excel(
            os.path.join(root, file_name),
            usecols=list(translation_table.keys()),
            sheet_name=0,
        )
    except:
        print(f"\r{file_name} ...SKIPPED")
        return None

    print(f"\r{file_name}", end="".ljust(20))
    data.rename(columns=translation_table, inplace=True)

    # removes empty rows, including possible footers rows
    data.dropna(subset=["Cow Number", "Time"], inplace=True)

    data["foldername"] = os.path.basename(root)

    data["datetime"] = pd.to_datetime(data["Date"].astype(str) + " " + data["Time"].astype(str), format='mixed')

    return data


# %%
def get_source_data(language, core_count=0, relative_path=""):
    """Reads all .xslx and .xls files in current directory and merges into one dataframe.

    Files have to include the following column headers names:
    'Activity Change'
    'Cow Number'
    'Date'
    'Time'
    'Days in Lactation'
    'Lactation Number'

    File is skipped, if columns are not present or file is damaged.
    Unnamed columns and empty rows are dismissed.

    Parameters
    ----------
    core_count : int
        How many logical core to use. 0 means auto

    language : str
        Select column header language, ger or eng

    relative_path : str
        Specify optional relative path

    Returns
    -------
    dataframe : pandas.DataFrame()
        One Dataframe with all read tables combined

    """

    folderpath = os.path.join(os.getcwd(), relative_path)

    # right hand side are mandatory column headers
    # left hand side can be edited, to comply with different column header languages
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

    file_list = []
    print(f"Searching for files in directory {folderpath}:")
    for root, _, files in os.walk(folderpath):
        for name in files:
            if name.endswith((".xlsx", ".xls")) and not name.startswith((".", "~", "BovHEAT")):
                file_list.append((root, name, translation_table))

    print(len(file_list), "files found.", end="")

    if core_count == 1:  # do not use multiprocessing
        print(f"Reading with {core_count} core(s) ...")
        df_list = list(starmap(read_clean_file, file_list))
    else:
        if core_count == 0:  # auto core count selection
            read_cores = multiprocessing.cpu_count() - 1
        else:  # core count fixed
            read_cores = core_count

        print(f"Reading with {read_cores} core(s) ...")
        with multiprocessing.Pool(processes=read_cores) as pool:
            df_list = pool.starmap(read_clean_file, file_list)

    valids_df = [df for df in df_list if isinstance(df, pd.DataFrame)]
    if len(valids_df) < 1:
        raise Exception("No files found or readable.")

    # None items are silently dropped by concat
    sum_df = pd.concat(df_list, axis=0, sort=False)

    return sum_df
