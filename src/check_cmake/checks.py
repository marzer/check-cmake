#!/usr/bin/env python3
# This file is a part of marzer/check_cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check_cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import re
from io import StringIO
from pathlib import Path
from typing import Collection, List, Tuple, Union

import colorama

from . import utils
from .grid import Grid

INDENT = '  '

BS = '\\'


class Link(object):
    def __init__(self, uri, description=None):
        self.uri = str(uri)
        self.description = description
        if self.description is not None:
            self.description = str(self.description)
        else:
            last_slash = self.uri.rfind('/')
            last_dot = self.uri.rfind('.')
            if last_slash == -1 or last_dot == -1 or last_dot < last_slash:
                return
            self.description = self.uri[last_slash + 1 : last_dot]
            if (
                re.fullmatch('[a-z_]+', self.description)
                and re.match('^(set_|target_|find_|project)', self.description)
                and not re.match('\(\s*\)\s*$', self.description)
            ):
                self.description += '()'

    def __bool__(self):
        return bool(self.uri)

    def __str__(self):
        if self.description:
            return rf'{self.description}: {self.uri}'
        return self.uri


class Links(object):
    # SHOUTY
    CMAKE_C_KNOWN_FEATURES = Link('https://cmake.org/cmake/help/latest/prop_gbl/CMAKE_C_KNOWN_FEATURES.html')
    CMAKE_CXX_KNOWN_FEATURES = Link('https://cmake.org/cmake/help/latest/prop_gbl/CMAKE_CXX_KNOWN_FEATURES.html')
    # PascalCase
    ExternalProject = Link('https://cmake.org/cmake/help/latest/module/ExternalProject.html')
    # snake_case
    effective_modern_cmake = Link(
        'https://gist.github.com/mbinna/c61dbb39bca0e4fb7d1f73b0d66a4fd1', 'Effective Modern CMake'
    )
    find_package = Link('https://cmake.org/cmake/help/latest/command/find_package.html')
    private_public_interface = Link(
        'https://leimao.github.io/blog/CMake-Public-Private-Interface/', 'Public vs. Private vs. Interface'
    )
    project = Link('https://cmake.org/cmake/help/latest/command/project.html')
    set_target_properties = Link('https://cmake.org/cmake/help/latest/command/set_target_properties.html')
    target_compile_definitions = Link('https://cmake.org/cmake/help/latest/command/target_compile_definitions.html')
    target_compile_features = Link('https://cmake.org/cmake/help/latest/command/target_compile_features.html')
    target_compile_options = Link('https://cmake.org/cmake/help/latest/command/target_compile_options.html')
    target_include_directories = Link('https://cmake.org/cmake/help/latest/command/target_include_directories.html')
    target_link_libraries = Link('https://cmake.org/cmake/help/latest/command/target_link_libraries.html')
    add_library = Link('https://cmake.org/cmake/help/latest/command/add_library.html')


class Span(object):
    def __init__(self, start: int, length: int = 1, end: int = None):
        self.start = int(start)
        assert self.start >= 0
        if end is not None:
            self.length = int(end) - self.start
        else:
            self.length = int(length)
        assert self.length >= 0

    def __bool__(self):
        return bool(self.length)

    def __len__(self) -> int:
        return self.length

    @property
    def end(self) -> int:
        return self.start + self.length

    def line_mask(self, text: str) -> int:
        if not self.length or self.start >= len(text):
            return 0
        first = utils.calc_line_and_column(text, self.start)[0]
        last = min(self.end, len(text)) - 1
        last = utils.calc_line_and_column(text, last)[0] if last > first else first
        mask = 0
        for i in range(first, last + 1):
            mask |= 1 << i
        return mask


