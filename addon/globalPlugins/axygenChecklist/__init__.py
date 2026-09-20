# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Entry point of the Axygen Checklist add-on: the global commands.

The behaviour is specified in docs/requirements.md. What this module holds is
the half of it that cannot be unit tested — gestures, series of presses, speech
— and it holds as little of that as it can: where the tester is and where a
move takes them is worked out in `core.navigation`, and the words are in
`wording`.

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
screen reader. The command mode is not a series and does not ask (section 6);
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

**The position reaches the disk whenever a command moves it.** Section 2 keeps
it in `state.json` — navigation included, not only where a status is being
written beside it — so that a restart of the screen reader puts the tester back
where they stopped. `_remember` is the one place that writes, and that is the
whole of the discipline: there is no other moment at which the file is brought
up to date, as there is none for the checklist. Reading the position back is
not a change and writes nothing; `_restore` says what that buys.

**A command that changes data writes first and speaks second** (section 4).
The two files differ in what a failed write costs and so in what is said about
it: losing the position costs the place and is answered with a line in the log,
while losing a verdict costs the run and refuses the command out loud, every
time. What the tester hears then is one phrase and nothing after it.

**The restore happens on construction; only its failures wait.** Reading the
file is the first thing this plugin does, so that a reload of the plugins
(`NVDA+Ctrl+F3`) comes back holding the same checklist. What cannot happen that
early is speech: at start-up NVDA is still announcing itself and the window in
focus, and a message spoken into that would be cut off by it. So a failure is
kept until `core.postNvdaStartup`, which NVDA queues into its own loop once the
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
The window itself is `guiwindow`'s, and it is modal like the other four — so
while it stands, nothing here runs (section 3.3.1).

