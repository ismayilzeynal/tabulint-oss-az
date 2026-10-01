import sys

import pytest

from tabulint import NumericRule, check_file, check_records


def test_python_records_support_mixed_nested_mapping_key_types():
    report = check_records([
        {"metadata": {1: "one", "two": 2}},
        {"metadata": {"two": 2, 1: "one"}},
    ])
    assert len(report.issues) == 1
    assert report.issues[0].code == "duplicate-record"


def test_oversized_native_integers_keep_exact_duplicate_identity():
    value = 10**5000
    report = check_records([{"n": value}, {"n": value + 1}, {"n": value}])
    assert len(report.issues) == 1
    assert report.issues[0].message == "record from row 1 is repeated at rows 3"


def test_oversized_native_integer_can_be_checked_with_numeric_rule():
    report = check_records([{"n": 10**5000}], [NumericRule("n", maximum=1)])
    assert [issue.code for issue in report.issues] == ["above-maximum"]


@pytest.mark.parametrize("suffix", [".json", ".jsonl", ".ndjson"])
def test_deep_json_duplicates_are_compared_structurally(tmp_path, suffix):
    depth = sys.getrecursionlimit() // 2
    first_value = "[" * depth + '{"x": 1, "y": 2}' + "]" * depth
    second_value = "[" * depth + '{"y": 2, "x": 1}' + "]" * depth
    rows = ['{"value": ' + value + "}" for value in (first_value, second_value)]
    text = "[" + ",".join(rows) + "]" if suffix == ".json" else "\n".join(rows)
    path = tmp_path / ("deep" + suffix)
    path.write_text(text, encoding="utf-8")

    report = check_file(path)

    assert len(report.issues) == 1
    assert report.issues[0].code == "duplicate-record"
    assert report.issues[0].message == "record from row 1 is repeated at rows 2"
