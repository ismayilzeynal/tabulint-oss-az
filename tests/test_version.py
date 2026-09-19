"""Keep the CLI/API version aligned with the published package metadata."""

import tomllib
from pathlib import Path

from tabulint import __version__


def test_package_version_matches_project_metadata():
    project = Path(__file__).resolve().parents[1]
    with (project / "pyproject.toml").open("rb") as metadata_file:
        metadata = tomllib.load(metadata_file)

    assert __version__ == metadata["project"]["version"]
