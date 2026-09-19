# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The window one item is looked at and answered in (section 3.3.1).

The second press of `NVDA+Alt+I` opens it (section 3.3). It is the only place
in the add-on where a comment is entered, and the third of the three ways a
status is set — the other two never open a window at all, which is what leaves
the focus invariant of section 1 intact while this one stands.

**It collects, and it decides nothing.** What the tester chose comes back out
of `show` as a pair of plain values, and what that pair means — whether
anything changed, what reaches the file, what is spoken — is settled where
every other change of data is settled, in the plugin and the core. So the
rules of section 4 have one home rather than one per window, and nothing here
touches a file.

**The two read-only fields are multi-line, and that is what makes them
reachable.** wxWidgets leaves a single-line read-only text control out of the
Tab chain — `AcceptsFocusFromKeyboard()` returns False for one, which is wx
treating it as a caption rather than a control — while a multi-line read-only
one stays in. Measured on wxWidgets 3.2.6, the build NVDA 2025.3 ships;
`SetEditable(False)` in place of the style does the same thing.

Section 3.3.1 weighed the two halves of itself and chose this one. Single-line
bought the announcement: NVDA reads a dialog out on opening from the static
text, the labels and the read-only edit fields that are **not** multi-line
(`NVDAObjects.behaviors.Dialog.getDialogText`), so the item and the note were
heard at once, without a single Tab. Multi-line buys what makes a field a
field: Tab, the arrows, Shift+arrows and Ctrl+C. The cost is named rather than
hidden — the description of the window now holds neither of them, and they are
heard by walking to them. Neither is lost work: the text of the item is spoken
on every landing on it (section 3.1) and the note with it (section 3.3).

Their labels are the plain words of the specification and carry no mnemonic,
so that each matches the accessible name of the field beneath it exactly.
NVDA drops a label whose name is the name of the control after it, as the
label it plainly is; a label that did not match would be read out as a word of
its own (section 3.3.1).

**An item with no note gets no note field**, rather than an empty one under a
label saying so. That label was worth having while the fields were single-line
and it was read out for free with the window; now it would cost a Tab press to
be told nothing, and it would cost it on the way back to the item text, which
runs past it — on most items, since most items carry no note. The tester knows
the answer already: a note is spoken on every landing on its item (section
3.3), so a field repeating it here repeats what was heard a moment ago. The
price of this is a window whose shape varies, and section 3.3.1 takes it: NVDA
names every control, so a different number of presses is not a place to get
lost in.

**The status is chosen, never typed.** `wx.CB_READONLY` makes arbitrary text
structurally impossible, and section 3.3.1 wants it that way for a reason the
file pays: one typo would put an unknown value in `status`, which section 2
makes fatal on read — the checklist would stop opening altogether. The words
and their order come from the one dictionary the whole add-on speaks from
(`wording.status_word` over `core.status.STATUSES`), never from a list written
out again here.

**The buttons are built by hand, with their labels spelled out.**
`CreateButtonSizer` and bare stock ids are forbidden by section 3.3.1: it
takes the wording from wxWidgets' own catalogues, which never reach the
catalogue of the add-on (section 6), it does not know `wx.ID_SAVE` among its
buttons at all, and it takes the focus for itself — against the one thing the
window must open with, the focus in *"Comment"*.

**There is no default button**, and Enter therefore saves nowhere. In the
multi-line comment Enter inserts a line (wxMSW gives such controls
`ES_WANTRETURN`) and never reaches the dialog, and a key that saved in the
other fields but not in that one would be worse than a key that saves in none.
Escape is made to mean Cancel explicitly, because wx otherwise sends it to the
affirmative button when there is no cancel — that is, Escape would save.

**The keyboard needs no code of its own** (section 6), and must not have any.
`wx.TE_PROCESS_TAB` is set nowhere, which is what leaves Tab as navigation
even in the multi-line field, and `EVT_CHAR_HOOK` is bound to nothing: NVDA
uses it on its settings windows, none of which holds an editable multi-line
field, and here it would swallow Enter in *"Comment"*.

