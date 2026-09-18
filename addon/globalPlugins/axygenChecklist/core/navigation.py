# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Where the tester is in the checklist, and how a command moves them.

Sections 3.1 and 3.4 of docs/requirements.md. Two rules shape everything here,
and both are invariants rather than preferences.

**A position is a real pair of indices into the full structure** — section and
item — and never an offset into a list of the items currently on show. Section
3.4 weighs that second model and rejects it: an item may perfectly well fail
the visibility predicate and still be where the tester is standing (a verdict
recorded with auto-advance off leaves them there), and a list of visible items
cannot express that state without renumbering itself under their feet.

**The filter is a predicate applied while scanning**, so there is one scan and
no branch anywhere on whether a filter is on. Section 3.4 reduces both presses
of the navigation keys to the same operation — walk the candidates lying one
way from a starting point and stop at the first the predicate accepts — with
only the start (the current position, or the anchor of the series) and the step
(an item, or a section) telling them apart. `scan` takes all four, and that is
the whole of navigation.

The predicate ships identically true (`visible` below): section 3.4 holds the
command back to 0.2.0 but not the model, because writing the navigation
"straight" and fitting a filter into it afterwards would mean arriving at the
rejected model first and paying to leave it.
"""

import dataclasses
import enum
from collections.abc import Callable

from .checklist import Checklist, Item, Section


@dataclasses.dataclass(frozen=True, order=True)
class Position:
	"""Where the tester is: the index of a section, and of an item within it.

	Ordered, and ordered by section first, because that is the order the file
	lists its items in and the order the tester walks them in. Comparing two
	positions is how a scan tells the candidates ahead from the ones behind.
	"""

	section: int
	item: int


class Direction(enum.Enum):
	"""Which way a command scans: towards the end of the file, or the start."""

	FORWARD = enum.auto()
	BACKWARD = enum.auto()


class Step(enum.Enum):
	"""What a command steps over: one item, or one whole section.

	The two presses of section 3.1, and the only thing that differs between
	them besides where they start.
	"""

	ITEM = enum.auto()
	SECTION = enum.auto()


#: The visibility predicate of section 3.4: whether a scan may land on an item.
#: A predicate rather than a flag read from somewhere, because the core is never
#: told where to find anything — what arrives is the item to judge, not a way to
#: work out the rules.
VisibilityPredicate = Callable[[Item], bool]


def unfiltered(item: Item) -> bool:
	"""The predicate while the filter is off: every item is one to land on.

	Identically true, and that is the whole of the filter in 0.1.0 (section
	3.4). In 0.2.0 the `F` key of the command mode supplies a second predicate
	beside this one, `item.status == "pending"`, and nothing else about
	navigation changes. It is named for the state it stands for rather than for
	the concept, so that the second one has a name left to take.
	"""
	return True


def section_at(checklist: Checklist, position: Position) -> Section:
	"""The section `position` stands in."""
	return checklist.sections[position.section]


def item_at(checklist: Checklist, position: Position) -> Item:
	"""The item `position` stands on."""
	return section_at(checklist, position).items[position.item]


def resume(checklist: Checklist, position: Position | None) -> Position | None:
	"""Where the tester stands when `checklist` is opened, or None if nowhere.

	`position` is what was remembered of this file, and None when nothing was —
	a file opened for the first time. Section 2 keeps it in `state.json`, which
	section 7.1 calls an internal cache: it holds indices, and the file they
	index into is edited by its author between sessions. So the pair may no
	longer name a place at all, and then the run starts at the first item of
	the file.

	Trimming an index to the nearest one that still exists is rejected by
	section 2: the structure those indices described is gone, and stopping
	"nearby" would fake a precision they have lost. What holds an item together
	across edits is `id`, and no behaviour of the add-on reads it.

	No visibility predicate is taken, and that is deliberate. Opening a file is
	not navigation: section 3.4 states that the item the tester stands on need
	not satisfy the predicate, whereas landing nowhere because the filter
	happened to be on would be a state nothing in the specification answers.

	None comes back only from a checklist there is genuinely nowhere to stand
	in — one whose sections are all empty, which section 2 allows.
	"""
	if position is not None and _holds(checklist, position):
		return position
	return next(iter(_positions(checklist)), None)


def _holds(checklist: Checklist, position: Position) -> bool:
	"""Whether `position` names a real place in `checklist`."""
	if not 0 <= position.section < len(checklist.sections):
		return False
	return 0 <= position.item < len(section_at(checklist, position).items)


def scan(
	checklist: Checklist,
	start: Position,
	direction: Direction,
	step: Step,
	visible: VisibilityPredicate,
) -> Position | None:
	"""Where a move from `start` lands, or None when it runs off the end.

	The one operation behind every navigation command (section 3.4). `start` is
	the current position for a single press and the anchor of the series for a
	double one (section 3.1); `step` is what the press moves over. None is the
	ordinary answer at the edge of the checklist — nothing is wrong, there is
	simply nothing that way — and the caller turns it into the signal or the
	message section 3.1 asks for, leaving the position where it was.
	"""
	candidates = (
		_sections(checklist, start, direction)
		if step is Step.SECTION
		else _items(checklist, start, direction)
	)
	for position in candidates:
		if visible(item_at(checklist, position)):
			return position
	return None


def _items(checklist: Checklist, start: Position, direction: Direction) -> list[Position]:
	"""Every position lying `direction` of `start`, in the order it is reached.

	The flat order of the file, so that a step forward from the last item of a
	section reaches the first item of the next one: section 3.1 moves to the
	next item *of the list*, and the list runs through the sections.
	"""
	positions = _positions(checklist)
	if direction is Direction.FORWARD:
		return [position for position in positions if position > start]
	return [position for position in reversed(positions) if position < start]


def _positions(checklist: Checklist) -> list[Position]:
	"""Every position of `checklist`, in the order the file lists them.

	The whole of the checklist as one flat run of places to stand — sections
	holding no items simply contribute none. Both the step of section 3.1 and
	the start of a run read it; where they differ is only which end they take.
	"""
	return [
		Position(section, item)
		for section, entry in enumerate(checklist.sections)
		for item in range(len(entry.items))
	]


def _sections(checklist: Checklist, start: Position, direction: Direction) -> list[Position]:
	"""Every position of every section lying `direction` of the one `start` is in.

	The sections run in the direction of the jump, but the items inside each
	one always run forward, and that asymmetry is the requirement rather than
	an accident: section 3.1 lands a jump on the **first** item of the
	neighbouring section, backwards as well as forwards. Offering the whole
	section rather than only its first item is what lets one predicate do the
	other half of section 3.4 — a section whose items are all filtered out
	yields nothing, so the scan carries on to the next one, and "skip sections
	with no unchecked items" needs no code of its own.
	"""
	indices = range(len(checklist.sections))
	if direction is Direction.FORWARD:
		wanted = [index for index in indices if index > start.section]
	else:
		wanted = [index for index in reversed(indices) if index < start.section]
	return [
		Position(section, item)
		for section in wanted
		for item in range(len(checklist.sections[section].items))
	]
