#!/usr/bin/env python3
# This file is a part of marzer/check_cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check_cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

from io import StringIO
from typing import Tuple

from misk import *


def calc_line_and_column(text: str, pos: int) -> Tuple[int, int]:
    assert 0 <= pos <= len(text)
    line = 0
    col = 0
    for i in range(min(len(text), pos)):
        if text[i] == '\n':
            line += 1
            col = 0
        else:
            col += 1
    return (line + 1, col + 1)


def find_first_char_on_line(text: str, pos: int) -> int:
    assert 0 <= pos <= len(text)
    if text:
        pos = max(min(len(text) - 1, pos), 0)
        assert text[pos] != '\n'
        for i in range(pos, -1, -1):
            if text[i] == '\n':
                return i + 1
    return 0


def find_last_char_on_line(text: str, pos: int) -> int:
    assert 0 <= pos <= len(text)
    if text:
        pos = max(min(len(text) - 1, pos), 0)
        assert text[pos] != '\n'
        for i in range(pos, len(text)):
            if text[i] == '\n':
                return i - 1
        return len(text) - 1
    return 0


def strip_cmake_comments(text: str) -> str:
    # todo: this currently does not support cmake's multi-line bracket syntax,
    # nor does it take strings into account (so a # in a string will count as a comment)
    in_comment = False
    with StringIO() as buf:
        for c in text:
            if in_comment:
                if c == '\n':
                    buf.write('\n')
                    in_comment = False
            else:
                if c == '#':
                    in_comment = True
                else:
                    buf.write(c)
        return buf.getvalue()


__all__ = ['calc_line_and_column', 'find_first_char_on_line', 'find_last_char_on_line', 'strip_cmake_comments']
