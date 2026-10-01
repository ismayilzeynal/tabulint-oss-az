import io
import os
import sys

import pytest

from tabulint import load_csv
from tabulint.cli import main


def test_crlf_csv_preserves_quoted_data_without_trailing_carriage_returns(tmp_path):
    lf = tmp_path / "lf.csv"
    crlf = tmp_path / "crlf.csv"
    content = 'name,note\nAda,"a,b"\nGrace,"quoted ""word"""\n'
    lf.write_bytes(content.encode("utf-8"))
    crlf.write_bytes(content.replace("\n", "\r\n").encode("utf-8"))
    expected = [{"name": "Ada", "note": "a,b"},
                {"name": "Grace", "note": 'quoted "word"'}]
    assert load_csv(crlf) == load_csv(lf) == expected


@pytest.mark.parametrize("exists", [True, False], ids=["report", "load-error"])
def test_cli_native_paths_and_cp1252_console(tmp_path, monkeypatch, exists):
    directory = tmp_path / "data with spaces"
    directory.mkdir()
    path = directory / "café漢.json"
    if exists:
        path.write_text('[{"café漢": "Ada"}]', encoding="utf-8")
    if os.name == "nt":
        assert "\\" in str(path) and path.drive

    buffer = io.BytesIO()
    console = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout" if exists else "stderr", console)
    try:
        assert main([str(path)]) == (0 if exists else 2)
        console.flush()
        rendered = buffer.getvalue().decode("cp1252")
        assert str(path).encode("cp1252", "backslashreplace").decode("cp1252") in rendered
        assert "café\\u6f22" in rendered
        assert "Traceback" not in rendered
        assert ("no issues found" if exists else "error") in rendered
    finally:
        console.detach()
