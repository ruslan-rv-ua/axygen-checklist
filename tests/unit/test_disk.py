# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""How a file of the add-on reaches the disk.

Section 2 of `docs/requirements.md` asks the same thing of both files the
add-on writes — the checklist and `state.json` — and the rule is the same
sentence for each: **the write arrives whole or not at all**. Both are
rewritten hundreds of times a session by an add-on that is able to bring the
screen reader down, and writing straight into either would empty it before
filling it again; a crash inside that window leaves a stump where a tester's
texts and notes had been.

The rule lives in one module, so its proof lives in one place too. What each
caller puts *in* its file is its own business and is tested beside it.
"""

import unittest
from pathlib import Path
from unittest import mock

from core import disk

from .support import temporary_directory


class OnDisk(unittest.TestCase):
	def setUp(self) -> None:
		super().setUp()
		self.directory = temporary_directory(self)
		self.path = self.directory / "written.txt"

	def contents(self) -> str:
		return self.path.read_text(encoding="utf-8")


class TestWriting(OnDisk):
	def test_the_text_arrives(self):
		disk.write(self.path, "hello\n")
		self.assertEqual(self.contents(), "hello\n")

	def test_writing_again_replaces_what_was_there(self):
		disk.write(self.path, "first\n")
		disk.write(self.path, "second\n")
		self.assertEqual(self.contents(), "second\n")

	def test_the_text_is_written_as_utf8(self):
		disk.write(self.path, "Кирилиця\n")
		self.assertIn("Кирилиця".encode(), self.path.read_bytes())

	def test_line_breaks_are_written_as_they_were_given(self):
		# `\n` whatever the platform default is: a checklist usually lives in
		# version control beside the product under test, so what the add-on
		# writes is the same on every machine that reads the repository.
		disk.write(self.path, "one\ntwo\n")
		self.assertNotIn(b"\r\n", self.path.read_bytes())

	def test_nothing_is_left_lying_beside_the_file(self):
		disk.write(self.path, "hello\n")
		self.assertEqual([path.name for path in self.directory.iterdir()], ["written.txt"])

	def test_a_folder_that_is_not_there_is_not_made_here(self):
		# Making one is a decision about where a file belongs, and the caller
		# is what has it: `session.save` makes the add-on's own folder inside
		# NVDA's configuration directory, and a checklist's folder exists
		# already because the checklist was read out of it.
		with self.assertRaises(OSError):
			disk.write(self.directory / "not-there" / "written.txt", "hello\n")


class TestAWriteThatFails(OnDisk):
	"""Section 2: whole or not at all."""

	def test_the_previous_contents_are_still_there(self):
		disk.write(self.path, "first\n")
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			with self.assertRaises(OSError):
				disk.write(self.path, "second\n")
		self.assertEqual(self.contents(), "first\n")

	def test_nothing_is_left_lying_beside_the_file(self):
		disk.write(self.path, "first\n")
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			with self.assertRaises(OSError):
				disk.write(self.path, "second\n")
		self.assertEqual([path.name for path in self.directory.iterdir()], ["written.txt"])

	def test_a_file_that_was_not_there_is_still_not_there(self):
		missing = self.directory / "never-written.txt"
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			with self.assertRaises(OSError):
				disk.write(missing, "hello\n")
		self.assertEqual(list(self.directory.iterdir()), [])
