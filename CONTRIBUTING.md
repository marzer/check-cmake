# Contributing to check-cmake

Firstly: thanks! Any help is greatly appreciated.

For most situations the easiest way for you to contribute is to simply let me know what's going on,
by reporting a bug or requesting a feature in [Issues].

If you'd like to contribute more directly via a pull request, see below.

- [Pull Requests](#pull-requests)
	- [Getting started](#getting-started)
	- [Running the tests](#running-the-tests)
	- [Code style](#code-style)
	- [Versioning and releases](#versioning-and-releases)

## Pull Requests

### Getting started

A prerequisite of working on check-cmake with the intention of making a pull request is to have it installed
as 'editable' from a clone of the repository, with the pre-commit hooks enabled:

```sh
git clone <your check-cmake fork>
cd check-cmake
pip install -e '.[dev]'
pre-commit install
```

The `[dev]` extra pulls in pytest, ruff, pyright and pre-commit (matching the versions CI uses).

### Running the tests

```sh
pytest
```

There are three test modules:

-   [tests/test_units.py] covers the helpers, the suppression pragmas and each check against minimal CMake snippets.
-   [tests/test_fixtures.py] runs the checks over every project in `tests/error` and `tests/valid`, and compares
    the issues found against an exact list for each.
-   [tests/test_cli.py] runs check-cmake in a subprocess over generated project trees. It covers the exit codes,
    the command-line options and the rules for skipping folders and files.

CMake is never run. The .gitignore and submodule tests need git, and are skipped if it is not on your PATH.

A new check needs a fixture in both directories. The fixture tests fail if a check has no error fixture.

Some fixtures deliberately have no final newline, so the whitespace hooks and .editorconfig leave both
directories alone.

### Code style

It's Python. I'm primarily a C++ programmer. I really don't care that much.
The codebase is linted and formatted with [ruff] and type-checked with [pyright] (config in `pyproject.toml`).
The pre-commit hooks run ruff on each commit, and CI enforces both. To run them by hand:

```sh
pre-commit run --all-files
pyright
```

I'm not too fussy though. I'm unlikely to reject a PR on the basis of style unless you do something truly horrendous.

### Versioning and releases

The version is stored in one place: the `VERSION` file at the repo root, a bare `major.minor.patch` triplet.
setuptools reads it at build time, and at runtime check-cmake reads it back from the same file. A wheel install
has no such file, so there it falls back to the installed package metadata.

Releases are automated and maintainer-only. Bumping `VERSION` on `main` cuts a release: CI tags `v<version>`,
and that tag triggers the publish workflow that uploads to PyPI.

The practical upshot for a PR: **don't touch `VERSION`**, and put any changelog entries under the `Unreleased`
heading in `CHANGELOG.md`. I bump the version myself when cutting a release, so a PR that also bumps it just
invites a merge conflict or an accidental publish.

<br /><br />

[issues]: https://github.com/marzer/check-cmake/issues
[ruff]: https://docs.astral.sh/ruff/
[pyright]: https://microsoft.github.io/pyright/
[tests/test_units.py]: tests/test_units.py
[tests/test_fixtures.py]: tests/test_fixtures.py
[tests/test_cli.py]: tests/test_cli.py
