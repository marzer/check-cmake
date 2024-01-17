#!/usr/bin/env python3
# This file is a part of marzer/check_cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check_cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import argparse
import multiprocessing
import re
import shutil
import signal
import subprocess
import sys
from io import StringIO
from pathlib import Path

import colorama

from . import checks, paths, utils
from .colour import *
from .version import *


def error(text):
    print(rf"{bright(rf'error:', 'red')} {text}", file=sys.stderr)


STOP = None


def sigint_handler(signal, frame):
    global STOP
    if STOP is not None:
        STOP.set()


def make_boolean_optional_arg(args: argparse.ArgumentParser, name: str, default, help='', **kwargs):
    if sys.version_info.minor >= 9:
        args.add_argument(rf'--{name}', default=default, help=help, action=argparse.BooleanOptionalAction, **kwargs)
    else:
        args.add_argument(rf'--{name}', action=r'store_true', help=help, **kwargs)
        args.add_argument(
            rf'--no-{name}',
            action=r'store_false',
            help=(help if help == argparse.SUPPRESS else None),
            dest=name,
            **kwargs,
        )
        args.set_defaults(**{name: default})


def main_impl():
    args = argparse.ArgumentParser(
        description=r'CMake checker for C and C++ projects.',
        epilog=rf'v{VERSION_STRING} - github.com/marzer/check_cmake',
    )
    args.add_argument(r'-v', r'--verbose', action=r'store_true', help=r"enable verbose output")
    args.add_argument(
        r"root", type=Path, nargs=r'?', default=Path('.'), help="path to the project root (default: %(default)s)"
    )
    args.add_argument(r'--version', action=r'store_true', help=r"print the version and exit", dest=r'print_version')
    make_boolean_optional_arg(args, r"recurse", default=True, help=rf"recurse into subfolders (default: %(default)s)")
    args.add_argument(r"--limit", type=int, default=0, help="maximum errors to emit (default: %(default)s)")
    args.add_argument(r'--where', action=r'store_true', help=argparse.SUPPRESS)
    args = args.parse_args()

    if args.print_version:
        print(VERSION_STRING)
        return

    if args.where:
        print(paths.PACKAGE)
        return

    print(rf'{bright("check_cmake", colour="cyan")} v{VERSION_STRING} - github.com/marzer/check_cmake')

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
    global STOP
    STOP = multiprocessing.Event()

    def print_ex(*args):
        nonlocal prev_print_was_issue
        prev_print_was_issue = False
        print(*args)

    def check_directory(dir: Path):
        global STOP
        nonlocal args
        nonlocal root_is_git_repo
        nonlocal issue_count
        nonlocal file_count
        nonlocal prev_print_was_issue
        for item in dir.iterdir():
            if STOP.is_set():
                break
            item = item.resolve()
            item_relative = item.relative_to(root_absolute)

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

            # read all text
            file_count += 1
            text = utils.read_all_text_from_file(item).replace('\r\n', '\n').replace('\r', '\n')

            # check for 'ignore this line' pragrams
            ignored_lines = 0
            lines = text.split('\n')
            for i, line in zip(range(len(lines)), lines):
                if re.fullmatch(
                    r'^[^#]*?#\s*(?:(?:cmake[ _-]+(?:lint|check)|(?:lint|check)[ _-]+cmake)[:\s]+(?:disable|ignore)|no(?:lint|check))\s*$',
                    line,
                    flags=re.I,
                ):
                    ignored_lines |= 1 << (i + 1)

            # check files
            text = utils.strip_cmake_comments(text)
            issues_in_file = []
            issues_in_file: list[checks.Issue]
            for check in checks.CHECKS:
                issues = check(item, text)
                if issues is None:
                    continue
                issues = list(utils.coerce_collection(issues))
                if not issues:
                    continue
                if ignored_lines:
                    issues = [i for i in issues if (i.span.line_mask(text) & ignored_lines) == 0]
                issues_in_file += issues

            # sort issues by start location and print
            issues_in_file.sort(key=lambda i: i.span.start)
            for issue in issues_in_file:
                if not prev_print_was_issue:
                    print('')
                print(f"{bright(rf'error:', 'red')} {issue}\n")
                prev_print_was_issue = True
                issue_count += 1
                if args.limit > 0 and issue_count >= args.limit > 0:
                    print_ex(f"reached error limit, stopping.")
                    return
            if not issues_in_file and args.verbose:
                print_ex(rf'[OK] {item_relative}')

    check_directory(args.root)

    print_ex(
        rf'found {issue_count} error{"" if issue_count == 1 else "s"} in {file_count} file{"" if file_count == 1 else "s"}.'
    )
    return issue_count


def main():
    signal.signal(signal.SIGINT, sigint_handler)
    colorama.init()
    result = None
    try:
        result = main_impl()
        if result is None:
            sys.exit(0)
        elif isinstance(result, int):
            sys.exit(result)
        elif isinstance(result, str):  # error message
            error(result)
            sys.exit(-1)
        else:
            error('unexpected result type')
            sys.exit(-1)
    except SystemExit as exit:
        raise exit from None
    except argparse.ArgumentError as err:
        error(err)
        sys.exit(-1)
    except BaseException as err:
        with StringIO() as buf:
            buf.write(
                f'\n{dim("*************", "red")}\n\n'
                'You appear to have triggered an internal bug!'
                f'\n{style("Please file an issue at github.com/marzer/check_cmake/issues")}'
                '\nMany thanks!'
                f'\n\n{dim("*************", "red")}\n\n'
            )
            utils.print_exception(err, include_type=True, include_traceback=True, skip_frames=1, logger=buf)
            buf.write(f'{dim("*************", "red")}\n')
            print(buf.getvalue(), file=sys.stderr)
        sys.exit(-1)


if __name__ == '__main__':
    main()
