#!/usr/bin/env python3
# This file is a part of marzer/check-cmake and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check-cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import argparse
import shutil
import signal
import subprocess
import sys
import threading
from io import StringIO
from pathlib import Path
from typing import Union

import colorama

from . import checks, paths, utils
from .colour import *
from .version import *


def error(text):
    print(rf"{bright(rf'error:', 'red')} {text}", file=sys.stderr)


STOP = threading.Event()


def sigint_handler(signal, frame):
    STOP.set()


def make_boolean_optional_arg(parser: argparse.ArgumentParser, name: str, default, help='', **kwargs):
    name = name.strip().lstrip('-')
    action = parser.add_argument(rf'--{name}', default=default, action=argparse.BooleanOptionalAction, **kwargs)
    action.help = help


def main_impl() -> Union[int, str, None]:
    parser = argparse.ArgumentParser(
        description=r'CMake checker for C and C++ projects.',
        epilog=rf'v{VERSION_STRING} - github.com/marzer/check-cmake',
    )
    parser.add_argument(r'-v', r'--verbose', action=r'store_true', help=r"enable verbose output")
    parser.add_argument(
        r"root", type=Path, nargs=r'?', default=Path('.'), help="path to the project root (default: %(default)s)"
    )
    parser.add_argument(r'--version', action=r'store_true', help=r"print the version and exit", dest=r'print_version')
    make_boolean_optional_arg(parser, r"recurse", default=True, help=rf"recurse into subfolders (default: %(default)s)")
    parser.add_argument(r"--limit", type=int, default=0, help="maximum errors to emit (default: %(default)s)")
    parser.add_argument(r'--where', action=r'store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.print_version:
        print(VERSION_STRING)
        return

    if args.where:
        print(paths.PACKAGE)
        return

    print(rf'{bright("check_cmake", colour="cyan")} v{VERSION_STRING} - github.com/marzer/check-cmake')

    if not args.root.is_dir():
        return rf"root '{bright(args.root)}' did not exist or was not a directory"

    root_absolute = args.root.resolve()
    print(f'root: {root_absolute}')

    root_is_git_repo = (args.root / ".git").exists()
    git_ok = False
    if root_is_git_repo:
        if args.verbose:
            print('detected git repository')
        git_ok = shutil.which('git') is not None
        if not git_ok:
            print(rf"{bright(rf'warning:', 'yellow')} could not detect git; .gitignore rules will not be respected")
        elif args.verbose:
            print('detected git')

    issue_count = 0
    file_count = 0
    prev_print_was_issue = False

    def print_ex(*args):
        nonlocal prev_print_was_issue
        prev_print_was_issue = False
        print(*args)

    def limit_reached() -> bool:
        return 0 < args.limit <= issue_count

    def check_directory(dir: Path):
        nonlocal issue_count
        nonlocal file_count
        nonlocal prev_print_was_issue
        for item in sorted(dir.iterdir()):
            if STOP.is_set() or limit_reached():
                return
            item = item.resolve()

            try:
                item_relative = item.relative_to(root_absolute)  # breaks venv usage
            except ValueError:
                item_relative = item

            # check permissions
            try:
                item.stat()
            except PermissionError:
                if args.verbose:
                    print_ex(rf'[--] {item_relative} skipped (insufficient permissions)')
                continue

            # subdirectories
            if item.is_dir():
                if not args.recurse:
                    continue
                try:
                    # skip git submodules
                    if root_is_git_repo and (item / ".git").exists():
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (git submodule)')
                        continue
                    # skip meson build folders
                    if (
                        (item / 'meson-info').is_dir()
                        or (item / 'meson-logs').is_dir()
                        or (item / 'meson-private').is_dir()
                    ):
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (meson build folder)')
                        continue
                    # skip cmake build folders
                    if (item / 'CMakeCache.txt').is_file():
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (CMake build folder)')
                        continue
                    # skip ninja build folders
                    if (item / 'build.ninja').is_file():
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (ninja build folder)')
                        continue
                    # skip misc build folders
                    if (item / 'compile_commands.json').is_file():
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (build folder)')
                        continue
                    # skip conan database folders
                    if (item / '.conan.db').is_file():
                        if args.verbose:
                            print_ex(rf'[--] {item_relative} skipped (conan database)')
                        continue
                except PermissionError:
                    if args.verbose:
                        print_ex(rf'[--] {item_relative} skipped (insufficient permissions)')
                    continue
                check_directory(item)
                continue

            # non-files
            if not item.is_file():
                continue

            # everything else is a file; skip non-CMake files
            if not (item.name.lower() == 'cmakelists.txt' or item.suffix.lower() == '.cmake'):
                continue

            # skip .gitignored files
            if root_is_git_repo and git_ok:
                if (
                    subprocess.run(
                        ['git', 'check-ignore', '--quiet', str(item)],
                        capture_output=True,
                        encoding='utf-8',
                        cwd=str(dir),
                        check=False,
                    ).returncode
                    == 0
                ):
                    if args.verbose:
                        print_ex(rf'[--] {item_relative} skipped (.gitignore)')
                    continue

            file_count += 1
            issues = checks.check_text(item, utils.read_all_text_from_file(item))
            for issue in issues:
                if not prev_print_was_issue:
                    print('')
                print(f"{bright(rf'error:', 'red')} {issue}\n")
                prev_print_was_issue = True
                issue_count += 1
                if limit_reached():
                    print_ex(f"reached error limit, stopping.")
                    return
            if not issues and args.verbose:
                print_ex(rf'[OK] {item_relative}')

    check_directory(args.root)

    print_ex(
        rf'found {issue_count} error{"" if issue_count == 1 else "s"} in {file_count} file{"" if file_count == 1 else "s"}.'
    )
    return 1 if issue_count else 0


def main_internal() -> int:
    signal.signal(signal.SIGINT, sigint_handler)
    colorama.init()
    result = None
    try:
        result = main_impl()
        if result is None:
            return 0
        elif isinstance(result, int):
            return result
        elif isinstance(result, str):  # error message
            error(result)
            return -1
        else:
            error('unexpected result type')
            return -1
    except SystemExit as exit:
        raise exit from None
    except argparse.ArgumentError as err:
        error(err)
        return -1
    except BaseException as err:
        with StringIO() as buf:
            buf.write(
                f'\n{dim("*************", "red")}\n\n'
                'You appear to have triggered an internal bug!'
                f'\n{style("Please file an issue at github.com/marzer/check-cmake/issues")}'
                '\nMany thanks!'
                f'\n\n{dim("*************", "red")}\n\n'
            )
            utils.print_exception(err, include_type=True, include_traceback=True, skip_frames=1, logger=buf)
            buf.write(f'{dim("*************", "red")}\n')
            print(buf.getvalue(), file=sys.stderr)
        return -1


def main():
    result = main_internal()
    sys.exit(result)


if __name__ == '__main__':
    main()
