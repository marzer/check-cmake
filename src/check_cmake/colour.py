#!/usr/bin/env python3
# This file is a part of marzer/check_cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check_cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import colorama

BRIGHTNESSES = (colorama.Style.DIM, colorama.Style.NORMAL, colorama.Style.BRIGHT)


def style(text, colour="WHITE", brightness=0):
    if not isinstance(text, str):
        text = rf'{text}'
    brightness = BRIGHTNESSES[max(min(int(brightness), 1), -1) + 1]
    return rf"{getattr(colorama.Fore, str(colour).upper())}{brightness}{text}{colorama.Style.RESET_ALL}"


def bright(text, colour="WHITE"):
    return style(text, colour=colour, brightness=1)


def dim(text, colour="WHITE"):
    return style(text, colour=colour, brightness=-1)


__all__ = ['style', 'bright', 'dim']
