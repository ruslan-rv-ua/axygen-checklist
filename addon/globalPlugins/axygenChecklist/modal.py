# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The one way a window of the add-on is shown.

Section 6 of docs/requirements.md gives every modal window of the add-on the
same life — the item dialog, the confirmation of a reset (of a section,
section 3.2.2, or of the run, section 5), the file dialog and the dialog of
fragments: every window but the GUI, which is not modal and lives long
(section 3.3.1) — and this module is where that life is written down once, so
that the windows themselves hold only what they ask.

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

**The series ends with the window** (section 6). `scriptHandler.clearLastScript()`
is called on the way in, for every window and not only the item dialog section
3.3.1 asks it for: a press right after the window has closed would otherwise
count as the next press of the series that opened it, and the add-on defines no
behaviour for a third press. For a window opened from the command mode the call
changes nothing, which is what makes it safe to make always.

**What is said after a window has closed is said late** (section 6). The window
gives the focus back to the application under test, and NVDA handles that
change only after the code of the add-on has had its say: the foreground event
cancels speech, so a phrase queued at once would be cut off by the announcement
of the window that got the focus back. `message` below goes through
`ui.delayedMessage`, which holds a phrase for a short moment of NVDA's own — the
same move NVDA makes when it refuses a blocked action.

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

import addonHandler
import gui
import scriptHandler
import ui
import wx
from gui.message import DefaultButtonSet, DialogType, MessageDialog, ReturnCode, displayDialogAsModal
from logHandler import log

addonHandler.initTranslation()

#: The window a caller of `show` builds, handed back to them with its answer
#: as the type they built rather than as a bare `wx.Dialog`.
DialogT = TypeVar("DialogT", bound=wx.Dialog)


def show(create: Callable[[wx.Window], DialogT], then: Callable[[DialogT, int], None]) -> None:
	"""Show the window `create` builds, once the script asking has returned.

	`create` is handed the parent every window of the add-on must have and
	gives back the window; `then` is handed that window and the code it was
	closed with — `wx.ID_OK`, `wx.ID_CANCEL`, one of the `ReturnCode`s of a
	`MessageDialog` — before the window is destroyed, so it may still read
	what the tester put in it. Whatever `then` does with the answer, the
	focus is already on its way back to where it was, and anything it wants
	said goes through `message`.
	"""
	wx.CallAfter(_show, create, then)
	scriptHandler.clearLastScript()


def _show(create: Callable[[wx.Window], DialogT], then: Callable[[DialogT, int], None]) -> None:
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


def message(text: str) -> None:
	"""Say `text` now that a window has closed, after the focus has been announced.

	The `ui.message` of the moment right after a window: what a command says
	from where the tester stands goes through `ui.message` and is heard at
	once (section 4), while a phrase queued at this moment would be cancelled
	by the foreground event of the window getting the focus back (section 6).
	Every word the add-on says after a window — the result of a confirmation,
	the one phrase of a failed write — comes through here.
	"""
	ui.delayedMessage(text)


def confirm(question: str, on_yes: Callable[[], None]) -> None:
	"""Ask `question` with Yes and No, and run `on_yes` on Yes only.

	The shape of every confirmation of the add-on. A warning, with the icon
	and the sound NVDA gives an action that may lose data for good, because
	both commands that ask one erase what the tester recorded and cannot be
	undone (sections 3.2.2 and 5). The title is the product name (section 6):
	the tester is working in someone else's window, and the title is what
	says who is asking. Yes is where the focus opens, as in every other
	question NVDA asks, and No is what Escape means — set explicitly, since a
	`MessageDialog` holding only Yes and No otherwise ignores Escape
	altogether, and the key that usually closes a window may not do the one
	irreversible thing the window exists to guard.

	No is answered with nothing at all: no change, no word, the same silence
	as cancelling the item dialog (section 3.3.1).
	"""

	def create(parent: wx.Window) -> MessageDialog:
		dialog = MessageDialog(
			parent,
			question,
			# Translators: The title of the add-on's confirmation dialogs: the product name,
			# which is not translated in any locale.
			_("Axygen Checklist"),
			DialogType.WARNING,
			buttons=DefaultButtonSet.YES_NO,
		)
		return dialog.setFallbackAction(ReturnCode.NO)

	def answered(dialog: MessageDialog, answer: int) -> None:
		if answer == ReturnCode.YES:
			on_yes()

	show(create, answered)
