# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Guards the Ukrainian catalogue against the two ways it silently goes stale.

Section 6 of `docs/requirements.md` writes the interface in English and ships
Ukrainian as a translation catalogue, which makes `nvda.po` a derived artefact
in the same sense as the schema of section 2: it restates, in another file,
something the add-on already says elsewhere. Derived artefacts drift, and both
directions of the drift here are silent.

A string added to the code and never carried into the catalogue falls back to
its English original. Nothing raises, nothing is logged, and the add-on goes on
working -- in the wrong language, for the only locale it has. Running `scons
pot` and `msgmerge` is the remedy and a habit, and a habit is what this suite
replaces everywhere else it can.

A string dropped from the code leaves its translation behind. That one costs
nothing at runtime, but it grows: a catalogue carrying entries for text nobody
can reach no longer answers the question it exists to answer, which is whether
the add-on is fully translated.

The third strand is the status table. Section 2 calls its five words the single
source of every status the add-on speaks, and gives them for `uk` normatively
-- the specification is where those words are decided, and the catalogue only
carries them. So the table is read out of the specification and matched against
the catalogue through `wording.py`, which holds the one mapping from a status
to the two strings it speaks. Three files, one word each, no copy typed here.

The parser below reads what `msgmerge` writes and nothing wider. A `.po` file
admits more than this (contexts, previous msgids, line wrapping we never ask
for), and a dependency that handled all of it would have to be pinned and
installed in CI for a file the project writes itself.
"""

import ast
import unittest
from pathlib import Path
from typing import Iterator, NamedTuple

from buildVars import i18nSources

from .support import REPO_ROOT, translation_lookups

CATALOGUE = REPO_ROOT / "addon" / "locale" / "uk" / "LC_MESSAGES" / "nvda.po"
SPECIFICATION = REPO_ROOT / "docs" / "requirements.md"
WORDING = REPO_ROOT / "addon" / "globalPlugins" / "axygenChecklist" / "wording.py"
PLUGIN = REPO_ROOT / "addon" / "globalPlugins" / "axygenChecklist" / "__init__.py"

#: The name of the add-on, which section 6 keeps the same in every locale.
PRODUCT_NAME = "Axygen Checklist"

#: The one script section 3.5 exempts from carrying a description, and the
#: reason it is named here rather than counted: the digits `1`-`5` are five
#: spellings of one command, bound only while the command mode is armed, and an
#: empty description is what keeps all five out of the Input Gestures dialog.
#: The exemption belongs to this script and to no other, so the test says which.
SETS_THE_STATUS = "script_setStatus"


class Description(NamedTuple):
	"""What a `@script` says about its command in the Input Gestures dialog."""

	msgid: str
	#: Whether the string goes through `_()`. Without it the dialog shows the
	#: English under a Ukrainian NVDA (section 6), and nothing else would tell:
	#: the string is in the catalogue either way, because the same words are
	#: written in the source either way.
	looked_up: bool


class StatusWords(NamedTuple):
	"""What one status of section 2 is spoken as, both columns of the table.

	The same pair travels from the specification, from `wording.py` and from the
	catalogue, and the three are compared as wholes; naming the columns is what
	makes the diff of a failure say which of them moved.
	"""

	word: str
	#: What stands in front of the text of an item in the tree of the GUI
	#: window, the separator included, and empty for the status that has none.
	prefix: str


class Entry(NamedTuple):
	"""One message of a catalogue, as the file spells it."""

	msgid: str
	#: The plural form of `msgid`, or `None` when the message has no plural.
	msgid_plural: str | None
	#: The translations: one for a message without a plural, and one per plural
	#: form of the language for a message with one.
	msgstrs: tuple[str, ...]
	#: `fuzzy` among them means `msgmerge` guessed the translation from a
	#: similar message and nobody has looked at it since.
	flags: frozenset[str]
	#: Whether the entry is commented out with `#~`, which is what `msgmerge`
	#: does to a translation whose message has left the code.
	obsolete: bool


def parse_catalogue(path: Path) -> list[Entry]:
	"""Every entry of the catalogue at `path`, header included.

	The header is the entry whose `msgid` is empty; callers that mean the
	messages skip it by name rather than by position.
	"""
	entries: list[Entry] = []
	for block in path.read_text(encoding="utf-8").split("\n\n"):
		entry = _parse_entry(block)
		if entry is not None:
			entries.append(entry)
	return entries


def _parse_entry(block: str) -> Entry | None:
	"""The entry `block` holds, or `None` when it holds only comments."""
	flags: set[str] = set()
	obsolete = False
	fields: dict[str, str] = {}
	field: str | None = None
	for line in block.split("\n"):
		if line.startswith("#~"):
			obsolete = True
			line = line[2:].strip()
		if line.startswith("#,"):
			flags.update(flag.strip() for flag in line[2:].split(","))
			continue
		if line.startswith("#") or not line.strip():
			continue
		if line.startswith('"'):
			# A continuation of the field opened above: gettext writes a long
			# message as an empty first line and one quoted chunk per line.
			assert field is not None, f"a continuation line with no field above it: {line}"
			fields[field] += _unquote(line)
			continue
		field, _space, quoted = line.partition(" ")
		fields[field] = _unquote(quoted)
	if "msgid" not in fields:
		return None
	plurals = sorted(name for name in fields if name.startswith("msgstr["))
	return Entry(
		msgid=fields["msgid"],
		msgid_plural=fields.get("msgid_plural"),
		msgstrs=tuple(fields[name] for name in plurals) if plurals else (fields.get("msgstr", ""),),
		flags=frozenset(flags),
		obsolete=obsolete,
	)


def _unquote(quoted: str) -> str:
	"""The text of one or more adjacent quoted chunks of a `.po` file.

	The escapes a catalogue uses are a subset of Python's, so the literal is
	read as one -- adjacent string literals concatenate there too, which is what
	a wrapped message is.
	"""
	return ast.literal_eval(quoted.strip())


def interface_strings() -> dict[str, list[Path]]:
	"""Every string the code hands a translation lookup, and where it is said.

	The files are the ones `buildVars.py` gives `scons pot`, so a source added
	to the build is covered here without being named twice.
	"""
	found: dict[str, list[Path]] = {}
	for path in sorted(_i18n_paths()):
		for text in translation_lookups(path):
			found.setdefault(text, []).append(path.relative_to(REPO_ROOT))
	return found


def _i18n_paths() -> Iterator[Path]:
	"""The files `buildVars.i18nSources` names."""
	for pattern in i18nSources:
		yield from REPO_ROOT.glob(pattern)


def script_descriptions() -> dict[str, Description | None]:
	"""What describes each command of the add-on, by the script it is written on.

	`None` where the `@script` carries no description at all, which section 3.5
	allows exactly one script to do.
	"""
	tree = ast.parse(PLUGIN.read_text(encoding="utf-8"), filename=str(PLUGIN))
	scripts = (
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.FunctionDef) and node.name.startswith("script_")
	)
	return {node.name: _description_on(node) for node in scripts}


def _description_on(node: ast.FunctionDef) -> Description | None:
	"""What `node`'s `@script` gives as its description, if it gives one."""
	for decorator in node.decorator_list:
		if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name):
			continue
		if decorator.func.id != "script":
			continue
		for keyword in decorator.keywords:
			if keyword.arg == "description":
				value = keyword.value
				return Description(
					msgid=_msgid_of(value),
					# Asked of the node rather than of the string that comes
					# back, because `_msgid_of` takes a bare literal too -- the
					# status table needs it to (section 2) -- and a description
					# written without `_()` is spelled exactly like one written
					# with it by the time it is a string.
					looked_up=_is_lookup(value),
				)
	return None


