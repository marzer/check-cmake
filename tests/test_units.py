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

import colorama
import pytest

from check_cmake import checks, utils
from check_cmake.checks import IGNORE_PRAGMA, Check, Issue, Link, Span
from check_cmake.grid import Grid
from check_cmake.version import VERSION, VERSION_STRING

CHECKS = {check.name: check for check in checks.CHECKS}


@pytest.mark.parametrize(
    'val,expected', [(None, ()), ('abc', ('abc',)), (42, (42,)), (['a', 'b'], ('a', 'b')), (('a', 'b'), ('a', 'b'))]
)
def test_as_tuple_boxes_everything_but_lists_and_tuples(val, expected):
    assert utils.as_tuple(val) == expected


@pytest.mark.parametrize('pos,expected', [(0, (1, 1)), (2, (1, 3)), (3, (2, 1)), (5, (2, 3))])
def test_calc_line_and_column_is_one_based(pos, expected):
    assert utils.calc_line_and_column('ab\ncd', pos) == expected


@pytest.mark.parametrize('pos,expected', [(0, 0), (1, 0), (4, 3), (7, 7)])
def test_find_first_char_on_line(pos, expected):
    assert utils.find_first_char_on_line('ab\ncde\nf', pos) == expected


@pytest.mark.parametrize('pos,expected', [(0, 1), (3, 5), (4, 5), (7, 7)])
def test_find_last_char_on_line(pos, expected):
    assert utils.find_last_char_on_line('ab\ncde\nf', pos) == expected


def test_strip_cmake_comments_keeps_every_line():
    assert utils.strip_cmake_comments('a # b\n# c\nd') == 'a \n\nd'


def test_grid_yields_a_newline_cell_between_rows():
    assert list(Grid('ab\nc')) == [(1, 1, 'a'), (1, 2, 'b'), (1, 3, '\n'), (2, 1, 'c')]


@pytest.mark.parametrize('text,expected', [('a', (1, 1, 1, 1)), ('b', (1, 2, 1, 2)), ('c\nd', (1, 3, 2, 1))])
def test_grid_find_range_returns_the_first_and_last_cell(text, expected):
    assert Grid('abc\ndef').find_range(text) == expected


@pytest.mark.parametrize('text,expected', [('f', (2, 3, 2, 3)), ('def', (2, 1, 2, 3)), ('abc\ndef', (1, 1, 2, 3))])
def test_grid_find_range_matches_at_the_end_of_the_grid(text, expected):
    assert Grid('abc\ndef').find_range(text) == expected


@pytest.mark.parametrize('text', [None, '', 'x', 'abc\ndefg'])
def test_grid_find_range_returns_none_without_a_match(text):
    assert Grid('abc\ndef').find_range(text) is None


def test_span_length_and_end():
    assert (len(Span(2, 3)), Span(2, 3).end) == (3, 5)
    assert (len(Span(2, end=7)), Span(2, end=7).end) == (5, 7)
    assert not Span(4, end=4)


@pytest.mark.parametrize(
    'span,expected',
    [(Span(0, 2), 0b10), (Span(1, end=4), 0b110), (Span(3, end=8), 0b1100), (Span(3, 0), 0b100), (Span(8), 0)],
)
def test_span_line_mask_sets_one_bit_per_line(span, expected):
    assert span.line_mask('ab\ncd\nef') == expected


def test_span_line_mask_covers_spans_that_start_or_end_at_a_line_break():
    assert Span(0, end=2).line_mask('\nx') == 0b110
    assert Span(4, 0).line_mask('abc\nd') == 0b100


@pytest.mark.parametrize(
    'uri,description',
    [
        ('https://cmake.org/cmake/help/latest/command/target_link_libraries.html', 'target_link_libraries()'),
        ('https://cmake.org/cmake/help/latest/command/find_package.html', 'find_package()'),
        ('https://cmake.org/cmake/help/latest/module/ExternalProject.html', 'ExternalProject'),
        ('https://cmake.org/cmake/help/latest/prop_tgt/INSTALL_RPATH.html', 'INSTALL_RPATH'),
        ('https://gist.github.com/mbinna/c61dbb39bca0e4fb7d1f73b0d66a4fd1', None),
    ],
)
def test_link_derives_its_description_from_the_uri(uri, description):
    assert Link(uri).description == description


def test_link_prints_its_description_before_the_uri():
    assert str(Link('https://example.com/x', 'Example')) == 'Example: https://example.com/x'
    assert str(Link('https://example.com/x')) == 'https://example.com/x'
    assert not Link('')


