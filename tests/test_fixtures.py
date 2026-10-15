#!/usr/bin/env python3
# This file is a part of marzer/check-cmake and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check-cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from check_cmake import checks

TESTS = Path(__file__).resolve().parent

EXPECTED = {
    'error/externalproject': [('external_project_add_cmake_args', 4)],
    'error/library_type': [('specify_library_type', 1), ('specify_library_type', 3)],
    'error/rpath': [('use_set_target_properties_rpath', 1), ('use_set_target_properties_rpath', 3)],
    'error/target_include_directories': [('target_include_directories_system', 5)],
    'error/target_include_directories_var': [('target_include_directories_system', 5)],
    'error/target_recommended': [
        ('use_target_compile_options', 1),
        ('use_target_compile_features_language_standard', 2),
        ('use_target_compile_definitions', 3),
        ('use_target_include_directories', 4),
        ('use_target_link_libraries', 5),
        ('use_target_compile_options', 7),
        ('use_target_compile_features_language_standard', 8),
        ('use_target_compile_definitions', 9),
        ('use_target_include_directories', 10),
        ('use_target_link_libraries', 11),
        ('use_target_compile_features_language_standard', 13),
        ('use_set_target_properties_pic', 14),
    ],
    'error/target_scope': [('specify_scope_on_target_functions', line) for line in range(1, 8)],
    'error/threads': [('use_threads_package', 1), ('use_threads_package', 3)],
    'error/version': [
        ('specify_minimum_cmake_version', 1),
        ('specify_project_version', 6),
        ('specify_project_version', 10),
        ('specify_project_version', 14),
    ],
    'valid/externalproject': [],
    'valid/library_type': [],
    'valid/rpath': [],
    'valid/target_include_directories': [],
    'valid/target_include_directories_var': [],
    'valid/target_scope': [],
    'valid/threads': [],
    'valid/version': [],
    'valid/version_no_check': [],
}


def test_every_fixture_has_an_expectation():
    found = {path.parent.relative_to(TESTS).as_posix() for path in TESTS.glob('*/*/CMakeLists.txt')}
    assert found == set(EXPECTED)


def test_every_check_has_an_error_fixture():
    assert {name for issues in EXPECTED.values() for name, _ in issues} == {check.name for check in checks.CHECKS}


@pytest.mark.parametrize('fixture', EXPECTED)
def test_fixture(fixture, lint):
    path = TESTS / fixture / 'CMakeLists.txt'
    assert lint(path.read_text(encoding='utf-8'), path) == EXPECTED[fixture]
