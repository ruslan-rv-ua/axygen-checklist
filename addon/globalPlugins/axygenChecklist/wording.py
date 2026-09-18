# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The words the add-on says about a checklist item.

Two things live here, and the first is the reason the second does.

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
"""

import addonHandler

from .core import status
from .core.checklist import Item

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
