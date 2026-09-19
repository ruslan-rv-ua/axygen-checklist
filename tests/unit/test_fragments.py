# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The fragment convention of section 2, rule by rule."""

import json
import unittest

from core import checklist, fragments

from .support import REPO_ROOT

#: The sample walked by hand to hear the `C` key of the command mode; see
#: `TestTheSample` at the bottom of this module for what is asked of it.
SAMPLE = REPO_ROOT / "samples" / "fragments-by-ear.json"


def loaded(**fields: str) -> checklist.Checklist:
	"""A checklist of one item carrying `fields`, read through the load pass."""
	document = {
		"checklist_name": "Base checklist",
		"sections": [{"section_name": "Controls", "items": [{"id": 1, "text": "An item", **fields}]}],
	}
	return checklist.loads(json.dumps(document))


def item(**fields: str) -> checklist.Item:
	"""The one item of `loaded`, for the tests that need no file around it."""
	return loaded(**fields).sections[0].items[0]


class TestPairs(unittest.TestCase):
	def test_a_pair_of_delimiters_gives_the_string_between_them(self):
		self.assertEqual(
			fragments.of("Open `http://localhost:8080` - the home page appears"),
			["http://localhost:8080"],
		)

	def test_pairs_are_taken_from_the_left(self):
		# Three pairs' worth of delimiters would be ambiguous read from the
		# right: what lies between the second and the third is ordinary text.
		self.assertEqual(fragments.of("`a`b`c`"), ["a", "c"])

	def test_a_lone_delimiter_makes_no_fragment(self):
		self.assertEqual(fragments.of("Press `Enter to continue"), [])

	def test_a_delimiter_left_over_after_a_pair_stays_ordinary_text(self):
		self.assertEqual(fragments.of("Type `a` or `b"), ["a"])


class TestLineBreaks(unittest.TestCase):
	"""Section 2: a fragment does not cross a line break.

	So the clipboard always holds one line, and the question of turning `\\n`
	into CRLF never comes up at all.
	"""

	def test_a_delimiter_does_not_pair_across_a_line_break(self):
		# The delimiter before `http://a` has nothing to pair with on its own
		# line, so it stays ordinary text; the pair on the second line is a
		# fragment as usual.
		self.assertEqual(fragments.of("Open `http://a\nand `b` here"), ["b"])

	def test_a_windows_line_break_ends_the_search_the_same_way(self):
		# Checklists are written by hand on Windows, so this is the break an
		# author is most likely to put in a `note`.
		self.assertEqual(fragments.of("Open `http://a\r\nand `b` here"), ["b"])

	def test_no_fragment_ever_holds_a_line_break(self):
		found = fragments.of("`a\nb`", "`c\r\nd`", "`e`\n`f`")
		self.assertEqual(found, ["e", "f"])
		for fragment in found:
			self.assertEqual(fragment.splitlines(), [fragment])


class TestEdges(unittest.TestCase):
	def test_spaces_just_inside_a_pair_are_trimmed(self):
		self.assertEqual(fragments.of("Run ` git status ` first"), ["git status"])

	def test_an_empty_pair_makes_no_fragment(self):
		# There is nothing to put in the clipboard, and `api.copyToClip` answers
		# an empty string with a silent `False` (section 2).
		self.assertEqual(fragments.of("Two delimiters `` in a row"), [])

	def test_a_pair_holding_only_spaces_makes_no_fragment(self):
		self.assertEqual(fragments.of("Two delimiters `   ` apart"), [])


class TestSources(unittest.TestCase):
	def test_the_sources_are_read_in_the_order_they_are_given(self):
		# Section 2: collected from `text` and `note`, `text` first, each in the
		# order the fragments appear in it.
		self.assertEqual(
			fragments.of(
				"Open `http://localhost:8080` and run `npm test`",
				"The port comes from `config.toml`",
			),
			["http://localhost:8080", "npm test", "config.toml"],
		)

	def test_a_source_that_is_absent_is_no_source_at_all(self):
		# An item without a `note` reads as None, and the caller should not have
		# to say so: `of(item.text, item.note)` is the whole of it.
		self.assertEqual(fragments.of("Open `http://localhost:8080`", None), ["http://localhost:8080"])


