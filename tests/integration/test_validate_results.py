import io
import sys
import pandas as pd

from bovheat_src import bovheat


def test_complete_runthrough(monkeypatch):
    # add custom argv
    additional_argv = "example/data -s -5 30 -l eng -t 35 -o out_file -i 2".split(" ")
    monkeypatch.setattr(sys, "argv", [sys.argv[0]] + additional_argv)
    monkeypatch.setattr("sys.stdin", io.StringIO("enter"))

    # run bovheat from start to finish
    bovheat.main()
    import os

    print(os.getcwd())

    # read generated and validated dataset
    validated_results_df = pd.read_excel(
        "tests/integration/test_validate_results/validated_results.xlsx"
    )
    out_file_df = pd.read_excel("out_file.xlsx")

    # compare
    assert validated_results_df.equals(out_file_df)
