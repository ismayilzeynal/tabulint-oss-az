import pytest

from tabulint.cli import EXIT_ERROR, main


@pytest.mark.parametrize("suffix,content", [
    (".csv", "name\nAda\n"),
    (".json", '[{"name":"Ada"}]'),
    (".jsonl", '{"name":"Ada"}\n'),
    (".ndjson", '{"name":"Ada"}\n'),
])
@pytest.mark.parametrize("failure", ["non-text", "missing-bom", "nul-encoding", "nul-path"])
def test_invalid_reader_input_exits_two_without_overwriting_report(
    tmp_path, capsys, suffix, content, failure
):
    path = tmp_path / ("people" + suffix)
    path.write_bytes(content.encode("utf-16-le" if failure == "missing-bom" else "utf-8"))
    input_path = str(path)
    options = []
    if failure == "non-text":
        options = ["--encoding", "hex"]
    elif failure == "missing-bom":
        options = ["--encoding", "utf-16"]
    elif failure == "nul-encoding":
        options = ["--encoding", "utf-8\0"]
    else:
        input_path = str(tmp_path / ("invalid\0" + suffix))
    output = tmp_path / "report.txt"
    output.write_text("existing report", encoding="utf-8")

    assert main([
        input_path, *options, "--quiet", "--fail-on", "never", "--output", str(output),
    ]) == EXIT_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "tabulint: error:" in captured.err
    assert "Traceback" not in captured.err
    assert output.read_text(encoding="utf-8") == "existing report"