class Issue(object):
    def __init__(
        self, generator, source_path: Path, source_text: str, span: Span, description: str = None, context: Span = None
    ):
        assert generator is not None
        self.generator = generator

        assert source_path
        self.source_path = source_path

        assert source_text
        self.source_text = source_text

        self.description = description

        assert span is not None
        self.span = span
        self.context = span if context is None else context
        assert self.context.start <= self.span.start
        assert self.context.end >= self.span.end

        self.line_and_column = utils.calc_line_and_column(source_text, span.start)

        self.grid = Grid(source_text[self.context.start : self.context.end], indent=INDENT * 2)
        self.grid.line_number = utils.calc_line_and_column(source_text, context.start)[0]
        grid_highlight_range = self.grid.find_range(source_text[self.span.start : self.span.end])
        if grid_highlight_range is not None:
            self.grid.style_range(
                first_line=grid_highlight_range[0],
                first_col=grid_highlight_range[1],
                last_line=grid_highlight_range[2],
                last_col=grid_highlight_range[3],
                colour=colorama.Fore.RED,
            )
            self.grid.style_range(
                first_line=grid_highlight_range[2],
                first_col=grid_highlight_range[3] + 1,
                last_line=99999,
                last_col=99999,
                style=colorama.Style.RESET_ALL,
            )

    def __str__(self):
        with StringIO() as buf:
            buf.write('\n')
            buf.write(colorama.Style.BRIGHT)
            if self.source_path:
                buf.write(f'{self.source_path}')
            else:
                buf.write(f'<file>')
            buf.write(rf':{self.line_and_column[0]}:{self.line_and_column[1]}: {colorama.Style.RESET_ALL}')
            if self.description is not None:
                buf.write(self.description)
            else:
                buf.write(self.generator.description)
            # buf.write(rf' [{self.generator.name}]')
            if self.grid:
                buf.write(f'\n{INDENT}{colorama.Style.BRIGHT}Context:{colorama.Style.RESET_ALL}\n{self.grid}')
            if self.generator.replace_with:
                buf.write(
                    f'\n{INDENT}{colorama.Style.BRIGHT}Replace with:{colorama.Style.RESET_ALL}\n{INDENT*2}{self.generator.replace_with}'
                )
            if self.generator.example:
                buf.write(
                    f'\n{INDENT}{colorama.Style.BRIGHT}Example:{colorama.Style.RESET_ALL}\n{self.generator.example}'
                )
            if self.generator.more_info:
                buf.write(f'\n{INDENT}{colorama.Style.BRIGHT}More information:{colorama.Style.RESET_ALL}')
                for info in self.generator.more_info:
                    buf.write(f'\n{INDENT*2}{info}')
            return buf.getvalue().lstrip()


class Check(object):
    def __init__(
        self,
        name: str,
        description: str,
        replace_with: Union[str, Link] = None,
        example: Union[str, Grid] = None,
        more_info: Union[str, Link, Collection[Union[str, Link]]] = None,
    ):
        assert name is not None
        self.__name = str(name).strip()
        assert self.__name

        assert description is not None
        self.__description = str(description).strip()
        assert self.__description

        self.__replace_with = replace_with
        if self.__replace_with is not None and not isinstance(self.__replace_with, Link):
            self.__replace_with = str(self.__replace_with).strip()

        self.__example = example
        if self.__example is not None and not isinstance(self.__example, Grid):
            self.__example = str(self.__example).strip()
            self.__example = Grid(self.__example, line_number=-999999, indent=INDENT * 2) if self.__example else None

        self.__more_info = None
        if more_info is not None:
            self.__more_info = [i for i in list(utils.coerce_collection(more_info)) if i]
            for i in range(len(self.__more_info)):
                if not isinstance(self.__more_info[i], Link):
                    self.__more_info[i] = Link(str(self.__more_info[i]))
            self.__more_info = tuple(self.__more_info) if self.__more_info else None

    def __call__(self, source_path: Path, source_text: str) -> Union[Issue, List[Issue]]:
        raise Exception('not implemented')

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def example(self) -> Grid:
        return self.__example

    @property
    def replace_with(self) -> Union[str, Link]:
        return self.__replace_with

    @property
    def more_info(self) -> Tuple[Link]:
        return self.__more_info


