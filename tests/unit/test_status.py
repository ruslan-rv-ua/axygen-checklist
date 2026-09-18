# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The status dictionary, on the side of it that lives in the core.

Section 2 of `docs/requirements.md` keeps the statuses as one table for the
whole add-on. The table crosses the core/shell boundary, and the cut runs
between the identifier and the word: `"passed"` is an identifier, the same in
the file and in the code whatever the interface language, and lives here;
"passed"/"пройдено" is an interface string wrapped in `_()` and lives in the
shell. See "Межа ядра й оболонки" in docs/development.md.
"""

import unittest

from core import status


class TestIdentifiers(unittest.TestCase):
	def test_the_five_statuses_of_the_format(self):
		# Spelled out rather than derived from the module, so that renaming an
		# identifier in the code cannot quietly rename it in the file format.
		self.assertEqual(
			{status.PENDING, status.PASSED, status.FAILED, status.BLOCKED, status.SKIPPED},
			{"pending", "passed", "failed", "blocked", "skipped"},
		)

	def test_statuses_are_ordered_as_the_command_mode_digits(self):
		# Section 3.2.2: 1 passed, 2 failed, 3 blocked, 4 skipped, 5 pending.
		# The item dialog's combo box takes the same order (section 3.3.1), so
		# there is one ordering in the add-on rather than one per window.
		self.assertEqual(status.STATUSES, ("passed", "failed", "blocked", "skipped", "pending"))


class TestVerdicts(unittest.TestCase):
	def test_every_status_but_pending_is_a_verdict(self):
		# Section 4: auto-advance follows a verdict and stops after a return to
		# `pending`, which is the "undo" slot.
		self.assertEqual(
			[value for value in status.STATUSES if status.is_verdict(value)],
			["passed", "failed", "blocked", "skipped"],
		)

	def test_pending_is_not_a_verdict(self):
		self.assertFalse(status.is_verdict(status.PENDING))
