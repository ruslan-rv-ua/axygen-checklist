# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Reading a checklist file, and the validation contract of section 2.

The fixtures under `tests/fixtures` are shared with `test_schema.py`, which
validates them against the derived JSON schema. Here they are run through the
add-on's own pass, the one that actually decides whether a file loads.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core import checklist

from .support import fixture_names, fixture_text


class TestReading(unittest.TestCase):
	def test_a_minimal_file_reads_into_a_model(self):
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertEqual(loaded.name, "Base checklist")
		self.assertEqual([section.name for section in loaded.sections], ["Controls"])
		item = loaded.sections[0].items[0]
		self.assertEqual(item.id, 1)
		self.assertEqual(item.text, "An item")

	def test_a_section_may_hold_no_items(self):
		loaded = checklist.loads(fixture_text("valid", "empty-items"))
		self.assertEqual(list(loaded.sections[0].items), [])


class TestOptionalFields(unittest.TestCase):
	def test_an_item_without_a_status_is_pending(self):
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertEqual(loaded.sections[0].items[0].status, "pending")

	def test_a_written_status_is_read_back_as_it_stands(self):
		loaded = checklist.loads(fixture_text("valid", "all-statuses"))
		self.assertEqual(
			[item.status for item in loaded.sections[0].items],
			["pending", "passed", "failed", "blocked", "skipped"],
		)

	def test_an_item_without_a_note_has_none(self):
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertIsNone(loaded.sections[0].items[0].note)

	def test_a_note_is_read_as_it_stands(self):
		loaded = checklist.loads(fixture_text("valid", "complete"))
		self.assertEqual(loaded.sections[0].items[1].note, "Try Tab and Shift+Tab")

	def test_an_item_without_a_comment_has_none(self):
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertIsNone(loaded.sections[0].items[0].comment)

	def test_a_comment_is_read_as_it_stands(self):
		loaded = checklist.loads(fixture_text("valid", "complete"))
		self.assertEqual(loaded.sections[0].items[2].comment, "Phone has no label")

	def test_a_blank_comment_reads_as_no_comment_at_all(self):
		# Section 2: "comment absent" and "comment empty" are one state, and the
		# canonical form of it is one. Normalising on read as well as on write
		# keeps every consumer from having to ask `if comment.strip()`.
		loaded = checklist.loads(fixture_text("valid", "blank-comment"))
		self.assertIsNone(loaded.sections[0].items[0].comment)

	def test_an_empty_comment_reads_as_no_comment_at_all(self):
		loaded = checklist.loads(
			json.dumps(
				{
					"checklist_name": "Base checklist",
					"sections": [
						{"section_name": "Controls", "items": [{"id": 1, "text": "An item", "comment": ""}]},
					],
				},
			),
		)
		self.assertIsNone(loaded.sections[0].items[0].comment)


class TestUnknownFields(unittest.TestCase):
	"""Section 2: unknown fields are ignored on read and survive a rewrite.

	Saving mutates the structure that was loaded rather than building a fresh
	object out of the schema, so what the model must hold is the parsed
	document itself. The rewrite is a separate ticket; what is checked here is
	that nothing was dropped on the way in.
	"""

	def test_the_parsed_document_is_kept_whole(self):
		loaded = checklist.loads(fixture_text("valid", "unknown-fields"))
		self.assertEqual(loaded.document["generated_by"], "an agent")
		self.assertEqual(loaded.document["sections"][0]["severity"], "high")
		self.assertEqual(loaded.document["sections"][0]["items"][0]["ticket"], "AX-42")

	def test_an_unknown_field_is_not_a_violation(self):
		loaded = checklist.loads(fixture_text("valid", "unknown-fields"))
		self.assertEqual(loaded.sections[0].items[0].text, "An item")

	def test_the_schema_url_is_left_alone(self):
		# Section 2: `$schema` is a field the add-on never reads and never
		# writes. It survives on the same rule as any other unknown field.
		loaded = checklist.loads(fixture_text("valid", "complete"))
		self.assertIn("$schema", loaded.document)