class RegexCheck(Check):
    def __init__(
        self,
        name: str,
        description: str,
        pattern: Union[str, Collection[str]],
        replace_with: Union[str, Link] = None,
        example: str = None,
        more_info: Union[str, Link, Collection[Union[str, Link]]] = None,
        flags: int = 0,
        inner_group_index: int = 1,
        inner_group_must_match: str = None,
    ):
        super().__init__(name, description, replace_with=replace_with, example=example, more_info=more_info)

        self._description_has_group_placeholders = re.search(r'\\[0-9]', self.description)

        assert pattern is not None
        pattern = utils.coerce_collection(pattern)
        assert pattern
        self._patterns = []
        for p in pattern:
            p = str(p)
            if p:
                self._patterns.append(re.compile(p, flags=int(flags) | re.DOTALL))
        self._patterns = tuple(self._patterns)
        assert self._patterns

        self._inner_group_index = int(inner_group_index)

        self._inner_group_must_match = None
        if inner_group_must_match is not None and bool(inner_group_must_match):
            self._inner_group_must_match = re.compile(str(inner_group_must_match), flags=int(flags) | re.DOTALL)

    def __call__(self, source_path: Path, source_text: str) -> List[Issue]:
        results = []
        for pattern in self._patterns:
            for m in pattern.finditer(source_text):
                inner_group_index = self._inner_group_index
                try:
                    m[inner_group_index]
                except IndexError:
                    inner_group_index = 0
                if self._inner_group_must_match is not None:
                    m2 = self._inner_group_must_match.search(str(m[inner_group_index]))
                    if m2:
                        continue
                description = self.description
                if self._description_has_group_placeholders:
                    for i in range(10):
                        try:
                            description = description.replace(f'\\{i}', str(m[i]))
                        except IndexError:
                            pass
                results.append(
                    Issue(
                        generator=self,
                        source_path=source_path,
                        source_text=source_text,
                        description=description,
                        span=Span(m.start(inner_group_index), end=m.end(inner_group_index)),
                        context=Span(
                            utils.find_first_char_on_line(source_text, m.start(0)),
                            end=utils.find_last_char_on_line(source_text, m.end(0) - 1) + 1,
                        ),
                    )
                )
        return results


# "not closing bracket"
NCB = r'[^)]*?'

# "not string"
NSTR = r'[^"]*?'


def emphasis(text):
    return rf'{colorama.Fore.YELLOW}{text}{colorama.Style.RESET_ALL}'


class SpecifyMinimumCMakeVersion(Check):
    def __init__(self):
        super().__init__(
            r'specify_minimum_cmake_version',
            rf"scripts which contain a {emphasis('project()')} should specify a {emphasis('cmake_minimum_required()')} before it",
            example='cmake_minimum_required(VERSION 3.16)\n\nproject(\n    # ...\n)',
            more_info=Link(
                r'https://cmake.org/cmake/help/latest/command/cmake_minimum_required.html', r'cmake_minimum_required()'
            ),
        )
        self.__find_project = re.compile(rf'\b(project)\s*\(({NCB})\)', flags=re.DOTALL)
        self.__find_min_required = re.compile(rf'\b(cmake_minimum_required)\s*\(({NCB})\)', flags=re.DOTALL)

    def __call__(self, source_path: Path, source_text: str) -> Issue:
        if source_path.name.lower() != 'cmakelists.txt':
            return None
        project = self.__find_project.search(source_text)
        if not project:
            return None
        min_required = self.__find_min_required.search(source_text)
        if not min_required:
            return Issue(
                generator=self,
                source_path=source_path,
                source_text=source_text,
                span=Span(project.start(1), end=project.end(1)),
                context=Span(
                    utils.find_first_char_on_line(source_text, project.start()),
                    end=utils.find_last_char_on_line(source_text, project.end() - 1) + 1,
                ),
            )
        elif min_required.start() > project.start():
            return Issue(
                generator=self,
                source_path=source_path,
                source_text=source_text,
                span=Span(min_required.start(1), end=min_required.end(1)),
                context=Span(
                    utils.find_first_char_on_line(source_text, project.start()),
                    end=utils.find_last_char_on_line(source_text, max(project.end(), min_required.end()) - 1) + 1,
                ),
            )


