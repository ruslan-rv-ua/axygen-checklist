# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The one way a window of the add-on is shown.

Section 6 of docs/requirements.md gives every modal window of the add-on the
same life — the item dialog, the two confirmations, the file dialog and the
list of fragments — and this module is where that life is written down once,
so that the windows themselves hold only what they ask.

**The script that asks for a window returns first.** The window is shown from
`wx.CallAfter`, and this is not a nicety: NVDA runs a script for every press of
a series without waiting for the series to end (section 6), and a script that
blocked on a dialog would hold the gesture handler with it.

**The window is created with `gui.mainFrame` as its parent**, and around it
runs `prePopup()` → `displayDialogAsModal()` → `postPopup()`. The pair records
where the focus was and, once the window has gone, puts it back there — which
is what section 3.3.1 promises of every button and of Escape.
`displayDialogAsModal` is not a spelling of `ShowModal()`: it raises the
modality counter NVDA keeps, and `blockAction.Context.MODAL_DIALOG_OPEN`, which
every script of the add-on is decorated with, reads that counter. Without it
`NVDA+Alt+Space` would change the status of the very item a window is open on.
The counter is raised by the call whatever the window is, so a native
`wx.FileDialog` will be blocked behind as well (section 6). The pair is called
here rather than left to `displayDialogAsModal` because that function calls it
itself only for a window without a parent, and a window without a parent is not
one section 6 allows.

**The series ends with the window.** `scriptHandler.clearLastScript()` is
called on the way in, for every window and not only the item dialog section
3.3.1 asks it for: a press right after the window has closed would otherwise
count as the next press of the series that opened it, and the add-on defines no
behaviour for a third press (section 6). For a window opened from the command
mode the call changes nothing, which is what makes it safe to make always.

**The window is destroyed here**, after whoever asked for it has read what they
need out of it. A `wx.Dialog` shown modally is not destroyed by being closed,
and the caller of `show` should not have to remember that; NVDA's own
`MessageDialog` schedules its own destruction, for which a second `Destroy()`
is a no-op.

What a window says and which buttons it has is the business of the window. The
confirmation built at the bottom is the one shape two commands share — resetting
a section (section 3.2.2) and resetting the run (section 5) — so it is built
once, on NVDA's own `MessageDialog`. Its Yes and No are labelled by NVDA's own
catalogue rather than ours, which is the same move as the copy confirmation of
section 3.2.2: the tester hears the same words as from every other question the
screen reader asks.
"""

from collections.abc import Callable
from typing import TypeVar

import gui
import scriptHandler
import wx
from gui.message import DefaultButtonSet, DialogType, MessageDialog, ReturnCode, displayDialogAsModal
from logHandler import log

#: The window a caller of `show` builds, handed back to them with its answer
#: as the type they built rather than as a bare `wx.Dialog`.
Dialog = TypeVar("Dialog", bound=wx.Dialog)


def show(create: Callable[[wx.Window], Dialog], then: Callable[[Dialog, int], None]) -> None:
	"""Show the window `create` builds, once the script asking has returned.

	`create` is handed the parent every window of the add-on must have and
	gives back the window; `then` is handed that window and the code it was
	closed with — `wx.ID_OK`, `wx.ID_CANCEL`, one of the `ReturnCode`s of a
	`MessageDialog` — before the window is destroyed, so it may still read
	what the tester put in it. Whatever `then` does with the answer, the
	focus is already back where it was.
	"""
	wx.CallAfter(_show, create, then)
	scriptHandler.clearLastScript()


def _show(create: Callable[[wx.Window], Dialog], then: Callable[[Dialog, int], None]) -> None:
	frame = gui.mainFrame
	if frame is None:
		# NVDA has no main frame before its GUI is up and after it has been
		# torn down, and no script of the add-on runs in either window of
		# time. Nothing has changed, so there is nothing to say out loud.
		log.error("no main frame to show a window of the add-on from")
		return
	dialog = create(frame)
	try:
		frame.prePopup()
		try:
			answer = displayDialogAsModal(dialog)
		finally:
			frame.postPopup()
		then(dialog, answer)
	finally:
		_ = dialog.Destroy()


def confirm(question: str, title: str, then: Callable[[], None]) -> None:
	"""Ask `question` with Yes and No, and run `then` on Yes only.

	The shape of every confirmation of the add-on: a warning, because both
	commands that ask one erase what the tester recorded and cannot be undone
	(sections 3.2.2 and 5). Yes is where the focus opens, as in every other
	question NVDA asks, and No is what Escape means — set explicitly, since a
	`MessageDialog` holding only Yes and No otherwise ignores Escape
	altogether, and the key that usually closes a window may not do the one
	irreversible thing the window exists to guard.

	No is answered with nothing at all: no change, no word, the same silence
	as cancelling the item dialog (section 3.3.1).
	"""

	def create(parent: wx.Window) -> MessageDialog:
		dialog = MessageDialog(parent, question, title, DialogType.WARNING, buttons=DefaultButtonSet.YES_NO)
		return dialog.setFallbackAction(ReturnCode.NO)

	def answered(dialog: MessageDialog, answer: int) -> None:
		if answer == ReturnCode.YES:
			then()

	show(create, answered)
