# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Reading and writing the checklist file the rest of the add-on works with.

The format, the validation contract and the rules of writing are specified in
section 2 of docs/requirements.md. The contract is checked in one pass at load
time, and any breach refuses the file whole: the alternative is an exception in
the middle of a session, with the focus in the application under test and NVDA
suddenly silent. A blind tester sees no traceback, and one clear refusal at
load beats silence an hour into the run.

**There is no `save`.** Section 2 has every change to the data rewrite the
whole file at once, with no exceptions and no discipline anywhere about when
the file reaches the disk — so the change and the write are one operation
(`record_status`, `record_comment`, `reset`), and nothing here offers a way to
make the first without the second. A `save()` the shell had to remember to call
would be that discipline, and the deferred write it invites is what section 2
paid off when the double press of the space bar went away.

**What is written is the document that was read.** Saving mutates the parsed
structure rather than assembling a fresh one out of the fields this module
knows, which is what keeps unknown fields alive: without it the first press of
the space bar would erase whatever an author or an agent had written into the
file alongside them.

**Why the refusal carries no text.** Section 2 wants one source of the reason
for the whole add-on, and section 4 sends it to two places: a short spoken
message when a file loaded without the user asking, and the concrete reason —
which field, which item, which value — when the user has just picked the file
themselves. Both are interface strings wrapped in `_()`, and `_()` cannot live
here (see `core/__init__.py`). So the cut is the one the status dictionary
already makes: this module names the breach as a `Problem`, and the shell turns
it into a sentence, still from one table. Nothing here is ever shown to anyone.
"""

import dataclasses
import enum
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeGuard, cast

from . import status

#: The newest format version this add-on understands. A file that declares more
#: than this is refused with a message of its own: section 7.1 rests the whole
#: meaning of the major version number on an old add-on refusing a newer file,
#: because it is the old one that will meet it.
KNOWN_FORMAT_VERSION = 1

#: Every format version this add-on can read. Section 2 states the rule as "a
#: version the add-on knows" rather than "no higher than the newest one",
#: because which versions a release reads is that release's decision: 2.0.0
#: will say whether it still opens version 1 files, and there is nothing to
#: settle that on today.
KNOWN_FORMAT_VERSIONS = frozenset({KNOWN_FORMAT_VERSION})


class ProblemKind(enum.Enum):
	"""What the validation contract of section 2 has against a file.

	One kind is one sentence in the shell's table, so the kinds are cut where
	the sentences differ rather than where the code happens to branch.
	"""

	#: The file is not JSON at all.
	NOT_JSON = enum.auto()
	#: The document, a section or an item is not a JSON object.
	NOT_AN_OBJECT = enum.auto()
	#: A required field is absent.
	MISSING_FIELD = enum.auto()
	NOT_A_STRING = enum.auto()
	NOT_AN_INTEGER = enum.auto()
	NOT_AN_ARRAY = enum.auto()
	#: `sections` is there but holds nothing; flat checklists are not supported.
	NO_SECTIONS = enum.auto()
	#: Two items claim the same `id`.
	DUPLICATE_ID = enum.auto()
	#: `status` holds something outside the five the format allows.
	UNKNOWN_STATUS = enum.auto()
	#: `format_version` holds a number this add-on does not know, and which is
	#: not a later one either — there is no update to send anyone to.
	UNKNOWN_FORMAT = enum.auto()
	#: The file was written by a newer version of the add-on.
	FUTURE_FORMAT = enum.auto()


@dataclasses.dataclass(frozen=True)
class Problem:
	"""Why a file was refused, in the terms section 2 asks for.

	`field` names the field the contract names, and is empty when the breach is
	not about one field. `value` is what stands in the file where the breach
	is, for the kinds that have something to show. The three indices place it:
	`item_id` is what the author would search the file for, and is None when
	the item has no usable one — which is itself one of the breaches.
	"""

	kind: ProblemKind
	field: str = ""
	value: object = None
	section_index: int | None = None
	item_index: int | None = None
	item_id: int | None = None


class ChecklistError(Exception):
	"""The add-on refuses to load a checklist file.

	`problem` carries the reason. The `FUTURE_FORMAT` kind is the one breach
	section 2 gives a message of its own; every other kind speaks with the same
	short one.
	"""

	def __init__(self, problem: Problem) -> None:
		super().__init__(problem)
		self.problem = problem


class Item:
	"""One thing to check.

	`rewrite` puts the whole checklist on disk. Every method here that changes
	the item calls it, because section 2 knows no other moment at which a
	change reaches the file. The item is handed the call rather than the
	checklist so that it needs to know only that its changes are made durable,
	not by whom or where.
	"""

	def __init__(self, data: dict[str, Any], rewrite: Callable[[], None]) -> None:
		super().__init__()
		self._data = data
		self._rewrite = rewrite

	@property
	def id(self) -> int:
		"""Identifier of the item, unique within the file.

		No behaviour of the add-on navigates by it — a position is a pair of
		indices everywhere (section 3.1). It exists so that an item stays the
		same item across edits of the file, which is what the report and the
		run history will have to point at.
		"""
		return self._data["id"]

	@property
	def text(self) -> str:
		"""The text of the item, the one the screen reader speaks."""
		return self._data["text"]

	@property
	def status(self) -> str:
		"""Outcome of the check, one of `status.STATUSES`.

		An item without the field is `pending`: that is how a checklist written
		by hand looks, and section 2 makes the absent field mean exactly that.
		"""
		return self._data.get("status", status.PENDING)

	@property
	def note(self) -> str | None:
		"""Hint written by the author, or None when the item carries no note."""
		return self._data.get("note")

	@property
	def comment(self) -> str | None:
		"""Conclusion written by the tester, or None when the item carries none.

		A comment that is empty or nothing but whitespace reads as an absent
		field. Section 2 treats "no comment" and "an empty comment" as one
		state with one canonical form, so that no consumer has to ask whether
		the string it got is really there.
		"""
		return _text(self._data.get("comment"))

	def record_status(self, value: str) -> None:
		"""Give the item this status and rewrite the file at once (section 2).

		A value outside the five is a programming error rather than a refusal.
		Nothing in the shell can produce one — the combo box of the item dialog
		is read-only precisely so that a typo cannot (section 3.3.1) — and
		writing one would leave a file the add-on can no longer open, because
		section 2 makes an unrecognised status fatal on read.
		"""
		if value not in status.STATUSES:
			raise ValueError(f"not a status of the format: {value!r}")
		self._data["status"] = value
		self._rewrite()

	def record_comment(self, value: str | None) -> None:
		"""Give the item this comment and rewrite the file at once (section 2).

		`None` erases it, and so does a comment that is empty or nothing but
		whitespace: section 2 has one state there, and `_text` is the one place
		that decides what counts as a comment at all.
		"""
		_set_comment(self._data, value)
		self._rewrite()


class Section:
	"""A named group of items.

	`rewrite` is the same call the items were given; see `Item`.
	"""

	def __init__(self, data: dict[str, Any], rewrite: Callable[[], None]) -> None:
		super().__init__()
		self._data = data
		self._rewrite = rewrite
		self._items = [Item(item, rewrite) for item in data["items"]]

	@property
	def name(self) -> str:
		"""Name of the section."""
		return self._data["section_name"]

	@property
	def items(self) -> Sequence[Item]:
		"""The items of this section, in the order the file lists them."""
		return self._items

	def reset(self) -> None:
		"""Put every item back to `pending`, erase every comment, write once.

		Section 3.2.2 erases the comments along with the statuses: one that
		outlived a reset would hang on an unchecked item claiming "failed,
		because X" — and it would be spoken, so it is not dead data but
		misleading data. The note stays; it belongs to the author of the
		checklist rather than to the run (section 2).

		The whole section is cleared before anything reaches the disk. One
		command is one rewrite of the file, not one per item.
		"""
		_clear(self._data)
		self._rewrite()


class Checklist:
	"""A checklist file that has passed the validation contract.

	Built by `load` and `loads`, which is where the contract is enforced;
	handing the constructor a document that has not been through it is a
	programming error, not a refusal.

	`path` is the file this checklist came from and the file its changes go
	back to. Only `loads` leaves it unset, because reading a checklist out of a
	string is the parsing seam rather than a way to hold one: what the add-on
	works with always came from a file.
	"""

	def __init__(self, document: dict[str, Any], path: Path | None = None) -> None:
		super().__init__()
		self._document = document
		self._path = path
		self._sections = [Section(section, self._rewrite) for section in document["sections"]]

	@property
	def path(self) -> Path | None:
		"""The file this checklist was read from, and is written back to."""
		return self._path

	@property
	def document(self) -> dict[str, Any]:
		"""The parsed file itself, unknown fields and all.

		The model reads through it rather than copying out of it, so that
		saving can mutate this structure instead of assembling a fresh object
		out of the fields the add-on happens to know. Without that, the first
		press of the space bar would erase whatever an author or an agent had
		written into the file alongside them (section 2).
		"""
		return self._document

	@property
	def name(self) -> str:
		"""Name of the checklist."""
		return self._document["checklist_name"]

	@property
	def sections(self) -> Sequence[Section]:
		"""The sections of the checklist, in the order the file lists them."""
		return self._sections

	def reset(self) -> None:
		"""Put every item of every section back to `pending`, and write once.

		The whole-progress reset of the GUI (section 5). Same rule as resetting
		one section, and the same reason the comments go with the statuses:
		what a reset does to a section is written down once, in `_clear`.
		"""
		for section in self._document["sections"]:
			_clear(section)
		self._rewrite()

	def _rewrite(self) -> None:
		"""Put the whole checklist on disk, now.

		Every change to the data comes through here, and nothing else does:
		section 2 admits no deferred write and no other moment at which the
		file is brought up to date.
		"""
		if self._path is None:
			raise ValueError("this checklist was read from text and has no file to write back to")
		# `newline` rather than the platform default: the add-on only ever runs
		# on Windows, but a checklist is a data file that usually lives in
		# version control beside the product under test, so what it writes is
		# the same on every machine that reads the repository.
		self._path.write_text(dumps(self), encoding="utf-8", newline="\n")


def dumps(checklist: Checklist) -> str:
	"""The text of the file the add-on writes for `checklist`.

	Brings the loaded document into the form section 2 calls for and hands it
	back as text. The document is canonicalised **in place**: saving mutates
	the structure that was read instead of assembling a fresh one, which is
	what carries unknown fields through a rewrite. After this the model and the
	file say the same thing, down to the fields that were left implicit.

	What changes is how the checklist is written down, never what it says: no
	status, comment, note or text means anything different afterwards. So this
	is not a change escaping without a write — there is nothing here to write.
	"""
	return json.dumps(_canonical(checklist.document), ensure_ascii=False, indent=2) + "\n"


def loads(text: str) -> Checklist:
	"""Read a checklist out of the contents of a file.

	The result has no path and so cannot be changed; `load` is what the add-on
	itself uses. Raises `ChecklistError` if the text is not JSON or breaks the
	contract.
	"""
	return _read(text, None)


def load(path: str | Path) -> Checklist:
	"""Read the checklist stored at `path`.

	Raises `ChecklistError` if the file cannot be read as a checklist, and
	`OSError` if it cannot be read at all. The two are kept apart on purpose: a
	file that is not there is answered by section 2 with "Checklist file not
	found" and a file dialog, not with the reason a file was refused.
	"""
	file = Path(path)
	try:
		# `utf-8-sig` rather than `utf-8`: checklists are written by hand on
		# Windows, editors there still put a byte order mark at the front, and
		# `json` chokes on it. Without a mark the two are the same codec. The
		# mark is not written back: `_rewrite` uses plain `utf-8` (section 2).
		text = file.read_text(encoding="utf-8-sig")
	except UnicodeDecodeError as error:
		# A checklist saved in some other encoding is a file that could not be
		# read, which section 4 answers with the same short message as broken
		# JSON. Letting the decoder's own exception out would be the silence in
		# the middle of a session that section 2 exists to prevent.
		raise _refusal(ProblemKind.NOT_JSON) from error
	return _read(text, file)


def _read(text: str, path: Path | None) -> Checklist:
	"""Parse and validate `text`, as a checklist stored at `path`."""
	try:
		document: Any = json.loads(text)
	except ValueError as error:
		# Section 4 puts a parse error under the same message as the rest of the
		# contract, so it may not escape as an exception of the `json` module:
		# the shell would then have two ways to learn the file did not load.
		raise _refusal(ProblemKind.NOT_JSON) from error
	return Checklist(_validated(document), path)


def _canonical(document: dict[str, Any]) -> dict[str, Any]:
	"""Bring `document` into the form section 2 gives a written file.

	Three rules, and they run over the document itself rather than over a copy
	of it, so that everything the add-on does not know about stays where the
	author put it.
	"""
	# Written out even when the file never carried it: section 7.1 rests the
	# whole meaning of the major version number on an old add-on recognising a
	# newer file, and it has only this field to recognise it by. Section 2 asks
	# for the version to be explicit, though, not for it to be raised — the
	# version the file declared is kept. That matters from the first release
	# that knows two of them: `KNOWN_FORMAT_VERSIONS` is a set because 2.0.0
	# may still read version 1 files, and restamping one as it saved would be
	# exactly the silent corruption section 7.1 is built to prevent.
	#
	# In a file that had no version the key lands last, after `sections`,
	# because that is where a plain assignment puts it; moving it to the front
	# would mean rebuilding the document, and the rule that keeps unknown
	# fields alive is that the document is never rebuilt.
	document["format_version"] = document.get("format_version", KNOWN_FORMAT_VERSION)
	for section in document["sections"]:
		for item in section["items"]:
			# Explicitly for every item, `pending` included. Reading treats an
			# absent field as `pending` all the same, but the tester who opens
			# the file should find the state of every item written down.
			item["status"] = item.get("status", status.PENDING)
			# The deliberate exception to "write it explicitly": a comment the
			# file carries but that says nothing goes out with the rest.
			_set_comment(item, item.get("comment"))
	return document


def _text(value: object) -> str | None:
	"""`value` if it is a string with something in it, and None otherwise.

	The one predicate behind the `comment` rule of section 2: "no comment" and
	"an empty comment" are one state, so a blank string and an absent field get
	the same answer everywhere — reading an item, writing the file, and erasing
	a comment on a reset. Spelling the test out at each place a comment is used
	is what section 2 forbids.
	"""
	if isinstance(value, str) and value.strip():
		return value
	return None


def _set_comment(item: dict[str, Any], value: object) -> None:
	"""Put `value` in the comment of `item`, in the one form the format has.

	Anything that is not a string with something in it takes the key out
	altogether: that is what "no comment" looks like in a file, and it keeps
	the document from ever holding a shape — a JSON null — that the validation
	contract would refuse to read back.
	"""
	text = _text(value)
	if text is None:
		_ = item.pop("comment", None)
	else:
		item["comment"] = text


def _clear(section: dict[str, Any]) -> None:
	"""Put every item of `section` back to `pending` and drop its comment.

	Without writing: the caller decides when, and there is exactly one write
	per command (sections 3.2.2 and 5).
	"""
	for item in section["items"]:
		item["status"] = status.PENDING
		_set_comment(item, None)


@dataclasses.dataclass(frozen=True)
class _Where:
	"""Where in the document the pass currently is."""

	section_index: int | None = None
	item_index: int | None = None
	item_id: int | None = None


_NOWHERE = _Where()

#: Tells "the field is absent" apart from "the field holds JSON null".
_MISSING = object()


def _refusal(
	kind: ProblemKind,
	where: _Where = _NOWHERE,
	field: str = "",
	value: object = None,
) -> ChecklistError:
	"""The exception that refuses a file, with the reason filled in."""
	return ChecklistError(
		Problem(
			kind=kind,
			field=field,
			value=value,
			section_index=where.section_index,
			item_index=where.item_index,
			item_id=where.item_id,
		),
	)


def _is_integer(value: object) -> TypeGuard[int]:
	"""Whether `value` is a whole number as the format means one.

	JSON `true` parses to a Python bool, and a bool is an int; a checklist that
	said `"id": true` would otherwise pass for a numbered item.
	"""
	return isinstance(value, int) and not isinstance(value, bool)


def _read_object(value: Any, where: _Where) -> dict[str, Any]:
	"""Require `value` to be a JSON object, and hand it back as a mapping."""
	if not isinstance(value, dict):
		raise _refusal(ProblemKind.NOT_AN_OBJECT, where)
	# JSON parses to `Any`, and narrowing it leaves the key and value types
	# unknown; the check above is what makes the cast true. JSON object keys
	# are strings by the grammar, so nothing is being assumed here.
	return cast(dict[str, Any], value)


def _required(data: dict[str, Any], field: str, where: _Where) -> object:
	value = data.get(field, _MISSING)
	if value is _MISSING:
		raise _refusal(ProblemKind.MISSING_FIELD, where, field)
	return value


def _check_string(data: dict[str, Any], field: str, where: _Where) -> None:
	"""Require `field` to be there and to be a string."""
	value = _required(data, field, where)
	if not isinstance(value, str):
		raise _refusal(ProblemKind.NOT_A_STRING, where, field, value)


def _check_optional_string(data: dict[str, Any], field: str, where: _Where) -> None:
	"""Require `field`, if it is there at all, to be a string."""
	value = data.get(field, _MISSING)
	if value is not _MISSING and not isinstance(value, str):
		raise _refusal(ProblemKind.NOT_A_STRING, where, field, value)


def _read_array(data: dict[str, Any], field: str, where: _Where) -> list[Any]:
	"""Require `field` to be there and to be an array, and hand it back."""
	value = _required(data, field, where)
	if not isinstance(value, list):
		raise _refusal(ProblemKind.NOT_AN_ARRAY, where, field, value)
	return cast(list[Any], value)


def _read_integer(data: dict[str, Any], field: str, where: _Where) -> int:
	"""Require `field` to be there and to be a whole number, and hand it back."""
	value = _required(data, field, where)
	if not _is_integer(value):
		raise _refusal(ProblemKind.NOT_AN_INTEGER, where, field, value)
	return value


def _check_format_version(document: dict[str, Any]) -> None:
	"""Refuse a file from a newer format before judging it by this one's rules.

	This comes first in the pass, and that ordering is the point: a file
	written to a later format is entitled to break the rules of this one, so
	reporting one of those breaches instead would send the tester looking for
	a broken file that is not broken (section 2).
	"""
	version = document.get("format_version", _MISSING)
	if version is _MISSING:
		return
	if not _is_integer(version):
		raise _refusal(ProblemKind.NOT_AN_INTEGER, _NOWHERE, "format_version", version)
	if version > KNOWN_FORMAT_VERSION:
		raise _refusal(ProblemKind.FUTURE_FORMAT, _NOWHERE, "format_version", version)
	if version not in KNOWN_FORMAT_VERSIONS:
		# A version below the newest one we know is not a version at all: there
		# was never a format zero, so "update the add-on" would be the wrong
		# thing to say and the ordinary refusal is the right one.
		raise _refusal(ProblemKind.UNKNOWN_FORMAT, _NOWHERE, "format_version", version)


def _validated(document: Any) -> dict[str, Any]:
	"""Run the whole contract over a parsed document and hand it back.

	One pass, and it stops at the first breach: section 2 refuses the file
	whole either way, and a reason that names one field, one item and one value
	is what both the spoken message and the error dialog can use.

	`$schema` is not checked. Section 2 says the add-on neither reads nor
	writes it, which makes it an unknown field like any other; validating a
	field we then ignore would be the add-on having an opinion about someone
	else's tooling.
	"""
	mapping = _read_object(document, _NOWHERE)
	_check_format_version(mapping)
	_check_string(mapping, "checklist_name", _NOWHERE)
	sections = _read_array(mapping, "sections", _NOWHERE)
	if not sections:
		raise _refusal(ProblemKind.NO_SECTIONS, _NOWHERE, "sections")
	seen_ids: set[int] = set()
	for section_index, section in enumerate(sections):
		_validate_section(section, _Where(section_index=section_index), seen_ids)
	return mapping


def _validate_section(section: Any, where: _Where, seen_ids: set[int]) -> None:
	data = _read_object(section, where)
	_check_string(data, "section_name", where)
	for item_index, item in enumerate(_read_array(data, "items", where)):
		_validate_item(item, dataclasses.replace(where, item_index=item_index), seen_ids)


def _validate_item(item: Any, where: _Where, seen_ids: set[int]) -> None:
	data = _read_object(item, where)
	identifier = _read_integer(data, "id", where)
	# Everything after this point can name the item the way the author does.
	where = dataclasses.replace(where, item_id=identifier)
	if identifier in seen_ids:
		raise _refusal(ProblemKind.DUPLICATE_ID, where, "id", identifier)
	seen_ids.add(identifier)
	_check_string(data, "text", where)
	_validate_status(data, where)
	_check_optional_string(data, "note", where)
	_check_optional_string(data, "comment", where)


def _validate_status(item: dict[str, Any], where: _Where) -> None:
	"""An unrecognised status is fatal, and deliberately so.

	Section 2 forbids quietly normalising it to `pending`: the first change the
	tester makes rewrites the whole file, so normalising would erase a result
	someone had recorded there, with no way back.
	"""
	value = item.get("status", _MISSING)
	if value is _MISSING:
		return
	if value not in status.STATUSES:
		raise _refusal(ProblemKind.UNKNOWN_STATUS, where, "status", value)