class TargetIncludeDirectoriesSYSTEM(Check):
    def __init__(self):
        super().__init__(
            r'target_include_directories_system',
            rf"the {emphasis('SYSTEM')} specifier must be the first non-target argument passed to {emphasis('target_include_directories()')}",
            example='target_include_directories(my_lib\n\tSYSTEM\n\tINTERFACE\n\t\t$<INSTALL_INTERFACE:include>\n)',
            more_info=Links.target_include_directories,
        )
        self.__tid_with_system = re.compile(
            rf'\btarget_include_directories\s*\(({NCB}\b(SYSTEM)\b{NCB})\)', flags=re.DOTALL
        )
        self.__good_args = re.compile(rf'^\s*(?:[a-zA-Z0-9_-]+|"{NSTR}")\s+SYSTEM\s+.*?$', flags=re.DOTALL)

    def __call__(self, source_path: Path, source_text: str) -> Issue:
        tid = self.__tid_with_system.search(source_text)
        if not tid:
            return None
        if self.__good_args.fullmatch(tid[1]):
            return None
        return Issue(
            generator=self,
            source_path=source_path,
            source_text=source_text,
            span=Span(tid.start(2), end=tid.end(2)),
            context=Span(
                utils.find_first_char_on_line(source_text, tid.start()),
                end=utils.find_last_char_on_line(source_text, tid.end() - 1) + 1,
            ),
        )


