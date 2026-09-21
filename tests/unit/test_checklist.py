# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Reading and writing a checklist file, under the contract of section 2.

The fixtures under `tests/fixtures` are shared with `test_schema.py`, which
validates them against the derived JSON schema. Here they are run through the
add-on's own pass, the one that actually decides whether a file loads.

Reading and writing are tested together because they are two halves of one
contract: everything the add-on writes it has to be able to read again, and
the fixtures that state what a valid file is state it for both.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from core import checklist, disk, status

from .support import fixture_names, fixture_text, temporary_directory


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

	def test_the_items_of_the_whole_file_run_in_the_order_it_lists_them(self):
		# What is true of a run rather than of a place reads the checklist as one
		# stretch of items: whether anything is still pending (section 4), and
		# later the report (section 7.2).
		loaded = checklist.loads(fixture_text("valid", "complete"))
		self.assertEqual([item.id for item in loaded.items], [1, 2, 3, 4])

	def test_a_section_holding_no_items_contributes_none_to_the_whole(self):
		loaded = checklist.loads(
			json.dumps(
				{
					"checklist_name": "Base checklist",
					"sections": [
						{"section_name": "First", "items": [{"id": 1, "text": "An item"}]},
						{"section_name": "Empty", "items": []},
						{"section_name": "Last", "items": [{"id": 2, "text": "Another item"}]},
					],
				},
			),
		)
		self.assertEqual([item.id for item in loaded.items], [1, 2])


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
	document itself. What is checked here is that nothing was dropped on the
	way in; that nothing is dropped on the way out is checked further down.
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


class OnDisk(unittest.TestCase):
	"""A checklist in a temporary directory of its own.

	Writing shows only on disk, so the tests about it load a real file and read
	that same file back afterwards; the ones about reading need a file to read.
	Both are served from here so that the temporary directory is set up and
	swept away in one place.
	"""

	def write(self, text: str, encoding: str = "utf-8") -> Path:
		"""Put `text` in a checklist file of its own, and hand back the path."""
		path = temporary_directory(self) / "checklist.json"
		path.write_text(text, encoding=encoding)
		return path

	def loaded(self, name: str = "minimal") -> checklist.Checklist:
		"""The valid fixture `name`, loaded from a file it can be written back to."""
		return checklist.load(self.write(fixture_text("valid", name)))

	def on_disk(self, loaded: checklist.Checklist) -> dict[str, Any]:
		"""What the file of `loaded` says right now."""
		assert loaded.path is not None
		return json.loads(loaded.path.read_text(encoding="utf-8"))


class TestLoadingFromDisk(OnDisk):
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
		path = self.write("")
		path.write_bytes('{"checklist_name": "Тест", "sections": []}'.encode("cp1251"))
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.load(path)
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.NOT_JSON)

	def test_a_broken_file_on_disk_is_refused_like_broken_text(self):
		path = self.write(fixture_text("invalid", "unknown-status"))
		with self.assertRaises(checklist.ChecklistError) as refusal:
			checklist.load(path)
		self.assertEqual(refusal.exception.problem.kind, checklist.ProblemKind.UNKNOWN_STATUS)