**A checklist arrives two ways, and they are one operation.** Start-up reads
the path out of `state.json`; the `O` key of the command mode asks the tester
for one (section 3.2.2). What differs is where the path came from and what is
said afterwards — nothing else, which is why `_adopt` holds the part in the
middle. A start-up that finds its file gone does both in turn: it says so, and
then opens the very dialog `O` would have (section 2). The GUI of section 5
will be the third way in and the same operation again.
"""

import dataclasses
from collections.abc import Callable
from pathlib import Path

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

# `override` is in `typing` from Python 3.12 on. NVDA 2025.3 runs the add-on under
# 3.11 and ships `typing_extensions` for its own use, so that is where it comes from
# until the Python of `addon_lastTestedNVDAVersion` moves.
from typing_extensions import override

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
from .core import checklist, navigation, progress, session, status
from .core.checklist import Checklist, Item, Section
from .core.navigation import Direction, Position, Step
from .core.session import Session

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


@dataclasses.dataclass(frozen=True)
class _RestoreFailure:
	"""What a restore at start-up could not do, until there is anyone to hear it.

	There is always something to say — section 4 gives every way a checklist can
	fail to load its own short sentence — so the message is not optional, and a
	restore that went well has no `_RestoreFailure` at all rather than an empty
	one. Only one failure also owes a window: the file named in `state.json` is
	no longer on the disk, so there is nothing to work with until another path
	is given, and section 2 has the add-on ask for one. A file that is there and
	broken is not that case and opens no window (section 4).
	"""

	message: str
	choose_a_file: bool = False


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


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin holding the checklist commands."""

	# Translators: The name of the category this add-on's commands appear under
	# in NVDA's Input Gestures dialog.
	scriptCategory = _("Axygen Checklist")

	def __init__(self):
		super().__init__()
		#: The checklist the commands work on, or None while none is loaded.
		#: Loading it is the business of the file dialog and of `state.json`;
		#: until one of them puts it here, every command says so (section 4).
		self._checklist: Checklist | None = None
		#: Where the tester is, and None when there is nowhere to stand.
		#:
		#: Optional rather than a position that starts at the top, because a
		#: checklist with no items in it at all is a *valid* file: section 2
		#: requires at least one section and never a minimum of items. Whatever
		#: loads a checklist has to work out where a run starts and may find
		#: that there is no answer; asserting `Position(0, 0)` instead would
		#: read past the end of an empty section, and an exception inside a
		#: global plugin is exactly the mid-session silence section 2 exists to
		#: prevent.
		self._position: Position | None = None
		#: Where the current series of presses started. Section 3.1: the single
		#: press has already moved by the time the second press arrives, so a
		#: jump measured from the item it landed on would skip a whole section.
		#: Scratch for the length of one series, and read only on a press that
		#: has a press of its own before it.
		self._anchor = Position(0, 0)
		#: The temporary layer the rare commands live behind (section 3.2.2).
		#: Not armed until `NVDA+Alt+O` arms it, and never arming itself.
		self._mode = commandmode.CommandMode(self, _MODE_KEYS)
		#: Where the position between runs of NVDA is kept (section 2).
		self._state = _state_file()
		#: The add-on's entry in NVDA's Tools menu, and None when there was
		#: nowhere to put one. Kept so that `terminate` can take it away again.
		self._menu_item = self._add_to_tools_menu()
		#: What the restore could not do, until there is anyone to hear it. None
		#: when it went well, which section 2 answers with silence.
		self._startup_failure = self._restore()
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

	def _restore(self) -> _RestoreFailure | None:
		"""Pick the run up where the last one left it, and say what stopped it.

		Section 2: the path and the pair of indices come out of `state.json`,
		and a restart of NVDA lands the tester back on the item they stopped
		on. Nothing is said when that works — no command was given, and NVDA is
		mid-sentence about itself at this moment anyway. What comes back is what
		a failure has earned, for `_announce_restore` to make good on later.

		**Nothing is written back here**, whether this went well or badly. A
		restore reads the position rather than changing it, and section 2 has
		the file written on a change; a failure has all the more reason to
		leave it alone, since the path in it is where the file dialog starts
		browsing (section 3.2.2) and that is wanted precisely when the file it
		names has gone. Even a position the file has outgrown is left standing:
		the next move writes the real one, and until then a checklist broken
		only for the moment can still give the tester their place back.
		"""
		remembered = session.load(self._state)
		if remembered.checklist is None:
			return None
		try:
			loaded = checklist.load(remembered.checklist)
		except FileNotFoundError:
			return _RestoreFailure(
				# Translators: Spoken when NVDA starts and the checklist that was open
				# last time is no longer where it was.
				_("Checklist file not found"),
				choose_a_file=True,
			)
		except OSError:
			# Everything else that stops a file being read at all: no permission,
			# a drive that is not there, a name Windows will not open. Section 2
			# gives them the same four words as a broken file, and the log is
			# where the difference between them survives.
			log.error(f"could not read the checklist at {remembered.checklist}", exc_info=True)
			return _RestoreFailure(wording.spoken_refusal())
		except checklist.ChecklistError as refusal:
			return _RestoreFailure(wording.spoken_refusal(refusal.problem))
		self._adopt(loaded, remembered.position_in(remembered.checklist))
		return None

	def _announce_restore(self) -> None:
		"""Say what the restore could not do, now that NVDA can be heard.

		Section 4 allows the short spoken message and forbids a window for a
		file that is there and will not load: the tester is working in the
		application under test, and a dialog that appeared by itself would take
		the focus with it. A file that has **gone** is the other case, and
		section 2 answers it with this warning and then the file dialog —
		because there is nothing to work with at all until another path is
		given, and that dialog is what the tester would open with their first
		command anyway.

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
		whole explanation of a window the tester did not ask for.

		A failure with no window keeps `ui.message` (section 4). There is
		nothing about to cancel it, and delaying it would buy nothing.
		"""
		failure = self._startup_failure
		if failure is None:
			return
		# Cleared before anything is said, so that nothing here can be owed twice.
		self._startup_failure = None
		if not failure.choose_a_file:
			ui.message(failure.message)
			return
		modal.message(failure.message)
		self._choose_checklist()

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
		self._navigate(Direction.FORWARD)

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
		self._navigate(Direction.BACKWARD)

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
		self._mode.disarm()
		self._record_status(status.toggled)

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
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		if scriptHandler.getLastScriptRepeatCount() == 0:
			self._speak(loaded, position)
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
		item = navigation.item_at(loaded, position)
		itemdialog.show(
			item,
			lambda status_value, comment: self._save_item(loaded, item, status_value, comment),
		)

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
		# toggle away from it. So nothing here asks whether the status is already
		# the one being assigned — the write and the word happen either way.
		self._record_status(lambda _current: value)

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
		# a checklist arrives at all. `_standing` is not called, and nothing
		# here says "No checklist loaded" — that would put the only way in
		# behind having already come in. `A` is the other, for a reason of its
		# own (section 4): what it toggles does not live in the file.
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
		self._speak_progress()

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
		# and no second timer runs over the first (section 3.2.2). The mode is
		# dropped now, as by any key of it, and the answer arrives after this
		# script has long returned; what it is about is settled here, while
		# the tester still stands in the section they asked about.
		self._mode.disarm()
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		section = navigation.section_at(loaded, position)
		modal.confirm(
			_(
				# Translators: The question asked before the current section of the checklist
				# is reset, that is every item put back to not checked and every comment erased.
				"Reset the section? Every status and comment in the section will be erased. "
				"This cannot be undone.",
			),
			on_yes=lambda: self._reset_section(loaded, section),
		)

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
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		found = navigation.item_at(loaded, position).fragments
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
		"""Show the window, on the checklist and the place the commands work on.

		Section 5: whichever way in was used, what the window is given is what
		every command is given — the checklist in hand and where the tester
		stands in it — so the node that opens selected is the item the next
		command would be about. Both may be None, and neither is a refusal: the
		window opens on an empty tree, and `guiwindow.show` says why.

		Nothing is remembered here, and the callbacks are why nothing needs to
		be: selecting in the tree is a view and moves no one (section 5), and
		everything that does change something comes back out as a call. "Move
		to" arrives once the window has closed, which is what makes `_move_to`
		speak late; a save from the item dialog and a file picked with
		`Browse...` arrive while it still stands.
		"""
		guiwindow.show(
			self._checklist,
			self._position,
			self._move_to,
			self._save_from_window,
			self._browse,
			self._reset_all,
		)

	def _browse(self, path: Path) -> guiwindow.Browsed:
		"""Open the file picked with `Browse...`, and say what became of it (section 5).

		The second way to open a checklist, and `_load` is the first thing it
		reaches: the file, the position it lands on and the write to
		`state.json` are settled there, once, for this and for the `O` key
		alike (section 3.2.2).

		What differs is everything after, and both halves are the window's rule
		of silence (section 5.3). Nothing is spoken — neither the item landed
		on nor the fact that a file opened — because the window still stands
		and NVDA has its own proof to give; and the refusal is handed back
		rather than shown, because the window it belongs over is the GUI window
		rather than `gui.mainFrame` (section 6).

		`state.json` is read here rather than carried in from the window: the
		window knows where the tester stands in the checklist, and this needs
		what the **file** remembers about the one they just picked. Nothing can
		have changed it in between — the add-on is the only writer, and its
		commands are blocked while the window stands (section 3.3.1).
		"""
		answer = self._load(path, session.load(self._state))
		if isinstance(answer, str):
			return answer
		return guiwindow.Standing(answer, self._position)

	def _move_to(self, found: Position) -> None:
		"""Stand where the window was asked to move to (section 5.1).

		The one action of the window that moves the position, and it is an
		ordinary move once it gets here: the position reaches `state.json` at
		once and the item is spoken, exactly as after a navigation key.

		Two things about it are the window's. The section is named, because
		this is a jump and the most deliberate kind — the same reason it is
		named after a double press and after a file has just been opened
		(sections 3.1 and 3.2.2). And the phrase goes out late: the window has
		just handed the focus back, and NVDA is about to announce the window
		that took it (section 6).

		`_standing` is not asked, and would answer the wrong question: what the
		window handed back is a place in the checklist it was built from, and
		nothing could have changed either while it stood.
		"""
		loaded = self._checklist
		if loaded is None:
			# Unreachable: a window with no checklist has an empty tree, and an
			# empty tree has nowhere to move to.
			log.error("the window asked for a move with no checklist open")
			return
		self._land(loaded, found, name_the_section=True, say=modal.message)

	def _save_from_window(self, item: Item, status_value: str, comment: str) -> None:
		"""Write what the item dialog collected, and let NVDA say what moved.

		The far side of Enter on the tree (section 5.2). It is `_save_item`
		with one thing taken away: the phrase naming what changed. The window
		is still standing, and while it stands the add-on says nothing of its
		own (section 5) — NVDA announcing the node of the tree with its new
		prefix is the proof, and a second word over the top of it is noise.

		What is left is what section 4 will not let go: a write that did not
		reach the disk speaks, every time, and the end of a run speaks because
		it is news about the run rather than about the window.

		`self._checklist` rather than a checklist handed in: nothing can have
		replaced it while the window stood, because every command is blocked
		behind it (section 3.3.1).
		"""
		loaded = self._checklist
		if loaded is None:
			# Unreachable: the dialog is opened from a node of the tree, and a
			# tree with nodes was built from a checklist.
			log.error("the window saved an item with no checklist open")
			return
		self._save_item(loaded, item, status_value, comment, name_the_change=False)

	def _reset_all(self) -> None:
		"""Put every item of the checklist back to pending and erase every comment.

		The far side of "Reset all progress" (section 5), and the twin of the
		`R` key with one difference — how much it takes in. The erasing is the
		same, the one write per command is the same, and so is the reason the
		comments go with the statuses (section 3.2.2): a comment that outlived
		a reset would be spoken over an item nobody has checked.

		**Success says nothing**, and that is where the twins part. `R` leaves
		the tester in the application under test, where nothing but the add-on
		would speak; here the window is still standing, and while it stands the
		add-on says nothing of its own (sections 5 and 5.3). A write that did
		not reach the disk speaks all the same, as it does from everywhere
		(section 4), and goes out late: the confirmation has just closed, and
		NVDA is about to announce the window that took the focus back (section
		6).

		No end-of-run notice, and none possible: nothing in the checklist
		carries a verdict any more.
		"""
		loaded = self._checklist
		if loaded is None:
			# Unreachable: the button is disabled whenever no checklist is open.
			log.error("the window asked for a reset with no checklist open")
			return
		_ = self._write(loaded, loaded.reset, say=modal.message)

	def _choose_checklist(self) -> None:
		"""Ask the tester which checklist to open (section 3.2.2).

		The browsing starts in the folder of the last path in `state.json`,
		which is lying there anyway (section 3.2.2), and the file is read off
		the disk rather than off `self._checklist`: the two agree while one is
		open, and the moment they do not is exactly the moment this is wanted —
		start-up found the file gone, so there is no checklist in hand and the
		only thing left pointing anywhere is that path (section 2).

		What was remembered is read once, here, and carried to `_open` rather
		than read again on the far side: nothing can have changed it in between,
		because the add-on is the only writer of that file and its commands are
		blocked while the dialog is open (section 3.3.1).

		The answer arrives long after this has returned, in `_open`.
		"""
		remembered = session.load(self._state)
		folder = remembered.checklist
		modal.choose_file(
			None if folder is None else folder.parent,
			lambda path: self._open(path, remembered),
		)

	def _open(self, path: Path, remembered: Session) -> None:
		"""Open the checklist the tester just picked, or show why it will not open.

		The far side of the file dialog opened by `O` (section 3.2.2). The
		opening itself is `_load`'s, and what is left here is what belongs to
		this way in: a refusal goes into a window, and a file that opened is
		spoken. Both are the difference from the same load at start-up, where
		section 4 forbids the window and allows only four words — the person
		who pressed "Open" is waiting for an answer, and one who pressed
		nothing is not.

		A refusal that names a file which could not be opened at all should not
		happen, since the dialog only offers files that exist, but a file can
		be taken away or locked between the picking and the opening.

		`remembered` is what `state.json` said when the dialog was opened, read
		once by `_choose_checklist` and carried here rather than read again.
		"""
		answer = self._load(path, remembered)
		if isinstance(answer, str):
			modal.report(answer)
			return
		self._speak_opened(answer)

	def _load(self, path: Path, remembered: Session) -> Checklist | str:
		"""Open the checklist at `path` and stand in it, or say why it will not open.

		The whole of opening a file, and the one place it happens: the `O` key
		gets here through `_open` and `Browse...` in the GUI window through
		`_browse` (sections 3.2.2 and 5). Section 3.2.2 calls those one
		operation differing only in where the path came from, and this is the
		operation — down to where the tester lands, which `_adopt` settles the
		same way for both.

		The answer is the checklist that is now open, or the sentence saying why
		none is — one or the other, and the caller tells them apart by asking
		whether it got a string. The sentence is the long form, which names the
		field, the item and the value (section 2): both callers were asked by
		the tester and both show a window, so the short spoken form section 4
		keeps for a file nobody asked for belongs to neither. Both build it from
		the same `Problem`, which is the one source of the wording the add-on is
		allowed.

		A file that could not be opened at all has no field, item or value to
		name, and what is shown is then the same short sentence the voice would
		have used: which encoding the author had in mind, or what the file
		system objected to, is not something the add-on can say.

		**A refusal leaves everything as it was** (section 2): `state.json` is
		not written, and neither the position nor the checklist in hand moves.
		A file that would not open has not replaced the one that did, and the
		path in `state.json` is where the file dialog starts browsing — erasing
		it here would erase it exactly when it is needed.
		"""
		try:
			loaded = checklist.load(path)
		except OSError:
			log.error(f"could not read the checklist at {path}", exc_info=True)
			return wording.shown_refusal()
		except checklist.ChecklistError as refusal:
			return wording.shown_refusal(refusal.problem)
		self._adopt(loaded, remembered.position_in(path))
		# The path and the position reach the disk now, as after any other
		# change of position (section 2), and a write that does not get there is
		# a line in the log; `_remember` holds both halves of that rule.
		self._remember()
		return loaded

	def _adopt(self, loaded: Checklist, remembered: Position | None) -> None:
		"""Make `loaded` the checklist every command works on, standing where it was left.

		The middle of both ways a checklist arrives — the restore at start-up
		and the file dialog — which section 3.2.2 calls one operation differing
		only in where the path came from.

		`remembered` is what `state.json` held **for this file**, which is why
		both callers ask for it by path: that file holds one pair of indices,
		measured in whichever checklist was open when it was written, so the
		same file reopened lands where the tester stopped while another starts
		at its first item (section 3.2.2). What to do with a pair that no longer
		names a place in the file it does belong to is `navigation.resume`'s,
		and it answers with the first item as well.
		"""
		self._checklist = loaded
		self._position = navigation.resume(loaded, remembered)

	def _speak_opened(self, loaded: Checklist) -> None:
		"""Say where the tester has landed in the checklist they just opened.

		Section 3.2.2 speaks the item the way a jump between sections speaks it
		(section 3.1) — the name of the section, then the text, the status and
		the note. The name is there for the same reason it is there after a
		jump, only more so: landing in a file that was not open a moment ago is
		the most deliberate jump there is, and without the section the tester
		would not know where they had arrived. The name of the checklist is not
		spoken — they picked the file themselves, so "which file?" already has
		an answer, while "where am I?" does not.

		Silence is what a restore at start-up gets and what this may not have
		(section 2): a command was given here, and a window that closed without
		a word would sound exactly like one that was cancelled.

		It goes out through `modal.message`, because the file dialog has just
		handed the focus back and NVDA is about to announce the window that
		took it — a phrase queued at once would be cut off by it (section 6).
		"""
		position = self._position
		if position is None:
			# A checklist of empty sections is valid (section 2), and there is
			# nowhere in it to stand; the same sentence says so as when a command
			# finds it, rather than a second one saying the same thing.
			self._say_there_is_no_item(modal.message)
			return
		self._speak(loaded, position, name_the_section=True, say=modal.message)

	def _navigate(self, direction: Direction) -> None:
		"""Move one item, or — on the second press of the series — one section.

		Both presses are the same scan of section 3.4, differing only in where
		they start and what they step over, so there is one path through here
		and no branch anywhere on the state of the filter.

		A third press and beyond is left doing what the second did: it scans
		from the same anchor to the same place and says it again. Section 6 has
		the add-on go no deeper than two levels and defines no behaviour for a
		third, and repeating the answer invents none.
		"""
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		jump = scriptHandler.getLastScriptRepeatCount() > 0
		if not jump:
			self._anchor = position
		start, step = (self._anchor, Step.SECTION) if jump else (position, Step.ITEM)
		found = navigation.scan(loaded, start, direction, step, navigation.unfiltered)
		if found is None:
			self._refuse(direction, jump=jump)
			return
		self._land(loaded, found, name_the_section=jump)

	def _land(
		self,
		loaded: Checklist,
		found: Position,
		name_the_section: bool = False,
		say: Callable[[str], None] = ui.message,
	) -> None:
		"""Stand on `found`, put that on disk, and say what is there.

		What every move of the position does, whoever made it: the navigation
		keys (section 3.1), auto-advance (section 4) and "Move to" in the
		window (section 5.1) all end here. The order is the rule rather than
		the convenience — the position reaches `state.json` **before** the item
		is spoken (sections 2 and 4), which is the same order a change of data
		is held to and holds for the same reason: the disk has stopped the
		keyboard either way, and all that is chosen is where inside that pause
		the voice starts.

		`name_the_section` belongs to a jump and to nothing else (section 3.1):
		a step to the next item would be paying for a word the tester already
		knows, on every press. `say` is how the phrase reaches them, as in
		`_speak` and `_write`: `ui.message` from a command that runs with the
		focus where it was, and `modal.message` from one that has just closed a
		window (section 6).

		Opening a checklist does not come through here, and that is not an
		oversight: it moves the path as well as the position (section 3.2.2).
		"""
		self._position = found
		self._remember()
		self._speak(loaded, found, name_the_section=name_the_section, say=say)

	def _remember(self) -> None:
		"""Put the position on disk, now (section 2).

		Every change of the position comes through here, and there is no other
		moment at which the file is brought up to date — the same rule the
		checklist is written by, and for the same reason: ten items read
		through without a single mark would otherwise be ten items lost to a
		crash, and reading ahead is ordinary work rather than an exception.
		Whatever opens a checklist of its own (section 3.2.2) changes the path
		as well as the position, and belongs here too.

		Nothing is written before a checklist has been opened, which is also
		what makes the position below safe to read: no file, nothing to
		remember. A tester who has never used the add-on gets no folder in
		their configuration directory for it.

		A write that does not get there is a line in the log and nothing else
		(section 2). This runs on every press of a navigation key, so a spoken
		refusal would arrive on every press too, over the top of the item it
		was pressed for; and what is lost is the place, not the run.
		"""
		if self._checklist is None:
			return
		try:
			session.save(self._state, Session(self._checklist.path, self._position))
		except OSError:
			log.error(f"could not write the session state to {self._state}", exc_info=True)

	def _refuse(self, direction: Direction, jump: bool) -> None:
		"""Say that there is nothing that way.

		Section 3.1 answers a single press with a tone and a jump with words.
		A tone is what the most frequent of the two can afford; a jump is
		deliberate, and silence would not say whether it failed or simply
		landed somewhere whose name went unheard.

		The position is left exactly as it stands, which after a failed jump is
		wherever the first press of the series already took it (section 3.1).
		Putting it back would mean undoing a press that had run — the one
		mechanism section 3.2.1 was glad to be rid of.
		"""
		if not jump:
			signals.list_boundary()
		elif direction is Direction.FORWARD:
			# Translators: Spoken when there is no section after this one to jump to.
			ui.message(_("End of list"))
		else:
			# Translators: Spoken when there is no section before this one to jump to.
			ui.message(_("Start of list"))

	def _speak(
		self,
		loaded: Checklist,
		position: Position,
		name_the_section: bool = False,
		say: Callable[[str], None] = ui.message,
	) -> None:
		"""Say the item at `position`, the way sections 3.1 and 3.3 both say it.

		`say` is `ui.message` from a command that runs with the focus where the
		tester left it, and `modal.message` from one that has just closed a
		window, whose phrase would otherwise be cut off by the focus coming
		back (section 6) — the same choice `_write` makes, and for the same
		reason.
		"""
		section = navigation.section_at(loaded, position).name if name_the_section else None
		say(wording.spoken_item(navigation.item_at(loaded, position), section))

	def _speak_progress(self) -> None:
		"""Say which section the tester is in and how far it has got (section 3.3).

		The `P` key of the command mode. It is asked from nowhere in particular,
		which is why it names the section out loud where a jump between sections
		does not (section 3.1), and it counts the **whole** section however the
		filter is set (section 3.4). Nothing is written and nothing moves: the
		command answers "where am I?" and leaves everything as it found it.
		"""
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		section = navigation.section_at(loaded, position)
		ui.message(wording.spoken_progress(section.name, progress.of(section.items)))

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

	def _record_status(self, rule: Callable[[str], str]) -> None:
		"""Give the current item the status `rule` makes of the one it holds.

		The two ways a status is assigned without opening a window meet here and
		differ only in `rule`, which is handed the status standing in the file
		and answers with the one to write. The quick toggle passes the total
		rule of section 3.2.1, which reads what it is replacing: `passed` goes
		back to `pending`, and any of the other four becomes `passed`. A digit
		of the command mode passes the status it stands for and ignores what was
		there (section 3.2.2). Everything after that is the same rule of section
		4 applied to both, which is why they are one method rather than two.

		Not called `verdict`: that word is taken, and taken narrowly — a verdict
		is any status but `pending` (`core.status.is_verdict`), and one of the
		two callers here is the digit that puts an item back to `pending`.

		The write, and what is said when it does not get there, are `_write`'s
		(section 4); the status word, the end-of-run notice and the move on to
		the next item follow only once the file holds the verdict they are
		about, and in that order. Section 4 puts the phrase describing **where
		the tester stands now** last, because that is the place the next command
		will be about; a run that ended is news about what has just happened,
		and belongs with the word for it.
		"""
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		item = navigation.item_at(loaded, position)
		if not self._write(loaded, lambda: item.record_status(rule(item.status))):
			return
		ui.message(wording.status_word(item.status))
		self._announce_completion(loaded)
		self._advance(loaded, position, item.status)

	def _advance(self, loaded: Checklist, marked: Position, recorded: str) -> None:
		"""Move on to the next visible item, when a verdict has just been given.

		Auto-advance (section 4), and the whole of it is which presses reach
		here: this is called from `_record_status` and from nowhere else.

		**A verdict moves, a return to `pending` stays.** The rule is *move on
		after a verdict, stop after a correction*, and `core.status.is_verdict`
		is the one place the two are told apart. The digit `5` and a space bar
		pressed on a `passed` item both mean the tester is fixing something and
		wants to stay on the item to read it again — the "undo" slot would be
		useless if it moved.

		The same rule has two more cases, and neither of them is here rather
		than by accident. A save from the item dialog does not reach this method
		at all (section 3.3.1): the dialog is a deliberate stop on one item, and
		moving the position behind a closing window would leave the next command
		describing something else. And a write that failed returns before this
		(`_record_status`), which is **stop after a refusal**: the tester will
		press on this item again, and a shifted position would send the repeat
		to the wrong one.

		`marked` is where the verdict was recorded, which is where the tester
		still stands: nothing has moved the position between the write and here.

		The scan is the one of section 3.4, forward, one item, through the
		visibility predicate — the same call a single press of the navigation
		key makes, because "the next visible item" is one idea and not two. In
		0.1.0 the predicate is identically true, so this is literally the next
		item; in 0.2.0 it becomes the next `pending` one and nothing here
		changes.

		**Nothing at the end of the checklist**: no tone, no message, the
		position simply stays (section 4). The tester gave no navigation
		command, so the boundary signal of section 3.1 would be reporting a
		failure that did not happen. That is the whole difference from a
		navigation key running off the end, and it is why this does not answer
		through `_refuse`; landing is the same operation for both, and
		`_land` is where it is written.
		"""
		if not status.is_verdict(recorded) or not preferences.auto_advance():
			return
		found = navigation.scan(
			loaded,
			marked,
			Direction.FORWARD,
			Step.ITEM,
			navigation.unfiltered,
		)
		if found is None:
			return
		self._land(loaded, found)

	def _save_item(
		self,
		loaded: Checklist,
		item: Item,
		status_value: str,
		comment: str,
		name_the_change: bool = True,
	) -> None:
		"""Write what the item dialog was closed on, and say what moved (section 3.3.1).

		The far side of the second press of `NVDA+Alt+I`, and — with
		`name_the_change` off — of Enter on the tree of the window (section
		5.2). The window collected a status and a comment and decided nothing
		about them; what they amount to is one comparison, made before anything
		is written because all three answers hang on it — whether to write at
		all, which words to speak, and whether a status has just closed the last
		pending item of the run.

		**`name_the_change` is who says what changed, not whether it is heard.**
		From `NVDA+Alt+I` the add-on names it, because the focus goes back to
		the application under test and nothing else would. From the tree the GUI
		window is still standing and NVDA is about to announce the node with its
		new prefix, so the add-on stays quiet and lets it (section 5). The rest
		of the method does not move either way: the same comparison, the same
		one write, the same end-of-run notice.

		**A save that moved neither field is a save that does nothing**: no
		file, no word, the same silence as Cancel. Writing anyway would buy
		exactly one thing — the chance to hear *"Error writing the file"* for a
		command that changed nothing (section 3.3.1).

		The status and the comment go into the document together and reach the
		disk in one rewrite, which is `Item.record`'s doing; here it matters
		only that the phrase comes after the write, as section 4 has it for
		every command that changes data.

		Everything spoken goes out late: the window has just handed the focus
		back, and NVDA is about to announce the window that took it, so a
		phrase queued at once would be cut off by it (section 6). The end of a
		run goes through `modal.later` rather than `modal.message` because it
		is a tone **and** a phrase, and delaying only the phrase would leave
		the tone sounding a window announcement ahead of it.

		**No auto-advance** (section 4): the dialog is a deliberate stop on one
		item, and moving the position quietly behind a closing window would
		leave the next command describing a different item than the one just
		edited. The end-of-run notice is the opposite case and is given — but
		only when the **status** moved, because a comment added to a checklist
		that had nothing pending before it closed nothing.
		"""
		change = checklist.Change.of(item, status_value, comment)
		if not change.anything:
			return
		if not self._write(loaded, lambda: item.record(status_value, comment), say=modal.message):
			return
		if name_the_change:
			modal.message(wording.spoken_save(change))
		if change.status is not None:
			modal.later(lambda: self._announce_completion(loaded))

	def _reset_section(self, loaded: Checklist, section: Section) -> None:
		"""Put every item of `section` back to pending, erase its comments, say so.

		The tester has just answered "Yes" (section 3.2.2), and the focus is on
		its way back to the application under test — NVDA is about to announce
		that window, and this phrase has to stand after it rather than under
		it, which is what `modal.message` is for (section 6). That there is a
		phrase at all is the rule section 4 holds every change to: a reset that
		said nothing would sound exactly like a reset that did not happen.

		No end-of-run notice, and none possible: the section held an item to
		stand on, and every item in it is pending now.
		"""
		if not self._write(loaded, section.reset, say=modal.message):
			return
		# Translators: Spoken after the current section of the checklist has been reset.
		modal.message(_("Section reset"))

	def _write(
		self,
		loaded: Checklist,
		change: Callable[[], None],
		say: Callable[[str], None] = ui.message,
	) -> bool:
		"""Make `change`, which rewrites the file, and say so only when it did not get there.

		Every command that changes data comes through here, and section 4
		holds them all to one order: **the file is written first and the
		result spoken second**. Reversed, a failure would arrive after the word
		it contradicts, where the next keypress cancels the speech queue and
		leaves the tester with "passed" and every reason to believe the result
		is safe — the silent loss the rest of section 2 is written against.
		The voice pays nothing for the order: the write was synchronous on
		every press either way, and all that moves is where inside that window
		the speech begins.

		So a write that fails **refuses the command**, and False is the
		caller's cue to add nothing: one phrase, no status word, no next item,
		no signal that the run is over. No window either — the tester is in the
		application under test, and section 1 forbids taking the focus out of
		it. It says so on every press, because a command that changes data and
		then falls silent is, at the keyboard, an add-on that has crashed; and
		the change is left standing in memory, because rolling it back is the
		mechanism section 3.2.1 was glad to be rid of. Any later write carries
		the whole file, so the first one that succeeds takes everything that
		has piled up with it.

		`say` is how that phrase reaches the tester: `ui.message` from a
		command that runs with the focus where it was, and `modal.message` from
		one that has just closed a window and would otherwise be cut off by
		the focus coming back (section 6).
		"""
		try:
			change()
		except OSError:
			log.error(f"could not write the checklist to {loaded.path}", exc_info=True)
			say(wording.spoken_write_failure())
			return False
		return True

	def _announce_completion(self, loaded: Checklist) -> None:
		"""Say that the run is over, when this status left nothing pending.

		Section 4, and it belongs to every path that gives an item a status —
		the quick toggle, a digit of the command mode, the combo box of the
		item dialog — rather than to any one of them. It is news about the run,
		so auto-advance has no say in whether it is spoken, and the condition
		is the measure `core.progress` counts by everywhere: nothing still
		`pending`, rather than everything passed. A checklist holding one
		failure is finished work.

		A write that failed never reaches here, and that is the point: the
		phrase would be claiming something about the run that the disk does not
		say.

		**The tone will be heard before the verdict it follows**, and that is
		accepted rather than overlooked. `ui.message` puts the status word in
		the speech queue while `tones.beep` sounds straight away, so the order
		written here — section 4's "additionally plays a signal and speaks" —
		is the order of the sentence rather than of the ear. Interleaving them
		properly would mean a `BeepCommand` inside a speech sequence, which
		costs both rules it would break: section 4 sends every message through
		`ui.message`, and `signals` is the only module that touches `tones`, so
		that the five signals can be picked to differ from one another.

		**The tone is why this takes no `say` of its own**, unlike everything
		else the add-on speaks. A save from the item dialog cannot delay the
		phrase and leave the tone where it was — that would part the two by a
		whole window announcement — so the caller delays the pair instead, with
		`modal.later`, and what happens inside here is the same either way.
		"""
		counted = progress.of(loaded.items)
		if not counted.finished:
			return
		signals.checklist_finished()
		ui.message(wording.spoken_completion(counted))

	def _standing(self) -> tuple[Checklist, Position] | None:
		"""The checklist and the place in it a command works on, or None for neither.

		Every command begins by asking this, because every command needs both
		halves and neither is promised: no checklist has been opened until
		`state.json` or the file dialog puts one here, and a checklist whose
		sections are all empty is valid and has nowhere to stand in (section 2).

		None means the reason has **already been spoken** and the caller has
		nothing left to do but return. Saying it here rather than at each call
		site is what keeps the two states of section 4 told apart in one place;
		`_say_there_is_no_item` is where the difference between them is written
		down.
		"""
		loaded = self._checklist
		position = self._position
		if loaded is None or position is None:
			self._say_there_is_no_item()
			return None
		return loaded, position

	def _say_there_is_no_item(self, say: Callable[[str], None] = ui.message) -> None:
		"""Section 4: why a command found nothing to work on, worded in one place.

		Two states reach here and they are not the same one. Nothing has been
		opened at all — and nothing could be, until `state.json` or the file
		dialog (section 3.2.2) puts a file here. Or a checklist is open and has
		no items in it: section 2 asks a file for at least one section and
		never for a minimum of items, so that file is valid and genuinely
		loaded, and answering it with "not loaded" would be a lie about the one
		thing the tester can check at that moment — whether they opened the
		file they meant to. What to do about them differs too: pick a file, or
		write some items into the one already picked.

		`say` is how it reaches them, as in `_speak` and `_write`: the second
		state is also what a checklist just opened by the file dialog can turn
		out to be, and a window has closed by then.
		"""
		if self._checklist is None:
			# Translators: Spoken when a command is used before a checklist has been opened.
			say(_("No checklist loaded"))
			return
		# Translators: Spoken when a command is used on a checklist whose sections
		# are all empty, so there is no item to stand on.
		say(_("The checklist has no items"))
