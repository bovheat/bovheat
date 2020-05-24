import argparse
import os
from argparse import RawDescriptionHelpFormatter

import pandas as pd


def get_start_parameters(args):

    # no parameters given
    if args.mode is None:
        return get_userinput()

    # automatic mode chosen
    if args.mode == "automatic":
        return {
            "language": args.language,
            "start_dim": args.start,
            "stop_dim": args.stop,
            "threshold": args.threshold,
        }


def get_args():

    parser = argparse.ArgumentParser(
        description="Bovine Heat Analysis Tool (BovHEAT) \
        \nTwo additional modes are available:",
        formatter_class=RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-rel_path", type=str, default="",
    )

    subparsers = parser.add_subparsers(help="Available processing modes:", dest="mode")

    parser_automatic = subparsers.add_parser(
        "automatic", help="Automatic processing with given start parameters"
    )
    parser_automatic.add_argument("-language", type=str, choices=["ger", "eng"], required=True)
    parser_automatic.add_argument("-start", type=int, required=True)
    parser_automatic.add_argument("-stop", type=int, required=True)
    parser_automatic.add_argument(
        "-threshold", type=int, choices=range(0, 101), metavar="[0-100]", required=True
    )

    # Todo bulldozer mode for heifers
    # parser_bulldozer = subparsers.add_parser(
    #     "bulldozer", help="Processes all data found. Ignoring start, stop and calving dates."
    # )
    # parser_bulldozer.add_argument(
    #     "-language", type=str, choices=["ger", "eng"], required=True
    # )
    # parser_bulldozer.add_argument(
    #     "-threshold", type=int, choices=range(0, 101), metavar="[0-100]", required=True
    # )

    args = parser.parse_args()

    if args.mode == "automatic":
        if args.start > args.stop:
            parser.error("Please choose start < stop.")

    return args


# %%
def get_userinput():

    # ToDo Check start_dim < stop_dim
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
            return {
                "language": language,
                "start_dim": start_dim,
                "stop_dim": stop_dim,
                "threshold": threshold,
            }


# %%
def read_sourcedata(language, relative_path=""):
    """Reads all .xslx files in current directory and merges into one dataframe
    Unnamend columns and empty rows are dismissed.


    Mandatory column with named headers in input SCR files:
    'Activity Change'
    'Cow Number'
    'Date'
    'Time'
    'Days in Lactation' - for estrus results and calving date determination
    'Lactation Number'

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
            if name.endswith((".xlsx", ".xls")) and not name.startswith((".", "~", "BovHEAT")):
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