@pytest.mark.parametrize(
    'line',
    [
        'add_library(foo) # nocheck',
        'add_library(foo) # nolint',
        'add_library(foo) #NOCHECK',
        'add_library(foo) # check-cmake ignore',
        'add_library(foo) # cmake-lint: disable',
        'add_library(foo) # lint_cmake disable',
        'add_library(foo) # cmake check: ignore',
        '# nocheck   ',
    ],
)
def test_ignore_pragma_matches(line):
    assert IGNORE_PRAGMA.fullmatch(line)


@pytest.mark.parametrize(
    'line',
    [
        'add_library(foo)',
        'add_library(foo) nocheck',
        'add_library(foo) # nocheck please',
        'add_library(foo) # check-cmake enable',
    ],
)
def test_ignore_pragma_rejects(line):
    assert not IGNORE_PRAGMA.fullmatch(line)


@pytest.mark.parametrize(
    'text,expected',
    [
        ('project(foo VERSION 1)', [('specify_minimum_cmake_version', 1)]),
        ('project(foo VERSION 1)\ncmake_minimum_required(VERSION 3.16)', [('specify_minimum_cmake_version', 2)]),
        ('cmake_minimum_required(VERSION 3.16)\nproject(foo VERSION 1)', []),
        ('target_include_directories(foo PRIVATE SYSTEM bar)', [('target_include_directories_system', 1)]),
        ('target_include_directories(foo SYSTEM PRIVATE bar)', []),
        ('cmake_minimum_required(VERSION 3.16)\nproject(foo)', [('specify_project_version', 2)]),
        ('target_link_libraries(foo bar)', [('specify_scope_on_target_functions', 1)]),
        ('target_compile_options(foo -Wall)', [('specify_scope_on_target_functions', 1)]),
        ('target_link_libraries(foo PRIVATE bar)', []),
        ('target_link_options(foo PRIVATE -Wl,-rpath=/opt/lib)', [('use_set_target_properties_rpath', 1)]),
        ('set_target_properties(foo PROPERTIES INSTALL_RPATH /opt/lib)', []),
        ('set(CMAKE_POSITION_INDEPENDENT_CODE ON)', [('use_set_target_properties_pic', 1)]),
        ('set_target_properties(foo PROPERTIES POSITION_INDEPENDENT_CODE ON)', []),
        ('add_definitions(-DFOO)', [('use_target_compile_definitions', 1)]),
        ('add_compile_definitions(FOO)', [('use_target_compile_definitions', 1)]),
        ('target_compile_definitions(foo PRIVATE FOO)', []),
        ('set(CMAKE_CXX_STANDARD 17)', [('use_target_compile_features_language_standard', 1)]),
        ('set_target_properties(foo PROPERTIES C_STANDARD 11)', [('use_target_compile_features_language_standard', 1)]),
        ('target_compile_features(foo PUBLIC cxx_std_17)', []),
        ('add_compile_options(-Wall)', [('use_target_compile_options', 1)]),
        ('set(CMAKE_CXX_FLAGS "-Wall")', [('use_target_compile_options', 1)]),
        ('target_compile_options(foo PRIVATE -Wall)', []),
        ('include_directories(include)', [('use_target_include_directories', 1)]),
        ('target_include_directories(foo PRIVATE include)', []),
        ('link_directories(lib)', [('use_target_link_libraries', 1)]),
        ('target_link_directories(foo PRIVATE lib)', []),
        ('target_link_libraries(foo PRIVATE pthread)', [('use_threads_package', 1)]),
        ('target_link_libraries(foo PRIVATE Threads::Threads)', []),
        ('ExternalProject_Add(foo CMAKE_ARGS -D FOO=1)', [('external_project_add_cmake_args', 1)]),
        ('ExternalProject_Add(foo CMAKE_ARGS -DFOO=1)', []),
        ('add_library(foo foo.cpp)', [('specify_library_type', 1)]),
        ('add_library(foo STATIC foo.cpp)', []),
    ],
)
def test_check(text, expected, lint):
    assert lint(text) == expected


def test_minimum_version_is_only_required_in_cmakelists(lint):
    assert lint('project(foo VERSION 1)', Path('foo.cmake')) == []
    assert lint('project(foo VERSION 1)', Path('cmakelists.TXT')) == [('specify_minimum_cmake_version', 1)]


def test_base_check_is_abstract():
    with pytest.raises(NotImplementedError):
        Check('name', 'description')(Path('CMakeLists.txt'), '')


