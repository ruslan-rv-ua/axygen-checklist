# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The core is free of the screen reader, and the import is the rule.

For NVDA's own modules — `ui`, `config`, `addonHandler` — the rule holds by
itself: they do not exist outside a running NVDA, so a core module that
reached for one would fail to import, and every test of it with it. `wx` is
the one exception. wxPython is installed in the development environment,
because the type check CI runs needs its stubs (docs/development.md), so a
core module that imported it would import here just fine, and nothing but
this test would notice. It imports every module of the core and asks whether
`wx` came along.
"""

import importlib
import pkgutil
import sys
import unittest

import core


class CoreImportsNoWx(unittest.TestCase):
	def test_importing_every_core_module_brings_in_no_wx(self) -> None:
		for module in pkgutil.iter_modules(core.__path__):
			importlib.import_module(f"core.{module.name}")
		self.assertFalse("wx" in sys.modules, "a module of the core imports wx")
