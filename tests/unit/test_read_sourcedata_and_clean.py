# pylint: disable-all
import pytest
from bovheat_src import bh_input, bovheat

# Test pass
@pytest.mark.parametrize(
    "lang, rel_path, out1, out2",
    [
        # Test 1 - eng and xlsx
        ("eng", "tests/unit/test_read_sourcedata_and_clean/Test1_eng_xlsx/", 6994, 6204),
        # Test 2 - ger and xls
        ("ger", "tests/unit/test_read_sourcedata_and_clean/Test2_ger_xls/", 6970, 6366),
    ],
)
def test_calc_calving_date_pass(lang, rel_path, out1, out2):
    # Test reading files
    df = bh_input.get_source_data(lang, rel_path)
    assert len(df) == out1

    # Test cleaning loaded data
    assert len(bovheat.get_cleaned_copy(df)) == out2


# Test exceptions
@pytest.mark.parametrize(
    "lang, rel_path, exception_msg",
    [
        # Test 3 - malformed and corrupted files
        ("eng", "tests/unit/test_read_sourcedata_and_clean/Test3_malformed_corrupted/", "No XLSX or XLS files found.",),
        # Test 4 - no valid files to read
        ("eng", "tests/unit/test_read_sourcedata_and_clean/Test4_empty/", "No XLSX or XLS files found."),
    ],
)
def test_calc_calving_date_fail(lang, rel_path, exception_msg):
    # Expect Exception
    with pytest.raises(Exception) as e:
        assert bh_input.get_source_data(lang, rel_path)

    # Check exception message
    assert exception_msg in str(e.value)
