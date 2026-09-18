# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The words the add-on says, where saying them twice would be a defect.

A fixed sentence spoken in one place stays in that place. What lives here is
what is built out of data, or said from more than one window — the strings
section 2 and section 4 insist on keeping to a single source.

**The status dictionary, on the side of it that is a word.** Section 2 of
docs/requirements.md keeps the statuses as a single table for the whole add-on:
the word spoken on a change (section 4), the word spoken on request (section
3.3), the entries of the combo box of the item dialog (section 3.3.1) and the
prefix in the GUI tree (section 5) all come from one place, and a wording of
its own per context is forbidden. The table crosses the boundary between the
core and the shell, and the cut runs between the identifier and the word: the
identifiers are in `core.status`, and what a tester hears for them is an
interface string wrapped in `_()` and belongs here.

**What a tester hears about one item.** Sections 3.1 and 3.3 both speak an item
— on landing on it after a move, and on being asked to say it again — and
section 3.1 says outright that the two are the same. So the sentence is built
once, here, beside the words it is built out of.

The order is text → status → note, and it is deliberately the reverse of the
GUI tree, where the status stands in front of the text (section 5). A tree is
scanned down the page and the prefix filters it by ear from the first syllable;
here there is only the one item, and its text matters more than the verdict on
it.

**Why a file was refused.** Section 2 wants one source of that text for the
whole add-on, and sends it to two places. The short spoken form goes wherever a
checklist loaded without anyone asking — at start-up, from `state.json`. The
concrete reason — which field, which item, which value — goes into a window
whenever the tester picked the file themselves, by the file dialog (section
3.2.2) or by `Browse...` in the GUI (section 5). Both are built here, out of
the same `Problem`, because both are interface strings and the core names a
breach without ever wording it; see `core/checklist.py`.

**Why a change was refused.** Its opposite number, and here for the same
reason: section 4 gives every command that changes data the one phrase, and by
0.1.0 that is the quick toggle, the digits of the command mode, a reset of a
section or of the run, and a save from the item dialog. The core raises
`OSError` and words nothing there either.

