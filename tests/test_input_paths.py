import os
from pathlib import Path

import pytest

from tabulint import TabulintError, load_csv, load_dataset
from tabulint.cli import main


@pytest.mark.parametrize("suffix", ["csv", "json", "jsonl", "ndjson"])
def test_directory_is_rejected_by_reader_and_cli(tmp_path, capsys, suffix):
    path = tmp_path / ("directory." + suffix)
    path.mkdir()
    with pytest.raises(TabulintError, match="directory.*not a regular file"):
        load_dataset(path)
    assert main([str(path)]) == 2
    assert "directory" in capsys.readouterr().err


def _symlink(link, target):
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


def test_relative_symlink_to_regular_file_preserves_supplied_path(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.csv"
    source.write_text("name\nAda\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    _symlink(link, "source.csv")
    monkeypatch.chdir(tmp_path)
    assert load_dataset("link.csv") == [{"name": "Ada"}]
    assert main(["link.csv"]) == 0
    output = capsys.readouterr().out
    assert "tabulint: link.csv" in output
    assert str(tmp_path) not in output


def test_symlink_loop_returns_error_without_resolving_path(tmp_path, monkeypatch, capsys):
    _symlink(tmp_path / "loop.csv", "loop.csv")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(TabulintError, match="loop.csv"):
        load_dataset("loop.csv")
    assert main(["loop.csv"]) == 2
    error = capsys.readouterr().err
    assert "loop.csv" in error and str(tmp_path) not in error
    assert "Traceback" not in error


def test_unreadable_regular_file(tmp_path, capsys):
    if os.name == "nt":
        pytest.skip("chmod does not remove Windows read permission")
    path = tmp_path / "private.csv"
    path.write_text("name\nAda\n", encoding="utf-8")
    path.chmod(0)
    try:
        if os.access(path, os.R_OK):
            pytest.skip("current user can still read permission-restricted files")
        with pytest.raises(TabulintError, match="could not read file"):
            load_dataset(path)
        assert main([str(path)]) == 2
        assert "Traceback" not in capsys.readouterr().err
    finally:
        path.chmod(0o600)


def test_device_is_rejected_before_reading(capsys):
    path = Path("NUL.csv") if os.name == "nt" else Path("/dev/null")
    with pytest.raises(TabulintError, match="device or special file"):
        load_csv(path)
    if os.name == "nt":
        assert main([str(path)]) == 2
        assert "device or special file" in capsys.readouterr().err


def test_fifo_is_rejected_without_blocking(tmp_path, capsys):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFOs unavailable")
    path = tmp_path / "pipe.csv"
    os.mkfifo(path)
    with pytest.raises(TabulintError, match="device or special file"):
        load_dataset(path)
    assert main([str(path)]) == 2
    assert "device or special file" in capsys.readouterr().err