class TestWriteRules(unittest.TestCase):
	"""Section 2, the rules of writing.

	They exist so that a file the add-on has written is a file it can read
	again, and so that nothing anyone put in the file is quietly lost on the
	way through.
	"""

	def written(self, name: str) -> dict[str, Any]:
		"""The valid fixture `name`, put through the write rules and read back."""
		return json.loads(checklist.dumps(checklist.loads(fixture_text("valid", name))))

	def test_the_status_of_every_item_is_written_out(self):
		# Section 2: explicitly, for every item, `pending` included — even
		# though an absent field reads back as exactly that. What is written
		# down is a state the tester can see in the file.
		document = self.written("complete")
		statuses = [item["status"] for section in document["sections"] for item in section["items"]]
		self.assertEqual(statuses, ["passed", "pending", "failed", "pending"])

	def test_a_file_that_carried_no_version_is_given_the_newest_one_known(self):
		# Section 2, and section 7.1 rests on it: a file this add-on wrote says
		# which format it is in, so that a later version knows what it has.
		self.assertEqual(self.written("minimal")["format_version"], 1)

	def test_a_version_the_file_already_carried_is_kept_as_it_stands(self):
		# Section 2 asks for the version to be explicit, not for it to be
		# raised. With one version known the rule cannot show itself, so the
		# add-on is told it knows two: a release that still reads version 1
		# files must leave one a version 1 file when it saves, and restamping
		# it would be the silent corruption section 7.1 exists to prevent.
		#
		# This patches a constant of the add-on's own, not a module of NVDA's:
		# the ban on stubbing in docs/development.md is about faking the
		# core/shell boundary, which nothing here does.
		with (
			mock.patch.object(checklist, "KNOWN_FORMAT_VERSION", 2),
			mock.patch.object(checklist, "KNOWN_FORMAT_VERSIONS", frozenset({1, 2})),
		):
			self.assertEqual(self.written("complete")["format_version"], 1)

	def test_a_blank_comment_is_not_written(self):
		# Section 2: "no comment" and "an empty comment" are one state, and it
		# has one canonical form. This is the single point where that is
		# settled — the deliberate exception to "write it explicitly".
		item = self.written("blank-comment")["sections"][0]["items"][0]
		self.assertNotIn("comment", item)

	def test_a_comment_that_says_something_is_written(self):
		item = self.written("complete")["sections"][0]["items"][2]
		self.assertEqual(item["comment"], "Phone has no label")

	def test_unknown_fields_survive_at_every_level(self):
		document = self.written("unknown-fields")
		self.assertEqual(document["generated_by"], "an agent")
		self.assertEqual(document["sections"][0]["severity"], "high")
		self.assertEqual(document["sections"][0]["items"][0]["ticket"], "AX-42")

	def test_the_schema_url_survives(self):
		# Section 2: a field the add-on never reads and never writes, kept
		# alive by the rule that keeps every other unknown field.
		self.assertIn("$schema", self.written("complete"))

	def test_everything_the_add_on_writes_it_can_read_again(self):
		for name in fixture_names("valid"):
			with self.subTest(fixture=name):
				text = checklist.dumps(checklist.loads(fixture_text("valid", name)))
				self.assertIsInstance(checklist.loads(text), checklist.Checklist)

	def test_writing_the_same_checklist_twice_gives_the_same_file(self):
		# The rules canonicalise the document they were handed, so the text
		# they produce is a fixed point: a session of a hundred changes leaves
		# a hundred identical rewrites of the parts nobody touched.
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertEqual(checklist.dumps(loaded), checklist.dumps(loaded))

	def test_an_item_is_written_on_a_line_of_its_own(self):
		# Section 2, and the shape every example in the documentation is drawn
		# in: `text` and `note` are edited by hand, and an item opened out over
		# seven lines would turn a checklist of sixty into a file of four
		# hundred.
		lines = checklist.dumps(checklist.loads(fixture_text("valid", "complete"))).splitlines()
		items = [line.strip().rstrip(",") for line in lines if line.strip().startswith('{"id"')]
		self.assertEqual(len(items), 4)
		for item in items:
			with self.subTest(item=item):
				self.assertIsInstance(json.loads(item), dict)

	def test_the_document_and_its_sections_are_opened_out(self):
		# The three levels that are the structure of a checklist; everything
		# inside an item is on the item's own line.
		text = checklist.dumps(checklist.loads(fixture_text("valid", "complete")))
		self.assertIn('\n  "sections": [\n', text)
		self.assertIn('\n      "items": [\n', text)

	def test_a_section_holding_no_items_keeps_an_empty_array(self):
		written = checklist.dumps(checklist.loads(fixture_text("valid", "empty-items")))
		self.assertIn('"items": []', written)

	def test_an_unknown_field_is_written_compactly_however_deep_it_goes(self):
		# Section 2: the add-on knows nothing of the shape of such a field, and
		# has no grounds for opening that shape out.
		loaded = checklist.loads(
			json.dumps(
				{
					"checklist_name": "x",
					"meta": {"agent": "an agent", "runs": [1, 2]},
					"sections": [{"section_name": "s", "items": []}],
				},
			),
		)
		self.assertIn('"meta": {"agent": "an agent", "runs": [1, 2]}', checklist.dumps(loaded))

	def test_writing_a_file_the_add_on_wrote_changes_nothing_in_it(self):
		# Stronger than the fixed point above, because it goes back through the
		# parser: after the first save of a session, the hundreds that follow
		# leave every part nobody touched exactly as it was.
		once = checklist.dumps(checklist.loads(fixture_text("valid", "complete")))
		self.assertEqual(checklist.dumps(checklist.loads(once)), once)

	def test_the_file_stays_one_a_person_can_edit(self):
		# Checklists are written by hand, and the add-on hands the file back to
		# whoever wrote it: indented, with the words in it rather than escapes,
		# and ending in a newline like any other text file.
		loaded = checklist.loads(
			json.dumps({"checklist_name": "Тест", "sections": [{"section_name": "Розділ", "items": []}]}),
		)
		text = checklist.dumps(loaded)
		self.assertIn('"checklist_name": "Тест"', text)
		self.assertIn('\n  "sections"', text)
		self.assertTrue(text.endswith("\n"))