def _is_lookup(node: ast.expr) -> bool:
	"""Whether `node` passes its string through `_()` rather than standing as one."""
	return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"


def status_table_of_specification() -> dict[str, StatusWords]:
	"""The status table of section 2: the word and the tree prefix of each status.

	The table is found by its own heading row and read to the end of it, rather
	than by the shape of its rows. A three-celled row whose first cell is a
	quoted identifier is not a rare thing to write in a document of seven
	hundred lines, and a second one joining this table by accident would be a
	failure in the shape of a passing test.

	A status with no prefix -- `pending`, whose absence of one is what the tree
	says about it -- comes back with an empty string, which is what the add-on
	puts in front of its text.
	"""
	table: dict[str, StatusWords] = {}
	rows = iter(SPECIFICATION.read_text(encoding="utf-8").split("\n"))
	for line in rows:
		if _cells(line) == ["`status`", "Слово озвучення", "Префікс у дереві GUI"]:
			break
	else:
		raise AssertionError("the status table of section 2 is not where the parser looks for it")
	next(rows)  # The `|---|---|---|` that separates a heading from its body.
	for line in rows:
		cells = _cells(line)
		if len(cells) != 3:
			break
		name, word, prefix = cells
		table[name.strip("`").strip('"')] = StatusWords(
			word=word,
			prefix="" if prefix.startswith("*(") else prefix.strip("`"),
		)
	assert table, "the status table of section 2 has a heading and no rows"
	return table


