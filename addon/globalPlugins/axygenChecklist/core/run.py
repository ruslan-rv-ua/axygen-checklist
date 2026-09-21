# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The run: what a command does to it, answered as the events that happened.

A **run** (CONTEXT.md) is the tester's passage through a checklist — from the
file being opened, or reset, to the moment nothing in it is still `pending`.
Its state is the checklist with its verdicts and the place the tester stands
on, and until a file has been opened the run has not begun. There is one run
for the whole life of the plugin: it holds the checklist or its absence, and
both forms of "nowhere to stand" are its answers.

**The rules of section 4 live here**, and nowhere else: the file is written
before anything is said; a failed write refuses the command outright; a verdict
moves the position on and a return to `pending` leaves it; the end of the list
under auto-advance is silence rather than a boundary; the status is heard
before the end of the run before the next item; a save that changed nothing
writes nothing; and the anchor of a series of presses (section 3.1). Every one
of them used to be a matter of the order of two lines in the plugin, where no
test could reach them.

**Every command answers with a list of events, in the order they happened.**
The shell turns the list into words, tones and the choice of a channel; the
core says only what took place. A list rather than a record with fields,
because the order section 4 prescribes for the voice is the order of the
events, and as the order of a list it is asserted on in the tests. Values
rather than exceptions, because a forgotten `except` in a global plugin is
silence in the middle of a session, whereas a `match` that misses an event is
an error of the type check. The core never calls the shell back: the boundary
between the two is held by the import, and a callback would be a way round it.

A failed write of the checklist is one event and nothing after it (section 4);
a save that changed nothing is an empty list, and the silence is literal. A
failed write of `state.json` is an event of its own, ahead of the landing it
belongs to, and the shell puts it in the log: section 2 keeps it out of the
voice, and the core keeps out of the log altogether — `logging` in NVDA
reaches the screen reader's own file only by a binding nobody wrote down, and
under `unittest` it would spill into stderr.