class TestRecordingAChange(OnDisk):
	"""Section 2: a change to the data rewrites the whole file at once.

	There is no deferred write in the add-on, and no discipline anywhere about
	when the file reaches the disk — so the change and the write are one
	operation, and the model offers no way to make the first without the
	second. Each test here reads the file back, because the file is the only
	thing the rule is about.
	"""

	def test_a_status_reaches_the_file_at_once(self):
		loaded = self.loaded()
		loaded.sections[0].items[0].record_status(status.PASSED)
		self.assertEqual(self.on_disk(loaded)["sections"][0]["items"][0]["status"], "passed")

	def test_the_model_shows_the_change_as_well_as_the_file(self):
		loaded = self.loaded()
		loaded.sections[0].items[0].record_status(status.FAILED)
		self.assertEqual(loaded.sections[0].items[0].status, "failed")

	def test_a_comment_reaches_the_file_at_once(self):
		loaded = self.loaded()
		loaded.sections[0].items[0].record(status.PENDING, "Slow, but it works")
		self.assertEqual(self.on_disk(loaded)["sections"][0]["items"][0]["comment"], "Slow, but it works")

	def test_a_blank_comment_never_reaches_the_file(self):
		loaded = self.loaded()
		loaded.sections[0].items[0].record(status.PENDING, "   ")
		self.assertNotIn("comment", self.on_disk(loaded)["sections"][0]["items"][0])
		self.assertIsNone(loaded.sections[0].items[0].comment)

	def test_erasing_a_comment_takes_it_out_of_the_file(self):
		loaded = self.loaded("complete")
		loaded.sections[0].items[2].record(status.FAILED, None)
		self.assertNotIn("comment", self.on_disk(loaded)["sections"][0]["items"][2])

	def test_a_save_of_both_fields_writes_the_file_once(self):
		# Section 3.3.1: the Save button of the item dialog is one command, so
		# it is one rewrite of the file rather than one per field. Of two
		# writes the second may fail, which would leave the disk holding half
		# of a change section 4 then says nothing at all about.
		loaded = self.loaded()
		with mock.patch("core.disk.write", wraps=disk.write) as written:
			loaded.sections[0].items[0].record(status.FAILED, "Phone has no label")
		self.assertEqual(written.call_count, 1)
		item = self.on_disk(loaded)["sections"][0]["items"][0]
		self.assertEqual(item["status"], "failed")
		self.assertEqual(item["comment"], "Phone has no label")

	def test_a_save_with_a_status_outside_the_five_writes_nothing_at_all(self):
		# Not even the comment, which is the half that would otherwise reach
		# the disk before the status was looked at.
		loaded = self.loaded()
		with self.assertRaises(ValueError):
			loaded.sections[0].items[0].record("done", "Phone has no label")
		self.assertNotIn("comment", self.on_disk(loaded)["sections"][0]["items"][0])

	def test_a_change_keeps_what_the_add_on_knows_nothing_about(self):
		# The rule this ticket exists for. Without it the first press of the
		# space bar would erase whatever an author or an agent had written into
		# the file beside the fields the add-on happens to know (section 2).
		loaded = self.loaded("unknown-fields")
		loaded.sections[0].items[0].record_status(status.PASSED)
		document = self.on_disk(loaded)
		self.assertEqual(document["generated_by"], "an agent")
		self.assertEqual(document["sections"][0]["severity"], "high")
		self.assertEqual(document["sections"][0]["items"][0]["ticket"], "AX-42")
		statuses = [item["status"] for section in document["sections"] for item in section["items"]]
		self.assertEqual(statuses, ["passed"])

	def test_a_status_outside_the_five_never_reaches_the_file(self):
		# Section 2 makes an unrecognised status fatal on read, so writing one
		# would leave a file the add-on can no longer open. The shell cannot
		# produce one — the status is picked from a `wx.Choice` (section 3.3.1) —
		# which makes this a programming error rather than a refusal.
		loaded = self.loaded()
		with self.assertRaises(ValueError):
			loaded.sections[0].items[0].record_status("done")
		self.assertNotIn("status", self.on_disk(loaded)["sections"][0]["items"][0])

	def test_the_file_is_written_without_a_byte_order_mark(self):
		# Section 2: a mark at the front is tolerated on the way in and never
		# put there on the way out.
		loaded = self.loaded()
		loaded.sections[0].items[0].record_status(status.PASSED)
		assert loaded.path is not None
		self.assertFalse(loaded.path.read_bytes().startswith(b"\xef\xbb\xbf"))

	def test_the_file_is_written_as_utf8(self):
		loaded = self.loaded()
		loaded.sections[0].items[0].record(status.PENDING, "Кирилиця")
		assert loaded.path is not None
		self.assertIn("Кирилиця".encode(), loaded.path.read_bytes())

	def test_nothing_is_left_lying_beside_the_checklist(self):
		# The file the write goes through first is swept up behind it, whether
		# the write got there or not.
		loaded = self.loaded()
		loaded.sections[0].items[0].record_status(status.PASSED)
		assert loaded.path is not None
		self.assertEqual([path.name for path in loaded.path.parent.iterdir()], ["checklist.json"])

	def test_a_write_that_fails_leaves_the_file_as_it_was(self):
		# Section 2: the change reaches the disk whole or not at all. Writing
		# straight into the checklist would empty it before filling it again,
		# and this add-on runs inside a screen reader it is able to bring down.
		loaded = self.loaded("complete")
		before = self.on_disk(loaded)
		with mock.patch("os.replace", side_effect=OSError("no swap for you")):
			with self.assertRaises(OSError):
				loaded.sections[0].items[0].record_status(status.FAILED)
		self.assertEqual(self.on_disk(loaded), before)
		assert loaded.path is not None
		self.assertEqual([path.name for path in loaded.path.parent.iterdir()], ["checklist.json"])

	def test_a_checklist_that_came_from_text_has_no_file_to_write_to(self):
		# `loads` is the parsing seam, not a way to hold a checklist: what the
		# add-on works with always came from a file it can write back to.
		loaded = checklist.loads(fixture_text("valid", "minimal"))
		self.assertIsNone(loaded.path)
		with self.assertRaises(ValueError):
			loaded.sections[0].items[0].record_status(status.PASSED)


