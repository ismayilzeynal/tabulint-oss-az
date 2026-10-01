import pytest

from tabulint import check_records, infer_type, profile_fields
from tabulint.cli import main


@pytest.mark.parametrize("value", ["nan", "NaN", "+NAN", "-nan", "inf", "+Inf",
    "-INF", "infinity", "+Infinity", "-INFINITY", "  NaN  ", "1e9999",
    float("nan"), float("inf"), float("-inf")])
def test_nonfinite_values_infer_as_strings(value):
    assert infer_type(value) == "string"


@pytest.mark.parametrize("value,expected", [("+5", "integer"), ("1_000", "integer"),
    ("-1_000", "integer"), ("1_000.5", "float"), ("1__000", "string"),
    ("1,000", "string"), ("Ada", "string")])
def test_signs_and_underscore_separators(value, expected):
    assert infer_type(value) == expected


@pytest.mark.parametrize("values", [[1.5, 2.5, 3], ["1.5", "2.5", "+3"]])
def test_integers_are_compatible_with_dominant_float(values):
    records = [{"n": value} for value in values]
    assert check_records(records).issues == []
    profile = profile_fields(records)[0]
    assert profile.dominant_type == "float"
    assert profile.type_counts == {"float": 2, "integer": 1}


@pytest.mark.parametrize("last", [3.5, 3.0, "3.5", "3.0"])
def test_float_in_dominant_integer_field_remains_mismatch(last):
    report = check_records([{"n": 1}, {"n": 2}, {"n": last}])
    assert [(i.code, i.row) for i in report.issues] == [("type-mismatch", 3)]


def test_nonfinite_string_is_not_numeric_inference_noise_in_text_field():
    report = check_records([{"n": "Ada"}, {"n": "Grace"}, {"n": "NaN"}])
    assert report.ok and report.profiles[0].dominant_type == "string"


def test_cli_mixed_float_and_integer_csv_passes(tmp_path, capsys):
    path = tmp_path / "mixed.csv"
    path.write_text("n\n1.5\n2.5\n3\n", encoding="utf-8")
    assert main([str(path)]) == 0
    assert "no issues found" in capsys.readouterr().out
