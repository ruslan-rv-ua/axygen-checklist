# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The window a fragment is picked out of (section 3.2.2).

The `C` key of the command mode opens it, and only for an item carrying two
fragments or more: nothing to choose between is answered without a window at
all — a single fragment goes straight to the clipboard, and none at all is a
sentence. So this window exists for the one case where there is a choice to
make, and everything in it is about making that choice quickly.

**It collects, and it decides nothing**, as the item dialog does: what comes
back out of `show` is the string the tester picked, and putting it in the
clipboard is the plugin's. Nothing here touches `api.copyToClip`, which is
what keeps the timing of the confirmation in one place (section 6).

**Flat, because an item is the whole of the scope.** A `wx.ListBox` and not a
tree: the fragments of one item have no hierarchy to show, and the label of an
entry is the fragment itself, without the delimiters that mark it in the text
(section 2). The delimiters stay everywhere the text is *shown*; here the
string is on its way to the clipboard, which is the one place they would be
wrong. Stripping them is `core.fragments`' doing and has happened long before
anything reaches this module.

**The first fragment is selected when the window opens** (section 3.2.2), and
the focus is on the list. A list holding no selection announces itself by the
name of the control alone, and the tester would have to press an arrow to hear
the thing the window was opened for.

**Enter on the list is handled explicitly** (section 3.2.2), and there is no
other way to do it. Measured on wxWidgets 3.2.6, the build NVDA 2025.3 ships:
of `EVT_CHAR_HOOK`, `EVT_KEY_DOWN` and `EVT_CHAR` bound on the list box, only
the first is ever given the Return key — the other two never see it, and with
no handler at all the key does nothing, since the window has no default button
for `IsDialogMessage` to press. That is wx ticket #3725, the same one NVDA
works around in its own Elements List (`browseMode.ElementsListDialog`), and
Enter is the first key anyone will press here.

The hook is bound on the **list**, not on the dialog, which is what keeps it
clear of section 6's refusal to hook a dialog of the add-on: that refusal is
about a hook seeing every key of every control, and it was written for the one
window holding an editable multi-line field, where it would swallow Enter in
the comment. Bound on the list, it sees the keys of the list, and this window
has no field to type in at all.

**Activation closes the window first and copies after** (section 3.2.2), which
falls out of the shape rather than being arranged: the window ends with
`wx.ID_OK`, and `modal.show` hands the answer on only once the window has gone.
So the focus is back in the application under test before the confirmation is
heard — safe, because the owner `api.copyToClip` gives the clipboard is
`gui.mainFrame` and never this window.

**The buttons are built by hand with their labels spelled out**, for the
reasons section 3.3.1 gives: stock ids without labels take their wording from
wxWidgets' own catalogues, which never reach the catalogue of the add-on
(section 6). Copy carries `wx.ID_OK` all the same, so that wx closes the window
on it without a handler of ours — the id is the affirmative one a dialog
answers for, and the label over it is ours.

Neither label carries a mnemonic, where the item dialog's `_("&Save")` does.
That ampersand is in section 3.3.1 by name, and it is there because that
window has no default button and no other key that saves; here Enter on the
list is the way Copy is reached, and it is the first key anyone presses. A
mnemonic would be a second answer to a question that already has one.

