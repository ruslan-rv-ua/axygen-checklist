# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The core of the add-on: everything that does not need a running NVDA.

Nothing under this package may import NVDA's own modules — `ui`, `wx`,
`config`, `addonHandler` and the rest exist only inside a running screen
reader, and a module that reaches for them cannot be imported by the unit
tests at all. The import is the rule: a green test run is the proof that the
core is free of NVDA, and no separate check is needed. The section on the
core/shell boundary in docs/development.md says what falls on each side.

For the same reason the core is never told how to find anything. The
configuration directory is known to `config`, the path of a checklist to the
file dialog; what arrives here is a ready path, not a way to work one out.
"""
