import json

import pytest

import tabulint
from tabulint.cli import main


@pytest.mark.parametrize("value", [None, "", " \t\n"])
def test_required_missing_value_reports_correct_row(value):
    issues = tabulint.check_required_fields([{"email": "a@b.test"}, {"email": value}], ["email"])
    assert [(i.code, i.severity, i.field_name, i.row) for i in issues] == [
        ("required-missing", "error", "email", 2)
    ]
    assert "email" in issues[0].message


@pytest.mark.parametrize("value", [0, False, "0", "false", " a@b.test ", [], {}])
def test_required_present_values_pass(value):
    assert tabulint.check_required_fields([{"email": value}], ["email"]) == []


def test_required_absent_key_reports_record_row():
    issues = tabulint.check_required_fields([{}, {"email": "a@b.test"}], ["email"])
    assert [(i.code, i.severity, i.field_name, i.row) for i in issues] == [
        ("required-missing", "error", "email", 1)
    ]


def test_required_global_absence_is_once_per_distinct_name_in_requested_order():
    records = [{"id": 1}, {"id": 2}]
    names = ["email", "name", "email"]
    issues = tabulint.check_required_fields(records, names)
    assert [(i.code, i.severity, i.field_name, i.row) for i in issues] == [
        ("required-missing", "error", "email", None),
        ("required-missing", "error", "name", None),
    ]
    assert all(i.field_name in i.message for i in issues)
    assert records == [{"id": 1}, {"id": 2}]
    assert names == ["email", "name", "email"]


def test_required_repeated_names_do_not_repeat_row_errors():
    issues = tabulint.check_required_fields([{"email": ""}, {}], ["email", "email"])
    assert [(i.field_name, i.row) for i in issues] == [("email", 1), ("email", 2)]


def test_required_names_match_exactly():
    issues = tabulint.check_required_fields([{"email": "a@b.test"}], ["Email", " email", "email"])
    assert [(i.field_name, i.row) for i in issues] == [("Email", None), (" email", None)]


def test_required_helper_has_no_empty_dataset_issue():
    assert tabulint.check_required_fields([], ["email"]) == []
    assert tabulint.check_required_fields([{}], []) == []


def test_required_check_records_preserves_structural_and_numeric_issues():
    records = [{"email": "", "age": 200}, {"age": 30}]
    rules = [tabulint.NumericRule("age", maximum=120)]
    baseline = tabulint.check_records(records, rules, "sample")
    report = tabulint.check_records(records, rules, "sample", required_fields=["email"])
    assert [i for i in report.issues if i.code != "required-missing"] == baseline.issues
    assert {i.code for i in baseline.issues} == {"missing-value", "missing-field", "above-maximum"}
    assert [(i.field_name, i.row) for i in report.issues if i.code == "required-missing"] == [
        ("email", 1), ("email", 2)
    ]
    assert report.path == "sample"
    assert report.profiles == baseline.profiles
    assert report.field_names == baseline.field_names
    assert report.row_count == baseline.row_count


@pytest.mark.parametrize("required", [None, []])
def test_no_required_names_preserves_complete_report(required):
    records = [{"email": ""}, {"email": "a@b.test"}, {}]
    assert tabulint.check_records(records, required_fields=required) == tabulint.check_records(records)


@pytest.mark.parametrize("suffix,content", [
    ("csv", "id,email\n1,\n2,a@b.test\n"),
    ("json", '[{"id": 1, "email": null}, {"id": 2, "email": "a@b.test"}]'),
    ("jsonl", '\n{"id": 1, "email": ""}\n\n{"id": 2, "email": "a@b.test"}\n'),
    ("ndjson", '{"id": 1, "email": " "}\n{"id": 2, "email": "a@b.test"}\n'),
])
def test_check_file_required_fields_across_formats(write, suffix, content):
    path = write("records." + suffix, content)
    report = tabulint.check_file(path, required_fields=["email"])
    assert [(i.field_name, i.row) for i in report.issues if i.code == "required-missing"] == [("email", 1)]
    assert any(i.code == "missing-value" for i in report.issues)


def test_check_file_combines_required_with_existing_keyword_and_positional_arguments(write):
    path = write("records.csv", "nom;age\n;200\n", encoding="utf-16")
    report = tabulint.check_file(path, [tabulint.NumericRule("age", maximum=120)],
                                delimiter=";", encoding="utf-16", required_fields=["nom"])
    assert {i.code for i in report.issues} == {"missing-value", "above-maximum", "required-missing"}


@pytest.mark.parametrize("suffix,content", [
    ("csv", ""), ("csv", "email\n"), ("json", "[]"), ("jsonl", "\n"), ("ndjson", ""),
])
def test_zero_row_inputs_keep_only_existing_warning(write, suffix, content):
    path = write("empty." + suffix, content)
    report = tabulint.check_file(path, required_fields=["email", "absent"])
    assert report == tabulint.check_file(path)
    assert [(i.code, i.severity, i.row) for i in report.issues] == [("empty-dataset", "warning", None)]


def test_check_records_empty_keeps_only_existing_warning():
    assert tabulint.check_records([], required_fields=["email"]) == tabulint.check_records([])


@pytest.mark.parametrize("options,expected", [([], 1), (["--fail-on", "error"], 1),
    (["--fail-on", "warning"], 1), (["--fail-on", "never"], 0)])
def test_cli_required_preserves_fail_on_and_json_report(write, capsys, options, expected):
    path = write("records.csv", "id,email\n1,\n")
    assert main([path, "--required", "email", "--format", "json", *options]) == expected
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert [(i["code"], i["severity"], i["field"], i["row"]) for i in report["issues"]] == [
        ("missing-value", "warning", "email", 1),
        ("required-missing", "error", "email", 1),
    ]


def test_cli_required_repeatable_global_absence_and_output(write, tmp_path, capsys):
    path = write("records.csv", "id\n1\n2\n")
    output = tmp_path / "report.json"
    assert main([path, "--required", "email", "--required", "name", "--required", "email",
                 "--quiet", "--format", "json", "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    report = json.loads(output.read_text(encoding="utf-8"))
    assert [(i["code"], i["field"], i["row"]) for i in report["issues"]] == [
        ("required-missing", "email", None), ("required-missing", "name", None)
    ]


def test_cli_required_populated_zero_and_false_pass(write, capsys):
    path = write("records.json", '[{"count": 0, "enabled": false}]')
    assert main([path, "--required", "count", "--required", "enabled"]) == 0
    assert "no issues found" in capsys.readouterr().out


@pytest.mark.parametrize("options,expected", [([], 1), (["--fail-on", "error"], 0),
    (["--fail-on", "warning"], 1), (["--fail-on", "never"], 0)])
def test_cli_required_header_only_obeys_existing_warning_threshold(write, capsys, options, expected):
    path = write("empty.csv", "email\n")
    assert main([path, "--required", "email", *options]) == expected
    output = capsys.readouterr().out
    assert "empty-dataset" in output
    assert "required-missing" not in output


def test_cli_required_never_does_not_suppress_load_error(write, capsys):
    path = write("broken.json", "[")
    assert main([path, "--required", "email", "--fail-on", "never"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err


def test_cli_required_needs_a_field_argument(write, capsys):
    path = write("records.csv", "email\na@b.test\n")
    with pytest.raises(SystemExit) as exc:
        main([path, "--required"])
    assert exc.value.code == 2
    assert "expected one argument" in capsys.readouterr().err