CHECKS = (
    SpecifyMinimumCMakeVersion(),
    TargetIncludeDirectoriesSYSTEM(),
    RegexCheck(
        r'specify_project_version',
        rf"{emphasis('project()')} should specify a {emphasis('VERSION')}",
        rf'\bproject\s*\(({NCB})\)',
        inner_group_must_match=r'\bVERSION\b',
        more_info=Links.project,
    ),
    RegexCheck(
        r'specify_scope_on_target_functions',
        rf'{emphasis(BS+r"1()")} should specify at least one dependency scope '
        rf'({emphasis("PRIVATE")}, {emphasis("INTERFACE")} or {emphasis("PUBLIC")}) ',
        rf'\b(target_(?:link_(?:options|libraries)|compile_(?:options|features|definitions)|(?:include|link)_directories))\s*\(({NCB})\)',
        inner_group_index=2,
        inner_group_must_match=r'\b(?:PRIVATE|PUBLIC|INTERFACE)\b',
        more_info=(Links.private_public_interface, Links.effective_modern_cmake),
    ),
    RegexCheck(
        r'use_set_target_properties_rpath',
        rf'rpaths should be set using {emphasis("set_target_properties()")} and {emphasis("INSTALL_RPATH")}',
        r'(-Wl,-rpath=)',
        replace_with=Links.set_target_properties,
        example=r'''
get_target_property(my_current_rpaths my_lib INSTALL_RPATH)
list(APPEND my_current_rpaths "/opt/lib")
set_target_properties(my_lib PROPERTIES INSTALL_RPATH "${my_current_rpaths}")
''',
        more_info=r'https://cmake.org/cmake/help/latest/prop_tgt/INSTALL_RPATH.html',
    ),
    RegexCheck(
        r'use_set_target_properties_pic',
        rf'position-independent code should be set per-target using {emphasis("set_target_properties()")} and {emphasis("POSITION_INDEPENDENT_CODE")}',
        rf'\bset\s*\({NCB}\b(CMAKE_POSITION_INDEPENDENT_CODE)\b{NCB}\)',
        replace_with=Links.set_target_properties,
        example=r'set_target_properties(my_lib PROPERTIES POSITION_INDEPENDENT_CODE ON)',
        more_info=r'https://cmake.org/cmake/help/latest/prop_tgt/POSITION_INDEPENDENT_CODE.html',
    ),
    RegexCheck(
        r'use_target_compile_definitions',
        rf'compiler defines should be set on a per-target basis using {emphasis("target_compile_definitions()")}',
        rf'\b(add_(?:compile_)?definitions)\s*\({NCB}\)',
        replace_with=Links.target_compile_definitions,
        more_info=Links.effective_modern_cmake,
    ),
    RegexCheck(
        r'use_target_compile_features_language_standard',
        rf'language standard level should be set on a per-target basis using {emphasis("target_compile_features()")}',
        (
            rf'\bset_target_properties\s*\({NCB}\b(C(?:XX)?_STANDARD)\b{NCB}\)',
            rf'\bset\s*\(\s*\b(CMAKE_C(?:XX)?_STANDARD)\b{NCB}\)',
        ),
        replace_with=Links.target_compile_features,
        more_info=(Links.CMAKE_CXX_KNOWN_FEATURES, Links.CMAKE_C_KNOWN_FEATURES),
    ),
    RegexCheck(
        r'use_target_compile_options',
        rf'compiler options should be set on a per-target basis using {emphasis("target_compile_options()")}',
        (rf'\b(add_compile_options)\s*\({NCB}\)', rf'\bset\s*\(\s*(CMAKE_C(?:XX)?_FLAGS)\b{NCB}\)'),
        replace_with=Links.target_compile_options,
        more_info=Links.effective_modern_cmake,
    ),
    RegexCheck(
        r'use_target_include_directories',
        rf'include paths should be set on a per-target basis using {emphasis("target_include_directories()")}',
        rf'\b(include_directories)\s*\({NCB}\)',
        replace_with=Links.target_include_directories,
        more_info=Links.effective_modern_cmake,
    ),
    RegexCheck(
        r'use_target_link_libraries',
        rf'linker paths should be inherited from library targets using {emphasis("target_link_libraries()")}',
        rf'\b(link_directories)\s*\({NCB}\)',
        replace_with=Links.target_link_libraries,
        more_info=Links.effective_modern_cmake,
    ),
    RegexCheck(
        r'use_threads_package',
        rf'support for threading should be provided by linking with {emphasis("Threads::Threads")} from the {emphasis("Threads")} package',
        rf'\btarget_link_libraries\s*\({NCB}\b(pthread)\b{NCB}\)',
        replace_with='Threads::Threads',
        example=r'find_package(Threads REQUIRED)\ntarget_link_libraries(my_lib PUBLIC Threads::Threads)',
        more_info=(r'https://cmake.org/cmake/help/latest/module/FindThreads.html', Links.find_package),
    ),
    RegexCheck(
        r'external_project_add_cmake_args',
        rf"{emphasis('ExternalProject_Add()')} variable definitions specified via {emphasis('CMAKE_ARGS')} must not"
        + rf" have a space after {emphasis('-D')} (use quotes around the entire argument if the RHS might have whitespace)",
        rf'\bExternalProject_Add\s*\({NCB}\s+CMAKE_ARGS\s+{NCB}(-D\s+[a-zA-Z0-9_]+=){NCB}\)',
        example='\nExternalProject_Add(\n\tsome_lib\n\tSOURCE_DIR\n\t\t"some_lib/source"\n\tCMAKE_ARGS\n\t\t"-DCMAKE_CXX_COMPILER=${{CMAKE_CXX_COMPILER}}"\n)',
        more_info=Links.ExternalProject,
    ),
    RegexCheck(
        r'specify_library_type',    
        rf"{emphasis('add_library()')} should specify the library type "
        rf'(one of {emphasis("STATIC")}, {emphasis("SHARED")}, {emphasis("MODULE")}, '
            + rf'{emphasis("OBJECT")}, {emphasis("INTERFACE")}, {emphasis("IMPORTED")}, {emphasis("ALIAS")}) ',
        rf'\badd_library\s*\(({NCB})\)',
        inner_group_must_match=r'\b(?:STATIC|SHARED|MODULE|OBJECT|INTERFACE|IMPORTED|ALIAS)\b',
        more_info=(Links.add_library, Links.effective_modern_cmake),
    ),
)

__all__ = ['Issue', 'CHECKS']