class TestWhatASaveChanges(unittest.TestCase):
	"""Section 3.3.1: a save speaks only what really changed, and nothing else.

	The same comparison answers three questions — whether to write at all,
	which words to say, and whether a status has just closed the last pending
	item — so it is made once and asked here on its own. Nothing is written by
	any of this: the question comes before the write.
	"""

	def item(self, name: str = "complete", index: int = 0) -> checklist.Item:
		"""One item of the valid fixture `name`, read from text and unwritable."""
		return checklist.loads(fixture_text("valid", name)).sections[0].items[index]

	def test_a_save_that_moved_neither_field_changes_nothing(self):
		# The Save button doing what Cancel does: no file, no word.
		item = self.item()
		change = checklist.Change.of(item, status.PASSED, None)
		self.assertFalse(change.anything)
		self.assertIsNone(change.status)
		self.assertIs(change.comment, checklist.CommentChange.UNCHANGED)

	def test_a_status_that_moved_is_the_status_to_write(self):
		change = checklist.Change.of(self.item(), status.BLOCKED, None)
		self.assertEqual(change.status, status.BLOCKED)
		self.assertIs(change.comment, checklist.CommentChange.UNCHANGED)
		self.assertTrue(change.anything)

	def test_a_comment_where_there_was_none_is_saved(self):
		change = checklist.Change.of(self.item(), status.PASSED, "Slow, but it works")
		self.assertIsNone(change.status)
		self.assertIs(change.comment, checklist.CommentChange.SAVED)

	def test_a_comment_written_over_is_saved(self):
		change = checklist.Change.of(self.item(index=2), status.FAILED, "No label on Phone either")
		self.assertIs(change.comment, checklist.CommentChange.SAVED)

	def test_a_comment_emptied_is_deleted(self):
		change = checklist.Change.of(self.item(index=2), status.FAILED, "")
		self.assertIs(change.comment, checklist.CommentChange.DELETED)
		self.assertTrue(change.anything)

	def test_a_comment_left_holding_spaces_is_deleted_too(self):
		# Section 2 has "no comment" and "an empty comment" as one state, and
		# whitespace is that state as much as an empty string is.
		change = checklist.Change.of(self.item(index=2), status.FAILED, "   ")
		self.assertIs(change.comment, checklist.CommentChange.DELETED)

	def test_spaces_typed_where_there_was_no_comment_are_no_change(self):
		# The other side of the same rule: nothing was deleted, because there
		# was nothing there. A save of this alone says nothing and writes
		# nothing.
		change = checklist.Change.of(self.item(), status.PASSED, "  \n ")
		self.assertIs(change.comment, checklist.CommentChange.UNCHANGED)
		self.assertFalse(change.anything)

	def test_both_fields_move_at_once(self):
		change = checklist.Change.of(self.item(), status.FAILED, "Nothing is announced")
		self.assertEqual(change.status, status.FAILED)
		self.assertIs(change.comment, checklist.CommentChange.SAVED)