**How far the run has got.** Section 4 speaks it at the end of the checklist
and section 3.3 for one section, out of the single count in `core.progress`;
the clause about failures is the same clause in both, so it is written once
below and neither caller spells it out.
"""

import json

import addonHandler

from .core import status
from .core.checklist import Item, Problem, ProblemKind
from .core.progress import Progress

addonHandler.initTranslation()


def status_word(value: str) -> str:
	"""The word a tester hears for the status `value`.

	`value` is one of `core.status.STATUSES`; the validation contract of
	section 2 admits nothing else into a checklist, and the combo box of the
	item dialog is read-only so that nothing else can be written back.

	The table is built on each call rather than once at import, so that the
	words follow the interface language of NVDA rather than whatever it was
	when the plugin was loaded.
	"""
	words = {
		# Translators: The status of a checklist item that has been checked and works.
		status.PASSED: _("passed"),
		# Translators: The status of a checklist item that has been checked and does not work.
		status.FAILED: _("failed"),
		# Translators: The status of a checklist item that could not be checked because
		# something else is in the way.
		status.BLOCKED: _("blocked"),
		# Translators: The status of a checklist item that was deliberately left unchecked.
		status.SKIPPED: _("skipped"),
		# Translators: The status of a checklist item that has not been checked yet.
		status.PENDING: _("not checked"),
	}
	return words[value]


def spoken_item(item: Item, section_name: str | None = None) -> str:
	"""What NVDA says about `item`, with the name of its section when asked for.

	Sections 3.1 and 3.3. The text, the status and — when the tester has left
	one — the fact that there is a comment make one phrase separated by commas;
	the note, and the section name in front of it all, are sentences of their
	own. The full stop is a pause, and it is what tells someone else's words
	apart by ear — the author's hint and the heading of a section — from what
	the add-on is saying about the item itself (section 3.3).

	`section_name` is given by the double press of a navigation key and by
	nothing else (section 3.1): a jump between sections has to announce where
	it landed, while a step to the next item would only be paying for a word
	the tester already knows on every single press.

	**The comment is marked, not read.** Section 3.3: a `note` is written by the
	author of the checklist to be heard every time, whereas a `comment` is
	written by the tester and may be a paragraph — speaking it on every pass
	would punish them for having been thorough. The marker costs two words, and
	the text itself is one press of the item dialog away.

	Fragments (section 2) carry no marker of their own and keep their
	delimiters: they lie *inside* the text that is being spoken, so hearing the
	address is already knowing there is something here to copy.
	"""
	spoken = [item.text, status_word(item.status)]
	if item.comment:
		# Translators: Spoken after the status of a checklist item the tester has
		# commented on. The comment itself is not spoken; the item dialog shows it.
		spoken.append(_("has a comment"))
	sentences = [", ".join(spoken)]
	if item.note:
		sentences.append(item.note)
	if section_name is not None:
		sentences.insert(0, section_name)
	return ". ".join(sentences)


def spoken_refusal(problem: Problem | None = None) -> str:
	"""What the tester hears when a checklist would not load (section 4).

	Four words for every breach of the validation contract, and a sentence of
	its own for the one breach that sends the tester somewhere else: a
	`format_version` from a later release means the add-on is old rather than
	the file broken, and "Error reading the file" would send them hunting for
	damage that is not there (section 2). Both are equally short; they differ
	only in where they send the person who hears them.

	`problem` is None when the file never got as far as being judged — it could
	not be opened at all. Section 2 puts that under the same four words: which
	encoding the author had in mind, or why the file would not open, is not
	something the add-on can say.

	This is the short spoken form, which section 4 allows only where the file
	loaded without the user asking for it. When the user has just picked the
	file themselves, the reason shown is the concrete one — which field, which
	item, which value — and it is built from the same `Problem`.
	"""
	if problem is not None and problem.kind is ProblemKind.FUTURE_FORMAT:
		# Translators: Spoken when a checklist file was written by a newer version of
		# the add-on than the one running, which cannot know what is in it.
		return _("This file was created by a newer version of the add-on")
	# Translators: Spoken when a checklist file cannot be read, or holds something
	# that is not a valid checklist.
	return _("Error reading the file")


def shown_refusal(problem: Problem | None = None) -> str:
	"""Why a file the tester picked themselves would not load (sections 2 and 4).

	The long form of `spoken_refusal`, and the one section 2 asks to name **which
	field, which item, which value**. It is shown in a window rather than spoken
	because the person who has just pressed "Open" is waiting for an answer and
	is entitled to know what is wrong; four words would send them away with
	nothing to go and fix.

	Two lines where there is a place to name: where in the file the breach is,
	and then what it is. The place counts sections and items from one, the way
	someone reading the JSON counts them, and names the `id` as well when the
	item has a usable one — that is the thing they will actually search the file
	for (section 2).

	`problem` is None when the file could not be opened at all. Nothing can be
	named then — not the field, not the value, and not the reason the file
	system had — so what is shown is the same short sentence the voice would
	have used.
	"""
	if problem is None:
		return spoken_refusal()
	place = _place(problem)
	breach = _breach(problem)
	return f"{place}\n{breach}" if place else breach


def _place(problem: Problem) -> str:
	"""Where in the file the breach is, or nothing when it is the file itself.

	Counted from one rather than from zero: these numbers exist to be matched
	against a file being read by a person, and a person counting the items of
	an array starts at the first one.
	"""
	if problem.section_index is None:
		return ""
	if problem.item_index is None:
		# Translators: Shown above the reason a checklist file was refused, naming where in
		# the file the problem is. {section} counts the sections of the file from one.
		return _("Section {section}").format(section=problem.section_index + 1)
	# Translators: Shown above the reason a checklist file was refused, naming where in the
	# file the problem is. {section} and {item} count the sections of the file, and the items
	# of that section, from one.
	place = _("Section {section}, item {item}").format(
		section=problem.section_index + 1,
		item=problem.item_index + 1,
	)
	if problem.item_id is None:
		return place
	# Translators: Added to the place a problem in a checklist file was found at, when the
	# item there carries a usable id. {id} is the value of the item's "id" field, which is
	# what the author of the file would search for.
	return place + _(", id {id}").format(id=problem.item_id)


def _breach(problem: Problem) -> str:
	"""What the validation contract of section 2 has against the file.

	One sentence per kind, and every kind answered here rather than through a
	default: a `match` with no catch-all is what makes the type check report a
	kind that has been added to the core and forgotten in this table. The words
	the tester reads are the only place the reason exists, so a kind arriving
	here nameless would refuse the file and say nothing about it.
	"""
	field = problem.field
	value = _value(problem.value)
	match problem.kind:
		case ProblemKind.FUTURE_FORMAT:
			# The one breach with a sentence of its own, and the same one the voice
			# says (section 2). There is no concrete reason to give: the file was
			# written to rules this add-on does not know, so the field and the value
			# are all there is, and "update the add-on" is the whole of the answer.
			return spoken_refusal(problem)
		case ProblemKind.NOT_JSON:
			# A file in some other encoding arrives here too: section 2 puts it
			# under the same answer, because which encoding the author had in mind
			# is not something the add-on can say.
			# Translators: Shown when a checklist file the tester picked cannot be parsed.
			return _("The file is not valid JSON.")
		case ProblemKind.NOT_AN_OBJECT:
			return _not_an_object(problem)
		case ProblemKind.MISSING_FIELD:
			# Translators: Shown when a checklist file the tester picked leaves out a field
			# the format requires. {field} is the name of that field, as it is spelled in the
			# file.
			return _('The required field "{field}" is missing.').format(field=field)
		case ProblemKind.NOT_A_STRING:
			# Translators: Shown when a field of a checklist file the tester picked holds the
			# wrong kind of value. {field} is the name of the field and {value} is what stands
			# there, written the way the file spells it.
			return _('The field "{field}" must be text, but holds {value}.').format(
				field=field,
				value=value,
			)
		case ProblemKind.NOT_AN_INTEGER:
			# Translators: Shown when a field of a checklist file the tester picked holds the
			# wrong kind of value. {field} is the name of the field and {value} is what stands
			# there, written the way the file spells it.
			return _('The field "{field}" must be a whole number, but holds {value}.').format(
				field=field,
				value=value,
			)
		case ProblemKind.NOT_AN_ARRAY:
			# Translators: Shown when a field of a checklist file the tester picked holds the
			# wrong kind of value. {field} is the name of the field and {value} is what stands
			# there, written the way the file spells it.
			return _('The field "{field}" must be a list, but holds {value}.').format(
				field=field,
				value=value,
			)
		case ProblemKind.NO_SECTIONS:
			# Translators: Shown when a checklist file the tester picked holds no sections at
			# all. Flat checklists without sections are not supported.
			return _('The field "sections" is empty; a checklist needs at least one section.')
		case ProblemKind.DUPLICATE_ID:
			# Translators: Shown when two items of a checklist file the tester picked carry
			# the same id, which has to be unique within the file. {value} is that id.
			return _("The id {value} belongs to more than one item.").format(value=value)
		case ProblemKind.UNKNOWN_STATUS:
			return _(
				# Translators: Shown when an item of a checklist file the tester picked carries a
				# status outside the five the format allows. {value} is what stands there, written
				# the way the file spells it.
				'The field "status" holds {value}, which is not one of '
				'"pending", "passed", "failed", "blocked" and "skipped".',
			).format(value=value)
		case ProblemKind.UNKNOWN_FORMAT:
			return _(
				# Translators: Shown when a checklist file the tester picked declares a format
				# version this add-on does not know and which is not a later one either, so there
				# is no update to send anyone to. {value} is the version the file declares.
				'The field "format_version" holds {value}, which is not a version of this format.',
			).format(
				value=value,
			)


def _not_an_object(problem: Problem) -> str:
	"""The one breach that has to name what it was looking at.

	Every other sentence names a field and stands on its own; this one says
	only that something is of the wrong shape, so the thing is named here rather
	than left to the line above — which is absent altogether when the breach is
	the file itself.
	"""
	if problem.section_index is None:
		# Translators: Shown when a checklist file the tester picked does not hold a JSON
		# object at its top level, so there is no checklist in it at all.
		return _("The file does not hold a checklist.")
	if problem.item_index is None:
		# Translators: Shown when an entry of the "sections" list of a checklist file is not
		# a section at all, but a number, a piece of text or a list.
		return _("This section is not written as a section.")
	# Translators: Shown when an entry of the "items" list of a checklist file is not an item
	# at all, but a number, a piece of text or a list.
	return _("This item is not written as an item.")


def _value(value: object) -> str:
	"""What stands in the file, written the way the file spells it.

	JSON rather than Python: the tester is going to open the file and look for
	this, and `true` and `True` are not the same string to search for. Anything
	that reaches here was parsed out of JSON in the first place, so there is
	nothing here that cannot be written back as JSON.
	"""
	return json.dumps(value, ensure_ascii=False)


def spoken_write_failure() -> str:
	"""What the tester hears when a change did not reach the disk (section 4).

	One phrase for every cause. A read-only file, an antivirus or an open
	editor holding it, a folder that left with its removable drive, a full
	disk — they all arrive the same way and they all send the tester to the
	same place: free the file and press again. The two messages on the way in
	(section 2) are two because they lead different ways, to a broken file or
	to an update of the add-on; there is no such split here, and what tells the
	causes apart stays in the log.

	Hearing it means the command was refused, not that the verdict came with a
	footnote: nothing else is spoken after it — no status word, no next item,
	no signal that the checklist is finished. The change does stay in memory,
	and any later write carries the whole file, so the first one that succeeds
	takes everything that has piled up with it.
	"""
	# Translators: Spoken when a change to the checklist could not be written to the
	# file, so it is in memory but not on disk.
	return _("Error writing the file")


def spoken_completion(counted: Progress) -> str:
	"""What the tester hears when nothing in the checklist is pending (section 4).

	Said whichever way the last verdict was recorded and whatever auto-advance
	is set to, because it is news about the run rather than about the command
	that ended it. Not said after a write that failed: the phrase would be
	claiming something about the run that is not on the disk.

	The count is of every item in the file, and it is a count of items looked
	at rather than of items that worked — section 3.3 refuses "done" for the
	same reason. A checklist holding a failure is finished work, and the
	failures are named after the total rather than taken out of it.
	"""
	spoken = ngettext(
		# Translators: Spoken when the last item of a checklist has been given a
		# status, so nothing in it is left unchecked. {count} is how many items
		# the checklist holds. The word "All" is dropped from the singular, where
		# it reads as a flourish over a count of one.
		"Checklist complete! {count} item processed",
		"Checklist complete! All {count} items processed",
		counted.total,
	)
	return spoken.format(count=counted.total) + _failures(counted.failed)


def spoken_progress(section_name: str, counted: Progress) -> str:
	"""How far the run has got through one section (section 3.3).

	What the `P` key of the command mode answers, and the reason it names the
	section out loud while a jump between sections does not (section 3.1): `P`
	is asked from nowhere in particular — "where am I?" — whereas a jump has
	just said where it went. The label is what makes the name an answer rather
	than a word the tester has to place.

	`counted` is taken over the **whole** section whatever the filter is doing
	(section 3.4). Counting only what is on show would say "0 of 1 processed"
	in a section the tester has nearly finished.

	Neither number needs a plural form of its own (section 6): they stand on
	their own rather than in front of a noun, and it is the noun that would
	have to agree with them.
	"""
	# Translators: Spoken for the current section of the checklist: its name, how many
	# of its items carry a verdict, and how many it holds in all.
	spoken = _("Section: {name}, {processed} of {total} processed")
	counts = spoken.format(name=section_name, processed=counted.processed, total=counted.total)
	return counts + _failures(counted.failed)


def _failures(count: int) -> str:
	"""The clause naming failures, and nothing at all when there were none.

	Section 4 adds it to the end of the checklist and section 3.3 to the
	progress of a section — the same words in both, and in both only when there
	is something to add. No noise when all is well, loud when it is not.
	"""
	if not count:
		return ""
	# Translators: Added after a count of checklist items when some of them failed,
	# running straight on from it: "All 12 items processed, 2 failed".
	return _(", {count} failed").format(count=count)