class TestDuplicates(unittest.TestCase):
	"""Section 2: exact duplicates collapse into one.

	The label in the dialog is the fragment itself, so two identical strings
	are two list entries a tester cannot tell apart.
	"""

	def test_a_repeated_fragment_is_listed_once(self):
		self.assertEqual(fragments.of("Run `git status`, read it, run `git status`"), ["git status"])

	def test_a_fragment_repeated_across_sources_is_listed_once(self):
		self.assertEqual(fragments.of("Open `config.toml`", "See `config.toml`"), ["config.toml"])

	def test_the_first_appearance_keeps_its_place(self):
		self.assertEqual(
			fragments.of("Run `npm test` then `npm run build` then `npm test`"),
			["npm test", "npm run build"],
		)

	def test_two_fragments_are_the_same_once_they_are_trimmed(self):
		# Trimming happens first, so what is compared is what would reach the
		# clipboard rather than what stood between the delimiters.
		self.assertEqual(fragments.of("Run `npm test` or ` npm test `"), ["npm test"])


class TestItems(unittest.TestCase):
	"""Which fields of an item its fragments are collected from (section 2)."""

	def test_an_item_takes_its_fragments_from_text_and_then_note(self):
		self.assertEqual(
			item(
				text="Open `http://localhost:8080` - the home page appears",
				note="The port comes from `config.toml`",
			).fragments,
			["http://localhost:8080", "config.toml"],
		)

	def test_an_item_without_a_note_has_only_the_fragments_of_its_text(self):
		self.assertEqual(item(text="Open `http://localhost:8080`").fragments, ["http://localhost:8080"])

	def test_an_item_without_fragments_has_none(self):
		self.assertEqual(item(text="Check that the buttons are reachable").fragments, [])

	def test_a_comment_is_not_a_source_of_fragments(self):
		# Section 2: `comment` belongs to the tester, and text is copied out of
		# it from the item dialog instead.
		self.assertEqual(item(text="An item", comment="I had to run `npm ci` first").fragments, [])


class TestNoEscape(unittest.TestCase):
	"""Section 2: a fragment that holds a delimiter is not expressible.

	The limit is named and accepted rather than worked around, so what is
	checked here is that no accidental escape has crept in — an author who
	tries one gets something they can see is wrong, not a silent half-fragment.
	"""

	def test_a_doubled_delimiter_is_not_an_escape(self):
		# Markdown would read ``a`` as a code span holding "a". Here the two
		# pairs each hold nothing, and nothing is what comes out.
		self.assertEqual(fragments.of("Use ``a`` here"), [])

	def test_a_delimiter_inside_a_fragment_ends_it(self):
		# Trying to write the single fragment "a`b" gets the pair closed early.
		self.assertEqual(fragments.of("Run `a`b`"), ["a"])


class TestValidation(unittest.TestCase):
	"""Section 2: fragments do not touch the validation contract.

	An odd delimiter, an empty pair, a delimiter in the middle of a word — all
	of it is ordinary text. `text` is the user's data, and the add-on has no
	right to refuse a checklist over a stray backtick.
	"""

	def test_a_stray_delimiter_is_not_a_violation(self):
		# The load pass is what would refuse the file, and it never looks at the
		# convention at all: whatever the delimiters do or fail to do here, the
		# item reads back exactly as it was written.
		wild = "Press `Enter, then `` twice, then a`b"
		self.assertEqual(item(text=wild, note="and `one more").text, wild)

	def test_the_delimiters_stay_in_the_text(self):
		# Section 2 shows the delimiters everywhere the text is shown: the file
		# is the source of truth, and a delimiter that can be seen is itself the
		# hint that there is something here to copy.
		loaded = item(text="Open `http://localhost:8080` now")
		self.assertEqual(loaded.text, "Open `http://localhost:8080` now")

	def test_a_rewrite_leaves_the_delimiters_where_they_were(self):
		written = checklist.dumps(loaded(text="Open `http://localhost:8080` now"))
		self.assertIn('"text": "Open `http://localhost:8080` now"', written)


class TestTheSample(unittest.TestCase):
	"""`samples/fragments-by-ear.json` is the file the `C` key is heard on.

	Section 3.2.2 answers with three different shapes depending on how many
	fragments the item carries: a sentence for none, the clipboard for one, a
	window for more. The sample exists so that all three can be walked in a
	single run, and an edit that took the last item of one kind away -- a
	backtick closed, a note reworded -- would leave the file perfectly valid
	and quietly stop covering a third of the command. Nothing else would
	notice, so the three kinds are counted here.
	"""

	def setUp(self):
		self.counts = [len(item.fragments) for item in checklist.load(SAMPLE).items]

	def test_an_item_answered_without_a_window_and_without_a_copy(self):
		self.assertIn(0, self.counts)

	def test_an_item_copied_at_once_without_a_window(self):
		self.assertIn(1, self.counts)

	def test_an_item_that_opens_the_dialog(self):
		self.assertTrue([count for count in self.counts if count > 1])