class TestResetting(OnDisk):
	"""Section 3.2.2 and section 5: a reset clears statuses *and* comments.

	A comment that outlived a reset would hang on a `pending` item and say
	"failed, because X" about an item nobody has checked — and it would be
	spoken (section 3.2.2). The write rules make the file follow at once, as
	they do for any other change.
	"""

	def test_resetting_a_section_clears_its_statuses_and_comments(self):
		loaded = self.loaded("complete")
		loaded.sections[0].reset()
		items = self.on_disk(loaded)["sections"][0]["items"]
		self.assertEqual([item["status"] for item in items], ["pending", "pending", "pending"])
		self.assertTrue(all("comment" not in item for item in items))

	def test_resetting_a_section_leaves_the_others_alone(self):
		loaded = self.loaded("complete")
		loaded.sections[1].items[0].record_status(status.PASSED)
		loaded.sections[0].reset()
		self.assertEqual(self.on_disk(loaded)["sections"][1]["items"][0]["status"], "passed")

	def test_resetting_a_section_keeps_the_notes_the_author_wrote(self):
		# Section 2: `note` belongs to the author of the checklist and survives
		# a reset; `comment` belongs to the tester and does not.
		loaded = self.loaded("complete")
		loaded.sections[0].reset()
		self.assertEqual(self.on_disk(loaded)["sections"][0]["items"][1]["note"], "Try Tab and Shift+Tab")

	def test_resetting_the_checklist_clears_every_section(self):
		loaded = self.loaded("complete")
		loaded.reset()
		items = [item for section in self.on_disk(loaded)["sections"] for item in section["items"]]
		self.assertEqual({item["status"] for item in items}, {"pending"})
		self.assertTrue(all("comment" not in item for item in items))

	def test_resetting_keeps_what_the_add_on_knows_nothing_about(self):
		loaded = self.loaded("complete")
		loaded.reset()
		self.assertIn("$schema", self.on_disk(loaded))

	def test_resetting_keeps_unknown_fields_at_every_level(self):
		# A reset is the change with the most to erase — every item of every
		# section — so the rule of section 2 is worth asking of it in full,
		# and not only of the document it is written at the top of.
		loaded = self.loaded("unknown-fields")
		loaded.reset()
		document = self.on_disk(loaded)
		self.assertEqual(document["generated_by"], "an agent")
		self.assertEqual(document["sections"][0]["severity"], "high")
		self.assertEqual(document["sections"][0]["items"][0]["ticket"], "AX-42")
