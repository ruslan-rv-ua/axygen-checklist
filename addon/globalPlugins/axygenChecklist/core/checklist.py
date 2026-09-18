# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Reading a checklist file into the model the rest of the add-on works with.

The format and the validation contract are specified in section 2 of
docs/requirements.md. The contract is checked in one pass at load time, and any
breach refuses the file whole: the alternative is an exception in the middle of
a session, with the focus in the application under test and NVDA suddenly
silent. A blind tester sees no traceback, and one clear refusal at load beats
silence an hour into the run.

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
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeGuard, cast

from . import status

#: The newest format version this add-on understands. A file that declares more
#: than this is refused with a message of its own: section 7.1 rests the whole
#: meaning of the major version number on an old add-on refusing a newer file,
#: because it is the old one that will meet it.
KNOWN_FORMAT_VERSION = 1


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
	"""One thing to check."""

	def __init__(self, data: dict[str, Any]) -> None:
		super().__init__()
		self._data = data

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
		comment = self._data.get("comment")
		return comment if comment is not None and comment.strip() else None


class Section:
	"""A named group of items."""

	def __init__(self, data: dict[str, Any]) -> None:
		super().__init__()
		self._data = data
		self._items = [Item(item) for item in data["items"]]

	@property
	def name(self) -> str:
		"""Name of the section."""
		return self._data["section_name"]

	@property
	def items(self) -> Sequence[Item]:
		"""The items of this section, in the order the file lists them."""
		return self._items


class Checklist:
	"""A checklist file that has passed the validation contract.

	Built by `load` and `loads`, which is where the contract is enforced;
	handing the constructor a document that has not been through it is a
	programming error, not a refusal.
	"""

	def __init__(self, document: dict[str, Any]) -> None:
		super().__init__()
		self._document = document
		self._sections = [Section(section) for section in document["sections"]]

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


def loads(text: str) -> Checklist:
	"""Read a checklist out of the contents of a file.

	Raises `ChecklistError` if the text is not JSON or breaks the contract.
	"""
	try:
		document: Any = json.loads(text)
	except ValueError as error:
		# Section 4 puts a parse error under the same message as the rest of the
		# contract, so it may not escape as an exception of the `json` module:
		# the shell would then have two ways to learn the file did not load.
		raise _refusal(ProblemKind.NOT_JSON) from error
	return Checklist(_validated(document))


def load(path: str | Path) -> Checklist:
	"""Read the checklist stored at `path`.

	Raises `ChecklistError` if the file cannot be read as a checklist, and
	`OSError` if it cannot be read at all. The two are kept apart on purpose: a
	file that is not there is answered by section 2 with "Checklist file not
	found" and a file dialog, not with the reason a file was refused.
	"""
	try:
		# `utf-8-sig` rather than `utf-8`: checklists are written by hand on
		# Windows, editors there still put a byte order mark at the front, and
		# `json` chokes on it. Without a mark the two are the same codec.
		text = Path(path).read_text(encoding="utf-8-sig")
	except UnicodeDecodeError as error:
		# A checklist saved in some other encoding is a file that could not be
		# read, which section 4 answers with the same short message as broken
		# JSON. Letting the decoder's own exception out would be the silence in
		# the middle of a session that section 2 exists to prevent.
		raise _refusal(ProblemKind.NOT_JSON) from error
	return loads(text)


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
