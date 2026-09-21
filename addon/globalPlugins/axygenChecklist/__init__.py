# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Entry point of the Axygen Checklist add-on: the global commands.

The behaviour is specified in docs/requirements.md. What this module holds is
the half of it that cannot be unit tested — gestures, series of presses,
speech — and it holds as little of that as it can. The rules of section 4
live in `core.run`: every command here is a command of the one `Run` this
plugin holds, and what comes back is a list of events in the order they
happened. This module turns that list into words, tones and the choice of a
channel, and that is the whole of its half (docs/adr/0001).

**No command here changes the system focus from the first press of a global
combination.** That is the invariant of section 1, and the five windows of the
add-on all cost either a second press of a series or a deliberately armed
command mode. A command answers with speech or a tone and leaves the focus
where the tester put it; the ones that open a window do so through `modal`,
which is where the focus is taken and given back.

**Series of presses come from NVDA and from nowhere else.** Section 6 allows
only `scriptHandler.getLastScriptRepeatCount()`: NVDA runs the script on every
press of a series without waiting for the series to end, and the interval it
counts is the user's own `multiPressTimeout`. Measuring the time between calls
ourselves is forbidden, and would hard-code a setting that belongs to the
screen reader. The count is read at the moment of the press and handed to the
run as one boolean — whether this press is a jump — which is all the run needs
to know of it. The command mode is not a series and does not ask (section 6);
`commandmode` counts its own three seconds and says why.

**Every script here drops the command mode before it does anything else**, and
that one line is the whole of section 3.2.3: any command of the add-on but a
key of the armed mode takes the mode away and then runs as usual, announcing
nothing of its own about it. A `NVDA+Alt+PageDown` that said *"Cancelled"*
first would be reporting an action the tester never took. The line stands in
the scripts rather than in the methods below them because it is about the
gesture that arrived, not about the work that follows it. `script_armCommandMode`
is the one script without the line written out, and it is not an exception:
`arm` drops what it finds before taking the keys again, which is the same rule
reaching the same end.

A decorator would carry the rule better than six copies of a line, and one was
tried: a wrapper cannot reach `self._mode` from module scope without pyright's
`reportPrivateUsage`, which the type check CI runs in strict mode, and a
public method on the plugin existing only to be wrapped would be worse than
the line it saved.

**A blocked command is not a command that ran**, so it leaves the mode alone.
`blockAction.when` is the inner decorator and returns before the body, which
is deliberate: while a modal window of the add-on is open the mode cannot be
armed in the first place (arming is blocked too), and a command refused under
someone else's dialog has not executed, so consuming the mode on its behalf
would be inventing an action. The mode then ends the way it would have anyway,
on its own timer.

**One narrator, and it is where the channel is chosen.** `_narrate` walks the
events of an answer and says each in the order the run put them, which is the
order section 4 prescribes: the file is already written by the time the list
comes back, so speech cannot get ahead of the disk; a failed write is the only
event of its list, so one phrase and nothing after it is the shape of the
answer rather than a discipline of the callers; the word for the status stands
before the end of the run before the next item because that is how they
happened. The one thing the narrator is told that the run does not know is
`after_window`: whether a window of the add-on has just closed (section 6).
Then a phrase goes through `modal.message` rather than `ui.message`, or NVDA
announcing the window that got the focus back would cut it off; and the end
of the run, which is a tone **and** a phrase, waits whole through `modal.later`,
or the tone would sound a window announcement ahead of its words. The six
fixed sentences of the add-on stand in the narrator and nowhere else; what is
built out of data is `wording`'s.

**The restore happens on construction; only its failures wait.** Reading the
file is the first thing this plugin does, so that a reload of the plugins
(`NVDA+Ctrl+F3`) comes back holding the same checklist. What cannot happen that
early is speech: at start-up NVDA is still announcing itself and the window in
focus, and a message spoken into that would be cut off by it. So the answer of
`Run.restore` — empty when it went well, one refusal when it did not — is kept
until `core.postNvdaStartup`, which NVDA queues into its own loop once the
initial focus has been reported.

That action fires once per run of NVDA, so a plugin built after it — a reload,
or the add-on being enabled from the Add-on Store — restores in silence. That
is the right way round: the tester is looking at a dialog they opened, not at
the application under test, and the very next command tells them where they
stand anyway. Asking NVDA whether it has finished starting is what would settle
this properly, and there is no public way to: the flag is private, and the
nearest public thing, whether the `wx` main loop is running, is a proxy and not
the fact, since the loop is up before the first focus has been reported.

