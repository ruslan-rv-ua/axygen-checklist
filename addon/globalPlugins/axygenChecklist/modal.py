# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The one way a window of the add-on is shown.

Section 6 of docs/requirements.md gives every window of the add-on the same
life — the item dialog, the confirmation of a reset (of a section, section
3.2.2, or of the run, section 5), the file dialog, the dialog of fragments
and the GUI window itself — and this module is where that life is written
down once, so that the windows themselves hold only what they ask. There is
no non-modal window any more, and section 5 says what the add-on bought by
giving the last one up.

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

**A window opened from another window of ours takes a `parent`, and `show`
holds what that changes.** Three are so far, all from the GUI window (sections
5 and 6): the item dialog reached from the tree, and the file dialog and the
error of `Browse...`. Each hangs off that window instead, the pair above is not
called at all and the series is not cleared: both are about coming in from
somebody else's application, and these come in from ours. `show` says what each
of the three changes is for. Section 6 counts a fourth, the confirmation before
the whole run is reset; `confirm` takes no parent yet because that button is
not built.

**The series ends with the window** (section 6). `scriptHandler.clearLastScript()`
is called on the way in, for every window a script opened and not only the item
dialog section 3.3.1 asks it for: a press right after the window has closed
would otherwise count as the next press of the series that opened it, and the
add-on defines no behaviour for a third press. For a window opened from the
command mode the call changes nothing, which is what makes it safe to make
always.

**What is said after a window has closed is said late** (section 6). The window
gives the focus back to the application under test, and NVDA handles that
change only after the code of the add-on has had its say: the foreground event
cancels speech, so a phrase queued at once would be cut off by the announcement
of the window that got the focus back. `message` below goes through
`ui.delayedMessage`, which holds a phrase for a short moment of NVDA's own — the
same move NVDA makes when it refuses a blocked action. `later` holds anything
else for that same moment, and exists because a tone is not a phrase and would
otherwise be heard a whole window announcement ahead of the words it belongs
to.

**The window is destroyed here**, after whoever asked for it has read what they
need out of it. A `wx.Dialog` shown modally is not destroyed by being closed,
and the caller of `show` should not have to remember that; NVDA's own
`MessageDialog` schedules its own destruction, for which a second `Destroy()`
is a no-op.

What a window says and which buttons it has is the business of the window. The
three built at the bottom are the shapes more than one command shares, so each
is built once: the confirmation, asked before a section is reset (section 3.2.2)
and before the run is (section 5); the file dialog, opened by the `O` key, by
`Browse...` in the GUI window and by a start-up that found its checklist gone
(sections 3.2.2, 5 and 2); and the error, shown for a file the tester picked
themselves, whichever of the first two they picked it with (sections 3.2.2 and
5). The first two are NVDA's own `MessageDialog`,
and their buttons are labelled from NVDA's catalogue rather than ours — the same
move as the copy confirmation of section 3.2.2: the tester hears the words every
other question of the screen reader uses.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import addonHandler
import gui
import scriptHandler
import ui
import wx

# NVDA's own `core`, which shares a name with the add-on's `core` package. The
# two never collide — one is imported absolutely and the other relatively —
# but `core` in the body of this module would mean whichever the reader
# guessed, so the one name needed is taken out of it instead.
from core import callLater
from gui.message import DefaultButtonSet, DialogType, MessageDialog, ReturnCode, displayDialogAsModal
from logHandler import log

addonHandler.initTranslation()

#: The window a caller of `show` builds, handed back to them with its answer
#: as the type they built rather than as a bare `wx.Dialog`.
DialogT = TypeVar("DialogT", bound=wx.Dialog)

#: How long `later` holds an action, in milliseconds; see it for why the
#: number is here rather than taken from NVDA by name.
_A_TURN_OF_THE_LOOP = 1


