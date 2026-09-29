import sys

import pytest

from tabulint import analyze, infer_type, is_missing, profile_fields
from tabulint.analyzer import check_duplicates, check_missing_values, check_type_consistency
from tabulint.models import TabulintError


def codes(issues):
    return sorted(issue.code for issue in issues)


def test_is_missing():
    assert is_missing(None)
    assert is_missing("")
    assert is_missing("   ")
    assert not is_missing(0)
    assert not is_missing("0")
    assert not is_missing(False)


def test_infer_type_from_strings():
    assert infer_type("") == "null"
    assert infer_type("true") == "boolean"
    assert infer_type("FALSE") == "boolean"
    assert infer_type("42") == "integer"
    assert infer_type("-7") == "integer"
    assert infer_type("3.5") == "float"
    assert infer_type("Ada") == "string"


def test_infer_type_from_boolean_literals():
    for literal in ("yes", "no", "y", "n", "t", "f"):
        assert infer_type(literal) == "boolean"
        assert infer_type(literal.upper()) == "boolean"
        assert infer_type(f"  {literal}  ") == "boolean"
        assert infer_type(f"  {literal.upper()}  ") == "boolean"


def test_numeric_literals_remain_integers():
    assert infer_type("1") == "integer"
    assert infer_type("0") == "integer"


def test_integer_with_redundant_zeroes_does_not_infer_as_float():
    assert infer_type("0" * 4300 + "9007199254740993") == "integer"


def test_oversized_native_integer_type_mismatch_has_readable_message():
    issues = check_type_consistency([{"n": "word"}, {"n": "text"}, {"n": 10**5000}])
    assert len(issues) == 1
    assert issues[0].code == "type-mismatch"
    assert "integer" in issues[0].message


def test_mixed_boolean_spellings_have_no_type_mismatch():
    records = [{"active": "yes"}, {"active": "true"}, {"active": "N"}, {"active": "false"}]
    assert profile_fields(records)[0].dominant_type == "boolean"
    assert check_type_consistency(records) == []


def test_unrelated_string_is_not_boolean():
    assert infer_type("maybe") == "string"


def test_infer_type_from_native_values():
    assert infer_type(None) == "null"
    assert infer_type(True) == "boolean"
    assert infer_type(9) == "integer"
    assert infer_type(1.5) == "float"
    assert infer_type(["x"]) == "string"


def test_profile_fields_reports_dominant_type_and_missing():
    records = [
        {"age": "30", "name": "Ada"},
        {"age": "31", "name": ""},
        {"age": "x", "name": "Grace"},
    ]
    profiles = {p.name: p for p in profile_fields(records)}
    assert profiles["age"].dominant_type == "integer"
    assert profiles["age"].type_counts == {"integer": 2, "string": 1}
    assert profiles["name"].dominant_type == "string"
    assert profiles["name"].missing_count == 1


def test_clean_dataset_has_no_issues():
    records = [{"name": "Ada", "age": "36"}, {"name": "Grace", "age": "45"}]
    assert analyze(records) == []


def test_missing_values_are_reported():
    issues = check_missing_values([{"name": "Ada", "age": ""}, {"name": None, "age": "9"}])
    assert codes(issues) == ["missing-value", "missing-value"]
    assert issues[0].row == 1 and issues[0].field_name == "age"


def test_absent_field_is_an_error():
    issues = check_missing_values([{"name": "Ada", "age": "36"}, {"name": "Grace"}])
    assert codes(issues) == ["missing-field"]
    assert issues[0].severity == "error"
    assert issues[0].row == 2


def test_duplicate_records_are_grouped_into_one_issue():
    records = [{"a": "1"}, {"a": "2"}, {"a": "1"}, {"a": "1"}]
    issues = check_duplicates(records)
    assert len(issues) == 1
    assert issues[0].code == "duplicate-record"
    assert issues[0].row == 3
    assert issues[0].message == "record from row 1 is repeated at rows 3, 4"