How the window is shown, who gets the focus back and why the series ends with
it are `modal`'s, as for every window of the add-on.
"""

from collections.abc import Callable

import addonHandler
import wx
from gui import guiHelper
from logHandler import log

from . import modal, wording
from .core import status
from .core.checklist import Item

addonHandler.initTranslation()

#: How wide the fields are drawn, and how tall each kind is, in pixels. A
#: courtesy to whoever is looking at the screen rather than listening to it:
#: nothing here is measured by the tester, and every field holds its whole
#: value however small it is drawn. Unscaled, as in NVDA's own dialogs.
_FIELD_WIDTH = 500
_READ_ONLY_HEIGHT = 60
_COMMENT_HEIGHT = 120


def show(item: Item, then: Callable[[str, str], None]) -> None:
	"""Open the dialog on `item`, and hand what Save was pressed on to `then`.

	`then` is given the status standing in the combo box and the comment as
	the tester left it — text exactly as typed, blank or not, because what a
	blank comment amounts to is section 2's to decide and the core decides it
	in one place. It is called for Save and for nothing else: Cancel, Escape
	and the window being closed all mean the same thing, and section 3.3.1
	answers that with silence and no file.

	Called long after the script that asked has returned; `modal.show` says
	why, and holds the focus, the modality counter and the end of the series.
	"""

	def create(parent: wx.Window) -> _ItemDialog:
		return _ItemDialog(parent, item)

	def answered(dialog: _ItemDialog, answer: int) -> None:
		if answer == wx.ID_SAVE:
			then(dialog.chosen_status, dialog.typed_comment)

	modal.show(create, answered)


class _ItemDialog(wx.Dialog):
	"""The window itself: four fields in the order Tab walks them, and two buttons.

	Built in the order of the table of section 3.3.1, which is the whole of
	the Tab order — wx walks the children of a dialog in the order they were
	created, and the labels are not stops.
	"""

	def __init__(self, parent: wx.Window, item: Item) -> None:
		super().__init__(
			parent,
			# Translators: The title of the window that shows one checklist item in full and
			# is the only place a comment is written.
			title=_("Checklist item"),
		)
		#: The status the window opened on, and the answer if the combo box is
		#: ever asked while holding nothing; see `chosen_status`.
		self._opened_on = item.status
		main = wx.BoxSizer(wx.VERTICAL)
		contents = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		contents.addLabeledControl(
			# Translators: The label of the read-only field of the item dialog holding the
			# whole text of the checklist item.
			_("Item"),
			wx.TextCtrl,
			value=item.text,
			style=wx.TE_READONLY | wx.TE_MULTILINE,
			size=(_FIELD_WIDTH, _READ_ONLY_HEIGHT),
		)
		# The same test section 3.3 speaks a note by, and deliberately the same
		# one: the field is there exactly when the note is heard on landing, so
		# the add-on has one answer to "is there a note here" rather than two.
		if item.note:
			contents.addLabeledControl(
				# Translators: The label of the read-only field of the item dialog holding the
				# note the author of the checklist wrote about this item. The field is there
				# only for an item that carries one.
				_("Note"),
				wx.TextCtrl,
				value=item.note,
				style=wx.TE_READONLY | wx.TE_MULTILINE,
				size=(_FIELD_WIDTH, _READ_ONLY_HEIGHT),
			)
		self._status: wx.ComboBox = contents.addLabeledControl(
			# Translators: The label of the combo box of the item dialog, where the status of
			# the checklist item is chosen.
			_("Status"),
			wx.ComboBox,
			choices=[wording.status_word(value) for value in status.STATUSES],
			style=wx.CB_READONLY,
		)
		self._status.SetSelection(status.STATUSES.index(item.status))
		self._comment: wx.TextCtrl = contents.addLabeledControl(
			# Translators: The label of the editable field of the item dialog, where the tester
			# writes their conclusion about the checklist item.
			_("Comment"),
			wx.TextCtrl,
			value=item.comment or "",
			style=wx.TE_MULTILINE,
			size=(_FIELD_WIDTH, _COMMENT_HEIGHT),
		)
		buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
		save: wx.Button = buttons.addButton(
			self,
			id=wx.ID_SAVE,
			# Translators: The label of the button of the item dialog that writes the status
			# and the comment to the checklist file. The letter after the ampersand is the
			# mnemonic that activates it.
			label=_("&Save"),
		)
		save.Bind(wx.EVT_BUTTON, self._on_save)
		buttons.addButton(
			self,
			id=wx.ID_CANCEL,
			# Translators: The label of the button of the item dialog that closes it without
			# writing anything. Escape does the same.
			label=_("Cancel"),
		)
		contents.addDialogDismissButtons(buttons)
		main.Add(contents.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		main.Fit(self)
		self.SetSizer(main)
		# Escape means Cancel, said out loud rather than left to wx: without
		# this it goes to the affirmative button when there is no cancel one,
		# and a window guarded by Escape may not save on it (section 3.3.1).
		self.SetEscapeId(wx.ID_CANCEL)
		# Where the window opens (section 3.3.1): in the comment, with the
		# caret after whatever is already there and nothing selected — a
		# selection would go under the first letter typed, taking the comment
		# with it.
		self._comment.SetFocus()
		self._comment.SetInsertionPointEnd()
		self.CentreOnScreen()

	@property
	def chosen_status(self) -> str:
		"""The status standing in the combo box, as the identifier section 2 writes.

		Read off the position rather than off the word: the words follow the
		interface language and the identifiers never do, and the one ordering
		of the statuses is what ties the two together (section 3.2.2).
		"""
		chosen = self._status.GetSelection()
		if chosen == wx.NOT_FOUND:
			# Unreachable through the window: the list is read-only, so there
			# is no way to unselect what the constructor selected. Were it ever
			# to happen, the status the window opened on is the one honest
			# answer — an index of -1 would quietly read as the last of the
			# five and write `pending` over somebody's verdict.
			log.error("the status combo box of the item dialog is holding no selection")
			return self._opened_on
		return status.STATUSES[chosen]

	@property
	def typed_comment(self) -> str:
		"""The comment as the tester left it, blank and whitespace and all.

		Nothing is trimmed or judged here. Section 2 has one place that decides
		what a comment amounts to, and it is not a window.
		"""
		return self._comment.GetValue()

	def _on_save(self, event: wx.CommandEvent) -> None:
		"""Close the window with the answer Save stands for.

		Bound by hand because wx does not know this button: `wxDialog` answers
		for its affirmative id, for `wx.ID_APPLY` and for its escape id of its
		own accord, and `wx.ID_SAVE` is none of the three. Cancel needs no
		handler for the same rule read the other way — it *is* the escape id.
		"""
		self.EndModal(wx.ID_SAVE)
