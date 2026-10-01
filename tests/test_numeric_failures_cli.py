import json
import sys

import pytest

from tabulint.cli import EXIT_ERROR, EXIT_ISSUES, EXIT_OK, main


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e400"])
def test_non_finite_csv_values_fail_numeric_validation(write, capsys, value):
    path = write("numbers.csv", f"n\n{value}\n")

    assert main([path, "--min", "n=0", "--format", "json"]) == EXIT_ISSUES

    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert [issue["code"] for issue in document["issues"]] == ["not-numeric"]


@pytest.mark.parametrize("suffix", [".csv", ".json"])
@pytest.mark.parametrize("bound", [2**53 + 1, 10**400])
def test_large_integer_limit_violations_are_reported_without_rounding(write, capsys, suffix, bound):
    value = bound + 1
    content = f"n\n{value}\n" if suffix == ".csv" else json.dumps([{"n": value}])
    path = write("numbers" + suffix, content)

    assert main([path, "--max", f"n={bound}", "--format", "json"]) == EXIT_ISSUES

    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert [issue["code"] for issue in document["issues"]] == ["above-maximum"]
    assert document["issues"][0]["message"] == (
        f"field 'n' value {value} is above maximum {bound}"
    )


def test_large_integer_equal_to_limit_passes(write, capsys):
    value = 2**53 + 1
    path = write("numbers.json", json.dumps([{"n": value}]))

    assert main([path, "--max", f"n={value}", "--format", "json"]) == EXIT_OK

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["issues"] == []


def test_inverted_large_integer_bounds_exit_two(write, capsys):
    path = write("numbers.csv", "n\n1\n")

    assert main([path, "--min", f"n={2**53 + 1}", "--max", f"n={2**53}"]) == EXIT_ERROR

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "greater than maximum" in captured.err


def test_zero_padded_integer_above_limit_is_not_rounded(write, capsys):
    padded = "0" * (sys.get_int_max_str_digits() + 4300) + "9007199254740993"
    path = write("numbers.csv", f"n\n{padded}\n")

    assert main([path, "--max", "n=9007199254740992", "--format", "json"]) == EXIT_ISSUES

    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert [issue["code"] for issue in document["issues"]] == ["above-maximum"]
