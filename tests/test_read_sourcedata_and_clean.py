import pytest
from bovheat_src import bovheat as bh

# Test pass
@pytest.mark.parametrize("lang, rel_path, out1, out2",
                         # Test 1 eng and xlsx
                         [("eng", "tests/data/Test1_eng_xlsx/", 6994, 6204),
                          # Test 2 ger and xls
                          ("ger", "tests/data/Test2_ger_xls/", 6970, 6366)
                          ])
def test_calc_calving_date_pass(lang, rel_path, out1, out2):
    # Test Reading files
    df = bh.read_sourcedata(lang, rel_path)
    assert len(df) == out1

    # Test cleaning loaded data
    assert len(bh.get_cleaned_copy(df)) == out2


# Test Exceptions
@pytest.mark.parametrize("lang, rel_path, exception_msg",
                         # Test 1 eng and xlsx
                         [("eng", "tests/data/Test3_malformed/",
                           "Usecols do not match columns, columns expected but not found"),
                          # Test 2 ger and xls
                          ("eng", "tests/data/Test4_empty/", "No XLSX or XLS files found.")
                          ])
def test_calc_calving_date_fail(lang, rel_path, exception_msg):
    # Expect Exception
    with pytest.raises(Exception) as e:
        assert bh.read_sourcedata(lang, rel_path)

    # Check exception message
    assert exception_msg in str(e.value)