def _cells(line: str) -> list[str]:
	"""The cells of `line`, when `line` is a row of a Markdown table."""
	stripped = line.strip()
	if not stripped.startswith("|"):
		return []
	return [cell.strip() for cell in stripped.strip("|").split("|")]


def status_msgids_of_wording() -> dict[str, StatusWords]:
	"""The msgid of the word and of the tree prefix `wording.py` gives each status.

	The one table the add-on speaks statuses from, read where it stands. A
	status whose prefix is not a lookup -- `pending` again -- comes back with an
	empty string for it, as the specification's own column does.
	"""
	tree = ast.parse(WORDING.read_text(encoding="utf-8"), filename=str(WORDING))
	for node in ast.walk(tree):
		if not isinstance(node, ast.Dict):
			continue
		rows = _status_rows(node)
		if rows:
			return rows
	raise AssertionError("the status table of wording.py is not where the parser looks for it")


def _status_rows(node: ast.Dict) -> dict[str, StatusWords]:
	"""The rows of `node`, or nothing at all when `node` is some other dict.

	All of it or none of it: a dict whose first entries happen to have the shape
	of the table would otherwise come back truncated, and be taken for the table
	by the caller, which asks only whether anything came back.
	"""
	rows: dict[str, StatusWords] = {}
	for key, value in zip(node.keys, node.values):
		if not isinstance(key, ast.Attribute) or not isinstance(key.value, ast.Name):
			return {}
		if key.value.id != "status" or not isinstance(value, ast.Call):
			return {}
		columns = {keyword.arg: keyword.value for keyword in value.keywords}
		if set(columns) != {"word", "prefix"}:
			return {}
		rows[key.attr.lower()] = StatusWords(
			word=_msgid_of(columns["word"]),
			prefix=_msgid_of(columns["prefix"]),
		)
	return rows


def _msgid_of(node: ast.expr) -> str:
	"""The msgid of `node`, or the literal itself when `node` is not a lookup.

	Both shapes stand in the table: every status but `pending` speaks its prefix
	through `_()`, and `pending` has a bare `""` where the others have a lookup,
	because the absence of a prefix is what the tree says about it (section 2).
	"""
	if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_":
		node = node.args[0]
	assert isinstance(node, ast.Constant) and isinstance(node.value, str), (
		"a column of the status table is neither a literal string nor a lookup on one"
	)
	return node.value


ENTRIES = parse_catalogue(CATALOGUE)
MESSAGES = [entry for entry in ENTRIES if entry.msgid and not entry.obsolete]
TRANSLATIONS = {entry.msgid: entry.msgstrs[0] for entry in MESSAGES}


class TheCatalogue(unittest.TestCase):
	def test_holds_a_translation_for_every_message(self) -> None:
		for entry in MESSAGES:
			with self.subTest(msgid=entry.msgid):
				self.assertTrue(
					all(entry.msgstrs),
					"has no Ukrainian translation; run `scons pot`, `msgmerge` and translate it",
				)

	def test_holds_every_plural_form_the_language_has(self) -> None:
		# Ukrainian has three, and section 6 sends a string with a noun after a
		# number through `ngettext` for exactly this reason. Two forms filled out
		# of three is what a half-finished entry looks like, and the message it
		# misses is the one heard on most numbers.
		for entry in MESSAGES:
			if entry.msgid_plural is None:
				continue
			with self.subTest(msgid=entry.msgid):
				self.assertEqual(len(entry.msgstrs), 3)

	def test_guesses_nothing(self) -> None:
		# `msgmerge` marks a translation it carried over from a similar message
		# `fuzzy`, and a fuzzy entry is not used at runtime: the message falls
		# back to English while the catalogue looks complete.
		for entry in MESSAGES:
			with self.subTest(msgid=entry.msgid):
				self.assertNotIn("fuzzy", entry.flags)

	def test_carries_nothing_the_code_has_dropped(self) -> None:
		# An obsolete entry is a translation whose message has left the code.
		# Keeping it is how a catalogue stops answering whether the add-on is
		# fully translated, which is the whole of what it is read for.
		self.assertEqual([entry.msgid for entry in ENTRIES if entry.obsolete], [])


