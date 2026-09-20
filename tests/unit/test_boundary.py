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

Translation is the second exception, and it fails even more quietly. NVDA
installs `gettext` into builtins at startup, so `_()` in a core module would
resolve — to NVDA's own catalogue, which knows nothing of our strings. What
that costs is named in section 2: the core is the half that reads and writes
the checklist, and the values of `status` are identifiers rather than text.
A `_()` anywhere near them is the one way a Ukrainian NVDA could come to write
`пройдено` into a file that an English one then cannot read, and the format
would stop being portable between locales. The words belong to the shell,
still as the one table of section 2, and `wording.py` is where they are.
"""

import importlib
import sys
import unittest
from pathlib import Path

import core

from .support import translation_lookups

CORE = Path(str(core.__path__[0]))

#: Every module of the core, by the file it is written in. One enumeration for
#: both tests below: a module the walk misses is a module neither rule reaches,
#: and that is not a thing to have two chances of getting wrong.
#:
#: The walk recurses for the same reason `buildVars.pythonSources` does -- the
#: add-on already has one sub-package, and a sub-package of the core would
#: otherwise leave both rules at the door without saying so.
MODULES = sorted(CORE.rglob("*.py"))


def _import_name(path: Path) -> str:
	"""The name `path` imports under, packages' own `__init__` included."""
	parts = path.relative_to(CORE).with_suffix("").parts
	return ".".join(("core", *(part for part in parts if part != "__init__")))


class CoreImportsNoWx(unittest.TestCase):
	def test_importing_every_core_module_brings_in_no_wx(self) -> None:
		for path in MODULES:
			importlib.import_module(_import_name(path))
		self.assertFalse("wx" in sys.modules, "a module of the core imports wx")


class CoreAsksForNoTranslation(unittest.TestCase):
	def test_no_core_module_looks_a_string_up_in_a_catalogue(self) -> None:
		for path in MODULES:
			with self.subTest(module=path.name):
				self.assertEqual(
					list(translation_lookups(path)),
					[],
					"a module of the core translates a string; the words live in the shell",
				)
