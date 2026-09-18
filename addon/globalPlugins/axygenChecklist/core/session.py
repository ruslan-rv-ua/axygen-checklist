# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Where the tester was when the screen reader last stopped.

Section 2 of docs/requirements.md keeps the path of the active checklist and
the pair of indices the tester stood on in `state.json`, so that a restart of
NVDA puts them back where they were. The write is immediate — on every change
of the position, navigation included — for the reason the checklist is written
immediately: there is no deferred write anywhere in this add-on, and a second
writing mechanism with a discipline of its own would take back the debt section
2 has just paid off.

**This file is a cache, and everything here follows from that.** Section 7.1
puts it outside the version contract: the add-on builds it itself, and what it
holds is a place, not a result. So a file that cannot be read is discarded
whole, silently — there is nothing to recover and nobody asked for anything —
and nothing here ever raises on the way in. It also means the two rules the
checklist format lives by are deliberately absent: no version field, because a
version would promise a migration that a discarded cache never needs, and no
unknown fields carried through a rewrite, because that rule protects what
somebody else wrote into the tester's own file and nobody else writes here.

**It is read in pieces rather than all or nothing.** A path that arrives
without a usable position is still a path: the file dialog starts its browsing
from it (section 3.2.2), and that is wanted exactly when something else has
gone wrong.

Where the file lies is not settled here. The core is never told how to find
anything (see `core/__init__.py`); what arrives is a ready path.
"""

import dataclasses
import json
from pathlib import Path
from typing import Any, cast

from . import disk
from .navigation import Position


@dataclasses.dataclass(frozen=True)
class Session:
	"""The checklist that was open, and where in it the tester stood.

	Both halves are optional, and each absence means something of its own. No
	checklist is the state before the first file has ever been opened, and the
	state after a cache too damaged to read. No position is a checklist there
	is nowhere to stand in: section 2 asks a file for at least one section and
	never for a minimum of items, so a checklist of empty sections is valid.
	"""

	checklist: Path | None = None
	position: Position | None = None

	def position_in(self, checklist: Path) -> Position | None:
		"""Where the tester stood in the checklist at `checklist`, or None.

		Opening a file and restoring one at start-up are the same operation,
		differing only in where the path came from (section 3.2.2), and this is
		the one place where that difference shows: the path the file dialog
		hands over may name any file on the disk, while the indices held here
		were measured in whichever file was open when they were written. So
		they are asked for **by path**, and another file gets None — indices
		into a structure nobody opened describe nothing, and section 3.2.2
		starts such a file at its first item.

		Whether the indices still name a real place in the file they belong to
		is a different question, and `navigation.resume` answers it.
		"""
		if self.checklist != checklist:
			return None
		return self.position


def load(path: Path) -> Session:
	"""Read the session stored at `path`, or an empty one if it cannot be read.

	Never raises. Every way this can fail — the file is not there, cannot be
	opened, is not JSON, or holds something other than a session — has the same
	answer, and section 2 gives it: the cache is discarded whole and the add-on
	starts as though it had never been written.
	"""
	try:
		text = path.read_text(encoding="utf-8")
		document: Any = json.loads(text)
	except (OSError, ValueError):
		return Session()
	if not isinstance(document, dict):
		return Session()
	# JSON parses to `Any`, and narrowing it leaves the key and value types
	# unknown; the check above is what makes the cast true. JSON object keys are
	# strings by the grammar, so nothing is being assumed here.
	fields = cast(dict[str, Any], document)
	checklist = _path(fields.get("checklist"))
	if checklist is None:
		# A position without a file to open is a pair of numbers about nothing.
		return Session()
	return Session(checklist, _position(fields))


def save(path: Path, session: Session) -> None:
	"""Put `session` at `path`, now and whole (section 2).

	Raises `OSError` if it did not reach the disk. What to do about that is the
	caller's: section 2 answers it with a line in the log and nothing spoken,
	because this runs on every press of a navigation key and what is lost is
	the place rather than the run.
	"""
	document: dict[str, Any] = {}
	if session.checklist is not None:
		document["checklist"] = str(session.checklist)
	if session.position is not None:
		document["section"] = session.position.section
		document["item"] = session.position.item
	# The folder is the add-on's own inside NVDA's configuration directory
	# (section 2), and it is not there until the first checklist is opened.
	path.parent.mkdir(parents=True, exist_ok=True)
	disk.write(path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def _path(value: object) -> Path | None:
	"""`value` as the path of a checklist, or None when it is not one.

	A string with something in it, and one that could name a file at all: a
	null character inside it makes opening the path raise `ValueError` rather
	than the `OSError` everything else answers a bad path with, and that one
	would travel up through whoever opened it. JSON can spell `\\u0000`, and
	this file is a cache that may have been damaged by anything.

	Whether the file is still *there* is a different question, and not this
	one's: section 2 answers that out loud, with "Checklist file not found",
	while an unusable cache is discarded without a word.
	"""
	if isinstance(value, str) and value.strip() and "\0" not in value:
		return Path(value)
	return None


def _position(document: dict[str, Any]) -> Position | None:
	"""The position `document` holds, or None when it does not hold one.

	Half a position is no position: both indices have to be there and to be
	indices. A pair that no longer points anywhere in the checklist is not this
	function's business — the file it indexes into is not open yet, and
	`navigation.resume` is where that is settled.
	"""
	section = _index(document.get("section"))
	item = _index(document.get("item"))
	if section is None or item is None:
		return None
	return Position(section, item)


def _index(value: object) -> int | None:
	"""`value` as an index into the checklist, or None when it is not one.

	A whole number that is not negative. Both halves of that matter: JSON
	`true` parses to a Python bool and a bool is an int, and a negative index
	is legal Python that counts from the end of a list — either would quietly
	stand somewhere real and wrong.
	"""
	if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
		return value
	return None
