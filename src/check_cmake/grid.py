#!/usr/bin/env python3
# This file is a part of marzer/check_cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check_cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

from io import StringIO
from typing import Tuple

import colorama


class Cell(object):
    def __init__(self, char):
        self.__val = str(char)
        self.colour = None
        self.style = None
        assert len(self.__val) == 1

    def __str__(self) -> str:
        return self.__val

    @property
    def value(self) -> str:
        return self.__val


class Grid(object):
    def __init__(self, text: str, indent='', line_number=None):
        self.__rows = []
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = text.replace('\t', '    ')
        lines = text.split('\n')
        for line in lines:
            row = []
            for col in line:
                row.append(Cell(col))
            self.__rows.append(row)
        self.line_number = line_number
        self.__indent = str(indent)

    @property
    def line_number(self) -> int:
        return self.__line_num

    @line_number.setter
    def line_number(self, val: int):
        self.__line_num = int(val) if val is not None else None

    def __bool__(self) -> bool:
        return bool(self.__rows)

    def __str__(self) -> str:
        if not self.__rows:
            return ''
        current_style = None
        current_colour = None
        line_num = 1
        line_num_width = 0
        emit_line_num = False
        if self.__line_num is not None:
            emit_line_num = True
            line_num = int(self.__line_num)
            line_num_width = max(len(str(max(line_num, 0) + len(self.__rows) - 1)), 2)
        with StringIO() as buf:
            for row in self.__rows:
                buf.write(self.__indent)
                if emit_line_num:
                    if current_colour is not None or current_style is not None:
                        buf.write(rf'{colorama.Style.RESET_ALL}')
                    if line_num >= 0:
                        buf.write(rf'{line_num:>{line_num_width}} | ')
                    else:
                        buf.write(rf'{" "*line_num_width} | ')
                    if current_colour is not None:
                        buf.write(rf'{current_colour}')
                    if current_style is not None:
                        buf.write(rf'{current_style}')
                for col in row:
                    if col.style == colorama.Style.RESET_ALL:
                        if current_colour is not None or current_style is not None:
                            buf.write(rf'{colorama.Style.RESET_ALL}')
                        current_style = None
                        current_colour = None
                    else:
                        if col.style is not None and col.style != current_style:
                            current_style = col.style
                            buf.write(rf'{current_style}')
                        if col.colour is not None and col.colour != current_colour:
                            current_colour = col.colour
                            buf.write(rf'{current_colour}')
                    buf.write(str(col))
                line_num += 1
                buf.write('\n')
            return rf'{buf.getvalue().rstrip()}{colorama.Style.RESET_ALL}'

    def style_range(self, first_line, first_col, last_line=None, last_col=None, style=None, colour=None):
        assert first_line >= 1
        if last_line is None:
            last_line = first_line
        if last_col is None:
            last_col = first_col
        assert last_line >= first_line
        assert first_line != last_line or last_col >= first_col
        colour = None if style == colorama.Style.RESET_ALL else colour
        first_line -= 1
        first_col -= 1
        last_line -= 1
        last_col -= 1
        for r in range(first_line, last_line + 1):
            if r >= len(self.__rows):
                break
            row = self.__rows[r]
            for c in range(first_col if r == first_line else 0, (last_col + 1) if r == last_line else len(row)):
                if c >= len(row):
                    break
                col = row[c]
                col: Cell
                col.style = style
                col.colour = colour

    def __iter__(self):
        r = 1
        for row in self.__rows:
            if r > 1:
                yield (r - 1, c, '\n')
            c = 1
            for col in row:
                yield (r, c, col.value)
                c += 1
            r += 1

    def find_range(self, text) -> Tuple[int, int, int, int]:
        if text is None or not self.__rows:
            return None
        text = str(text)
        if not text:
            return None
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = text.replace('\t', '    ')

        def compare_from_offset(start):
            nonlocal self
            nonlocal text
            skipped = 0
            i = 0
            start_r = None
            start_c = None
            for r, c, val in self:
                if skipped < start:
                    skipped += 1
                    continue
                if start_r is None:
                    start_r = r
                    start_c = c
                if val != text[i]:
                    return None
                i += 1
                if i == len(text):
                    return (start_r, start_c, r, c)
            return None

        self_len = sum(1 for e in self)
        if len(text) > self_len:
            return None

        for i in range(0, self_len - len(text)):
            result = compare_from_offset(i)
            if result is not None:
                return result

        return None


__all__ = ['Grid']
