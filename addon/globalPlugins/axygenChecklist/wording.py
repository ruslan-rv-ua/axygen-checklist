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
3.3), the entries of the status list of the item dialog (section 3.3.1) and the
prefix in the GUI tree (section 5) all come from one place, and a wording of
its own per context is forbidden. The table crosses the boundary between the
core and the shell, and the cut runs between the identifier and the word: the
identifiers are in `core.status`, and what a tester hears for them is an
interface string wrapped in `_()` and belongs here.

It has the two columns section 2 draws it with, and they travel as one row
(`_status_words`). One table is what that section asks for in as many words,
and a row is what makes the asking mechanical: a sixth status is one place to
add it rather than two, of which one would eventually be missed.

**What the fields of the item dialog are called**, on the one occasion they are
named somewhere other than beside themselves: the choice of section 3.3.1, which
decides where that dialog opens. The words are the field labels and nothing more
elaborate, so the same rule applies as to the statuses — one field, one word —
and they are here rather than in the window because the window would otherwise
word a second time what the dialog has already worded once.

**What a tester hears about one item.** Sections 3.1 and 3.3 both speak an item
— on landing on it after a move, and on being asked to say it again — and
section 3.1 says outright that the two are the same. So the sentence is built
once, here, beside the words it is built out of.

The order is text → status → note, and it is deliberately the reverse of the
GUI tree, where the status stands in front of the text (section 5). A tree is
scanned down the page and the prefix filters it by ear from the first syllable;
here there is only the one item, and its text matters more than the verdict on
it.

**What a tester reads about one item.** The other half of that sentence: the
label an item carries in the tree of the GUI window, which is the same two
things in the other order. It is built here for the reason the spoken form is —
the status half of it is the dictionary above, and a label assembled in the
window would be a second wording of the same five words.

**What a save altered.** Section 3.3.1 speaks only what really moved, in the
order status → comment, and the status half of that is the dictionary above —
built anywhere else it would be a second wording of the same five words. Which
of the two fields moved is not decided here but in the core (`Change`), because
the same comparison decides whether anything is written at all.

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
from typing import NamedTuple

import addonHandler

from .core import focus, status
from .core.checklist import Change, CommentChange, Item, Problem, ProblemKind
from .core.progress import Progress

addonHandler.initTranslation()


class _StatusWords(NamedTuple):
	"""Both columns the status table of section 2 gives one status.

	A row carrying the pair, rather than a table per column: section 2 asks for
	**one** table in the code, and one is what a sixth status then has to be
	added to. Two mappings keyed on the same identifiers would be two places to
	forget, and the one that was forgotten would be found by a tester hearing a
	`KeyError`-shaped silence.
	"""

	#: What a tester hears for the status: spoken on a change (section 4) and on
	#: request (section 3.3), and shown in the status list of the item dialog.
	word: str
	#: What stands in front of the text of an item in the tree of the GUI window
	#: (section 5), the separator included.
	prefix: str


def status_word(value: str) -> str:
	"""The word a tester hears for the status `value`.

	`value` is one of `core.status.STATUSES`; the validation contract of
	section 2 admits nothing else into a checklist, and the status control of
	the item dialog is a `wx.Choice`, so nothing else can be written back.
	"""
	return _status_words(value).word


def focus_target_label(value: str) -> str:
	"""The label a tester reads for the focus target `value` (section 3.3.1).

	`value` is one of `focus.TARGETS`; `preferences.initial_focus`
	admits nothing else — the config spec does not, and says there why — so
	there is no fourth answer to give.

	**The words are the labels of the fields themselves**, not sentences about
	them: section 3.3.1 asks for *"Item"*, *"Status"*, *"Comment"* and nothing
	more elaborate, by the rule that makes the status dictionary one table for
	the whole add-on — one field, one word. They are therefore the same three
	`msgid`s the item dialog labels its fields with, which is how *"Comment"*
	already reaches both that dialog and the panel of the GUI window (section
	5): one catalogue entry, however many places ask for it.

	Built on each call rather than once at import, for the reason
	`_status_words` is: the words follow the interface language NVDA is running
	now.
	"""
	return {
		# Translators: One of the fields the item dialog can open on, named in the add-on's
		# settings. It is the label of the read-only field holding the item text, and has to
		# read exactly as that label does.
		focus.ITEM: _("Item"),
		# Translators: One of the fields the item dialog can open on, named in the add-on's
		# settings. It is the label of the control holding the status, and has to read
		# exactly as that label does.
		focus.STATUS: _("Status"),
		# Translators: One of the fields the item dialog can open on, named in the add-on's
		# settings. It is the label of the field the comment is written in, and has to read
		# exactly as that label does.
		focus.COMMENT: _("Comment"),
	}[value]


