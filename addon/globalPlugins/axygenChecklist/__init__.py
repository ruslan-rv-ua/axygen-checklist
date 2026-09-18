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

Opening a checklist any other way — the file dialog of section 3.2.2, the GUI
of section 5 — is still to come; until it arrives, the file named in
`state.json` is the only one the add-on can have.
"""

from collections.abc import Callable
from pathlib import Path

import addonHandler
import globalPluginHandler
import inputCore
import NVDAState
import scriptHandler
import ui

# NVDA's own `core`, which shares a name with the add-on's `core` package
# below. The two never collide — one is imported absolutely and the other
# relatively — but `core` in the body of this module would mean whichever the
# reader guessed, so the one name needed is taken out of it instead.
from core import postNvdaStartup
from gui import blockAction
from logHandler import log
from scriptHandler import script

from . import commandmode, modal, signals, wording
from .core import checklist, navigation, progress, session, status
from .core.checklist import Checklist, Section
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
		#: What the restore has to say, until there is anyone to hear it. None
		#: when it went well, which section 2 answers with silence.
		self._startup_message = self._restore()
		postNvdaStartup.register(self._announce_restore)
		log.info("Axygen Checklist loaded")

	def terminate(self) -> None:
		"""NVDA is done with this plugin: let go of the timer and the handler.

		The extension point holds bound methods weakly and would drop the
		start-up handler on its own, but only whenever the plugin is collected.
		Saying so here makes it the moment NVDA names for it.

		The command mode has to go for a harder reason. A `wx.CallLater` left
		running holds this plugin alive and fires into it afterwards — after a
		reload of the plugins (`NVDA+Ctrl+F3`), that is a tone from an add-on
		that no longer exists, and gestures taken off an object nobody is
		listening to any more.
		"""
		self._mode.disarm()
		postNvdaStartup.unregister(self._announce_restore)
		super().terminate()

	def _restore(self) -> str | None:
		"""Pick the run up where the last one left it, and say what stopped it.

		Section 2: the path and the pair of indices come out of `state.json`,
		and a restart of NVDA lands the tester back on the item they stopped
		on. Nothing is said when that works — no command was given, and NVDA is
		mid-sentence about itself at this moment anyway. What comes back is the
		message a failure has earned, for `_announce_restore` to say later.

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
			# Translators: Spoken when NVDA starts and the checklist that was open
			# last time is no longer where it was.
			return _("Checklist file not found")
		except OSError:
			# Everything else that stops a file being read at all: no permission,
			# a drive that is not there, a name Windows will not open. Section 2
			# gives them the same four words as a broken file, and the log is
			# where the difference between them survives.
			log.error(f"could not read the checklist at {remembered.checklist}", exc_info=True)
			return wording.spoken_refusal()
		except checklist.ChecklistError as refusal:
			return wording.spoken_refusal(refusal.problem)
		self._checklist = loaded
		self._position = navigation.resume(loaded, remembered.position)
		return None

	def _announce_restore(self) -> None:
		"""Say what the restore could not do, now that NVDA can be heard.

		Section 4 allows the short spoken message and forbids a window here:
		the tester is working in the application under test, and a dialog that
		appeared by itself would take the focus with it. Section 2 sends them
		on to the file dialog when the file has gone, which is the one part of
		this still to be built.
		"""
		if self._startup_message is None:
			return
		ui.message(self._startup_message)
		self._startup_message = None

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
			"Reads the current item of the checklist again",
		),
		gesture="kb:NVDA+alt+i",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_readItem(self, gesture: inputCore.InputGesture) -> None:
		self._mode.disarm()
		# Every press reads the item, the second one included. Section 3.3 gives
		# the second press the item dialog, which is not built yet, and the one
		# thing this may not do meanwhile is fall silent: NVDA cancels speech on
		# a keypress, so a second press that did nothing would cut the first one
		# off mid-word and leave the tester with a syllable and no explanation —
		# indistinguishable, at the keyboard, from an add-on that has crashed.
		standing = self._standing()
		if standing is None:
			return
		loaded, position = standing
		self._speak(loaded, position)

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
			# Translators: The title of the add-on's windows: the product name, which is
			# not translated in any locale.
			_("Axygen Checklist"),
			then=lambda: self._reset_section(loaded, section),
		)

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
		self._position = found
		self._remember()
		self._speak(loaded, found, name_the_section=jump)

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

	def _speak(self, loaded: Checklist, position: Position, name_the_section: bool = False) -> None:
		"""Say the item at `position`, the way sections 3.1 and 3.3 both say it."""
		section = navigation.section_at(loaded, position).name if name_the_section else None
		ui.message(wording.spoken_item(navigation.item_at(loaded, position), section))

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
		(section 4); the status word and the end-of-run notice follow only once
		the file holds the verdict they are about.
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

	def _reset_section(self, loaded: Checklist, section: Section) -> None:
		"""Put every item of `section` back to pending, erase its comments, say so.

		The tester has just answered "Yes" (section 3.2.2), and the focus is
		already back in the application under test — NVDA is announcing that
		window, and this phrase stands after it. That is why there is a phrase
		at all: a reset that said nothing would sound exactly like a reset that
		did not happen, which is the rule section 4 holds every change to.

		No end-of-run notice, and none possible: the section held an item to
		stand on, and every item in it is pending now.
		"""
		if not self._write(loaded, section.reset):
			return
		# Translators: Spoken after the current section of the checklist has been reset.
		ui.message(_("Section reset"))

	def _write(self, loaded: Checklist, change: Callable[[], None]) -> bool:
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
		"""
		try:
			change()
		except OSError:
			log.error(f"could not write the checklist to {loaded.path}", exc_info=True)
			ui.message(wording.spoken_write_failure())
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
		that the four signals can be picked to differ from one another.
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

	def _say_there_is_no_item(self) -> None:
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
		"""
		if self._checklist is None:
			# Translators: Spoken when a command is used before a checklist has been opened.
			ui.message(_("No checklist loaded"))
			return
		# Translators: Spoken when a command is used on a checklist whose sections
		# are all empty, so there is no item to stand on.
		ui.message(_("The checklist has no items"))
