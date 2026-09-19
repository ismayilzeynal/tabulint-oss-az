# Releasing tabulint

Releases are cut manually by a maintainer with write access to this repository.
There is no release workflow in GitHub Actions. The current publish destination
is a GitHub Release with source and wheel artifacts. The [`tabulint` name on
PyPI](https://pypi.org/project/tabulint/) belongs to an unrelated project, so
**do not upload these artifacts to
PyPI under that name**. A future PyPI release requires a distinct distribution
name and an updated publication process.

Start from a clean `main` branch after all intended pull requests have been
merged. Confirm `origin` is this repository, not a fork:

```bash
git switch main
git pull --ff-only origin main
git status --short
git remote -v
gh auth status
python -m pip install -e ".[dev]"
python -m pytest
```

Before choosing a version, check that the previous version's tag and GitHub
Release actually exist. For the current `v0.1.0` changelog reference, run
`git ls-remote --tags origin v0.1.0` and `gh release view v0.1.0`. If either is
missing, resolve the historical tag or release with the maintainer before
relying on its compare link. Do not move an existing tag.

## Version policy

Use Semantic Versioning with a `v` prefix on Git tags, for example `v0.2.0`.
The version stored in the package and release heading omits the `v`. During
the pre-1.0 period, a breaking change to the CLI or Python API bumps the minor
version (`0.1.0` to `0.2.0`); a compatible new feature also bumps the minor
version, and a compatible bug fix bumps the patch version (`0.1.0` to
`0.1.1`). This is the project's pre-1.0 convention; users should not assume
the API is stable until `1.0.0`.

The version appears in two package files and in release metadata. Update all
of these together:

- `pyproject.toml`: `[project] version` (package metadata).
- `src/tabulint/__init__.py`: `__version__` (used by `tabulint --version`).
- `CHANGELOG.md`: the dated release heading, its link reference, and the
  `[Unreleased]` comparison link pointing from the new tag to `HEAD`.
- The Git tag and GitHub Release name: `v` followed by the same version.

## Release steps

Use `0.2.0` below only as an example; substitute the version you chose.

1. **Update the changelog.** Move the relevant bullets from `## [Unreleased]`
   into a new `## [0.2.0] - YYYY-MM-DD` section, using the release date.
   Leave an empty `## [Unreleased]` section above it. Add
   `[0.2.0]: https://github.com/ismayilzeynal/tabulint-oss-az/releases/tag/v0.2.0`
   to the link references, and change the `[Unreleased]` comparison URL to
   `https://github.com/ismayilzeynal/tabulint-oss-az/compare/v0.2.0...HEAD`.
   Keep earlier release sections and links intact.
2. **Bump the version.** Set both `pyproject.toml` and
   `src/tabulint/__init__.py` to `0.2.0`. Refresh the editable installation,
   run the tests, and check the CLI version:

   ```bash
   python -m pip install -e ".[dev]"
   python -m pytest
   tabulint --version
   ```

   The CLI must report the new version. Check the changelog links and review
   the diff.
3. **Commit the release changes.** Stage the three edited files and commit:

   ```bash
   git add CHANGELOG.md pyproject.toml src/tabulint/__init__.py
   git commit -m "Release 0.2.0"
   git push origin main
   ```

4. **Tag that commit.** Create an annotated tag from the release commit:

   ```bash
   git tag -a v0.2.0 -m "Release 0.2.0"
   git show --no-patch v0.2.0
   ```

5. **Push the tag.** `git push origin v0.2.0`. Confirm that it points to the
   release commit on `main`.
6. **Build and check artifacts.** In a clean working tree, install the manual
   release tools and build the source distribution and wheel:

   ```bash
   python -m pip install --upgrade build twine
   python -m build
   python -m twine check dist/*
   ```

   Inspect the generated filenames and confirm they contain the intended
   version. If `dist/` already contains artifacts from another build, clear
   that directory before building so only this release is published.
7. **Publish.** Create a GitHub Release from the pushed tag and attach the two
   checked artifacts:

   ```bash
   gh release create v0.2.0 dist/* --verify-tag --title "v0.2.0" --notes "See [CHANGELOG.md](https://github.com/ismayilzeynal/tabulint-oss-az/blob/v0.2.0/CHANGELOG.md) for the changes in this release."
   ```

   Verify the GitHub Release page opens, both artifacts are attached, and the
   `[Unreleased]` comparison link starts at the new tag. This release is
   available through GitHub, not through `pip install tabulint` from PyPI.