def _title() -> str:
	"""The title every window of the add-on carries: the product name (section 6).

	The tester is working in someone else's window, and the title is what says
	who is asking. It is not translated in any locale — it is the name the
	add-on goes by in the Add-on Store, in the configuration directory and in
	its documentation — and the entry in the Ukrainian catalogue deliberately
	repeats the original.

	Looked up on each call rather than held in a constant, so that the words
	follow the interface language NVDA is running now rather than whatever it
	was when this module was imported. That matters for the catalogue rather
	than for this string, which is the same in both, but the rule is the one
	`wording.status_word` follows and there is no reason for a second.
	"""
	# Translators: The title of the add-on's windows: the product name, which is
	# not translated in any locale.
	return _("Axygen Checklist")


def _nothing(dialog: wx.Dialog, answer: int) -> None:
	"""The answer of a window that has none: the default `then` of `show`.

	A window with one button says only that it was read, and there is nothing
	to do with that. Spelling it once here beats a do-nothing callback written
	out at each such call.
	"""


def show(
	create: Callable[[wx.Window], DialogT],
	then: Callable[[DialogT, int], None] = _nothing,
	parent: wx.Window | None = None,
) -> None:
	"""Show the window `create` builds, once the script asking has returned.

	`create` is handed the parent every window of the add-on must have and
	gives back the window; `then` is handed that window and the code it was
	closed with — `wx.ID_OK`, `wx.ID_CANCEL`, one of the `ReturnCode`s of a
	`MessageDialog` — before the window is destroyed, so it may still read
	what the tester put in it. Whatever `then` does with the answer, the
	focus is already on its way back to where it was, and anything it wants
	said goes through `message`.

	A `then` that opens a window of its own is safe: this one has closed and
	been destroyed by the time the next is built, because `show` schedules
	rather than shows. That is the path from the file dialog to the error.

	**`parent` is for a window opened from another window of the add-on** — the
	ones the GUI window opens (sections 5 and 6) — and passing it changes three
	things at once, all for the same reason: the foreground already belongs to
	us. The window hangs off that one rather than
	off `gui.mainFrame`; `prePopup()` / `postPopup()` are not called, because
	the first brings NVDA forward out of somebody else's application and the
	second would blank `gui.mainFrame.prevFocus` in the middle of the outer
	window's life — erasing where the focus must go when **that** one closes;
	and the series is not cleared, because no script opened this and there is
	no series to end (section 6).
	"""
	wx.CallAfter(_show, create, then, parent)
	if parent is None:
		scriptHandler.clearLastScript()


def _show(
	create: Callable[[wx.Window], DialogT],
	then: Callable[[DialogT, int], None],
	parent: wx.Window | None,
) -> None:
	owner: wx.Window | None = parent
	# Whose foreground is borrowed for the window, and None when it is already
	# ours: that one fact is the whole of what `parent` changes here.
	surround = None
	if owner is None:
		surround = gui.mainFrame
		if surround is None:
			# NVDA has no main frame before its GUI is up and after it has been
			# torn down, and no script of the add-on runs in either window of
			# time. Nothing has changed, so there is nothing to say out loud.
			log.error("no main frame to show a window of the add-on from")
			return
		owner = surround
	dialog = create(owner)
	try:
		if surround is not None:
			surround.prePopup()
		try:
			answer = displayDialogAsModal(dialog)
		finally:
			if surround is not None:
				surround.postPopup()
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


def later(action: Callable[[], None]) -> None:
	"""Do `action` on the same turn of the event loop `message` waits for.

	`message`'s sibling, for a window's parting word that `message` cannot
	carry on its own. Section 6 puts two kinds of thing here, and neither is a
	bare phrase of the add-on's.

	One is a phrase with something attached. The end of a run is that: section
	4 has it *play a signal and speak a message*, one event in one order, and
	`tones.beep` sounds the moment it is called — so a run finished by a save
	from the item dialog would sound its tone while the window was still
	closing, a whole window announcement ahead of the words it belongs to.
	Handed to this, the pair keeps together and keeps its place behind
	whatever `message` queued first.

	The other is a phrase that is not the add-on's to hold. The confirmation
	of a copy (section 3.2.2) is spoken from NVDA's own catalogue, inside
	`api.copyToClip`, which says it through `ui.message`; there is no string
	here to delay, so the call that makes it waits instead. Cancelling speech
	does not ask whose line it is, which is why the rule reaches a phrase the
	add-on never wrote.

	The delay is the one `ui.delayedMessage` takes, and for the same reason: a
	millisecond is not a wait for anything but a turn of the event loop, after
	which the foreground event of the window that got the focus back has
	already done its cancelling. NVDA keeps the number in a private constant of
	`ui`, so it stands here as a number rather than as a name.
	"""
	callLater(_A_TURN_OF_THE_LOOP, action)


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
			_title(),
			DialogType.WARNING,
			buttons=DefaultButtonSet.YES_NO,
		)
		return dialog.setFallbackAction(ReturnCode.NO)

	def answered(dialog: MessageDialog, answer: int) -> None:
		if answer == ReturnCode.YES:
			on_yes()

	show(create, answered)


