#!/usr/bin/env python3
# This file is a part of marzer/check-cmake and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/check-cmake/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

from .main import main
from .version import VERSION, VERSION_STRING

__all__ = ['main', 'VERSION', 'VERSION_STRING']

__version__ = VERSION_STRING

if __name__ == '__main__':
    main()
