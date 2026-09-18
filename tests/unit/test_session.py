# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""What the add-on remembers between one run of NVDA and the next.

Section 2 of `docs/requirements.md`, "Збереження стану сесії": the path of the
active checklist and the pair of indices the tester stood on, kept in
`state.json` so that a restart of the screen reader puts them back where they
stopped.

The tests below are shaped by what section 7.1 says this file is: an internal
cache of the position, rebuilt by the add-on itself and outside the version
contract. So half of them are about damage — a file that is not there, is not
JSON, or holds nonsense where a number should be — and all of them expect the
same answer, which is silence and an empty session. There is nothing to report
and nobody to report it to: the tester gave no command.
"""

import json
import unittest
from pathlib import Path
from typing import Any

from core import session
from core.navigation import Position
from core.session import Session

from .support import temporary_directory


class OnDisk(unittest.TestCase):
	"""A state file in a temporary directory of its own.

	Reading and writing show only on disk, so every test here works through a
	real file; the directory is made and swept away in one place.
	"""

	def setUp(self) -> None:
		super().setUp()
		self.directory = temporary_directory(self)
		self.path = self.directory / "state.json"

	def written(self, text: str) -> Path:
		"""Put `text` in the state file by hand, as damage would leave it."""
		self.path.write_text(text, encoding="utf-8")
		return self.path

	def document(self) -> dict[str, Any]:
		"""What the state file says right now."""
		document: Any = json.loads(self.path.read_text(encoding="utf-8"))
		assert isinstance(document, dict)
		return document


class TestRemembering(OnDisk):
	"""A session written and read back is the session that was written."""

	def test_the_path_and_the_position_both_come_back(self):
		checklist = self.directory / "checklist.json"
		session.save(self.path, Session(checklist, Position(1, 4)))
		self.assertEqual(session.load(self.path), Session(checklist, Position(1, 4)))

	def test_a_checklist_with_nowhere_to_stand_still_remembers_its_path(self):
		# A checklist of empty sections is valid (section 2 asks for at least
		# one section and never for a minimum of items), so there is a file to
		# reopen and no position in it.
		checklist = self.directory / "checklist.json"
		session.save(self.path, Session(checklist, None))
		self.assertEqual(session.load(self.path), Session(checklist, None))

	def test_the_folder_is_made_when_it_is_not_there_yet(self):
		# The add-on's own folder inside NVDA's configuration directory does not
		# exist until the first checklist is opened (section 2).
		path = self.directory / "axygenChecklist" / "state.json"
		session.save(path, Session(self.directory / "checklist.json", Position(0, 0)))
		self.assertTrue(path.is_file())

	def test_a_path_outside_ascii_survives_the_trip(self):
		# The usual case rather than an exotic one: a Windows profile named in
		# Ukrainian puts the checklist under a path like this.
		checklist = self.directory / "Тестування" / "чекліст.json"
		session.save(self.path, Session(checklist, Position(0, 1)))
		self.assertEqual(session.load(self.path).checklist, checklist)


class TestWhatIsWritten(OnDisk):
	"""Section 2: the file holds the path and two indices, and nothing else."""

	def test_nothing_but_the_path_and_the_two_indices_is_written(self):
		# Section 2 keeps the state of the filter (section 3.4) and the
		# auto-advance option (section 4) out of this file deliberately: the
		# first is a temporary working mode, the second a preference that lives
		# in NVDA's own configuration. Neither may arrive here by accident.
		session.save(self.path, Session(self.directory / "checklist.json", Position(1, 2)))
		self.assertEqual(set(self.document()), {"checklist", "section", "item"})

	def test_a_session_with_no_position_writes_no_indices(self):
		session.save(self.path, Session(self.directory / "checklist.json", None))
		self.assertEqual(set(self.document()), {"checklist"})

	def test_an_empty_session_writes_an_empty_document(self):
		session.save(self.path, Session())
		self.assertEqual(self.document(), {})

	def test_the_file_is_utf8_with_the_letters_left_as_letters(self):
		session.save(self.path, Session(self.directory / "чекліст.json", None))
		self.assertIn("чекліст".encode(), self.path.read_bytes())

	def test_the_file_ends_with_a_line_break(self):
		session.save(self.path, Session(self.directory / "checklist.json", Position(0, 0)))
		self.assertTrue(self.path.read_text(encoding="utf-8").endswith("\n"))

	def test_unknown_fields_do_not_survive_a_rewrite(self):
		# The opposite of the rule for a checklist (section 2), and deliberately
		# so: that rule protects what an author or an agent wrote into the
		# tester's own file, while this one is a cache the add-on writes to
		# itself. Keeping someone else's field here would mean admitting that
		# someone else writes here.
		self.written('{"checklist": "somewhere.json", "filter": true}')
		session.save(self.path, session.load(self.path))
		self.assertNotIn("filter", self.document())


class TestADamagedCache(OnDisk):
	"""Anything that cannot be read as a session is discarded whole (section 2).

	Silently, and with no window: the add-on starts as though the file had never
	been there. It is a cache the add-on builds itself, so there is nothing to
	recover and nothing to tell anyone.
	"""

	def test_a_file_that_is_not_there_remembers_nothing(self):
		self.assertEqual(session.load(self.directory / "no-such-state.json"), Session())

	def test_a_file_that_cannot_be_read_at_all_remembers_nothing(self):
		# A directory standing where the file should be is the cheapest way to
		# reach the branch; a locked or unreadable file arrives at the same one.
		self.directory.joinpath("state.json").mkdir()
		self.assertEqual(session.load(self.path), Session())

	def test_a_file_that_is_not_json_remembers_nothing(self):
		self.written("{not json at all")
		self.assertEqual(session.load(self.path), Session())

	def test_a_document_that_is_not_an_object_remembers_nothing(self):
		self.written("[1, 2, 3]")
		self.assertEqual(session.load(self.path), Session())

	def test_a_document_without_a_path_remembers_nothing(self):
		# Without a file to reopen, a position is a pair of numbers about
		# nothing.
		self.written('{"section": 1, "item": 2}')
		self.assertEqual(session.load(self.path), Session())

	def test_a_path_that_is_not_a_string_remembers_nothing(self):
		self.written('{"checklist": 12, "section": 1, "item": 2}')
		self.assertEqual(session.load(self.path), Session())

	def test_an_empty_path_remembers_nothing(self):
		self.written('{"checklist": "   ", "section": 1, "item": 2}')
		self.assertEqual(session.load(self.path), Session())

	def test_a_path_that_could_not_be_opened_at_all_remembers_nothing(self):
		# A null character inside the string makes opening it raise ValueError
		# rather than the OSError a bad path is answered with everywhere else —
		# and that one would travel up through whoever opened the checklist.
		self.written('{"checklist": "check\\u0000list.json", "section": 0, "item": 0}')
		self.assertEqual(session.load(self.path), Session())


class TestADamagedPosition(OnDisk):
	"""A path that reads without a usable position is still a path (section 2).

	The starting folder of the file dialog (section 3.2.2) hangs off that path,
	and it is wanted exactly when something else has gone wrong.
	"""

	def path_only(self) -> Session:
		return Session(Path("somewhere/checklist.json"))

	def test_a_document_without_indices_keeps_the_path(self):
		self.written('{"checklist": "somewhere/checklist.json"}')
		self.assertEqual(session.load(self.path), self.path_only())

	def test_half_a_position_is_no_position(self):
		self.written('{"checklist": "somewhere/checklist.json", "section": 1}')
		self.assertEqual(session.load(self.path), self.path_only())

	def test_an_index_that_is_not_a_whole_number_keeps_the_path(self):
		self.written('{"checklist": "somewhere/checklist.json", "section": 1, "item": 0.5}')
		self.assertEqual(session.load(self.path), self.path_only())

	def test_an_index_that_is_true_keeps_the_path(self):
		# JSON `true` parses to a Python bool, and a bool is an int: without a
		# check of its own it would index the sections as 1.
		self.written('{"checklist": "somewhere/checklist.json", "section": true, "item": 0}')
		self.assertEqual(session.load(self.path), self.path_only())

	def test_a_negative_index_keeps_the_path(self):
		# Negative indices are legal Python and count from the end of a list, so
		# one left here by damage would quietly stand somewhere real and wrong.
		self.written('{"checklist": "somewhere/checklist.json", "section": 0, "item": -1}')
		self.assertEqual(session.load(self.path), self.path_only())

	def test_an_index_that_is_null_keeps_the_path(self):
		self.written('{"checklist": "somewhere/checklist.json", "section": null, "item": null}')
		self.assertEqual(session.load(self.path), self.path_only())


class TestThePositionBelongsToOneFile(unittest.TestCase):
	"""Whose place the remembered indices are (sections 2 and 3.2.2).

	The file dialog may be pointed at any file on the disk, while `state.json`
	holds one position and it was measured in whichever file was open when it
	was written. Asking for it by path is what keeps the two apart: the same
	file reopened lands where the tester stopped, another file starts at the
	top, because indices into a structure nobody opened describe nothing.
	"""

	def remembered(self) -> Session:
		return Session(Path("C:/checklists/forms.json"), Position(1, 4))

	def test_the_same_file_gets_the_position_back(self):
		self.assertEqual(
			self.remembered().position_in(Path("C:/checklists/forms.json")),
			Position(1, 4),
		)

	def test_another_file_gets_no_position(self):
		self.assertIsNone(self.remembered().position_in(Path("C:/checklists/menus.json")))

	def test_the_same_file_spelled_another_way_gets_the_position_back(self):
		# The add-on writes what the file dialog handed it and reads it back as
		# text, so the same file can arrive spelled two ways. Windows tells
		# neither the case nor the separator apart, and `Path` compares the two
		# the way the platform does.
		self.assertEqual(
			self.remembered().position_in(Path(r"c:\Checklists\FORMS.json")),
			Position(1, 4),
		)

	def test_a_file_remembered_without_a_position_gets_none(self):
		nowhere = Session(Path("C:/checklists/forms.json"))
		self.assertIsNone(nowhere.position_in(Path("C:/checklists/forms.json")))

	def test_nothing_remembered_at_all_gets_no_position(self):
		self.assertIsNone(Session().position_in(Path("C:/checklists/forms.json")))