How the window is shown, who gets the focus back and why the series ends with
it are `modal`'s, as for every window of the add-on.
"""

from collections.abc import Callable, Sequence

import addonHandler
import wx
from gui import guiHelper
from logHandler import log

from . import modal

addonHandler.initTranslation()

#: How wide the list is drawn, and how tall, in pixels. The width is the one
#: the item dialog gives its fields, so that the two windows of the add-on are
#: the same size on screen; what such a number is for is said there once.
_LIST_WIDTH = 500
_LIST_HEIGHT = 200


def show(found: Sequence[str], then: Callable[[str], None]) -> None:
	"""Open the list on `found`, and hand the fragment picked to `then`.

	`then` is called for Copy and for nothing else: Cancel, Escape and the
	window being closed all mean the same thing, and section 3.2.2 answers
	that with no clipboard and no word.

	`found` holds two fragments or more. One is copied without a window and
	none is a sentence (section 3.2.2), so neither ever gets this far; nothing
	below would break on a shorter list, but nothing below is written for one
	either.

	Called long after the script that asked has returned; `modal.show` says
	why, and holds the focus, the modality counter and the end of the series.
	"""

	def create(parent: wx.Window) -> _FragmentsDialog:
		return _FragmentsDialog(parent, found)

	def answered(dialog: _FragmentsDialog, answer: int) -> None:
		if answer != wx.ID_OK:
			return
		chosen = dialog.chosen
		if chosen is not None:
			then(chosen)

	modal.show(create, answered)


class _FragmentsDialog(wx.Dialog):
	"""The window itself: the list the focus opens on, and two buttons."""

	def __init__(self, parent: wx.Window, found: Sequence[str]) -> None:
		super().__init__(
			parent,
			# Translators: The title of the window that lists the fragments of a checklist
			# item so that one of them can be copied to the clipboard.
			title=_("Copy a fragment"),
		)
		#: What the list is showing, kept so that the answer is read off the
		#: position rather than off the label — the same move the item dialog
		#: makes with its combo box, and for the same reason: the string that
		#: goes to the clipboard should be the one that came out of the item,
		#: not one that has been through a control on the way.
		self._found = list(found)
		main = wx.BoxSizer(wx.VERTICAL)
		contents = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self._list: wx.ListBox = contents.addLabeledControl(
			# Translators: The label of the list of the fragments of a checklist item, one
			# of which is about to be copied to the clipboard.
			_("Fragments"),
			wx.ListBox,
			choices=self._found,
			size=(_LIST_WIDTH, _LIST_HEIGHT),
		)
		self._list.SetSelection(0)
		buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
		buttons.addButton(
			self,
			id=wx.ID_OK,
			# Translators: The label of the button that puts the selected fragment of the
			# checklist item in the clipboard. Enter on the list does the same.
			label=_("Copy"),
		)
		buttons.addButton(
			self,
			id=wx.ID_CANCEL,
			# Translators: The label of the button that closes the list of fragments without
			# copying anything. Escape does the same.
			label=_("Cancel"),
		)
		contents.addDialogDismissButtons(buttons)
		main.Add(contents.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		main.Fit(self)
		self.SetSizer(main)
		# Escape means Cancel, said out loud rather than left to wx: without
		# this it goes to the affirmative button when there is no cancel one,
		# and here that button copies (sections 3.2.2 and 3.3.1).
		self.SetEscapeId(wx.ID_CANCEL)
		# The one binding this window needs, and the only event that would
		# carry the key; see the module docstring for what was measured.
		self._list.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
		self._list.SetFocus()
		self.CentreOnScreen()

	@property
	def chosen(self) -> str | None:
		"""The fragment standing in the list, or None when it is holding none.

		None is unreachable through the window — the constructor selects the
		first entry and a `wx.ListBox` offers no way to unselect it — and the
		answer to it is to copy nothing. An index of -1 would read as the last
		fragment of the list and put a string in the clipboard that the tester
		never picked, which is worse than the silence of a cancel.
		"""
		index = self._list.GetSelection()
		if index == wx.NOT_FOUND:
			log.error("the list of the fragments dialog is holding no selection")
			return None
		return self._found[index]

	def _on_char_hook(self, event: wx.KeyEvent) -> None:
		"""Enter on the list means Copy; every other key is the list's own.

		The event is not skipped on the way out, which is what keeps the key
		from going on to `IsDialogMessage` afterwards. Numpad Enter comes with
		it, as NVDA checks both codes in its own windows (section 3.3.1).
		"""
		if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			self.EndModal(wx.ID_OK)
			return
		event.Skip()
