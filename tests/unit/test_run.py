# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The run: the rules of section 4, asked through the commands of `core.run`.

Section 4 of `docs/requirements.md` is written as an order of things heard —
the file before the word, the status before the end of the run before the
next item, one phrase after a failed write and nothing after it — and until
now those rules lived in the plugin, where no test could reach them. `Run`
answers every command with a list of events in the order they happened, and
that order is what every test here asserts on.

Nothing here reads the wording of anything: an event names what happened, and
what is said about it is the shell's. `tests/unit/test_checklist.py` keeps
testing the primitives underneath; the rules that compose them into behaviour
are tested here, and only through the commands.
"""

import itertools
import json
import unittest
from collections.abc import Callable, Sequence
from pathlib import Path
from unittest import mock

from core import navigation, session
from core.checklist import Change, CommentChange, Item, ProblemKind
from core.navigation import Direction, Position
from core.progress import Progress
from core.run import (
	Answer,
	Boundary,
	ChecklistGone,
	ChecklistReset,
	Finished,
	Here,
	Landed,
	NoChecklist,
	NoItems,
	PlaceNotSaved,
	Recorded,
	Refused,
	Run,
	Saved,
	SectionProgress,
	SectionReset,
	Unreadable,
	WriteFailed,
)
from core.session import Session

from .support import temporary_directory

FORWARD = Direction.FORWARD
BACKWARD = Direction.BACKWARD


def _item(number: int, value: str) -> dict[str, object]:
	"""One item, numbered straight through the file and saying so in its text."""
	return {"id": number, "text": f"Item {number}", "status": value}


class RunOnDisk(unittest.TestCase):
	"""A run with a state file and checklist files in a directory of its own.

	Every command that changes anything writes a file, so every test here goes
	through real files and reads them back; the directory is made and swept
	away in one place.
	"""

	def setUp(self) -> None:
		super().setUp()
		self.directory = temporary_directory(self)
		# The add-on's own folder inside the configuration directory, not there
		# until the first checklist is opened (section 2).
		self.state = self.directory / "axygenChecklist" / "state.json"

	def new_run(self) -> Run:
		return Run(self.state)

	def checklist_file(self, *sections: Sequence[str], name: str = "checklist.json") -> Path:
		"""A checklist file whose sections hold items with the statuses given.

		One list of statuses per section, so that the shape a test needs is the
		first thing on the line. The items are numbered straight through the
		file.
		"""
		numbers = itertools.count(1)
		document = {
			"checklist_name": "Run",
			"sections": [
				{
					"section_name": f"Section {index + 1}",
					"items": [_item(next(numbers), value) for value in statuses],
				}
				for index, statuses in enumerate(sections)
			],
		}
		path = self.directory / name
		path.write_text(json.dumps(document), encoding="utf-8")
		return path

	def opened(self, *sections: Sequence[str]) -> Run:
		"""A run standing on the first item of a checklist with these sections."""
		run = self.new_run()
		answer = run.open(self.checklist_file(*sections))
		assert answer == [self.landed(run, 0, 0, jump=True)], answer
		return run

	def landed(self, run: Run, section: int, item: int, jump: bool) -> Landed:
		"""The landing on `item` of `section` a command of `run` answers with."""
		assert run.checklist is not None
		position = Position(section, item)
		return Landed(
			navigation.item_at(run.checklist, position),
			navigation.section_at(run.checklist, position),
			jump,
		)

	def statuses_on_disk(self, run: Run) -> list[str]:
		"""The status of every item, as the file of `run` says it right now."""
		assert run.checklist is not None
		assert run.checklist.path is not None
		document = json.loads(run.checklist.path.read_text(encoding="utf-8"))
		return [item["status"] for section in document["sections"] for item in section["items"]]


class TestOpening(RunOnDisk):
	"""Section 3.2.2: opening a file lands the tester in it, and says where."""

	def test_a_file_opened_for_the_first_time_starts_at_its_first_item(self):
		run = self.new_run()
		path = self.checklist_file(["pending", "pending"], ["pending"])
		# A jump, and the most deliberate one there is: the section is named.
		self.assertEqual(run.open(path), [self.landed(run, 0, 0, jump=True)])
		self.assertEqual(run.position, Position(0, 0))

	def test_opening_puts_the_path_and_the_position_on_disk(self):
		run = self.new_run()
		path = self.checklist_file(["pending"])
		run.open(path)
		self.assertEqual(session.load(self.state), Session(path, Position(0, 0)))


class TestNowhereToStand(RunOnDisk):
	"""Section 4: the two answers to a command that finds nothing to work on.

	They are not the same answer. One means no file has been opened; the other
	means the file that was opened holds no items — a valid file (section 2),
	and calling it "not loaded" would be a lie about the one thing the tester
	can check.
	"""

	def test_before_any_checklist_has_been_opened(self):
		self.assertEqual(self.new_run().here(), [NoChecklist()])

	def test_a_checklist_whose_sections_are_all_empty(self):
		run = self.new_run()
		self.assertEqual(run.open(self.checklist_file([], [])), [NoItems()])
		self.assertEqual(run.here(), [NoItems()])
		self.assertIsNotNone(run.checklist)
		self.assertIsNone(run.position)


class TestAskingWhereTheTesterStands(RunOnDisk):
	"""Section 3.3: the item is said again, and nothing moves or is written."""

	def test_the_item_and_its_section_come_back_without_a_move(self):
		run = self.opened(["pending"], ["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		assert run.checklist is not None
		section = run.checklist.sections[1]
		with mock.patch("core.disk.write") as written:
			self.assertEqual(run.here(), [Here(section.items[0], section)])
		written.assert_not_called()
		self.assertEqual(run.position, Position(1, 0))


class TestNavigating(RunOnDisk):
	"""Section 3.1: a single press steps by an item, a double press jumps by a section."""

	def test_a_single_press_lands_on_the_next_item_without_naming_the_section(self):
		run = self.opened(["pending", "pending"])
		self.assertEqual(run.navigate(FORWARD, jump=False), [self.landed(run, 0, 1, jump=False)])
		self.assertEqual(run.position, Position(0, 1))

	def test_a_landing_reaches_the_state_file_before_it_is_spoken(self):
		# Section 2 writes the position on navigation, not only where a status
		# is written beside it; the landing is the last event, after the write.
		run = self.opened(["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		self.assertEqual(session.load(self.state).position, Position(0, 1))

	def test_a_single_press_at_the_edge_is_a_boundary_and_moves_nobody(self):
		run = self.opened(["pending"])
		self.assertEqual(run.navigate(FORWARD, jump=False), [Boundary(FORWARD, jump=False)])
		self.assertEqual(run.navigate(BACKWARD, jump=False), [Boundary(BACKWARD, jump=False)])
		self.assertEqual(run.position, Position(0, 0))

	def test_a_double_press_lands_on_the_first_item_of_the_next_section_and_names_it(self):
		run = self.opened(["pending", "pending"], ["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		self.assertEqual(run.navigate(FORWARD, jump=True), [self.landed(run, 1, 0, jump=True)])

	def test_a_double_press_at_the_edge_is_a_boundary_with_words(self):
		run = self.opened(["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		self.assertEqual(run.navigate(FORWARD, jump=True), [Boundary(FORWARD, jump=True)])
		# Section 3.1: a failed jump leaves the tester where the first press of
		# the series already took them.
		self.assertEqual(run.position, Position(0, 1))

	def test_a_command_before_any_checklist_says_so(self):
		self.assertEqual(self.new_run().navigate(FORWARD, jump=False), [NoChecklist()])


class TestTheAnchorOfASeries(RunOnDisk):
	"""Section 3.1: the second press scans from where the series started.

	The single press has already moved by the time the second arrives, so a
	jump measured from the item it landed on would skip a whole section. The
	third press and beyond repeat the second: section 6 defines no behaviour
	for a third level, and repeating the answer invents none.
	"""

	def test_the_second_press_jumps_from_where_the_first_started(self):
		# From the last item of section 1 the single press lands in section 2;
		# a jump from there would reach section 3, and the anchor keeps it in 2.
		run = self.opened(["pending", "pending"], ["pending"], ["pending"])
		run.navigate(FORWARD, jump=False)
		run.navigate(FORWARD, jump=False)
		self.assertEqual(run.position, Position(1, 0))
		self.assertEqual(run.navigate(FORWARD, jump=True), [self.landed(run, 1, 0, jump=True)])

	def test_the_third_press_repeats_the_second(self):
		run = self.opened(["pending"], ["pending"], ["pending"])
		run.navigate(FORWARD, jump=False)
		self.assertEqual(run.navigate(FORWARD, jump=True), [self.landed(run, 1, 0, jump=True)])
		self.assertEqual(run.navigate(FORWARD, jump=True), [self.landed(run, 1, 0, jump=True)])
		self.assertEqual(run.position, Position(1, 0))

	def test_a_jump_backward_is_measured_from_the_anchor_too(self):
		run = self.opened(["pending"], ["pending"], ["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		run.navigate(FORWARD, jump=False)
		run.navigate(FORWARD, jump=False)
		# Standing on the last item of section 3, the single press goes to its
		# first item and the jump from that anchor reaches section 2.
		run.navigate(BACKWARD, jump=False)
		self.assertEqual(run.navigate(BACKWARD, jump=True), [self.landed(run, 1, 0, jump=True)])


class TestRecordingAStatus(RunOnDisk):
	"""Sections 3.2 and 4: the quick toggle and the digits, and what follows a verdict."""

	def test_the_toggle_records_passed_and_says_so(self):
		run = self.opened(["pending"], ["pending"])
		self.assertEqual(run.toggle(advance=False), [Recorded("passed")])
		self.assertEqual(self.statuses_on_disk(run), ["passed", "pending"])

	def test_a_digit_assigns_the_status_outright_and_repeats_honestly(self):
		# Section 4: the digit is the honest repeat, and may be pressed as often
		# as the tester likes — the write and the word happen either way.
		run = self.opened(["pending"], ["pending"])
		self.assertEqual(run.assign("failed", advance=False), [Recorded("failed")])
		self.assertEqual(run.assign("failed", advance=False), [Recorded("failed")])
		self.assertEqual(self.statuses_on_disk(run), ["failed", "pending"])

	def test_a_verdict_moves_on_to_the_next_item_when_auto_advance_is_on(self):
		run = self.opened(["pending", "pending"])
		self.assertEqual(
			run.toggle(advance=True),
			[Recorded("passed"), self.landed(run, 0, 1, jump=False)],
		)
		self.assertEqual(run.position, Position(0, 1))

	def test_a_verdict_stays_put_when_auto_advance_is_off(self):
		run = self.opened(["pending", "pending"])
		self.assertEqual(run.toggle(advance=False), [Recorded("passed")])
		self.assertEqual(run.position, Position(0, 0))

	def test_a_return_to_pending_stays_put_even_with_auto_advance_on(self):
		# Section 4: move on after a verdict, stop after a correction. The
		# tester is fixing something and wants to read the item again.
		run = self.opened(["passed", "pending"])
		self.assertEqual(run.toggle(advance=True), [Recorded("pending")])
		self.assertEqual(run.assign("pending", advance=True), [Recorded("pending")])
		self.assertEqual(run.position, Position(0, 0))

	def test_auto_advance_at_the_end_of_the_list_is_silence_not_a_boundary(self):
		# Section 4: the tester gave no navigation command, so a boundary would
		# report a failure that did not happen. Nothing follows the word.
		run = self.opened(["passed", "pending"])
		run.navigate(FORWARD, jump=False)
		self.assertEqual(
			run.assign("skipped", advance=True),
			[Recorded("skipped"), Finished(Progress(total=2, processed=2, failed=0))],
		)
		self.assertEqual(run.position, Position(0, 1))

	def test_the_status_is_heard_before_the_end_of_the_run_before_the_next_item(self):
		# Section 4: the last pending item closed in the middle of the file, with
		# a next item to move to. The order is the order of the list.
		run = self.opened(["pending", "failed"])
		self.assertEqual(
			run.assign("blocked", advance=True),
			[
				Recorded("blocked"),
				Finished(Progress(total=2, processed=2, failed=1)),
				self.landed(run, 0, 1, jump=False),
			],
		)

	def test_the_end_of_the_run_is_announced_whatever_auto_advance_is_set_to(self):
		run = self.opened(["pending"])
		self.assertEqual(
			run.toggle(advance=False),
			[Recorded("passed"), Finished(Progress(total=1, processed=1, failed=0))],
		)

	def test_nothing_is_recorded_before_a_checklist_is_open(self):
		self.assertEqual(self.new_run().toggle(advance=True), [NoChecklist()])
		self.assertEqual(self.new_run().assign("passed", advance=True), [NoChecklist()])


class TestAWriteThatFails(RunOnDisk):
	"""Section 4: a write that did not reach the disk refuses the command.

	One event and nothing after it: no status word, no end of the run, no next
	item. The position stays, because the tester will press on this item
	again; the change stays in memory, because rolling it back is the
	mechanism section 3.2.1 was glad to be rid of.
	"""

	def refused(self, command: Callable[[], list[Answer]]) -> list[Answer]:
		"""What `command` answers while nothing can be swapped into place on disk."""
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			return command()

	def test_a_failed_write_is_the_only_event_and_moves_nobody(self):
		# The item is the last pending one and has a next item: a successful
		# write would have answered with all three events.
		run = self.opened(["pending", "failed"])
		answer = self.refused(lambda: run.toggle(advance=True))
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], WriteFailed)
		self.assertEqual(run.position, Position(0, 0))
		self.assertEqual(self.statuses_on_disk(run), ["pending", "failed"])

	def test_the_change_stays_in_memory(self):
		run = self.opened(["pending"])
		self.refused(lambda: run.toggle(advance=False))
		assert run.checklist is not None
		self.assertEqual(run.checklist.items[0].status, "passed")

	def test_the_next_write_that_succeeds_carries_the_earlier_verdict(self):
		# The divergence from the file (CONTEXT.md), end to end: after a refused
		# write the disk is behind, and the first write that gets there takes
		# everything that piled up with it — the earlier verdict included.
		run = self.opened(["pending", "pending"])
		self.refused(lambda: run.assign("failed", advance=False))
		run.navigate(FORWARD, jump=False)
		# The end of the run counts the earlier verdict too: it is on the disk
		# now, and the answer says so.
		self.assertEqual(
			run.toggle(advance=False),
			[Recorded("passed"), Finished(Progress(total=2, processed=2, failed=1))],
		)
		self.assertEqual(self.statuses_on_disk(run), ["failed", "passed"])


class TestSavingFromTheItemDialog(RunOnDisk):
	"""Section 3.3.1: one save, one write, and only what really moved is answered."""

	def item(self, run: Run, section: int = 0, index: int = 0) -> Item:
		assert run.checklist is not None
		return run.checklist.sections[section].items[index]

	def test_a_save_answers_with_what_it_altered(self):
		run = self.opened(["pending", "pending"])
		answer = run.save(self.item(run), "failed", "Phone has no label")
		self.assertEqual(answer, [Saved(Change(status="failed", comment=CommentChange.SAVED))])
		self.assertEqual(self.statuses_on_disk(run), ["failed", "pending"])

	def test_a_save_that_changed_nothing_writes_nothing_and_answers_nothing(self):
		# Section 3.3.1: Save doing what Cancel does. The silence is literal,
		# and the file is not touched — not even to be rewritten the same.
		run = self.opened(["passed"])
		with mock.patch("core.disk.write") as written:
			self.assertEqual(run.save(self.item(run), "passed", "   "), [])
		written.assert_not_called()

	def test_a_save_does_not_move_the_position_whatever_auto_advance_says(self):
		# Section 4: the dialog is a deliberate stop on one item, so there is
		# no auto-advance to ask about, and `save` takes no such argument.
		run = self.opened(["pending", "pending"])
		run.save(self.item(run), "passed", "")
		self.assertEqual(run.position, Position(0, 0))

	def test_a_status_that_closed_the_last_pending_item_ends_the_run(self):
		run = self.opened(["pending", "passed"])
		answer = run.save(self.item(run), "skipped", "")
		self.assertEqual(
			answer,
			[
				Saved(Change(status="skipped", comment=CommentChange.UNCHANGED)),
				Finished(Progress(total=2, processed=2, failed=0)),
			],
		)

	def test_a_comment_alone_ends_nothing(self):
		# Section 3.3.1: a comment added to a checklist that had nothing pending
		# closed nothing, so the end of the run is not news.
		run = self.opened(["passed", "passed"])
		answer = run.save(self.item(run), "passed", "Slow, but it works")
		self.assertEqual(answer, [Saved(Change(status=None, comment=CommentChange.SAVED))])

	def test_a_failed_write_refuses_the_save(self):
		run = self.opened(["pending"])
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			answer = run.save(self.item(run), "passed", "")
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], WriteFailed)
		self.assertEqual(self.statuses_on_disk(run), ["pending"])


class TestCyclingFromTheTree(RunOnDisk):
	"""Section 5.1: the next status of the cycle, written, and no move."""

	def test_the_item_gets_the_next_status_of_the_dictionary(self):
		run = self.opened(["skipped", "pending"])
		assert run.checklist is not None
		item = run.checklist.sections[0].items[0]
		self.assertEqual(run.cycle(item), [Recorded("pending")])
		self.assertEqual(run.cycle(item), [Recorded("passed")])
		self.assertEqual(self.statuses_on_disk(run), ["passed", "pending"])
		self.assertEqual(run.position, Position(0, 0))

	def test_the_end_of_the_run_is_answered_from_the_tree_too(self):
		run = self.opened(["pending"])
		assert run.checklist is not None
		self.assertEqual(
			run.cycle(run.checklist.sections[0].items[0]),
			[Recorded("passed"), Finished(Progress(total=1, processed=1, failed=0))],
		)

	def test_a_failed_write_refuses_the_cycle(self):
		run = self.opened(["pending"])
		assert run.checklist is not None
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			answer = run.cycle(run.checklist.sections[0].items[0])
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], WriteFailed)


class TestResetting(RunOnDisk):
	"""Sections 3.2.2 and 5: a reset writes once and says so once, or refuses."""

	def test_resetting_the_section_puts_its_items_back_and_leaves_the_rest(self):
		run = self.opened(["passed", "failed"], ["passed"])
		self.assertEqual(run.reset_section(), [SectionReset()])
		self.assertEqual(self.statuses_on_disk(run), ["pending", "pending", "passed"])
		self.assertEqual(run.position, Position(0, 0))

	def test_resetting_the_checklist_puts_every_item_back(self):
		run = self.opened(["passed", "failed"], ["passed"])
		self.assertEqual(run.reset(), [ChecklistReset()])
		self.assertEqual(self.statuses_on_disk(run), ["pending", "pending", "pending"])

	def test_a_failed_write_refuses_either_reset(self):
		run = self.opened(["passed"])
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			for answer in (run.reset_section(), run.reset()):
				self.assertEqual(len(answer), 1)
				self.assertIsInstance(answer[0], WriteFailed)
		self.assertEqual(self.statuses_on_disk(run), ["passed"])

	def test_nothing_is_reset_before_a_checklist_is_open(self):
		self.assertEqual(self.new_run().reset_section(), [NoChecklist()])
		self.assertEqual(self.new_run().reset(), [NoChecklist()])


class TestMovingTo(RunOnDisk):
	"""Section 5.1: "Move to" is a jump, and the position reaches the disk."""

	def test_moving_to_lands_there_and_names_the_section(self):
		run = self.opened(["pending"], ["pending", "pending"])
		self.assertEqual(run.move_to(Position(1, 1)), [self.landed(run, 1, 1, jump=True)])
		self.assertEqual(session.load(self.state).position, Position(1, 1))

	def test_nowhere_to_move_before_a_checklist_is_open(self):
		self.assertEqual(self.new_run().move_to(Position(0, 0)), [NoChecklist()])


class TestProgress(RunOnDisk):
	"""Section 3.3: the section the tester is in, counted whole."""

	def test_the_current_section_and_its_count(self):
		run = self.opened(["passed", "failed", "pending"], ["pending"])
		assert run.checklist is not None
		self.assertEqual(
			run.progress(),
			[SectionProgress(run.checklist.sections[0], Progress(total=3, processed=2, failed=1))],
		)

	def test_no_progress_before_a_checklist_is_open(self):
		self.assertEqual(self.new_run().progress(), [NoChecklist()])


class TestRestoring(RunOnDisk):
	"""Section 2: the run picks up where the last one left it, silently.

	A restore reads the position rather than changing it, so nothing is
	written back — whether it went well or badly. A failure leaves the path in
	`state.json` standing, because that path is where the file dialog starts
	browsing, and that is wanted exactly then.
	"""

	def remembered(self, path: Path, position: Position | None) -> None:
		session.save(self.state, Session(path, position))

	def test_nothing_remembered_restores_nothing_and_says_nothing(self):
		run = self.new_run()
		self.assertEqual(run.restore(), [])
		self.assertIsNone(run.checklist)

	def test_the_remembered_file_and_place_come_back_without_a_word(self):
		path = self.checklist_file(["pending", "pending"], ["pending"])
		self.remembered(path, Position(1, 0))
		run = self.new_run()
		with mock.patch("core.disk.write") as written:
			self.assertEqual(run.restore(), [])
		written.assert_not_called()
		self.assertIsNotNone(run.checklist)
		self.assertEqual(run.position, Position(1, 0))

	def test_a_place_the_file_has_outgrown_starts_over_at_the_first_item(self):
		path = self.checklist_file(["pending"])
		self.remembered(path, Position(4, 4))
		run = self.new_run()
		self.assertEqual(run.restore(), [])
		self.assertEqual(run.position, Position(0, 0))

	def test_a_file_that_has_gone_is_named_and_the_path_is_kept(self):
		gone = self.directory / "gone.json"
		self.remembered(gone, Position(0, 0))
		run = self.new_run()
		self.assertEqual(run.restore(), [ChecklistGone(gone)])
		self.assertIsNone(run.checklist)
		self.assertEqual(session.load(self.state).checklist, gone)

	def test_a_file_that_breaks_the_contract_is_refused_with_the_reason(self):
		broken = self.directory / "broken.json"
		broken.write_text('{"checklist_name": "x", "sections": []}', encoding="utf-8")
		self.remembered(broken, Position(0, 0))
		run = self.new_run()
		answer = run.restore()
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], Refused)
		assert isinstance(answer[0], Refused)
		self.assertEqual(answer[0].problem.kind, ProblemKind.NO_SECTIONS)
		self.assertIsNone(run.checklist)

	def test_a_file_that_cannot_be_read_at_all_is_told_from_a_broken_one(self):
		# A directory standing where the file should be is the cheapest way to
		# an error that is neither "not there" nor a breach of the contract.
		self.remembered(self.directory, Position(0, 0))
		run = self.new_run()
		answer = run.restore()
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], Unreadable)


class TestOpeningAgain(RunOnDisk):
	"""Section 3.2.2: the same file lands where it was left, another at the top."""

	def test_the_same_file_reopened_lands_where_the_tester_stopped(self):
		run = self.opened(["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		assert run.checklist is not None
		assert run.checklist.path is not None
		self.assertEqual(run.open(run.checklist.path), [self.landed(run, 0, 1, jump=True)])

	def test_another_file_starts_at_its_first_item(self):
		run = self.opened(["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		other = self.checklist_file(["pending", "pending"], name="other.json")
		self.assertEqual(run.open(other), [self.landed(run, 0, 0, jump=True)])
		self.assertEqual(session.load(self.state), Session(other, Position(0, 0)))

	def test_a_file_that_will_not_open_leaves_everything_as_it_was(self):
		# Section 2: a refusal writes nothing and moves nothing — the checklist
		# in hand and the path in `state.json` both stand.
		run = self.opened(["pending", "pending"])
		run.navigate(FORWARD, jump=False)
		before = run.checklist
		broken = self.directory / "broken.json"
		broken.write_text("{ not json", encoding="utf-8")
		answer = run.open(broken)
		self.assertEqual(len(answer), 1)
		self.assertIsInstance(answer[0], Refused)
		self.assertIs(run.checklist, before)
		self.assertEqual(run.position, Position(0, 1))
		self.assertEqual(session.load(self.state), Session(before.path, Position(0, 1)))

	def test_a_file_taken_away_between_picking_and_opening_is_named(self):
		run = self.new_run()
		gone = self.directory / "gone.json"
		self.assertEqual(run.open(gone), [ChecklistGone(gone)])


class TestAPlaceThatDidNotReachTheDisk(RunOnDisk):
	"""Section 2: a failed write of `state.json` is in the answer, not in the voice.

	The command goes on — what is lost is the place, not the run — and the
	event stands ahead of the landing it belongs to, for the shell to log.
	"""

	def setUp(self) -> None:
		super().setUp()
		# A file standing where the add-on's folder should be, so that making
		# the folder fails on every write.
		self.state.parent.write_text("", encoding="utf-8")

	def test_the_write_is_reported_ahead_of_the_landing(self):
		run = self.new_run()
		answer = run.open(self.checklist_file(["pending"]))
		self.assertEqual(len(answer), 2)
		self.assertIsInstance(answer[0], PlaceNotSaved)
		self.assertEqual(answer[1], self.landed(run, 0, 0, jump=True))

	def test_the_status_word_comes_before_it_and_the_next_item_after(self):
		run = self.new_run()
		run.open(self.checklist_file(["pending", "pending"]))
		answer = run.toggle(advance=True)
		self.assertEqual(len(answer), 3)
		self.assertEqual(answer[0], Recorded("passed"))
		self.assertIsInstance(answer[1], PlaceNotSaved)
		self.assertEqual(answer[2], self.landed(run, 0, 1, jump=False))


class TestWhereBrowsingStarts(RunOnDisk):
	"""Section 3.2.2: the file dialog starts in the folder of the last path remembered."""

	def test_nothing_remembered_leaves_the_choice_to_windows(self):
		self.assertIsNone(self.new_run().remembered())

	def test_the_folder_of_the_open_checklist(self):
		run = self.opened(["pending"])
		self.assertEqual(run.remembered(), self.directory)

	def test_the_folder_of_a_file_that_has_gone(self):
		# Wanted exactly then: start-up found the file gone, and the only thing
		# left pointing anywhere is that path.
		gone = self.directory / "elsewhere" / "gone.json"
		session.save(self.state, Session(gone, Position(0, 0)))
		run = self.new_run()
		run.restore()
		self.assertEqual(run.remembered(), gone.parent)