def test_distinct_records_are_not_duplicates():
    assert check_duplicates([{"a": "1"}, {"a": "2"}]) == []


def test_absent_fields_and_explicit_nulls_are_distinct_duplicate_groups():
    issues = check_duplicates([{"a": None}, {}, {"a": None}, {}])
    assert [issue.message for issue in issues] == [
        "record from row 1 is repeated at rows 3",
        "record from row 2 is repeated at rows 4",
    ]


def test_duplicate_objects_ignore_key_order_at_every_depth():
    records = [
        {"a": {"x": 1, "y": [{"first": True, "second": None}]}, "b": 2},
        {"b": 2, "a": {"y": [{"second": None, "first": True}], "x": 1}},
    ]
    issues = check_duplicates(records)
    assert len(issues) == 1
    assert issues[0].message == "record from row 1 is repeated at rows 2"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (True, 1),
        (1, 1.0),
        (1, "1"),
        (None, "None"),
        ([True], [1]),
        ({"a": True}, {"a": 1}),
        ({"a": None}, {}),
        ([1, 2], [2, 1]),
        ([], {}),
        ([[1], 2], [[1, 2]]),
        ([[], []], [[]]),
    ],
)
def test_duplicate_keys_preserve_types_order_and_container_boundaries(first, second):
    assert check_duplicates([{"value": first}, {"value": second}]) == []


def test_deeply_nested_duplicates_do_not_depend_on_python_recursion_limit():
    first = second = None
    for _ in range(sys.getrecursionlimit() + 10):
        first = {"a": [first], "b": 1}
        second = {"b": 1, "a": [second]}
    issues = check_duplicates([{"value": first}, {"value": second}])
    assert len(issues) == 1
    assert issues[0].row == 2


def test_shared_noncyclic_containers_are_allowed():
    shared = {"a": []}
    assert len(check_duplicates([{"value": [shared, shared]}] * 2)) == 1


@pytest.mark.parametrize("value", [[], {}])
def test_cyclic_containers_are_rejected(value):
    if isinstance(value, list):
        value.append(value)
    else:
        value["self"] = value
    with pytest.raises(TabulintError, match="cyclic objects or lists"):
        check_duplicates([{"value": value}])


def test_two_distinct_duplicate_groups_produce_two_issues():
    records = [
        {"a": "1"},
        {"a": "2"},
        {"a": "1"},
        {"a": "2"},
    ]
    issues = check_duplicates(records)
    assert [issue.row for issue in issues] == [3, 4]
    assert issues[0].message == "record from row 1 is repeated at rows 3"
    assert issues[1].message == "record from row 2 is repeated at rows 4"


def test_long_duplicate_group_truncates_row_list():
    records = [{"a": "1"}] * 13
    issues = check_duplicates(records)
    assert len(issues) == 1
    expected_rows = ", ".join(str(row) for row in range(2, 12))
    assert issues[0].message == (
        f"record from row 1 is repeated at rows {expected_rows}, and 2 more"
    )


def test_dataset_with_all_distinct_records_has_no_duplicate_issues():
    records = [{"a": "1"}, {"a": "2"}, {"a": "3"}]
    assert check_duplicates(records) == []


def test_inconsistent_types_are_reported():
    records = [{"age": "30"}, {"age": "31"}, {"age": "thirty"}]
    issues = check_type_consistency(records)
    assert len(issues) == 1
    assert issues[0].code == "type-mismatch"
    assert issues[0].row == 3
    assert issues[0].severity == "error"


def test_missing_values_do_not_count_as_type_mismatch():
    records = [{"age": "30"}, {"age": ""}, {"age": "31"}]
    assert check_type_consistency(records) == []


def test_single_type_field_has_no_mismatch():
    assert check_type_consistency([{"age": "30"}, {"age": "31"}]) == []
