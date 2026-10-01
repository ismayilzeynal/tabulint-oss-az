"""Regressions for report writing and terminal encoding failures."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tabulint import check_records, format_report
from tabulint.cli import EXIT_ERROR, EXIT_ISSUES, EXIT_OK, main


@pytest.mark.parametrize("content", [r'[{"\ud800": 1}]', r'[{"\udfff": null}]'])
def test_text_report_escapes_unpaired_surrogates(write, tmp_path, capsys, content):
    path = write("surrogate.json", content)
    output = tmp_path / "report.txt"
    output.write_text("previous report", encoding="utf-8")

    expected = EXIT_ISSUES if "null" in content else EXIT_OK
    assert main([path, "--output", str(output)]) == expected
    rendered = output.read_text(encoding="utf-8")
    assert r"\ud" in rendered
    assert capsys.readouterr().out == rendered


def test_text_report_escapes_surrogate_path_and_message():
    report = check_records([{"\ud800": None}], path="input-\udfff.json")
    rendered = format_report(report)
    assert r"input-\udfff.json" in rendered
    assert r"field '\ud800'" in rendered
    rendered.encode("utf-8")


@pytest.mark.parametrize("fail_on", ["warning", "error", "never"])
@pytest.mark.parametrize("invalid_path", ["bad\x00.txt", ""])
def test_invalid_output_path_exits_two(write, capsys, fail_on, invalid_path):
    path = write("clean.csv", "name\nAda\n")
    assert main([path, "--output", invalid_path, "--fail-on", fail_on]) == EXIT_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "could not write output file" in captured.err


@pytest.mark.parametrize("alias", ["same", "relative", "hardlink", "symlink"])
def test_output_cannot_overwrite_input_dataset(write, tmp_path, capsys, monkeypatch, alias):
    path = Path(write("input.csv", "name\nAda\n"))
    original = path.read_bytes()
    output = path
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        output = Path("input.csv")
    elif alias in {"hardlink", "symlink"}:
        output = tmp_path / "alias.txt"
        try:
            if alias == "hardlink":
                output.hardlink_to(path)
            else:
                output.symlink_to(path)
        except OSError as exc:
            pytest.skip(f"{alias} not available: {exc}")

    assert main([str(path), "--output", str(output), "--fail-on", "never"]) == EXIT_ERROR
    assert path.read_bytes() == original
    assert output.read_bytes() == original
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output path refers to the input dataset" in captured.err


def test_text_report_works_with_ascii_stdout_and_keeps_utf8_file(write, tmp_path):
    path = write("unicode.json", json.dumps([{"ad\u0131": 1}]))
    output = tmp_path / "report.txt"
    environment = dict(os.environ, PYTHONIOENCODING="ascii:strict")
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, "-m", "tabulint.cli", path, "--output", str(output)],
        capture_output=True,
        env=environment,
        check=False,
    )
    assert result.returncode == EXIT_OK
    assert result.stderr == b""
    assert b"ad\\u0131" in result.stdout
    assert "ad\u0131" in output.read_text(encoding="utf-8")


def test_output_symlink_loop_error_exits_two(write, tmp_path, monkeypatch, capsys):
    path = write("clean.csv", "name\nAda\n")
    output = tmp_path / "loop.txt"

    def loop_error(self, *args, **kwargs):
        raise RuntimeError("Symlink loop")

    monkeypatch.setattr(Path, "resolve", loop_error)
    assert main([path, "--output", str(output)]) == EXIT_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "could not write output file" in captured.err
    assert not output.exists()


def test_load_error_can_be_printed_to_ascii_stderr(tmp_path, monkeypatch):
    buffer = io.BytesIO()
    error_stream = io.TextIOWrapper(buffer, encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stderr", error_stream)
    path = str(tmp_path / "missing-\u0131.csv")
    assert main([path]) == EXIT_ERROR
    error_stream.flush()
    assert b"missing-\\u0131.csv" in buffer.getvalue()
    assert b"file not found" in buffer.getvalue()