class TestValidationContract(unittest.TestCase):
	"""Section 2: one pass at load time, and any violation refuses the file whole.

	The fixtures under `tests/fixtures/invalid` break exactly one clause of the
	contract each, so the table below reads as the contract itself. It is
	asserted to cover every fixture on disk: a clause that grows a fixture
	without growing a reason here would otherwise pass unnoticed.
	"""

	EXPECTED = {
		"missing-checklist-name": (checklist.ProblemKind.MISSING_FIELD, "checklist_name"),
		"missing-sections": (checklist.ProblemKind.MISSING_FIELD, "sections"),
		"missing-section-name": (checklist.ProblemKind.MISSING_FIELD, "section_name"),
		"missing-items": (checklist.ProblemKind.MISSING_FIELD, "items"),
		"missing-item-id": (checklist.ProblemKind.MISSING_FIELD, "id"),
		"missing-item-text": (checklist.ProblemKind.MISSING_FIELD, "text"),
		"type-checklist-name": (checklist.ProblemKind.NOT_A_STRING, "checklist_name"),
		"type-section-name": (checklist.ProblemKind.NOT_A_STRING, "section_name"),
		"type-note": (checklist.ProblemKind.NOT_A_STRING, "note"),
		"type-format-version": (checklist.ProblemKind.NOT_AN_INTEGER, "format_version"),
		"type-sections": (checklist.ProblemKind.NOT_AN_ARRAY, "sections"),
		"type-items": (checklist.ProblemKind.NOT_AN_ARRAY, "items"),
		"type-item-id": (checklist.ProblemKind.NOT_AN_INTEGER, "id"),
		"type-item-text": (checklist.ProblemKind.NOT_A_STRING, "text"),
		"type-comment": (checklist.ProblemKind.NOT_A_STRING, "comment"),
		"empty-sections": (checklist.ProblemKind.NO_SECTIONS, "sections"),
		"duplicate-id": (checklist.ProblemKind.DUPLICATE_ID, "id"),
		"unknown-status": (checklist.ProblemKind.UNKNOWN_STATUS, "status"),
		"format-version-too-high": (checklist.ProblemKind.FUTURE_FORMAT, "format_version"),
		"format-version-unknown": (checklist.ProblemKind.UNKNOWN_FORMAT, "format_version"),
	}

	def test_the_table_covers_every_invalid_fixture(self):
		self.assertEqual(sorted(self.EXPECTED), fixture_names("invalid"))

	def test_each_invalid_fixture_is_refused_for_its_own_reason(self):
		for name, (kind, field) in sorted(self.EXPECTED.items()):
			with self.subTest(fixture=name):
				with self.assertRaises(checklist.ChecklistError) as refusal:
					checklist.loads(fixture_text("invalid", name))
				self.assertEqual(refusal.exception.problem.kind, kind)
				self.assertEqual(refusal.exception.problem.field, field)

	def test_every_valid_fixture_loads(self):
		for name in fixture_names("valid"):
			with self.subTest(fixture=name):
				self.assertIsInstance(checklist.loads(fixture_text("valid", name)), checklist.Checklist)


class TestReasons(unittest.TestCase):
	"""The reason is structured: which field, which item, which value.

	Section 2 wants one source of the reason for the whole add-on, and the cut
	is the one the status dictionary already makes: the core names the
	violation, the shell turns it into a sentence wrapped in `_()`. Nothing
	here asserts on wording, because none is produced here.
	"""

	def refusal(self, kind: str, name: str) -> "checklist.Problem":
		with self.assertRaises(checklist.ChecklistError) as raised:
			checklist.loads(fixture_text(kind, name))
		return raised.exception.problem

	def test_a_violation_at_the_top_level_belongs_to_no_item(self):
		problem = self.refusal("invalid", "type-checklist-name")
		self.assertEqual(problem.value, 42)
		self.assertIsNone(problem.section_index)
		self.assertIsNone(problem.item_index)

	def test_a_violation_in_a_section_says_which_section(self):
		problem = self.refusal("invalid", "missing-items")
		self.assertEqual(problem.section_index, 0)
		self.assertIsNone(problem.item_index)

	def test_a_violation_in_an_item_says_which_item(self):
		problem = self.refusal("invalid", "type-comment")
		self.assertEqual((problem.section_index, problem.item_index, problem.item_id), (0, 0, 1))
		self.assertEqual(problem.value, 7)

	def test_an_item_that_has_no_identifier_yet_is_still_placed(self):
		# Its `id` is what the file was supposed to name it by, so the reason
		# falls back to where the item sits.
		problem = self.refusal("invalid", "missing-item-id")
		self.assertEqual((problem.section_index, problem.item_index), (0, 0))
		self.assertIsNone(problem.item_id)

	def test_a_duplicate_identifier_names_the_second_item_that_took_it(self):
		problem = self.refusal("invalid", "duplicate-id")
		self.assertEqual(problem.value, 1)
		self.assertEqual((problem.section_index, problem.item_index), (1, 0))

	def test_an_unknown_status_carries_the_value_that_was_written(self):
		# Section 2: fatal on purpose. Normalising it to `pending` would erase
		# a result the tester had recorded, because the next change rewrites
		# the whole file.
		problem = self.refusal("invalid", "unknown-status")
		self.assertEqual(problem.value, "done")


