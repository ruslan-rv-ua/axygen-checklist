# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Puts on `sys.path` what the tests import by name. Two entries, two reasons.

The **add-on package directory** makes `core` import as a top-level package.
The core of the add-on lives inside the add-on package, at
`addon/globalPlugins/axygenChecklist/core/`, because NVDA reloads plugins by
dropping everything under the `globalPlugins` prefix out of `sys.modules`.
Importing it as `globalPlugins.axygenChecklist.core` would execute the parent
`__init__.py`, which imports NVDA's own modules and so cannot run outside a
running screen reader. Putting the package directory itself on the path reaches
the same files without waking the parent.

This belongs in the package `__init__` rather than in a module the tests
import: unittest imports a package before the test modules inside it, whereas
two import lines in a test module would have to stay in the right order for
`core` to resolve at all.

Stubbing NVDA's own modules is deliberately not an option; see the section on
the core/shell boundary in docs/development.md.

The **repository root** makes `tools` and `buildVars` import at all. Running
the suite as `python -m unittest` from the root puts them within reach anyway,
which is exactly why the entry belongs here: a test that passes only when it is
run from one directory passes for a reason nobody wrote down. Every other path
in this suite is derived from `__file__`, and now these are too.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADDON_PACKAGE = _REPO_ROOT / "addon" / "globalPlugins" / "axygenChecklist"

for _entry in (_ADDON_PACKAGE, _REPO_ROOT):
	if str(_entry) not in sys.path:
		sys.path.insert(0, str(_entry))
