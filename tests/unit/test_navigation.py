# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Where the tester is in the checklist, and how a command moves them.

Sections 3.1 and 3.4 of `docs/requirements.md`. The position is a pair of
indices into the full structure, and every move is one scan: walk the
candidates that lie on one side of a starting point and stop at the first that
satisfies the visibility predicate. Single and double presses differ only in
where they start and what they step over, so this module has one scan and no
branch on the state of the filter.

The predicate is identically true in 0.1.0 and becomes `status == "pending"`
in 0.2.0 (section 3.4). The tests below pass one of their own wherever the
behaviour under test is about the predicate, because that is the whole point of
shipping the model before the command: the 0.2.0 behaviour is reachable today
by handing `scan` a different predicate, and nothing else has to change.
"""

import itertools
import json
import unittest
from collections.abc import Sequence

from core import checklist, navigation, status
from core.navigation import Direction, Position, Step

BACKWARD = Direction.BACKWARD
FORWARD = Direction.FORWARD
ITEM = Step.ITEM
SECTION = Step.SECTION


def loaded(*sections: Sequence[str]) -> checklist.Checklist:
	"""A checklist whose sections hold items with the statuses given.

	One list of statuses per section, so that the shape a test needs — how many
	sections, how long, which items a predicate will refuse — is the first
	thing on the line. The items are numbered straight through the file, and
	their text carries that number, so `item_at` can be checked against it.
	"""
	numbers = itertools.count(1)
	document = {
		"checklist_name": "Navigation",
		"sections": [
			{
				"section_name": f"Section {index + 1}",
				"items": [{"id": (number := next(numbers)), "text": f"Item {number}", "status": value}
					for value in statuses],
			}
			for index, statuses in enumerate(sections)
		],
	}
	return checklist.loads(json.dumps(document))


def pending_only(item: checklist.Item) -> bool:
	"""The predicate of the filter of section 3.4, as 0.2.0 will hand it over."""
	return item.status == status.PENDING


class TestPosition(unittest.TestCase):
	def test_a_position_is_a_pair_of_indices_into_the_full_structure(self):
		# Section 3.1: the position is never an offset into a list of visible
		# items, so that turning the filter on cannot renumber anything.
		position = Position(1, 2)
		self.assertEqual((position.section, position.item), (1, 2))

	def test_positions_run_in_the_order_the_file_lists_them(self):
		self.assertLess(Position(0, 1), Position(1, 0))
		self.assertLess(Position(0, 0), Position(0, 1))

	def test_item_at_reads_the_pair_as_indices(self):
		document = loaded(["pending", "pending"], ["pending"])
		self.assertEqual(navigation.item_at(document, Position(1, 0)).text, "Item 3")

	def test_section_at_reads_the_section_half_of_the_pair(self):
		document = loaded(["pending"], ["pending"])
		self.assertEqual(navigation.section_at(document, Position(1, 0)).name, "Section 2")


class Scanning(unittest.TestCase):
	"""Shared shorthand: a scan of `document` that always sees every item."""

	def scan(
		self,
		document: checklist.Checklist,
		start: Position,
		direction: Direction,
		step: Step,
	) -> Position | None:
		return navigation.scan(document, start, direction, step, navigation.visible)


class TestSteppingByItem(Scanning):
	def test_forward_lands_on_the_next_item(self):
		document = loaded(["pending", "pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, ITEM), Position(0, 1))

	def test_backward_lands_on_the_previous_item(self):
		document = loaded(["pending", "pending"])
		self.assertEqual(self.scan(document, Position(0, 1), BACKWARD, ITEM), Position(0, 0))

	def test_forward_crosses_into_the_next_section(self):
		# Section 3.1 moves to "the next item of the list", and the list runs
		# through the sections rather than stopping at the end of one.
		document = loaded(["pending"], ["pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, ITEM), Position(1, 0))

	def test_backward_crosses_into_the_last_item_of_the_previous_section(self):
		document = loaded(["pending", "pending"], ["pending"])
		self.assertEqual(self.scan(document, Position(1, 0), BACKWARD, ITEM), Position(0, 1))

	def test_there_is_nothing_past_the_last_item(self):
		document = loaded(["pending"], ["pending"])
		self.assertIsNone(self.scan(document, Position(1, 0), FORWARD, ITEM))

	def test_there_is_nothing_before_the_first_item(self):
		document = loaded(["pending"], ["pending"])
		self.assertIsNone(self.scan(document, Position(0, 0), BACKWARD, ITEM))

	def test_a_section_holding_no_items_is_stepped_straight_over(self):
		document = loaded(["pending"], [], ["pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, ITEM), Position(2, 0))
		self.assertEqual(self.scan(document, Position(2, 0), BACKWARD, ITEM), Position(0, 0))


class TestSteppingBySection(Scanning):
	def test_forward_lands_on_the_first_item_of_the_next_section(self):
		document = loaded(["pending", "pending"], ["pending", "pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, SECTION), Position(1, 0))

	def test_the_last_item_of_a_section_is_no_closer_to_the_next_one(self):
		# The reason section 3.1 keeps the anchor of the series: the single
		# press has already moved by the time the second press arrives, and a
		# jump measured from the item it landed on would skip a whole section.
		# Measured from either item of section 1, the answer here is the same.
		document = loaded(["pending", "pending"], ["pending"], ["pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, SECTION), Position(1, 0))
		self.assertEqual(self.scan(document, Position(0, 1), FORWARD, SECTION), Position(1, 0))

	def test_backward_lands_on_the_first_item_of_the_previous_section_not_its_last(self):
		# Section 3.1 says "the first item of the previous section", which is
		# the one place the two directions are not mirror images: stepping back
		# by an item ends at the bottom of the section, jumping back by a
		# section ends at its top.
		document = loaded(["pending", "pending"], ["pending", "pending"])
		self.assertEqual(self.scan(document, Position(1, 1), BACKWARD, SECTION), Position(0, 0))

	def test_a_jump_leaves_the_section_it_started_in(self):
		document = loaded(["pending", "pending", "pending"])
		self.assertIsNone(self.scan(document, Position(0, 1), FORWARD, SECTION))
		self.assertIsNone(self.scan(document, Position(0, 1), BACKWARD, SECTION))

	def test_there_is_nothing_past_the_last_section(self):
		document = loaded(["pending"], ["pending"])
		self.assertIsNone(self.scan(document, Position(1, 0), FORWARD, SECTION))

	def test_there_is_nothing_before_the_first_section(self):
		document = loaded(["pending"], ["pending"])
		self.assertIsNone(self.scan(document, Position(0, 0), BACKWARD, SECTION))

	def test_a_section_holding_no_items_is_jumped_straight_over(self):
		document = loaded(["pending"], [], ["pending"])
		self.assertEqual(self.scan(document, Position(0, 0), FORWARD, SECTION), Position(2, 0))
		self.assertEqual(self.scan(document, Position(2, 0), BACKWARD, SECTION), Position(0, 0))


class TestVisibility(unittest.TestCase):
	def test_every_item_is_visible_in_this_version(self):
		# Section 3.4 ships the model before the command: in 0.1.0 the
		# predicate is identically true, so nothing is ever skipped.
		document = loaded(list(status.STATUSES))
		self.assertTrue(all(navigation.visible(item) for item in document.sections[0].items))

	def test_a_step_passes_over_what_the_predicate_refuses(self):
		document = loaded(["pending", "passed", "pending"])
		found = navigation.scan(document, Position(0, 0), FORWARD, ITEM, pending_only)
		self.assertEqual(found, Position(0, 2))

	def test_a_step_that_finds_nothing_visible_reports_a_boundary(self):
		document = loaded(["pending", "passed", "failed"])
		found = navigation.scan(document, Position(0, 0), FORWARD, ITEM, pending_only)
		self.assertIsNone(found)

	def test_a_jump_lands_on_the_first_visible_item_of_the_section(self):
		document = loaded(["pending"], ["passed", "pending"])
		found = navigation.scan(document, Position(0, 0), FORWARD, SECTION, pending_only)
		self.assertEqual(found, Position(1, 1))

	def test_a_jump_skips_a_section_with_nothing_visible_in_it(self):
		# Section 3.4: with the filter on, a double press looks for the nearest
		# section holding at least one item that satisfies the predicate.
		document = loaded(["pending"], ["passed", "passed"], ["pending"])
		found = navigation.scan(document, Position(0, 0), FORWARD, SECTION, pending_only)
		self.assertEqual(found, Position(2, 0))

	def test_a_jump_backward_also_lands_on_the_first_visible_item(self):
		document = loaded(["passed", "pending", "pending"], ["pending"])
		found = navigation.scan(document, Position(1, 0), BACKWARD, SECTION, pending_only)
		self.assertEqual(found, Position(0, 1))

	def test_the_item_scanned_from_need_not_be_visible_itself(self):
		# Section 3.4 calls this a correct state rather than an error: an item
		# given a verdict with auto-advance off keeps the position, and the
		# next press moves on from there.
		document = loaded(["pending", "passed", "pending"])
		found = navigation.scan(document, Position(0, 1), FORWARD, ITEM, pending_only)
		self.assertEqual(found, Position(0, 2))