def tree_label(item: Item) -> str:
	"""The label `item` carries as a node of the tree in the GUI window (section 5).

	The status in front of the text, and the text as the file spells it — the
	fragments of section 2 keep their delimiters here as everywhere the text is
	shown. The comment is not in it: section 5 keeps the labels short, and a
	paragraph in one would undo that, which is what the panel under the tree is
	for.

	Neither is the marker `spoken_item` puts on a commented item (section 5).
	The tree answers that with a tone instead — `signals.node_has_comment`,
	sounded whenever a commented node is announced — and the tone says the same
	thing before the label is read and costs it no length at all.

	The order is the reverse of the sentence spoken about an item (`spoken_item`),
	and section 3.3 says why: a tree is scanned down the page, and a prefix
	filters it by ear from the first syllable, whereas a single item spoken on
	its own is its text before anything else.

	`pending` contributes nothing, deliberately (section 2). It is the commonest
	state by far, and a word in front of every one of several dozen items would
	cost the tester more than it told them; the absence of a prefix is itself
	what "not checked" looks like in a tree.
	"""
	return _status_words(item.status).prefix + item.text


def _status_words(value: str) -> _StatusWords:
	"""The row the status table of section 2 gives `value` — both columns at once.

	The one table the whole add-on speaks statuses from, and the shape is the
	specification's own: two columns, not a word and a rule for making the other
	one out of it. Deriving the prefix — capitalise the word, add a colon —
	would hard-code punctuation the catalogue is entitled to choose, and would
	leave a locale that wanted an abbreviation in the tree where the voice says
	a whole word with nowhere to say so.

	The table is built on each call rather than once at import, so that the
	words follow the interface language NVDA is running now rather than whatever
	it was when the plugin was loaded.
	"""
	return {
		status.PASSED: _StatusWords(
			# Translators: The status of a checklist item that has been checked and works.
			word=_("passed"),
			# Translators: Stands in front of the text of a checklist item in the tree of the
			# add-on's window, when the item has been checked and works. The colon and the space
			# are part of it.
			prefix=_("Passed: "),
		),
		status.FAILED: _StatusWords(
			# Translators: The status of a checklist item that has been checked and does not work.
			word=_("failed"),
			# Translators: Stands in front of the text of a checklist item in the tree of the
			# add-on's window, when the item has been checked and does not work. The colon and
			# the space are part of it.
			prefix=_("Failed: "),
		),
		status.BLOCKED: _StatusWords(
			# Translators: The status of a checklist item that could not be checked because
			# something else is in the way.
			word=_("blocked"),
			# Translators: Stands in front of the text of a checklist item in the tree of the
			# add-on's window, when the item could not be checked because something else is in
			# the way. The colon and the space are part of it.
			prefix=_("Blocked: "),
		),
		status.SKIPPED: _StatusWords(
			# Translators: The status of a checklist item that was deliberately left unchecked.
			word=_("skipped"),
			# Translators: Stands in front of the text of a checklist item in the tree of the
			# add-on's window, when the item was deliberately left unchecked. The colon and the
			# space are part of it.
			prefix=_("Skipped: "),
		),
		status.PENDING: _StatusWords(
			# Translators: The status of a checklist item that has not been checked yet.
			word=_("not checked"),
			# No prefix at all, which is the whole of what the tree says about an item
			# nobody has looked at yet; `tree_label` carries the reason.
			prefix="",
		),
	}[value]


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

	Those two words are the **marker**, and they belong to speech alone. The
	same fact reaches the tree of the GUI window as the **comment signal**, a
	tone (`signals.node_has_comment`), and the two names are kept apart on
	purpose. Here the words already sit inside a sentence being listened to
	whole; there the sentence is the label of a node, which section 2 keeps
	short, and a tone says it earlier for nothing (section 3.3).

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


def spoken_save(change: Change) -> str:
	"""What the tester hears after a save from the item dialog (section 3.3.1).

	Only what really moved, in the order status → comment: *"failed, comment
	saved"*, *"failed"*, *"comment saved"* or *"comment deleted"*. A save that
	moved neither field never reaches here — section 3.3.1 answers that one
	with the silence of a cancel, and with no write either.

	The status word is the dictionary's, as everywhere (section 2). The clause
	about the comment says only that there is one now, or that there is not:
	the text itself was on the screen the tester has just closed, and reading
	their own paragraph back to them is what section 3.3 refuses to do
	anywhere.

	The words are lowercase because the phrase is built out of them in either
	order, and the status word is lowercase in the dictionary; the capital in
	the specification is the first letter of a sentence quoted there, as it is
	wherever a single status word is quoted.
	"""
	spoken: list[str] = []
	if change.status is not None:
		spoken.append(status_word(change.status))
	match change.comment:
		case CommentChange.SAVED:
			# Translators: Spoken after a save from the item dialog that left a comment on the
			# item. The status word goes in front of it when that changed too, running straight
			# on: "failed, comment saved".
			spoken.append(_("comment saved"))
		case CommentChange.DELETED:
			# Translators: Spoken after a save from the item dialog emptied a comment the item
			# was carrying.
			spoken.append(_("comment deleted"))
		case CommentChange.UNCHANGED:
			pass
	return ", ".join(spoken)


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
