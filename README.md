# check-cmake

A simple linter for CMake.

## Installation

`check-cmake` requires Python 3.8 or higher.

```
pip3 install check-cmake
```

## Usage

`check-cmake` is a command-line application

```
usage: check-cmake [-h] [-v] [--version] [--recurse | --no-recurse] [--limit LIMIT] [root]

CMake checker for C and C++ projects.

positional arguments:
  root                  path to the project root (default: .)

options:
  -h, --help            show this help message and exit
  -v, --verbose         enable verbose output
  --version             print the version and exit
  --recurse, --no-recurse
                        recurse into subfolders (default: True)
  --limit LIMIT         maximum errors to emit (default: 0)

v0.3.0 - github.com/marzer/check_cmake
```

## Exit codes

| Value                                | Meaning                        |
| :----------------------------------- | :----------------------------- |
| 0                                    | No issues were found           |
| `N`, where `N` is a positive integer | `N` issues were found in total |
| -1                                   | A fatal error occurred         |

## Example output

```
error: /my_lib/CMakeLists.txt:29:9: language standard level should be set on a per-target basis using target_compile_features()
  Context:
    29 | set_target_properties(
    30 |     my_lib
    31 |     PROPERTIES
    32 |         CXX_STANDARD 14
    33 |         CXX_STANDARD_REQUIRED ON
    34 |         CXX_EXTENSIONS OFF
    35 | )
  Replace with:
    target_compile_features(): https://cmake.org/cmake/help/latest/command/target_compile_features.html
  More information:
    CMAKE_CXX_KNOWN_FEATURES: https://cmake.org/cmake/help/latest/prop_gbl/CMAKE_CXX_KNOWN_FEATURES.html
    CMAKE_C_KNOWN_FEATURES: https://cmake.org/cmake/help/latest/prop_gbl/CMAKE_C_KNOWN_FEATURES.html

found 1 error in 1 file.
```

## Suppressing checks

Checks can be suppressed using comment-based 'pragmas' at the end of the source line:

```cmake
set_target_properties(
    my_lib
    PROPERTIES
        CXX_STANDARD 14 # nocheck
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
)
```

For compatibility with other tools, any the following will also work:

```cmake
# nolint

# check-cmake ignore
# lint-cmake ignore
# cmake-check ignore
# cmake-lint ignore

# check-cmake disable
# lint-cmake disable
# cmake-check disable
# cmake-lint disable

# check-cmake: ignore
# lint-cmake: ignore
# cmake-check: ignore
# cmake-lint: ignore

# check-cmake: disable
# lint-cmake: disable
# cmake-check: disable
# cmake-lint: disable
```
