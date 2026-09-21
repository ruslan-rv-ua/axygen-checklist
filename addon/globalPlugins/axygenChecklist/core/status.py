# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The status of a checklist item, on the side of it that is an identifier.

Section 2 of docs/requirements.md keeps the statuses as a single table for the
whole add-on: the word spoken on a change, the word spoken on request, the
entries of the combo box in the item dialog and the prefix in the GUI tree all
come from one place. That table crosses the boundary between the core and the
shell, and the cut runs between the identifier and the word.

The identifiers are here. They are what stands in the file, they are the same
whatever the interface language, and translating them would make a checklist
saved under a Ukrainian NVDA unreadable under an English one. The words are
interface strings wrapped in `_()` and live in the shell, still as one table.
"""

PENDING = "pending"
PASSED = "passed"
FAILED = "failed"
BLOCKED = "blocked"
SKIPPED = "skipped"

#: Every status the format allows, in the order of the command mode digits
#: (section 3.2.2: 1 passed, 2 failed, 3 blocked, 4 skipped, 5 pending). The
#: combo box of the item dialog follows the same order (section 3.3.1), so the
#: add-on has one ordering of the statuses rather than one per window.
#:
#: Position 5 belongs to `pending` because it is the "undo" slot: it is the one
#: status that is not a verdict, and auto-advance deliberately stops on it.
STATUSES: tuple[str, ...] = (PASSED, FAILED, BLOCKED, SKIPPED, PENDING)


def is_verdict(status: str) -> bool:
	"""Whether `status` records that the item has been checked.

	Every status but `pending` is a verdict. Section 4 turns on this: a verdict
	moves the position to the next visible item when auto-advance is on, while
	a return to `pending` means the tester is correcting a mistake and wants to
	stay on the item and read it again. Section 3.3 counts the same set as the
	progress of a section, and section 4 ends the checklist when nothing is
	left outside it — three behaviours, one measure.
	"""
	return status != PENDING


def toggled(value: str) -> str:
	"""The status the quick toggle gives an item that currently has `value`.

	Section 3.2.1: `passed` goes back to `pending`, and **any** other status
	becomes `passed`. The rule is total on purpose — the other three verdicts
	are reachable through the command mode and the item dialog (section 3.2),
	and a toggle that only knew two states would be undefined on them.

	Nothing here is a series. A second press is simply another toggle, which
	puts `pending` and `passed` back where they were and leaves a third state
	at `passed`; section 3.2.1 wants the most frequent key of the add-on to
	cost nothing when the hand presses it twice.
	"""
	return PENDING if value == PASSED else PASSED


def cycled(value: str) -> str:
	"""The status after `value` in the cycle Shift+Enter walks (section 5.1).

	The order is `STATUSES` itself and wraps at the end, so the five states
	come round in the order the command mode digits and the combo box of the
	item dialog already use. Deriving it from the tuple rather than writing it
	out again is the point: one dictionary of statuses means one ordering of
	them too, and a second list here would be free to drift from the first.

	`pending` stays in the cycle. Leaving it out would make a mistake made in
	the tree uncorrectable from the tree, and section 4 builds a whole rule on
	the return to it — stop after a correction.

	There is no way round backwards, and none is needed: five states wrap, so
	the longest way back is four presses, and every one of them is spoken.
	"""
	return STATUSES[(STATUSES.index(value) + 1) % len(STATUSES)]