def choose_file(
	folder: Path | None,
	then: Callable[[Path], None],
	parent: wx.Window | None = None,
) -> None:
	"""Ask which checklist to open, and hand the file the tester picked to `then`.

	The standard file dialog of section 3.2.2, opened by the `O` key of the
	command mode and by a start-up that found the file named in `state.json`
	gone (section 2). It is a file dialog and not the GUI window on purpose:
	`O` answers "which checklist?", one action, while the window with the tree
	and the panels answers everything else.

	`folder` is where the browsing starts — the folder of the last path in
	`state.json`, which is lying there anyway (section 3.2.2) — and None when
	nothing has ever been opened, which leaves the choice to Windows.

	`parent` is the third way in: `Browse...` in the GUI window (section 5),
	which passes that window and gets what `show` makes of a parent. The
	starting folder then comes off the path field rather than off the disk,
	which is that button's business rather than this one's.

	A cancelled dialog calls nothing and says nothing, the same silence as "No"
	above. The window is native rather than one of NVDA's, and nothing about
	the rest changes for that: `displayDialogAsModal` raises the modality
	counter before it looks at what it was given, so the commands of the add-on
	stay blocked behind this one too (section 6).
	"""

	def create(parent: wx.Window) -> wx.FileDialog:
		return wx.FileDialog(
			parent,
			# Translators: The title of the dialog that picks a checklist file to open.
			message=_("Open a checklist"),
			defaultDir="" if folder is None else str(folder),
			# Two entries, and the second one matters (section 3.2.2). Narrowing
			# to `*.json` is worth having: a checklist usually sits in the
			# repository of the product under test, and a tester reading the list
			# by ear should not have to walk past the source files to reach it.
			# But `.json` is only the usual name — section 2 gives it as an
			# example and never as a rule — so "All files" stays, or a checklist
			# saved under any other extension could not be picked at all.
			wildcard="{checklists} (*.json)|*.json|{everything} (*.*)|*.*".format(
				# Translators: The kind of file the Open dialog offers, shown in its file type
				# filter. The pattern "(*.json)" is added after it.
				checklists=_("Checklist files"),
				# Translators: The second entry of the Open dialog's file type filter, which
				# shows every file rather than only checklists. The pattern "(*.*)" is added
				# after it.
				everything=_("All files"),
			),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		)

	def chosen(dialog: wx.FileDialog, answer: int) -> None:
		if answer == wx.ID_OK:
			then(Path(dialog.GetPath()))

	show(create, chosen, parent)


def report(text: str, parent: wx.Window | None = None) -> None:
	"""Show `text` as the error it is, and say nothing out loud.

	Why a file the tester picked themselves would not load (sections 2, 3.2.2
	and 5): which field, which item, which value. It is a window because the
	person pressed "Open" and is waiting for an answer, which is the very case
	section 4 separates from a file that loaded without anyone asking — that
	one gets four words spoken and no window at all.

	`parent` is the GUI window when the file was picked with `Browse...`
	(section 5), and None when it was picked by the `O` key. It goes straight
	to `show`, which holds what a parent of our own changes.

	An error, so the icon and the sound are the ones NVDA gives one. Escape
	closes it without any help from us — a `MessageDialog` falls back to its
	affirmative button when it has no cancel, and OK is the only button here.
	"""

	def create(owner: wx.Window) -> MessageDialog:
		return MessageDialog(
			owner,
			text,
			_title(),
			DialogType.ERROR,
		)

	show(create, parent=parent)