def test_threads_example_is_two_lines():
    example = str(CHECKS['use_threads_package'].example)
    assert '\\n' not in example
    assert len(example.splitlines()) == 2


def test_external_project_example_uses_plain_variable_syntax():
    assert '"-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}"' in str(CHECKS['external_project_add_cmake_args'].example)


def test_issue_context_defaults_to_the_span():
    issue = Issue(CHECKS['specify_library_type'], Path('CMakeLists.txt'), 'add_library(foo)', Span(12, 3))
    assert (issue.context.start, issue.context.end) == (12, 15)
    assert issue.grid.line_number == 1


def test_issue_highlights_a_span_at_the_end_of_its_context():
    (issue,) = checks.check_text(Path('CMakeLists.txt'), 'target_link_options(foo PRIVATE\n    -Wl,-rpath=\n)')
    assert colorama.Fore.RED in str(issue.grid)


def test_check_text_sorts_issues_by_position(lint):
    assert lint('add_library(foo)\ninclude_directories(include)\nadd_library(bar)') == [
        ('specify_library_type', 1),
        ('use_target_include_directories', 2),
        ('specify_library_type', 3),
    ]


def test_check_text_ignores_commented_out_code(lint):
    assert lint('# add_library(foo)\nadd_library(bar STATIC) # add_library(baz)') == []


def test_check_text_normalises_line_endings(lint):
    assert lint('add_library(foo)\r\nadd_library(bar)\radd_library(baz)') == [
        ('specify_library_type', 1),
        ('specify_library_type', 2),
        ('specify_library_type', 3),
    ]


@pytest.mark.parametrize('pragma', ['# nocheck', '# nolint', '# check-cmake: ignore'])
def test_pragma_suppresses_issues_on_its_line_only(pragma, lint):
    assert lint(f'add_library(foo) {pragma}\nadd_library(bar)') == [('specify_library_type', 2)]


def test_pragma_on_any_line_of_a_multiline_issue_suppresses_it(lint):
    assert lint('add_library(\n    foo\n)') == [('specify_library_type', 1)]
    assert lint('add_library(\n    foo # nocheck\n)') == []


def test_check_text_computes_no_line_masks_without_a_pragma(lint, monkeypatch):
    monkeypatch.setattr(Span, 'line_mask', lambda *_: pytest.fail('line mask computed without a pragma'))
    assert lint('add_library(foo)\nadd_library(bar)') == [('specify_library_type', 1), ('specify_library_type', 2)]


def test_version_is_three_part_tuple_matching_string():
    assert isinstance(VERSION, tuple)
    assert len(VERSION) == 3
    assert all(isinstance(v, int) for v in VERSION)
    assert VERSION_STRING == '.'.join(str(v) for v in VERSION)


def test_version_file_on_disk_is_a_clean_triplet():
    raw = (Path(__file__).parents[1] / r'VERSION').read_text(encoding='utf-8')
    stripped = raw.strip()
    assert '\n' not in stripped
    parts = stripped.split('.')
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
    assert stripped == VERSION_STRING


@pytest.mark.parametrize(
    'packages,dist_info_beside,pyproject,expected',
    [
        ('deps', False, True, '9.8.7'),
        ('src', True, True, '9.8.7'),
        ('src', False, False, '9.8.7'),
        ('src', False, True, '3.2.0'),
    ],
    ids=['copy_outside_src', 'target_install_into_src', 'src_without_pyproject', 'source_tree'],
)
def test_the_version_file_is_read_only_from_a_source_tree(tmp_path, packages, dist_info_beside, pyproject, expected):
    host = tmp_path / 'host'
    shutil.copytree(
        Path(__file__).resolve().parents[1] / 'src' / 'check_cmake',
        host / packages / 'check_cmake',
        ignore=shutil.ignore_patterns('__pycache__'),
    )
    if pyproject:
        (host / 'pyproject.toml').write_text('', encoding='utf-8')
    (host / 'VERSION').write_text('3.2.0\n', encoding='utf-8')
    site = host / packages if dist_info_beside else tmp_path / 'site'
    metadata = site / 'check_cmake-9.8.7.dist-info' / 'METADATA'
    metadata.parent.mkdir(parents=True)
    metadata.write_text('Metadata-Version: 2.1\nName: check_cmake\nVersion: 9.8.7\n', encoding='utf-8')
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(host / packages), str(tmp_path / 'site')])}
    result = subprocess.run(
        [sys.executable, '-c', 'from check_cmake.version import VERSION_STRING; print(VERSION_STRING)'],
        capture_output=True,
        encoding='utf-8',
        check=False,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
