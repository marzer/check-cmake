#!/usr/bin/env python3

# to run this tester script:
# virtualenv test_env
# source test_env/bin/activate
# pip install misk>=0.8.1 colorama

import argparse
import os
import sys
import misk
import subprocess
from pathlib import Path
from src.check_cmake.main import main_internal


def run_test(full_test_dir: Path, expect_error):
    sys.argv = ['']

    result = misk.run_python_script(
        Path(__file__).parent / "src" / "__main__.py",
        '--verbose',
        check=False,
        cwd=str(full_test_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
    )

    if result.returncode != 0 and result.returncode != 1:
        print(f"A fatal error occurred in {full_test_dir}: exit code {result.returncode}\n\n{str(result.stdout)}")
        sys.exit(-1)

    if result.returncode == 0 and expect_error:
        print(f"Expected an error(s) in {full_test_dir}, but got none.\n\n{str(result.stdout)}")
        sys.exit(1)

    if result.returncode == 1 and not expect_error:
        print(f"Expected no error(s) in {full_test_dir}, but got some.\n\n{str(result.stdout)}")
        sys.exit(1)

    print(f"Tests in {full_test_dir} OK")


def run_suite(testdir_root: Path, expect_error):
    original_dir = os.getcwd()

    for test in os.listdir(str(testdir_root)):
        full_test_dir = Path(testdir_root, test).absolute().resolve()
        if full_test_dir.is_dir():
            # check-cmake misbehaves without this switch of current dir and back as it has been designed for one-shot use
            os.chdir(str(full_test_dir))
            run_test(full_test_dir, expect_error)
            os.chdir(str(original_dir))


def main():
    parser = argparse.ArgumentParser(description="Starts integration test of check-cmake with a test files.")

    parser.add_argument(
        "--testdir",
        type=Path,
        default=Path(__file__).parent / "tests",
        help="Path to tests, each subdirectory is a full test suite to check against.",
    )

    args = parser.parse_args()
    testdir_root = args.testdir
    run_suite(testdir_root / "error", True)
    run_suite(testdir_root / "valid", False)

    return 0


if __name__ == "__main__":
    main()
