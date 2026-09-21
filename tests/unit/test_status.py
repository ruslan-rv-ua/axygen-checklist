# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The status dictionary, on the side of it that lives in the core.

Section 2 of `docs/requirements.md` keeps the statuses as one table for the
whole add-on. The table crosses the core/shell boundary, and the cut runs
between the identifier and the word: `"passed"` is an identifier, the same in
the file and in the code whatever the interface language, and lives here;
the word a tester hears for it is an interface string wrapped in `_()` and
lives in the shell. See the section on the core/shell boundary in
docs/development.md.
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


class TestTheQuickToggle(unittest.TestCase):
	"""Section 3.2.1: the rule behind `NVDA+Alt+Space`, and it is total."""

	def test_passed_goes_back_to_pending(self):
		self.assertEqual(status.toggled(status.PASSED), status.PENDING)

	def test_every_other_status_becomes_passed(self):
		# The rule is defined for all five states on purpose: a toggle that only
		# knew two of them would be undefined on the other three, which are
		# reachable through the command mode and the item dialog (section 3.2).
		self.assertEqual(
			{value: status.toggled(value) for value in status.STATUSES if value != status.PASSED},
			{
				status.PENDING: status.PASSED,
				status.FAILED: status.PASSED,
				status.BLOCKED: status.PASSED,
				status.SKIPPED: status.PASSED,
			},
		)

	def test_pressing_twice_puts_the_status_back(self):
		# Section 3.2.1 has no series here: a second press is simply another
		# toggle, so the most frequent key of the add-on costs nothing to press
		# again by accident.
		self.assertEqual(status.toggled(status.toggled(status.PENDING)), status.PENDING)

	def test_a_third_state_is_not_restored_by_pressing_twice(self):
		# A two-state toggle has nowhere to put `failed` back to: the first press
		# makes it `passed`, and the second carries on to `pending` rather than
		# returning. Section 4 names the honest repeat instead — a digit of the
		# command mode, which assigns a status outright however often it is used.
		self.assertEqual(status.toggled(status.toggled(status.FAILED)), status.PENDING)


class TestTheCycle(unittest.TestCase):
	"""Section 5.1: the rule behind Shift+Enter on the tree of the GUI window."""

	def test_each_status_gives_the_next_one_of_the_dictionary(self):
		self.assertEqual(
			{value: status.cycled(value) for value in status.STATUSES},
			{
				status.PASSED: status.FAILED,
				status.FAILED: status.BLOCKED,
				status.BLOCKED: status.SKIPPED,
				status.SKIPPED: status.PENDING,
				status.PENDING: status.PASSED,
			},
		)

	def test_the_cycle_wraps_at_the_end(self):
		# `pending` is last in the dictionary, so it is the one that has to come
		# round rather than run off the end.
		self.assertEqual(status.cycled(status.PENDING), status.PASSED)

	def test_five_presses_come_back_to_where_they_started(self):
		for value in status.STATUSES:
			with self.subTest(value):
				walked = value
				for _press in range(len(status.STATUSES)):
					walked = status.cycled(walked)
				self.assertEqual(walked, value)

	def test_the_cycle_is_the_dictionary_and_not_a_second_list(self):
		# The invariant section 5.1 names: one dictionary of statuses means one
		# ordering of them. Walking the cycle from the first entry has to lay the
		# tuple back out in order, so a list written out again here — or a cycle
		# that skipped `pending` — would fail rather than drift quietly.
		walked = [status.STATUSES[0]]
		while len(walked) < len(status.STATUSES):
			walked.append(status.cycled(walked[-1]))
		self.assertEqual(tuple(walked), status.STATUSES)

	def test_pending_stays_in_the_cycle(self):
		# Leaving it out would make a mistake made in the tree uncorrectable from
		# the tree, and section 4 builds "stop after a correction" on the return
		# to it.
		self.assertIn(status.PENDING, {status.cycled(value) for value in status.STATUSES})