class TestFormatVersion(unittest.TestCase):
	def test_a_newer_file_is_refused_on_its_own_terms(self):
		# Section 2: the one violation with a message of its own. The short
		# "could not read the file" would send the tester looking for broken
		# JSON that is not there; this one sends them to update the add-on.
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(fixture_text("invalid", "format-version-too-high"))
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.FUTURE_FORMAT)
		self.assertEqual(refusal.exception.problem.value, 2)

	def test_a_version_the_add_on_does_not_know_is_an_ordinary_refusal(self):
		# Section 2: only a *higher* version earns "created by a newer version".
		# There was never a format zero, so there is no update to send anyone to.
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(fixture_text("invalid", "format-version-unknown"))
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.UNKNOWN_FORMAT)
		self.assertEqual(refusal.exception.problem.value, 0)

	def test_the_known_version_written_out_is_accepted(self):
		loaded = checklist.loads(fixture_text("valid", "complete"))
		self.assertEqual(loaded.document["format_version"], 1)

	def test_a_newer_file_is_recognised_before_anything_else_is_judged(self):
		# A file from a later format is entitled to break this one's rules; that
		# is what the major number means. Reporting one of those breaches first
		# would hand the tester the wrong answer.
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(json.dumps({"format_version": 2, "sections": []}))
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.FUTURE_FORMAT)

	def test_a_format_version_that_is_not_a_number_is_an_ordinary_violation(self):
		# Only a version above the known one earns the message of its own; a
		# broken one is a type breach like any other.
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(fixture_text("invalid", "type-format-version"))
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_AN_INTEGER)


class TestMalformedFiles(unittest.TestCase):
	def test_text_that_is_not_json_is_refused_like_any_other_breach(self):
		# Section 4 puts a parse error under the same short message as the rest
		# of the contract, so it may not escape as a `json` exception.
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads("{ not json")
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_JSON)

	def test_a_document_that_is_not_an_object_is_refused(self):
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads("[]")
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_AN_OBJECT)

	def test_a_section_that_is_not_an_object_is_refused(self):
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(json.dumps({"checklist_name": "x", "sections": ["Controls"]}))
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_AN_OBJECT)
		self.assertEqual(refusal.exception.problem.section_index, 0)

	def test_an_item_that_is_not_an_object_is_refused(self):
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.loads(
				json.dumps({"checklist_name": "x", "sections": [{"section_name": "s", "items": [1]}]}),
			)
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_AN_OBJECT)
		self.assertEqual((refusal.exception.problem.section_index, refusal.exception.problem.item_index), (0, 0))


class TestLoadingFromDisk(unittest.TestCase):
	def write(self, text: str, encoding: str = "utf-8") -> "Path":
		directory = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, directory, True)
		path = Path(directory) / "checklist.json"
		path.write_text(text, encoding=encoding)
		return path

	def test_a_file_on_disk_reads_the_same_as_its_text(self):
		path = self.write(fixture_text("valid", "minimal"))
		self.assertEqual(checklist.load(path).name, "Base checklist")

	def test_a_path_may_be_a_string(self):
		# The shell has strings: `wx.FileDialog` returns one, and so does the
		# path kept in `state.json`.
		path = self.write(fixture_text("valid", "minimal"))
		self.assertEqual(checklist.load(str(path)).name, "Base checklist")

	def test_a_byte_order_mark_does_not_refuse_the_file(self):
		# Checklists are written by hand on Windows, where editors still put one
		# at the front; `json` alone chokes on it.
		path = self.write(fixture_text("valid", "minimal"), encoding="utf-8-sig")
		self.assertEqual(checklist.load(path).name, "Base checklist")

	def test_a_file_that_is_not_there_is_not_a_refusal(self):
		# Section 2 answers a missing file with "Checklist file not found" and a
		# file dialog, which is a different answer from "this file is broken".
		with self.assertRaises(OSError):
			checklist.load(Path(tempfile.gettempdir()) / "axygen-checklist-no-such-file.json")

	def test_a_file_in_another_encoding_is_refused_rather_than_thrown(self):
		# The same hand-edited-on-Windows file the byte order mark comes from
		# can arrive in a legacy code page. Section 2 refuses a file at load
		# precisely so that nothing throws later, with the focus in the
		# application under test and NVDA suddenly silent.
		directory = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, directory, True)
		path = Path(directory) / "checklist.json"
		path.write_bytes('{"checklist_name": "Тест", "sections": []}'.encode("cp1251"))
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.load(path)
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_JSON)

	def test_a_broken_file_on_disk_is_refused_like_broken_text(self):
		path = self.write(fixture_text("invalid", "unknown-status"))
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.load(path)
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.UNKNOWN_STATUS)
