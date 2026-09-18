# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""How far a run has got, counted once for the three behaviours that ask.

Section 4 of `docs/requirements.md` ends the checklist when no item is still
`pending`, section 3.3 reads the progress of a section out loud, and section
3.4 filters to what is still `pending`. The specification says outright that
the three are deliberately one measure with no divergence in the code, so the
count lives in one place and every caller reads it from there.
"""

import itertools
import json
import unittest
from collections.abc import Sequence

from core import checklist, progress


def loaded(*sections: Sequence[str]) -> checklist.Checklist:
	"""A checklist whose sections hold items with the statuses given."""
	numbers = itertools.count(1)
	document = {
		"checklist_name": "Progress",
		"sections": [
			{
				"section_name": f"Section {index + 1}",
				"items": [
					{"id": next(numbers), "text": "Item", "status": value} for value in statuses
				],
			}
			for index, statuses in enumerate(sections)
		],
	}
	return checklist.loads(json.dumps(document))


class TestCounting(unittest.TestCase):
	def test_an_item_of_any_status_but_pending_counts_as_processed(self):
		# Section 3.3 refuses the word "done": with five states it would mean
		# nothing in particular, and what is being counted is what has been
		# looked at.
		document = loaded(["passed", "failed", "blocked", "skipped", "pending"])
		self.assertEqual(progress.of(document.items).processed, 4)

	def test_the_total_is_every_item_offered(self):
		document = loaded(["passed", "pending"], ["pending"])
		self.assertEqual(progress.of(document.items).total, 3)

	def test_failures_are_counted_on_their_own(self):
		# Section 3.3 and section 4 both add ", N failed", and only when there
		# are any.
		document = loaded(["failed", "failed", "blocked", "passed"])
		self.assertEqual(progress.of(document.items).failed, 2)

	def test_nothing_but_a_failure_is_counted_as_one(self):
		document = loaded(["blocked", "skipped", "pending", "passed"])
		self.assertEqual(progress.of(document.items).failed, 0)

	def test_a_section_is_counted_the_same_way_as_a_whole_checklist(self):
		# Section 3.3 asks this of one section and section 4 of the whole file;
		# what arrives is items either way.
		document = loaded(["passed", "pending"], ["failed", "failed"])
		self.assertEqual(progress.of(document.sections[1].items), progress.Progress(2, 2, 2))


class TestBeingFinished(unittest.TestCase):
	def test_a_checklist_with_nothing_pending_left_is_finished(self):
		# Section 4: the condition is "no item is still pending", not "every
		# item passed" — a checklist holding one failure is finished work.
		document = loaded(["passed", "failed"], ["skipped", "blocked"])
		self.assertTrue(progress.of(document.items).finished)

	def test_one_pending_item_anywhere_is_enough_to_be_unfinished(self):
		document = loaded(["passed", "passed"], ["passed", "pending"])
		self.assertFalse(progress.of(document.items).finished)

	def test_an_item_that_was_never_given_a_status_counts_as_pending(self):
		# A handwritten checklist has no `status` fields at all (section 2).
		document = checklist.loads(
			json.dumps(
				{
					"checklist_name": "Progress",
					"sections": [{"section_name": "One", "items": [{"id": 1, "text": "Item"}]}],
				},
			),
		)
		self.assertFalse(progress.of(document.items).finished)

	def test_nothing_to_count_leaves_nothing_pending(self):
		# A checklist of empty sections is valid (section 2), and no command
		# reaches this: they answer "the checklist has no items" first. Said out
		# loud all the same, because vacuously finished is what the condition
		# means and guessing at it later would be worse.
		document = loaded([])
		self.assertTrue(progress.of(document.items).finished)