class EveryInterfaceString(unittest.TestCase):
	def test_is_in_the_catalogue(self) -> None:
		# The failure this catches is a string added to the code by someone who
		# did not then run `scons pot` and `msgmerge`: it reaches a Ukrainian
		# NVDA in English, and nothing anywhere says so.
		known = {entry.msgid for entry in MESSAGES} | {
			entry.msgid_plural for entry in MESSAGES if entry.msgid_plural
		}
		for text, said_in in interface_strings().items():
			with self.subTest(text=text):
				self.assertIn(text, known, f"said in {', '.join(map(str, said_in))}, translated nowhere")

	def test_is_still_said_somewhere(self) -> None:
		# The other direction, and the reason `msgmerge` has to be run rather
		# than new entries appended by hand: a message that has left the code
		# keeps its translation until something looks.
		said = set(interface_strings())
		for entry in MESSAGES:
			with self.subTest(msgid=entry.msgid):
				self.assertIn(entry.msgid, said)


class EveryCommand(unittest.TestCase):
	def test_describes_itself_in_the_input_gestures_dialog(self) -> None:
		# Section 3.5 turns on this: the dialog is the whole answer to a key
		# taken by another add-on, and it takes the name of a command from the
		# `description` of its `@script`. A script without one is not listed
		# with a blank line -- `inputCore` skips it, so the command leaves the
		# dialog altogether, and the answer to a conflict leaves with it.
		undescribed = [name for name, described in script_descriptions().items() if described is None]
		self.assertEqual(undescribed, [SETS_THE_STATUS])

	def test_says_it_in_ukrainian(self) -> None:
		# Section 6 asks for the description to be wrapped in `_()`, "інакше
		# діалог «Жести вводу» показував би англійські описи в українському
		# NVDA". The wrapping is the whole of the requirement: the words reach
		# the catalogue from the source either way, so a description written
		# without it is a string that is translated and never looked up.
		for name, described in script_descriptions().items():
			if described is None:
				continue
			with self.subTest(script=name):
				self.assertTrue(described.looked_up, "the description does not go through `_()`")
				self.assertIn(described.msgid, TRANSLATIONS)


class TheProductName(unittest.TestCase):
	def test_is_the_same_string_in_ukrainian(self) -> None:
		# Section 6: the add-on is listed under this name in the Add-on Store,
		# carries it as the name of its folder in NVDA's configuration, and is
		# documented under it. A translated name would part company with all
		# three. The same string is the category of the add-on's commands in the
		# Input Gestures dialog, so that is English too.
		self.assertEqual(TRANSLATIONS.get(PRODUCT_NAME), PRODUCT_NAME)


class TheStatusWords(unittest.TestCase):
	def test_say_in_ukrainian_what_the_specification_says(self) -> None:
		# Section 2 gives these words for `uk` normatively, which makes the
		# specification where they are decided and the catalogue where they are
		# kept. The tie runs through `wording.py` because that is the one place
		# that knows which English message a status speaks.
		#
		# Both columns are compared for all five statuses at once, rather than a
		# status at a time: a word that moved to the wrong row and a status that
		# left the table are the same mistake read two ways, and a whole-table
		# diff says which of them happened.
		spoken = {
			name: StatusWords(word=_translated(msgids.word), prefix=_translated(msgids.prefix))
			for name, msgids in status_msgids_of_wording().items()
		}
		self.assertEqual(spoken, status_table_of_specification())


def _translated(msgid: str) -> str:
	"""What a Ukrainian NVDA says for `msgid`.

	A message the catalogue does not carry falls back to its English original,
	because that is what `gettext` does and therefore what the tester would
	hear; whether the catalogue carries it at all is `EveryInterfaceString`'s
	question, asked of every message rather than of these ten.

	The empty msgid needs no case of its own. It is the prefix `pending` does
	not have (section 2) rather than a message, and an empty original falls
	back to an empty string like any other.
	"""
	return TRANSLATIONS.get(msgid, msgid)


if __name__ == "__main__":
	unittest.main()
