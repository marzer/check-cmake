# Changelog

## v0.6.0 - 2026-10-15

- fixed `--limit` stopping only the current directory, so later directories still reported issues
- fixed output order varying with the file system's directory order
- fixed the `Threads::Threads` example printing a literal `\n`
- fixed the `ExternalProject_Add()` example printing `${{CMAKE_CXX_COMPILER}}`
- fixed context snippets not highlighting an issue at the very end of the snippet
- fixed `--help` showing the `--recurse` default twice on older Python versions
- raised the minimum Python version to 3.9

## v0.5.3 - 2025-08-07

- Fixed `# nocheck` not working in some rare circumstances

## v0.5.2 - 2025-01-04

- Fixed internal `Path.relative_to()` error when used inside a virtual environment

## v0.5.1 - 2024-10-15

- Fixed false positive for incorrect use of `SYSTEM` in `target_include_directories()` in some cases

## v0.5.0 - 2024-03-25

- Added check for `add_library()` with implicit type (`STATIC`, `SHARED`, et cetera)

## v0.4.0 - 2024-01-17

- Fixed line numbers sometimes being wrong in context snippets
- Added check for incorrectly-placed `SYSTEM` in `target_include_directories()`
- Added check for extraneous space in `ExternalProject_Add()` `CMAKE_ARGS`

## v0.3.0 - 2024-01-13

- Fixed `#nocheck`

## v0.2.0 - 2024-01-11

- Added pragmas for ignoring checks on a line
- Added check for `cmake_minimum_required()` when `project()` is present
- Fixed minor formatting issues

## v0.1.0 - 2024-01-10

- First public release 🎉
