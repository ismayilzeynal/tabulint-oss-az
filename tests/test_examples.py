"""Keep the checked-in example datasets usable and predictable."""

from pathlib import Path

import pytest

from tabulint import check_file, load_dataset
from tabulint.cli import EXIT_ISSUES, EXIT_OK, main


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
EXPECTED_CODES = {
    "clean.csv": set(),
    "missing.csv": {"missing-value"},
    "duplicates.csv": {"duplicate-record"},
    "mixed_types.csv": {"type-mismatch"},
    "clean.json": set(),
    "clean.jsonl": set(),
    "clean.ndjson": set(),
}


@pytest.fixture(params=sorted(EXPECTED_CODES))
def example_path(request):
    return EXAMPLES / request.param


def test_every_example_is_covered():
    datasets = {
        path.name
        for path in EXAMPLES.iterdir()
        if path.suffix in {".csv", ".json", ".jsonl", ".ndjson"}
    }
    assert datasets == set(EXPECTED_CODES)


def test_every_example_loads(example_path):
    assert load_dataset(example_path)


def test_example_has_expected_issues(example_path):
    report = check_file(example_path)
    assert {issue.code for issue in report.issues} == EXPECTED_CODES[example_path.name]


def test_example_cli_exit_code(example_path, capsys):
    expected = EXIT_ISSUES if EXPECTED_CODES[example_path.name] else EXIT_OK
    assert main([str(example_path)]) == expected
    capsys.readouterr()
