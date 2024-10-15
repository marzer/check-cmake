import argparse
import os
import sys

# Quick instruction to run this tester script:
# virtualenv test_env
# source test_env/bin/activate
#
# dependencies through check-cmake: ['misk >= 0.8.1', 'colorama']
# In order to use it: pip install misk>=0.8.1 colorama
# The code generator tool and library versions need to match.
from src.check_cmake.main import main_internal

def run_test(full_test_dir, expect_error):
    sys.argv = ['']

    result = main_internal()
    if result != 0:
        print(f"Found an expected error in {full_test_dir}: {result}")

    if expect_error == True and result == 0:
        print(f"Expected an error in {full_test_dir}, but got none.")
        sys.exit(-1)

    if expect_error == False and result != 0:
        print(f"Expected no error in {full_test_dir}, but got one.")
        sys.exit(-1)

def run_suite(testdir_root, expect_error):
    original_dir = os.getcwd()

    for test in os.listdir(testdir_root):
        full_test_dir = os.path.join(testdir_root, test)
        print(f"Found a test {full_test_dir}")
        if os.path.isdir(full_test_dir):
            # check-cmake misbehaves without this switch of current dir and back as it has been designed for one-shot use
            os.chdir(full_test_dir)
            run_test(full_test_dir, expect_error)
            os.chdir(original_dir)

def main():
    parser = argparse.ArgumentParser(
        description="Starts integration test of check-cmake with a test files."
    )

    parser.add_argument(
        "--testdir",
        type=str,
        required=True,
        help="Path to tests, each subdirectory is a full test suite to check against.",
    )

    args = parser.parse_args()
    testdir_root = args.testdir
    run_suite(os.path.join(testdir_root, "error"), True)
    run_suite(os.path.join(testdir_root, "valid"), False)

    return 0

if __name__ == "__main__":
    main()