**The window of section 5 has two ways in, and one of them is not a gesture.**
The `G` key of the command mode is a script like any other; the entry in NVDA's
Tools menu is a `wx` menu item, which belongs to the screen reader's own GUI
rather than to this object and therefore has to be taken back out of it when
NVDA is done with the plugin. Both ways end in the same call, and both carry
the same blocking: the menu stays reachable while a window of the add-on is
open, so without it a second window would be opened from there over the first.
The window is handed the run and asks it for everything it does; the one thing
that comes back out is "Move to", because it has to outlive the window
(section 5.1). The window is `guiwindow`'s, and it is modal like the other four
— so while it stands, nothing here runs (section 3.3.1).

**A checklist arrives two ways, and they are one operation.** Start-up reads
the path out of `state.json`; the `O` key of the command mode asks the tester
for one (section 3.2.2). Both are `Run.open` underneath, and what differs is
where the path came from and what is done with a refusal: spoken in four words
when nobody asked, shown with the field, the item and the value when the tester
has just pressed "Open" (sections 2 and 4). `Browse...` in the window is the
third way in and the same call again.
"""

from collections.abc import Callable
from pathlib import Path
from typing import override

import addonHandler
import api
import globalPluginHandler
import gui
import inputCore
import NVDAState
import scriptHandler
import ui
import wx

# NVDA's own `core`, which shares a name with the add-on's `core` package
# below. The two never collide — one is imported absolutely and the other
# relatively — but `core` in the body of this module would mean whichever the
# reader guessed, so the one name needed is taken out of it instead.
from core import postNvdaStartup
from gui import blockAction
from logHandler import log
from scriptHandler import script

from . import (
	commandmode,
	fragmentsdialog,
	guiwindow,
	itemdialog,
	modal,
	preferences,
	signals,
	wording,
)
from .core import status
from .core.checklist import Item
from .core.navigation import Direction, Position
from .core.progress import Progress
from .core.run import (
	Answer,
	Boundary,
	ChecklistGone,
	ChecklistReset,
	Finished,
	Here,
	Landed,
	NoChecklist,
	NoItems,
	PlaceNotSaved,
	Recorded,
	Refused,
	Run,
	Saved,
	SectionProgress,
	SectionReset,
	Unreadable,
	WriteFailed,
)

addonHandler.initTranslation()

#: The add-on's own folder inside NVDA's configuration directory, where section
#: 2 puts `state.json`. Named after the add-on, which section 6 makes eternal —
#: it is the key of the add-on in the Add-on Store — and which the code package
#: around this file is already obliged to be named after.
_CONFIG_FOLDER = "axygenChecklist"

#: The status each digit of the command mode assigns, by the gesture carrying
#: it: 1 passed, 2 failed, 3 blocked, 4 skipped, 5 pending (section 3.2.2).
#: Read off the one ordering of the statuses rather than written out a second
#: time, so that the digits cannot drift from the combo box of the item dialog,
#: which takes its order from the same tuple.
#:
#: These identifiers are **looked up** as well as bound — `_digit_status` asks
#: an arriving gesture which digit it is — so they are normalized here, in the
#: form `normalizedIdentifiers` will offer them. The letters of `_MODE_KEYS`
#: below are only ever bound, and `bindGesture` normalizes for itself.
#:
#: Letters, not punctuation, and digits are safe for the same reason (section
#: 3.2.2): `A`–`Z` and the digits keep their virtual key codes in every layout,
#: while `[`, `]`, `,` and `.` move with it, so a gesture written with one
#: would stop being the same gesture when the tester switches to Ukrainian.
_DIGIT_STATUSES = {
	inputCore.normalizeGestureIdentifier(f"kb:{digit}"): value
	for digit, value in enumerate(status.STATUSES, start=1)
}

#: What the command mode binds while it is armed: a gesture identifier to the
#: name of the script it runs (section 3.2.2). Only the keys built so far stand
#: here — the rest of the table in the specification arrives with the commands
#: behind them — and none of them costs anything in the global space, which is
#: the currency the whole construction is bought with.
_MODE_KEYS = {
	**{identifier: "setStatus" for identifier in _DIGIT_STATUSES},
	"kb:a": "toggleAutoAdvance",
	"kb:c": "copyFragment",
	"kb:g": "showWindow",
	"kb:o": "openChecklist",
	"kb:p": "speakSectionProgress",
	"kb:r": "resetSection",
}


def _state_file() -> Path:
	"""Where the position is kept between runs of NVDA (section 2).

	`WritePaths.configDir` rather than a path worked out here: it follows the
	NVDA that is actually running, so a portable copy keeps its own state
	beside its own configuration.
	"""
	return Path(NVDAState.WritePaths.configDir) / _CONFIG_FOLDER / "state.json"


def _digit_status(gesture: inputCore.InputGesture) -> str | None:
	"""Which status the digit that raised `gesture` stands for, or None for neither.

	The five digits share one script (section 3.5), so the script is handed the
	gesture and asks it which of them arrived. A keyboard gesture carries both
	the layout-qualified identifier and the plain one, and the plain one is
	what the mode bound.
	"""
	for identifier in gesture.normalizedIdentifiers:
		value = _DIGIT_STATUSES.get(identifier)
		if value is not None:
			return value
	return None


def _hold(action: Callable[[], None], after_window: bool) -> None:
	"""Do `action` now, or on the turn of the event loop a closing window needs.

	What the narrator does with the two things that are not a bare phrase of
	the add-on's — a tone, and a tone with a phrase attached (section 6). A
	phrase on its own has `modal.message` for the same moment; these have to
	wait as a whole, or the tone would be heard a window announcement ahead
	of the words it belongs to.
	"""
	if after_window:
		modal.later(action)
	else:
		action()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin holding the checklist commands."""

	# Translators: The name of the category this add-on's commands appear under
	# in NVDA's Input Gestures dialog.
	scriptCategory = _("Axygen Checklist")

	def __init__(self):
		super().__init__()
		#: The one run of the plugin's life: the checklist or its absence, the
		#: position, the anchor of a series and the file the position is kept
		#: across restarts of NVDA. Every command is a command of it, and
		#: every answer comes back as events for `_narrate` to say.
		self._run = Run(_state_file())
		#: The temporary layer the rare commands live behind (section 3.2.2).
		#: Not armed until `NVDA+Alt+O` arms it, and never arming itself.
		self._mode = commandmode.CommandMode(self, _MODE_KEYS)
		#: The add-on's entry in NVDA's Tools menu, and None when there was
		#: nowhere to put one. Kept so that `terminate` can take it away again.
		self._menu_item = self._add_to_tools_menu()
		#: What the restore could not do, until there is anyone to hear it.
		#: Empty when it went well, which section 2 answers with silence.
		self._startup: list[Answer] = self._run.restore()
		postNvdaStartup.register(self._announce_restore)
		log.info("Axygen Checklist loaded")

	@override
	def terminate(self) -> None:
		"""NVDA is done with this plugin: let go of everything that outlives it.

		The extension point holds bound methods weakly and would drop the
		start-up handler on its own, but only whenever the plugin is collected.
		Saying so here makes it the moment NVDA names for it.

		The command mode has to go for a harder reason. A `wx.CallLater` left
		running holds this plugin alive and fires into it afterwards — after a
		reload of the plugins (`NVDA+Ctrl+F3`), that is a tone from an add-on
		that no longer exists, and gestures taken off an object nobody is
		listening to any more.

		The window and the menu item are the same story told in wx. Both belong
		to NVDA's own GUI rather than to this object, so neither goes anywhere
		when the plugin does: a reload would leave a window showing a checklist
		the new plugin knows nothing about, and a second entry in the Tools menu
		beside it.
		"""
		self._mode.disarm()
		guiwindow.close()
		self._remove_from_tools_menu()
		postNvdaStartup.unregister(self._announce_restore)
		super().terminate()

	def _add_to_tools_menu(self) -> wx.MenuItem | None:
		"""Put the add-on in NVDA's Tools menu (section 5).

		One of the two ways into the window, and the one that makes it findable:
		a tester who has not learned the `G` key of the command mode still has
		somewhere to arrive from. The label is the product name, which is what
		the window is titled too — a menu entry and a window announcing
		themselves differently would be the first thing heard and the first thing
		wrong (section 5).

		None comes back when NVDA has no main frame to hang a menu off, which no
		ordinary start-up reaches: `gui.initialize()` runs before global plugins
		are loaded. There is nothing to say out loud about it either — the tester
		asked for nothing — so it is a line in the log and the `G` key still
		works.
		"""
		frame = gui.mainFrame
		if frame is None:
			log.error("no main frame to offer the add-on in the Tools menu of")
			return None
		item: wx.MenuItem = frame.sysTrayIcon.toolsMenu.Append(
			wx.ID_ANY,
			# Translators: The add-on's entry in the Tools menu of NVDA, which opens the
			# window showing the whole checklist. It is the product name, which is not
			# translated in any locale.
			_("Axygen Checklist"),
		)
		frame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_item, item)
		return item

	def _remove_from_tools_menu(self) -> None:
		"""Take the entry out of NVDA's Tools menu again.

		The menu belongs to NVDA and outlives this plugin, so an entry left in it
		after a reload would sit beside the new one and call into a plugin that
		has gone.

		**The handler comes off before the entry does.** `Bind` leaves the tray
		icon holding a bound method of this object, and that reference outlives
		everything else here: an entry taken out of the menu without it would
		leave a reloaded NVDA holding one dead plugin per reload.

		A menu already destroyed is the ordinary case on the way out of NVDA, and
		wx answers a call into a destroyed object with `RuntimeError`. There is
		nothing to do about it and nobody to tell: the menu the entry was in does
		not exist any more either.
		"""
		item = self._menu_item
		self._menu_item = None
		frame = gui.mainFrame
		if item is None or frame is None:
			return
		try:
			frame.sysTrayIcon.Unbind(wx.EVT_MENU, source=item, handler=self._on_menu_item)
			# `Delete` rather than `Remove`: the second hands the entry back to
			# us still alive, and there is nothing here that wants one.
			frame.sysTrayIcon.toolsMenu.Delete(item)
		except RuntimeError:
			log.debug("the Tools menu had gone before the add-on's entry in it", exc_info=True)

	def _announce_restore(self) -> None:
		"""Say what the restore could not do, now that NVDA can be heard.

		Section 4 allows the short spoken message and forbids a window for a
		file that is there and will not load: the tester is working in the
		application under test, and a dialog that appeared by itself would take
		the focus with it. A file that has **gone** is the other case, and
		section 2 answers it with this warning and then the file dialog —
		because there is nothing to work with at all until another path is
		given, and that dialog is what the tester would open with their first
		command anyway. The two are told apart here rather than in the
		narrator, because the window is this method's to open, and the phrase
		has to precede it.

		**The warning that comes with a window goes out through `modal.message`**,
		and that was found by ear rather than reasoned out: spoken through
		`ui.message` it did not survive at all. NVDA cancels speech when the
		foreground changes (section 6), and a window opening is such a change,
		so the phrase was cut off by the file dialog announcing itself.
		`ui.delayedMessage` is the answer NVDA gives its own messages around a
		window, and its delay is one millisecond — not a wait for anything, but
		a turn of the event loop: the phrase is queued **after** the pending
		foreground event has done its cancelling, and at `Spri.NOW`, so nothing
		queued in front of it stands in its way. The same call carries it to
		braille, which matters here more than anywhere: this message is the
		whole explanation of a window the tester did not ask for. So the
		narrator is told `after_window` although the window is about to open
		rather than just closed: the mechanism is the same one, and section 2
		says so.

		A failure with no window keeps `ui.message` (section 4). There is
		nothing about to cancel it, and delaying it would buy nothing.
		"""
		answer = self._startup
		# Cleared before anything is said, so that nothing here can be owed twice.
		self._startup = []
		match answer:
			case [ChecklistGone()]:
				self._narrate(answer, after_window=True)
				self._choose_checklist()
			case _:
				self._narrate(answer)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Moves to the next item of the checklist. Twice: to the first item of the next section",
		),
		gesture="kb:NVDA+alt+pageDown",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_nextItem(self, gesture: inputCore.InputGesture) -> None:
		self._mode.disarm()
		self._narrate(
			self._run.navigate(Direction.FORWARD, jump=scriptHandler.getLastScriptRepeatCount() > 0),
		)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Moves to the previous item of the checklist. Twice: to the first item of the previous section",
		),
		gesture="kb:NVDA+alt+pageUp",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_previousItem(self, gesture: inputCore.InputGesture) -> None:
		self._mode.disarm()
		self._narrate(
			self._run.navigate(Direction.BACKWARD, jump=scriptHandler.getLastScriptRepeatCount() > 0),
		)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Marks the current checklist item as passed, or as not checked if it passed already",
		),
		gesture="kb:NVDA+alt+space",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_toggleStatus(self, gesture: inputCore.InputGesture) -> None:
		# `getLastScriptRepeatCount` is deliberately not asked. Section 3.2.1 gives
		# this command no series at all: a second press is another toggle, which
		# puts the status back, and the most frequent key of the add-on is
		# therefore never one accidental double tap away from anything
		# destructive. Resetting a section lives behind the command mode and a
		# Yes/No dialog instead.
		#
		# Auto-advance is read now and handed over as a value (section 4): the
		# option is NVDA's, a profile switch changes it without anything here
		# being told, and `preferences` says why it may not be held anywhere.
		self._mode.disarm()
		self._narrate(self._run.toggle(preferences.auto_advance()))

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Reads the current item of the checklist again. Twice: opens the item dialog",
		),
		gesture="kb:NVDA+alt+i",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_readItem(self, gesture: inputCore.InputGesture) -> None:
		self._mode.disarm()
		answer = self._run.here()
		if scriptHandler.getLastScriptRepeatCount() == 0:
			self._narrate(answer)
			return
		# The second press, and the heavy end of the series (section 3.3): the
		# window may not open on the first, which would take the focus and put
		# the second press out of reach (section 6). What the first press said
		# is cut off by this one, as any keypress cancels speech — which is why
		# the dialog puts the text of the item and the note in the description
		# NVDA reads on opening rather than leaving them to that first press
		# (section 3.3.1).
		#
		# There is no third press to answer: the window is modal, so every
		# command of the add-on is blocked behind it, and `modal.show` clears
		# the series besides (section 3.3.1).
		match answer:
			case [Here(item, _)]:
				itemdialog.show(
					item,
					lambda status_value, comment: self._saved(item, status_value, comment),
				)
			case _:
				# Nowhere to stand, and the reason is said again: the first press
				# said it too, and this press has just cut that off.
				self._narrate(answer)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Arms the command mode of the checklist for three seconds",
		),
		gesture="kb:NVDA+alt+o",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_armCommandMode(self, gesture: inputCore.InputGesture) -> None:
		# `getLastScriptRepeatCount` is not asked here either, and here section 6
		# forbids it outright: the mode lives longer than `multiPressTimeout`, so
		# NVDA would have called the second press the first of a new series
		# anyway. A second `NVDA+Alt+O` without letting the modifiers go is
		# therefore what section 3.2.3 makes of any command of the add-on — the
		# mode dropped, the command run as usual — and running this one as usual
		# is arming it again, tone and all. `arm` drops what it finds first.
		#
		# No checklist is asked for, unlike every other command. The mode is a
		# shell, and each key inside it answers for itself; refusing to arm
		# without a file would put `O`, the one command that opens a file, behind
		# having opened one.
		self._mode.arm()

	@script()
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_setStatus(self, gesture: inputCore.InputGesture) -> None:
		# No description, and that is exactly what keeps the five digits out of
		# the Input Gestures dialog (section 3.5). NVDA lists a script by its
		# `__doc__`, which the decorator sets from `description`, and skips the
		# ones that have none — so the empty decorator is the requirement rather
		# than an oversight, and it holds whatever anyone writes below it. They
		# are not five commands but five variants of one, and five rows in that
		# list would cost more than they gave.
		self._mode.disarm()
		value = _digit_status(gesture)
		if value is None:
			# Unreachable through the add-on: the mode binds these five and the
			# dialog cannot add a sixth. A gesture written into `gestures.ini` by
			# hand could still arrive, and there is no status to assign and
			# nothing worth saying out loud about it.
			log.error(f"no status behind the command mode gesture {gesture.normalizedIdentifiers}")
			return
		# The honest repeat of section 4: a digit assigns the status outright and
		# may be pressed as often as the tester likes, where the space bar would
		# toggle away from it. Nothing here asks whether the status is already
		# the one being assigned, and neither does the run.
		self._narrate(self._run.assign(value, preferences.auto_advance()))

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Opens a checklist file",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_openChecklist(self, gesture: inputCore.InputGesture) -> None:
		# The `O` key of the command mode, and the whole of it is "NVDA+Alt+O,
		# release, O" (section 3.2.2). Held down, a second NVDA+Alt+O is the
		# global command over again — the mode dropped and armed afresh — so the
		# cheat sheet writes that line out in full. The cost of getting it wrong
		# is a tone instead of a window, and nothing else.
		#
		# One of the two commands that ask for no checklist, and this one is how
		# a checklist arrives at all. The run is not asked where it stands, and
		# nothing here says "No checklist loaded" — that would put the only way
		# in behind having already come in. `A` is the other, for a reason of
		# its own (section 4): what it toggles does not live in the file.
		self._mode.disarm()
		self._choose_checklist()

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Reads the name of the current section of the checklist and the progress through it",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_speakSectionProgress(self, gesture: inputCore.InputGesture) -> None:
		# No gesture of its own: this one lives behind the command mode, and
		# section 3.5 has it stand in the Input Gestures dialog with an empty
		# binding all the same — reachable through the mode, and available to
		# anyone who would rather give it a key. Without that, moving a command
		# into the mode would take its rebinding away along with its hotkey.
		self._mode.disarm()
		self._narrate(self._run.progress())

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Resets the current section of the checklist, erasing its statuses and comments",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_resetSection(self, gesture: inputCore.InputGesture) -> None:
		# The `R` key of the command mode, and the first command of the add-on
		# to open a window. It may, and that is the focus invariant of section
		# 1 as it applies here: the window costs a deliberately armed mode, so
		# nobody working in someone else's window reaches it by accident. The
		# dialog is the confirmation entire — no state waits for a second press
		# and no second timer runs over the first (section 3.2.2).
		#
		# The run is asked where it stands before the question is asked, so
		# that a tester with nowhere to stand hears why instead of a question
		# about nothing. Which section the Yes will reset is settled by the run
		# when the answer arrives, and that is the section they asked about:
		# every command is blocked while the dialog stands (section 3.3.1), so
		# nothing can have moved the position in between.
		self._mode.disarm()
		answer = self._run.here()
		match answer:
			case [Here()]:
				modal.confirm(
					_(
						# Translators: The question asked before the current section of the checklist
						# is reset, that is every item put back to not checked and every comment erased.
						"Reset the section? Every status and comment in the section will be erased. "
						"This cannot be undone.",
					),
					on_yes=lambda: self._narrate(self._run.reset_section(), after_window=True),
				)
			case _:
				self._narrate(answer)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Copies a fragment of the current checklist item to the clipboard",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_copyFragment(self, gesture: inputCore.InputGesture) -> None:
		# The `C` key of the command mode (section 3.2.2), and the one command of
		# the add-on that answers three different ways depending on the data:
		# none, one and many. All three are announced, so the tester never has to
		# guess which one happened — a total rule that turns on the state of the
		# data, as section 3.2.1 already has.
		self._mode.disarm()
		answer = self._run.here()
		match answer:
			case [Here(item, _)]:
				self._copy_fragment_of(item)
			case _:
				self._narrate(answer)

	def _copy_fragment_of(self, item: Item) -> None:
		"""Put a fragment of `item` in the clipboard, or say that it has none (section 3.2.2)."""
		found = item.fragments
		if not found:
			# Worded away from NVDA's own "Unable to copy", which the Ukrainian
			# catalogue renders as "there is nothing to copy": without that, the
			# two cases would be one phrase by ear (section 3.2.2).
			ui.message(
				# Translators: Spoken when the copy command is used on a checklist item whose
				# text and note hold no fragments to copy.
				_("The item has no fragments"),
			)
			return
		if len(found) == 1:
			# No window, and that is the point: there is nothing to choose
			# between, and one would cost a change of focus and an Escape in the
			# commonest case of all. The command runs from where the tester
			# stands, so the confirmation is heard at once — unlike the one below.
			self._copy(found[0])
			return
		fragmentsdialog.show(found, self._copy_later)

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Turns on or off moving to the next checklist item once this one has a verdict",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_toggleAutoAdvance(self, gesture: inputCore.InputGesture) -> None:
		# The `A` key of the command mode (section 3.2.2), in the shape NVDA
		# gives its own toggles: assign in `config.conf`, then say the new state
		# (`script_toggleSpeakCommandKeys` and the rest of `globalCommands.py`).
		# The position is left where it was — like the filter of section 3.4,
		# this changes a mode rather than moving anyone.
		#
		# **No checklist is asked for** (section 4), which makes this the second
		# key of the mode not to, beside `O`. The preference lives in NVDA's
		# configuration rather than in the file, so there is nothing here a
		# checklist would supply; answering "No checklist loaded" would mean
		# either refusing to write the option, against the requirement to write
		# it at once, or writing it and then saying something else had happened.
		#
		# The two phrases are spoken from here and nowhere else, so they stay
		# here rather than going to `wording`: the checkbox of the GUI (section
		# 5) is the other way to the same option, and a checkbox is announced by
		# NVDA out of its own label.
		self._mode.disarm()
		enabled = not preferences.auto_advance()
		preferences.set_auto_advance(enabled)
		if enabled:
			# Translators: Spoken when auto-advance has just been turned on, so that giving an
			# item a verdict moves on to the next item of the checklist.
			ui.message(_("Auto-advance on"))
			return
		# Translators: Spoken when auto-advance has just been turned off, so that giving an item
		# a verdict leaves the position on the item it was given to.
		ui.message(_("Auto-advance off"))

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Opens the window showing the whole checklist",
		),
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_showWindow(self, gesture: inputCore.InputGesture) -> None:
		# The `G` key of the command mode (section 3.2.2), and the second way to
		# the one window the Tools menu also leads to (section 5). It may take
		# the focus, and the focus invariant of section 1 is why it may: the
		# window costs a deliberately armed mode, so nobody working in someone
		# else's window arrives here by accident.
		#
		# No checklist is asked for, which makes this the third key of the mode
		# not to, beside `O` and `A`. Section 5 puts the choosing of a file
		# inside this window, so asking for one at the door would put the way in
		# behind having come in.
		self._mode.disarm()
		self._show_window()

	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def _on_menu_item(self, event: wx.CommandEvent) -> None:
		"""The add-on was picked out of NVDA's Tools menu (section 5).

		The other way to the same window, and it is the same call: which of the
		two the tester used is not a difference the window is told about.

		**Blocked like every script**, and for a reason the scripts do not have:
		the menu of NVDA is still reachable while a window of the add-on stands,
		so this is the one way a second window could be asked for. The decorator
		is NVDA's own, so the refusal is spoken in NVDA's own words and the
		add-on says nothing (section 3.3.1).
		"""
		self._show_window()

	def _show_window(self) -> None:
		"""Show the window on the run, whichever way in was used.

		Section 5: the window is handed the run itself — the checklist in hand
		and where the tester stands in it, which may both be absent, and
		neither is a refusal: the window opens on an empty tree, and
		`guiwindow.show` says why. Everything the window changes it asks the
		run for directly, and decides for itself what silence section 5 owes
		it; "Move to" alone comes back out as a call, because it arrives once
		the window has closed and has to be spoken late (section 6).
		"""
		guiwindow.show(self._run, self._move_to)

	def _move_to(self, found: Position) -> None:
		"""Stand where the window was asked to move to (section 5.1).

		The one action of the window that moves the position, and an ordinary
		move once it gets here: the position reaches `state.json` at once and
		the item is spoken with the name of its section, as after a jump. The
		phrase goes out late: the window has just handed the focus back, and
		NVDA is about to announce the window that took it (section 6).
		"""
		self._narrate(self._run.move_to(found), after_window=True)

	def _saved(self, item: Item, status_value: str, comment: str) -> None:
		"""The item dialog was saved from `NVDA+Alt+I`: write, and say what moved.

		Whether anything is written, which words are owed and whether the run
		has just ended are the run's to settle (section 3.3.1); everything it
		answers goes out late, because the window has just handed the focus
		back (section 6). A save from the tree of the window is the same call
		made by the window, which owes different silences (section 5.2).
		"""
		self._narrate(self._run.save(item, status_value, comment), after_window=True)

	def _choose_checklist(self) -> None:
		"""Ask the tester which checklist to open (section 3.2.2).

		The browsing starts in the folder of the last path in `state.json`,
		which is lying there anyway (section 3.2.2), and the run reads it off
		the disk rather than off the checklist in hand: the two agree while one
		is open, and the moment they do not is exactly the moment this is
		wanted — start-up found the file gone, so there is no checklist in hand
		and the only thing left pointing anywhere is that path (section 2).

		The answer arrives long after this has returned, in `_open`.
		"""
		modal.choose_file(self._run.remembered(), self._open)

	def _open(self, path: Path) -> None:
		"""Open the checklist the tester just picked, or show why it will not open.

		The far side of the file dialog opened by `O` (section 3.2.2). The
		opening is `Run.open`'s, and it answers a refusal with exactly one
		event, which is what lets the list be taken apart by shape: one
		refusal, a window; anything else, the ordinary narration of a landing.

		The window shows the long form, which names the field, the item and
		the value (section 2): the person who pressed "Open" is waiting for an
		answer, where a file that loaded without anyone asking gets four words
		spoken and no window (section 4). A file that could not be opened at
		all — taken away or locked between the picking and the opening — has
		no field, item or value to name, and the window shows the same short
		sentence the voice would have used; which encoding the author had in
		mind, or what the file system objected to, is not something the add-on
		can say, and the log is where the second survives.

		What opened is spoken late: the file dialog has just handed the focus
		back, and NVDA is about to announce the window that took it (section
		6). A file just opened is a jump, so the section is named (section
		3.2.2), and a checklist with nowhere to stand in says so.
		"""
		answer = self._run.open(path)
		match answer:
			case [Refused(problem)]:
				modal.report(wording.shown_refusal(problem))
			case [Unreadable(error)]:
				log.error(f"could not read the checklist at {path}", exc_info=error)
				modal.report(wording.shown_refusal())
			case [ChecklistGone()]:
				log.error(f"the checklist at {path} was gone before it could be opened")
				modal.report(wording.shown_refusal())
			case _:
				self._narrate(answer, after_window=True)

	def _copy(self, fragment: str) -> None:
		"""Put `fragment` in the clipboard, and let NVDA say how that went.

		Section 3.2.2 hands the confirmation to `api.copyToClip(notify=True)`,
		which checks the write by reading it back and answers out of **NVDA's**
		catalogue rather than ours — the same wording the tester hears from
		`NVDA+F10` and `NVDA+T`, and not one new string to translate. This is
		the one exception section 4 makes to saying everything through
		`ui.message`, and the return value is dropped with it: what became of
		the write has already been spoken by the time it comes back.

		Called outright when the item held a single fragment, and through
		`modal.later` when the tester picked one out of the window. That delay
		is section 6's rule read through what it is really about:
		`api.copyToClip` speaks through `ui.message`, so a confirmation queued
		the moment the window closed would be cut off by the foreground event of
		the application under test getting the focus back. The phrase cannot be
		held on its own — it belongs to NVDA and is born inside the call — so
		the whole call waits the turn of the event loop, clipboard and all.
		"""
		_ = api.copyToClip(fragment, notify=True)

	def _copy_later(self, fragment: str) -> None:
		"""`_copy`, held for the turn of the event loop a closing window needs.

		What the fragments dialog is answered with. The window has just handed
		the focus back, and NVDA is about to announce the application that took
		it; section 6 delays the whole call rather than the phrase inside it,
		because the phrase belongs to NVDA's catalogue and is born within
		`api.copyToClip`. Named rather than written as a lambda at the call
		site so that the dialog is handed one plain callback, as the item
		dialog is, and so that the delay has somewhere to be explained.
		"""
		modal.later(lambda: self._copy(fragment))

	def _narrate(self, answer: list[Answer], after_window: bool = False) -> None:
		"""Say what the run answered, in the order it happened.

		The one place the events become words, tones and a channel. Every
		event is met here, and the type check holds the `match` to the whole
		set: an event added to the run and forgotten here would be silence,
		which is what a global plugin may least afford.

		`after_window` is whether a window of the add-on has just closed, and
		it chooses the channel and nothing else (section 6): `modal.message`
		for a phrase, which would otherwise be cut off by NVDA announcing the
		window that got the focus back, and `modal.later` for the two things
		that are not a bare phrase — a tone, and the tone with the phrase of
		the end of the run. From a command that runs with the focus where the
		tester left it, `ui.message` is heard at once, and a delay would only
		put the answer back.

		**Failures go to the log first**, with the traceback the core could
		not write: the core answers with the error and keeps out of NVDA's log
		altogether. A write of the checklist that failed is spoken as well,
		every time, because the phrase is the whole result of the command
		(section 4); a write of `state.json` that failed is not, because it
		runs on every press of a navigation key and would drown the item it
		was pressed for, and what is lost is the place rather than the run
		(section 2).
		"""
		say: Callable[[str], None] = modal.message if after_window else ui.message
		for event in answer:
			match event:
				case Landed(item, section, jump):
					# The name of the section belongs to a jump and to nothing
					# else (section 3.1): a step to the next item would be paying
					# for a word the tester already knows, on every press.
					say(wording.spoken_item(item, section.name if jump else None))
				case Here(item, _):
					say(wording.spoken_item(item))
				case Boundary(direction, jump):
					# Section 3.1 answers a single press with a tone and a jump
					# with words: a tone is what the most frequent of the two can
					# afford, while a jump is deliberate, and silence would not
					# say whether it failed or landed somewhere unheard.
					if not jump:
						_hold(signals.list_boundary, after_window)
					elif direction is Direction.FORWARD:
						# Translators: Spoken when there is no section after this one to jump to.
						say(_("End of list"))
					else:
						# Translators: Spoken when there is no section before this one to jump to.
						say(_("Start of list"))
				case NoChecklist():
					# Translators: Spoken when a command is used before a checklist has been opened.
					say(_("No checklist loaded"))
				case NoItems():
					# Translators: Spoken when a command is used on a checklist whose sections
					# are all empty, so there is no item to stand on.
					say(_("The checklist has no items"))
				case Recorded(value):
					say(wording.status_word(value))
				case Saved(change):
					say(wording.spoken_save(change))
				case Finished(counted):
					self._finish(counted, after_window)
				case SectionReset():
					# Translators: Spoken after the current section of the checklist has been reset.
					say(_("Section reset"))
				case ChecklistReset():
					# Answered only to the window, which owes it silence (section
					# 5): the tree it rebuilds is the proof, and a word over it
					# would be noise. Nothing here asks the run for one.
					pass
				case WriteFailed(error):
					log.error("could not write the checklist", exc_info=error)
					say(wording.spoken_write_failure())
				case PlaceNotSaved(error):
					log.error("could not write the session state", exc_info=error)
				case SectionProgress(section, counted):
					say(wording.spoken_progress(section.name, counted))
				case Refused(problem):
					say(wording.spoken_refusal(problem))
				case Unreadable(error):
					log.error("could not read the checklist", exc_info=error)
					say(wording.spoken_refusal())
				case ChecklistGone():
					# Translators: Spoken when NVDA starts and the checklist that was open
					# last time is no longer where it was.
					say(_("Checklist file not found"))

	def _finish(self, counted: Progress, after_window: bool) -> None:
		"""Say that the run is over: a tone, and the count (section 4).

		It belongs to every path that gives an item a status — the quick
		toggle, a digit of the command mode, the combo box of the item dialog
		— rather than to any one of them. It is news about the run, so
		auto-advance has no say in whether it is spoken, and the condition is
		the run's: nothing still `pending`, rather than everything passed.

		**The tone will be heard before the verdict it follows**, and that is
		accepted rather than overlooked. `ui.message` puts the status word in
		the speech queue while `tones.beep` sounds straight away, so the order
		written here — section 4's "additionally plays a signal and speaks" —
		is the order of the sentence rather than of the ear. Interleaving them
		properly would mean a `BeepCommand` inside a speech sequence, which
		costs both rules it would break: section 4 sends every message through
		`ui.message`, and `signals` is the only module that touches `tones`, so
		that the five signals can be picked to differ from one another.

		After a window the pair waits whole, through `_hold`: delaying only the
		phrase would part the two by a whole window announcement.
		"""

		def announce() -> None:
			signals.checklist_finished()
			ui.message(wording.spoken_completion(counted))

		_hold(announce, after_window)
