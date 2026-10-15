#!/usr/bin/env python3
# This file is a part of marzer/check-cmake and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check-cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

BAD = 'add_library(foo)\nadd_library(bar)\n'

GOOD = 'add_library(foo STATIC)\n'


def write(path: Path, text: str = BAD):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def reported(result: subprocess.CompletedProcess, root: Path) -> list[tuple[str, int]]:
    return [
        (Path(path).relative_to(root.resolve()).as_posix(), int(line))
        for path, line in re.findall(r'^error: (.+?):(\d+):\d+: ', result.stdout, flags=re.M)
    ]


def test_clean_project_exits_zero(run_cli):
    result = run_cli(REPO / 'tests' / 'valid' / 'version')
    assert result.returncode == 0
    assert 'found 0 errors in 1 file.' in result.stdout


def test_project_with_issues_exits_one(run_cli):
    result = run_cli(REPO / 'tests' / 'error' / 'threads')
    assert result.returncode == 1
    assert 'found 2 errors in 1 file.' in result.stdout


def test_missing_root_exits_minus_one(run_cli, tmp_path):
    result = run_cli(tmp_path / 'missing')
    assert result.returncode in (255, 0xFFFFFFFF)
    assert 'did not exist or was not a directory' in result.stderr


def test_bad_arguments_exit_two(run_cli):
    assert run_cli('--limit', 'lots').returncode == 2


def test_version_matches_version_file(run_cli):
    result = run_cli('--version')
    assert result.returncode == 0
    assert result.stdout.strip() == (REPO / 'VERSION').read_text(encoding='utf-8').strip()


def test_help_lists_the_recurse_default_once(run_cli):
    result = run_cli('--help')
    assert result.returncode == 0
    assert ' '.join(result.stdout.split()).count('(default: True)') == 1


def test_run_cli_hides_pycharm_so_piped_output_has_no_colour_codes(run_cli, monkeypatch, tmp_path):
    monkeypatch.setenv('PYCHARM_HOSTED', '1')
    write(tmp_path / 'CMakeLists.txt')
    result = run_cli(tmp_path)
    assert '\x1b' not in result.stdout + result.stderr
    assert reported(result, tmp_path) == [('CMakeLists.txt', 1), ('CMakeLists.txt', 2)]


def test_limit_stops_the_whole_walk(run_cli, tmp_path):
    write(tmp_path / 'a' / 'CMakeLists.txt')
    write(tmp_path / 'b' / 'CMakeLists.txt')
    result = run_cli(tmp_path, '--limit', 2)
    assert result.returncode == 1
    assert reported(result, tmp_path) == [('a/CMakeLists.txt', 1), ('a/CMakeLists.txt', 2)]
    assert result.stdout.count('reached error limit') == 1


def test_directories_are_walked_in_sorted_order(run_cli, tmp_path):
    names = [f'd{i:02}' for i in (7, 3, 11, 0, 5, 9, 1, 10, 4, 8, 2, 6)]
    for name in names:
        write(tmp_path / name / 'CMakeLists.txt', GOOD)
    result = run_cli(tmp_path, '--verbose')
    assert result.returncode == 0
    assert re.findall(r'^\[OK\] (\w+)', result.stdout, flags=re.M) == sorted(names)


def test_no_recurse_checks_only_the_root(run_cli, tmp_path):
    write(tmp_path / 'CMakeLists.txt', GOOD)
    write(tmp_path / 'sub' / 'CMakeLists.txt')
    assert run_cli(tmp_path).returncode == 1
    result = run_cli(tmp_path, '--no-recurse')
    assert result.returncode == 0
    assert 'found 0 errors in 1 file.' in result.stdout


def test_only_cmake_scripts_are_checked(run_cli, tmp_path):
    write(tmp_path / 'CMakeLists.txt')
    write(tmp_path / 'cmake' / 'helpers.cmake')
    write(tmp_path / 'docs' / 'notes.txt')
    result = run_cli(tmp_path)
    assert {path for path, _ in reported(result, tmp_path)} == {'CMakeLists.txt', 'cmake/helpers.cmake'}
    assert 'found 4 errors in 2 files.' in result.stdout


@pytest.mark.parametrize(
    'marker,reason',
    [
        ('meson-info/', 'meson build folder'),
        ('meson-logs/', 'meson build folder'),
        ('meson-private/', 'meson build folder'),
        ('CMakeCache.txt', 'CMake build folder'),
        ('build.ninja', 'ninja build folder'),
        ('compile_commands.json', 'build folder'),
        ('.conan.db', 'conan database'),
    ],
)
def test_build_folders_are_skipped(run_cli, tmp_path, marker, reason):
    write(tmp_path / 'out' / 'CMakeLists.txt')
    if marker.endswith('/'):
        (tmp_path / 'out' / marker).mkdir()
    else:
        write(tmp_path / 'out' / marker, '')
    result = run_cli(tmp_path, '--verbose')
    assert result.returncode == 0
    assert f'[--] out skipped ({reason})' in result.stdout


def test_gitignored_files_are_skipped(run_cli, git_repo):
    write(git_repo / '.gitignore', 'ignored/\n')
    write(git_repo / 'ignored' / 'CMakeLists.txt')
    write(git_repo / 'kept' / 'CMakeLists.txt')
    result = run_cli(git_repo, '--verbose')
    assert reported(result, git_repo) == [('kept/CMakeLists.txt', 1), ('kept/CMakeLists.txt', 2)]
    assert f'[--] {Path("ignored", "CMakeLists.txt")} skipped (.gitignore)' in result.stdout


def test_git_submodules_are_skipped(run_cli, git, git_repo, tmp_path_factory):
    upstream = tmp_path_factory.mktemp('upstream')
    write(upstream / 'CMakeLists.txt')
    git('init', '-q', upstream)
    git('-C', upstream, 'config', 'user.name', 'check-cmake tests')
    git('-C', upstream, 'config', 'user.email', 'tests@check-cmake.invalid')
    git('-C', upstream, 'add', '--all')
    git('-C', upstream, 'commit', '-q', '-m', 'upstream')
    git('-C', git_repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', upstream, 'sub')
    write(git_repo / 'kept' / 'CMakeLists.txt')
    assert (git_repo / 'sub' / '.git').is_file()
    result = run_cli(git_repo, '--verbose')
    assert reported(result, git_repo) == [('kept/CMakeLists.txt', 1), ('kept/CMakeLists.txt', 2)]
    assert '[--] sub skipped (git submodule)' in result.stdout
