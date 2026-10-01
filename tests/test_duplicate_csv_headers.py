import pytest

from tabulint import TabulintError, load_csv
from tabulint.cli import main


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
@pytest.mark.parametrize("with_records", [False, True], ids=["header-only", "with-records"])
def test_duplicate_csv_headers_rejected_by_loader_and_cli(tmp_path, capsys, delimiter, with_records):
    path = tmp_path / "duplicate.csv"
    content = delimiter.join(["id", "id"]) + "\n"
    if with_records:
        content += delimiter.join(["first", "second"]) + "\n"
    original = content.encode("utf-8")
    path.write_bytes(original)
    with pytest.raises(TabulintError) as error:
        load_csv(path, delimiter=delimiter)
    assert str(path) in str(error.value)
    assert "duplicate column name 'id'" in str(error.value)
    report = tmp_path / "report.txt"
    report.write_text("previous report", encoding="utf-8")
    cli_delimiter = r"\t" if delimiter == "\t" else delimiter
    assert main([str(path), "--delimiter", cli_delimiter, "--output", str(report),
                 "--fail-on", "never"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "duplicate column name 'id'" in captured.err
    assert "Traceback" not in captured.err
    assert path.read_bytes() == original
    assert report.read_text(encoding="utf-8") == "previous report"


@pytest.mark.parametrize("second", ["ID", " id", "id "])
def test_distinct_csv_header_names_remain_exact(tmp_path, second):
    path = tmp_path / "valid.csv"
    path.write_text(f"id,{second}\nfirst,second\n", encoding="utf-8")
    assert load_csv(path) == [{"id": "first", second: "second"}]


def test_duplicate_quoted_header_matches_decoded_name(tmp_path):
    path = tmp_path / "quoted.csv"
    path.write_text('"first,name","first,name"\na,b\n', encoding="utf-8")
    with pytest.raises(TabulintError, match="duplicate column name 'first,name'"):
        load_csv(path)


def test_valid_custom_delimiter_preserves_all_values(tmp_path, capsys):
    path = tmp_path / "valid.csv"
    path.write_text("id;value\nfirst;second\n", encoding="utf-8")
    assert load_csv(path, delimiter=";") == [{"id": "first", "value": "second"}]
    assert main([str(path), "--delimiter", ";"]) == 0
    assert "no issues found" in capsys.readouterr().out
