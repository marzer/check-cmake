#!/usr/bin/env python3
# This file is a part of marzer/check-cmake and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check-cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from check_cmake.checks import check_text

MAIN = Path(__file__).resolve().parents[1] / 'src' / '__main__.py'


@pytest.fixture
def lint():
    def run(text: str, path: Path = Path('CMakeLists.txt')) -> list[tuple[str, int]]:
        return [(issue.generator.name, issue.line_and_column[0]) for issue in check_text(path, text)]

    return run


@pytest.fixture
def run_cli():
    def run(*args) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key != 'PYCHARM_HOSTED'}
        return subprocess.run(
            [sys.executable, str(MAIN), *(str(arg) for arg in args)],
            capture_output=True,
            encoding='utf-8',
            check=False,
            env=env,
        )

    return run


@pytest.fixture
def git(monkeypatch: pytest.MonkeyPatch):
    if shutil.which('git') is None:
        pytest.skip('git not found on PATH')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', os.devnull)
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')

    def run(*args):
        subprocess.run(['git', *(str(arg) for arg in args)], check=True)

    return run


@pytest.fixture
def git_repo(git, tmp_path: Path) -> Path:
    git('init', '-q', tmp_path)
    return tmp_path