Auto-advance and whether a press is the second of a series arrive as arguments
read by the shell at the moment of the call. Section 4 keeps the first in
NVDA's own configuration, and `preferences` says why it may not be held in a
variable of the add-on's; the second is NVDA's count of a series, which section
6 lets nothing else measure. Paths arrive ready, as everywhere in the core.
"""

import dataclasses
from collections.abc import Callable
from pathlib import Path

from . import checklist, navigation, progress, session, status
from .checklist import Change, Checklist, Item, Problem, Section
from .navigation import Direction, Position, Step
from .progress import Progress
from .session import Session


@dataclasses.dataclass(frozen=True)
class Landed:
	"""The position moved to `item`, in `section`, and it is spoken (section 3.1).

	`jump` is true for the three deliberate landings, and the specification
	has the section named for each of them: a jump between sections (section
	3.1), "Move to" in the window (section 5.1) and a file just opened
	(section 3.2.2). A step to the next item, and auto-advance, land with it
	false, and the section goes unnamed.
	"""

	item: Item
	section: Section
	jump: bool


@dataclasses.dataclass(frozen=True)
class Here:
	"""Where the tester stands, asked for without moving (section 3.3)."""

	item: Item
	section: Section


@dataclasses.dataclass(frozen=True)
class Boundary:
	"""There is nothing `direction` of the tester; the position stays (section 3.1).

	`jump` tells the tone of a single press from the words of a double one.
	"""

	direction: Direction
	jump: bool


@dataclasses.dataclass(frozen=True)
class NoChecklist:
	"""No checklist has been opened, so there is nothing to work on (section 4)."""


@dataclasses.dataclass(frozen=True)
class NoItems:
	"""The checklist is open and holds no items, so there is nowhere to stand (section 4)."""


@dataclasses.dataclass(frozen=True)
class Recorded:
	"""The current item now holds `status`, on disk (sections 3.2 and 4)."""

	status: str


@dataclasses.dataclass(frozen=True)
class Saved:
	"""A save from the item dialog reached the disk, and this is what it altered (section 3.3.1)."""

	change: Change


@dataclasses.dataclass(frozen=True)
class Finished:
	"""Nothing in the checklist is still pending: the run is over (section 4)."""

	progress: Progress


@dataclasses.dataclass(frozen=True)
class SectionReset:
	"""The current section is back to pending, comments erased, on disk (section 3.2.2)."""


@dataclasses.dataclass(frozen=True)
class ChecklistReset:
	"""Every section is back to pending, comments erased, on disk (section 5)."""


@dataclasses.dataclass(frozen=True)
class WriteFailed:
	"""The checklist did not reach the disk; the command is refused (section 4).

	Always the only event of its answer: no status word, no end of the run,
	no next item. The change stays in memory, which is the divergence from the
	file of CONTEXT.md, and the next write that succeeds carries it.
	"""

	error: OSError


@dataclasses.dataclass(frozen=True)
class PlaceNotSaved:
	"""The position did not reach `state.json`; the command goes on (section 2).

	What is lost is the place, not the run, and section 2 keeps this out of
	the voice: it stands in the answer for the shell to log.
	"""

	error: OSError


@dataclasses.dataclass(frozen=True)
class SectionProgress:
	"""How far the current section has got (section 3.3)."""

	section: Section
	progress: Progress


@dataclasses.dataclass(frozen=True)
class Refused:
	"""The file would not open: it breaks the validation contract (section 2)."""

	problem: Problem


@dataclasses.dataclass(frozen=True)
class Unreadable:
	"""The file would not open: it could not be read at all (section 2)."""

	error: OSError


@dataclasses.dataclass(frozen=True)
class ChecklistGone:
	"""The file is no longer at `path` (section 2)."""

	path: Path


#: One thing a command did, or could not do. A command answers with a list of
#: these in the order they happened, and a narrator in the shell matches on
#: each; the type check holds every narrator to the whole set.
Answer = (
	Landed
	| Here
	| Boundary
	| NoChecklist
	| NoItems
	| Recorded
	| Saved
	| Finished
	| SectionReset
	| ChecklistReset
	| WriteFailed
	| PlaceNotSaved
	| SectionProgress
	| Refused
	| Unreadable
	| ChecklistGone
)

#: The three ways a file fails to open, and the whole of what `open` answers
#: when it did: exactly one of these, and nothing else in the list.
Refusal = Refused | Unreadable | ChecklistGone


@dataclasses.dataclass(frozen=True)
class _Standing:
	"""The checklist and the place in it a command works on, once both are there."""

	checklist: Checklist
	position: Position

	@property
	def item(self) -> Item:
		return navigation.item_at(self.checklist, self.position)

	@property
	def section(self) -> Section:
		return navigation.section_at(self.checklist, self.position)


class Run:
	"""One run, for the whole life of the plugin.

	`state` is where the position is kept across restarts of NVDA (section 2);
	the path arrives ready, because the core is never told how to find
	anything. Nothing is opened here: `restore` picks up what `state.json`
	remembers, and `open` takes the file the tester picked.
	"""

	def __init__(self, state: Path) -> None:
		super().__init__()
		self._state = state
		#: The checklist the commands work on, or None while none is open.
		self._checklist: Checklist | None = None
		#: Where the tester is, and None when there is nowhere to stand: no
		#: checklist, or one whose sections are all empty, which section 2
		#: allows.
		self._position: Position | None = None
		#: Where the current series of presses started (section 3.1). Scratch
		#: for the length of one series, and read only on a press that has a
		#: press of its own before it.
		self._anchor = Position(0, 0)

	@property
	def checklist(self) -> Checklist | None:
		"""The checklist the run is through, or None before one has been opened.

		For the window of section 5, which builds its tree from it. Nothing
		about the run is changed through it: the commands are how that happens.
		"""
		return self._checklist

	@property
	def position(self) -> Position | None:
		"""Where the tester stands, or None when there is nowhere to stand."""
		return self._position

	def here(self) -> list[Answer]:
		"""Where the tester stands, without moving (section 3.3)."""
		standing = self._standing()
		if not isinstance(standing, _Standing):
			return [standing]
		return [Here(standing.item, standing.section)]

	def navigate(self, direction: Direction, jump: bool) -> list[Answer]:
		"""Move one item, or — on the second press of the series — one section.

		Both presses are the same scan of section 3.4, differing only in where
		they start and what they step over, so there is one path through here
		and no branch anywhere on the state of the filter.

		`jump` is whether this press has a press of its own before it, which
		the shell reads off NVDA's count of the series (section 6). The first
		press of a series sets the anchor; the second scans from it rather than
		from where the first already landed, or a jump from the last item of a
		section would skip a whole section (section 3.1). A third press and
		beyond is left doing what the second did: it scans from the same
		anchor to the same place and answers it again. Section 6 has the
		add-on go no deeper than two levels and defines no behaviour for a
		third, and repeating the answer invents none.

		At the edge the position stays exactly where it is, which after a
		failed jump is wherever the first press of the series already took it
		(section 3.1): putting it back would mean undoing a press that had run.
		"""
		standing = self._standing()
		if not isinstance(standing, _Standing):
			return [standing]
		if not jump:
			self._anchor = standing.position
		start, step = (self._anchor, Step.SECTION) if jump else (standing.position, Step.ITEM)
		found = navigation.scan(standing.checklist, start, direction, step, navigation.unfiltered)
		if found is None:
			return [Boundary(direction, jump)]
		return self._land(standing.checklist, found, jump)

	def toggle(self, advance: bool) -> list[Answer]:
		"""Give the current item the status the quick toggle makes of the one it holds.

		Section 3.2.1: the total rule of `status.toggled`, read off what it is
		replacing. `advance` is auto-advance as the shell read it at the
		moment of the press (section 4); everything that follows the write is
		`_record`'s, and the same for the digits of the command mode.
		"""
		return self._record(status.toggled, advance)

	def assign(self, status_value: str, advance: bool) -> list[Answer]:
		"""Give the current item the status `status_value` outright.

		A digit of the command mode (section 3.2.2), and the honest repeat of
		section 4: nothing here asks whether the item holds that status
		already — the write and the word happen either way.
		"""
		return self._record(lambda _current: status_value, advance)

	def _record(self, value_of: Callable[[str], str], advance: bool) -> list[Answer]:
		"""Give the current item the status `value_of` makes of the one it holds.

		The two ways a status is assigned without opening a window meet here
		and differ only in the rule. Everything after the rule is section 4,
		in the order it prescribes: the file first, and a write that did not
		get there is the whole answer; then the word for the status; then the
		end of the run, if this closed the last pending item; then the next
		item, when a **verdict** was recorded and auto-advance is on.

		**A verdict moves, a return to `pending` stays**, and `status.is_verdict`
		is the one place the two are told apart: the digit `5` and a space bar
		pressed on a `passed` item both mean the tester is fixing something.
		A write that failed stays too, because the tester will press on this
		item again — stop after a refusal, the third case of the same rule.

		**Nothing at the end of the checklist**: the scan is the one a single
		press of the navigation key makes, and where it finds nothing the
		position simply stays, without the boundary of section 3.1 — the
		tester gave no navigation command, and a signal would be reporting a
		failure that did not happen.
		"""
		standing = self._standing()
		if not isinstance(standing, _Standing):
			return [standing]
		item = standing.item
		value = value_of(item.status)
		try:
			item.record_status(value)
		except OSError as error:
			return [WriteFailed(error)]
		answer: list[Answer] = [Recorded(value)]
		answer.extend(self._completion(standing.checklist))
		if not advance or not status.is_verdict(value):
			return answer
		found = navigation.scan(
			standing.checklist,
			standing.position,
			Direction.FORWARD,
			Step.ITEM,
			navigation.unfiltered,
		)
		if found is not None:
			answer.extend(self._land(standing.checklist, found, jump=False))
		return answer

	def save(self, item: Item, status_value: str, comment: str) -> list[Answer]:
		"""Write what the item dialog was closed on, and answer with what moved.

		Section 3.3.1. The dialog collected a status and a comment and decided
		nothing about them; what they amount to is one comparison, made before
		anything is written because all three answers hang on it — whether to
		write at all, what moved, and whether a status has just closed the
		last pending item of the run.

		**A save that moved neither field is a save that does nothing**: no
		file, no event, the same silence as Cancel. Writing anyway would buy
		exactly one thing — the chance of a failed write for a command that
		changed nothing. Both fields reach the disk in one rewrite, which is
		`Item.record`'s doing.

		**No auto-advance** (section 4), and no argument for it: the dialog is
		a deliberate stop on one item, and moving the position behind a
		closing window would leave the next command describing another item.
		The end of the run is the opposite case and is answered — but only
		when the **status** moved, because a comment added to a checklist that
		had nothing pending closed nothing.

		`item` came out of `here` or out of the tree of the window, both built
		from the checklist in hand, which is what makes the answer for a run
		with no checklist unreachable rather than a refusal of its own.
		"""
		loaded = self._checklist
		if loaded is None:
			return [NoChecklist()]
		change = Change.of(item, status_value, comment)
		if not change.anything:
			return []
		try:
			item.record(status_value, comment)
		except OSError as error:
			return [WriteFailed(error)]
		answer: list[Answer] = [Saved(change)]
		if change.status is not None:
			answer.extend(self._completion(loaded))
		return answer

	def cycle(self, item: Item) -> list[Answer]:
		"""Give `item` the next status of the cycle (section 5.1).

		The fourth way a status is set, and a rule for what comes next rather
		than a place where `status` is written: the cycle is `status.cycled`,
		the write is the item's, and the end of the run is asked for as after
		every other verdict. No auto-advance, for the reason `save` has none:
		the window is a deliberate stop, and what the tree has selected is not
		where the run stands.
		"""
		loaded = self._checklist
		if loaded is None:
			return [NoChecklist()]
		value = status.cycled(item.status)
		try:
			item.record_status(value)
		except OSError as error:
			return [WriteFailed(error)]
		return [Recorded(value), *self._completion(loaded)]

	def reset_section(self) -> list[Answer]:
		"""Put every item of the current section back to pending, erase its comments (section 3.2.2).

		The `R` key of the command mode, once the tester has answered Yes.
		The section is the one the position stands in **now**, which is the
		one they asked about: every command is blocked while the confirmation
		stands (section 3.3.1), so nothing can have moved it in between. One
		write for the whole section, and no end of the run — every item in it
		is pending now.
		"""
		standing = self._standing()
		if not isinstance(standing, _Standing):
			return [standing]
		try:
			standing.section.reset()
		except OSError as error:
			return [WriteFailed(error)]
		return [SectionReset()]

	def reset(self) -> list[Answer]:
		"""Put every item of the checklist back to pending and erase every comment (section 5).

		"Reset all progress" in the window, and the twin of `reset_section`
		with one difference — how much it takes in. A reset moves nobody: the
		position stays where it stood.
		"""
		loaded = self._checklist
		if loaded is None:
			return [NoChecklist()]
		try:
			loaded.reset()
		except OSError as error:
			return [WriteFailed(error)]
		return [ChecklistReset()]

	def move_to(self, position: Position) -> list[Answer]:
		"""Stand on `position`, which the window was asked to move to (section 5.1).

		An ordinary move once it gets here — the position reaches `state.json`
		and the landing is answered — and a jump: the most deliberate kind,
		named for the same reason a double press and a file just opened are.
		`position` names a node of a tree built from the checklist in hand.
		"""
		loaded = self._checklist
		if loaded is None:
			return [NoChecklist()]
		return self._land(loaded, position, jump=True)

	def progress(self) -> list[Answer]:
		"""Which section the tester is in and how far it has got (section 3.3).

		Counted over the **whole** section however the filter is set (section
		3.4). Nothing moves and nothing is written.
		"""
		standing = self._standing()
		if not isinstance(standing, _Standing):
			return [standing]
		section = standing.section
		return [SectionProgress(section, progress.of(section.items))]

	def _completion(self, loaded: Checklist) -> list[Answer]:
		"""The end of the run, when nothing in `loaded` is still pending (section 4).

		Asked after every write that gave an item a status, whichever way it
		was given, and the measure is the one `core.progress` counts by
		everywhere: nothing still `pending`, rather than everything passed. A
		checklist holding one failure is finished work.
		"""
		counted = progress.of(loaded.items)
		return [Finished(counted)] if counted.finished else []

	def _land(self, loaded: Checklist, found: Position, jump: bool) -> list[Answer]:
		"""Stand on `found`, put that on disk, and answer with what is there.

		What every move of the position does, whoever made it: the navigation
		keys (section 3.1), auto-advance (section 4) and "Move to" in the
		window (section 5.1) all end here. The position reaches `state.json`
		**before** the landing is answered (sections 2 and 4), which is the
		order every change of data is held to, and a write that did not get
		there stands in the answer ahead of the landing.

		Opening a checklist does not come through here, and that is not an
		oversight: it moves the path as well as the position (section 3.2.2).
		"""
		self._position = found
		answer = self._remember()
		answer.append(Landed(navigation.item_at(loaded, found), navigation.section_at(loaded, found), jump))
		return answer

	def open(self, path: Path) -> list[Answer]:
		"""Open the checklist at `path` and stand in it (section 3.2.2).

		The one operation behind the `O` key and `Browse...` in the window,
		differing only in where the path came from. Where the tester lands is
		settled by `state.json`, read here: the same file reopened lands where
		they stopped, another starts at its first item, and a remembered pair
		that no longer names a place is `navigation.resume`'s to answer.

		A file that opened is a change of position and is written to
		`state.json` at once, as after any other (section 2); a failed write
		of that is in the answer, ahead of the landing. A file that would not
		open leaves everything as it was, the checklist in hand and the path
		in `state.json` included — that path is where the file dialog starts
		browsing, wanted exactly now — and answers with the one refusal.
		"""
		remembered = session.load(self._state)
		loaded = self._read(path)
		if not isinstance(loaded, Checklist):
			return [loaded]
		self._adopt(loaded, remembered.position_in(path))
		answer: list[Answer] = self._remember()
		standing = self._standing()
		if not isinstance(standing, _Standing):
			answer.append(standing)
		else:
			answer.append(Landed(standing.item, standing.section, jump=True))
		return answer

	def restore(self) -> list[Answer]:
		"""Pick the run up where the last one left it (section 2).

		The path and the pair of indices come out of `state.json`, and a
		restart of NVDA lands the tester back on the item they stopped on.
		Nothing is answered when that works — no command was given — and
		nothing when nothing was remembered; what comes back is the one
		refusal a failure has earned, for the shell to say once NVDA can be
		heard.

		**Nothing is written back**, whether this went well or badly. A
		restore reads the position rather than changing it; a failure has all
		the more reason to leave the file alone, since the path in it is where
		the file dialog starts browsing and that is wanted precisely when the
		file it names has gone. Even a position the file has outgrown is left
		standing: the next move writes the real one, and until then a
		checklist broken only for the moment can still give the tester their
		place back.
		"""
		remembered = session.load(self._state)
		if remembered.checklist is None:
			return []
		loaded = self._read(remembered.checklist)
		if not isinstance(loaded, Checklist):
			return [loaded]
		self._adopt(loaded, remembered.position)
		return []

	def remembered(self) -> Path | None:
		"""Where the file dialog starts browsing: the folder of the last path remembered.

		Read off the disk rather than off the checklist in hand (section
		3.2.2): the two agree while one is open, and the moment they do not is
		exactly the moment this is wanted — start-up found the file gone, so
		there is no checklist and the only thing left pointing anywhere is
		that path. None when nothing has ever been opened, which leaves the
		choice of folder to Windows.
		"""
		path = session.load(self._state).checklist
		return None if path is None else path.parent

	def _read(self, path: Path) -> Checklist | Refusal:
		"""The checklist at `path`, or the one reason it would not open."""
		try:
			return checklist.load(path)
		except FileNotFoundError:
			return ChecklistGone(path)
		except OSError as error:
			return Unreadable(error)
		except checklist.ChecklistError as refusal:
			return Refused(refusal.problem)

	def _adopt(self, loaded: Checklist, remembered: Position | None) -> None:
		"""Make `loaded` the checklist every command works on, standing where it was left."""
		self._checklist = loaded
		self._position = navigation.resume(loaded, remembered)

	def _remember(self) -> list[Answer]:
		"""Put the position on disk, now (section 2), and say so only if it did not get there.

		Every change of the position comes through here, and there is no
		other moment at which `state.json` is brought up to date. Nothing is
		written before a checklist has been opened: no file, nothing to
		remember.
		"""
		if self._checklist is None:
			return []
		try:
			session.save(self._state, Session(self._checklist.path, self._position))
		except OSError as error:
			return [PlaceNotSaved(error)]
		return []

	def _standing(self) -> _Standing | NoChecklist | NoItems:
		"""What a command works on, or which of the two reasons there is nothing.

		Every command that needs an item to stand on begins here, because
		neither half is promised: no checklist has been opened until
		`state.json` or the file dialog puts one here, and a checklist whose
		sections are all empty is valid and has nowhere to stand in (section
		2). The two are told apart here and nowhere else (section 4).
		"""
		if self._checklist is None:
			return NoChecklist()
		if self._position is None:
			return NoItems()
		return _Standing(self._checklist, self._position)
