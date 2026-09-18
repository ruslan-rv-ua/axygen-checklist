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

**No command here changes the system focus.** That is the invariant of section
1, and the five windows of the add-on all cost either a second press of a
series or a deliberately armed command mode. Everything in this module answers
with speech or a tone and leaves the focus where the tester put it.

**Series of presses come from NVDA and from nowhere else.** Section 6 allows
only `scriptHandler.getLastScriptRepeatCount()`: NVDA runs the script on every
press of a series without waiting for the series to end, and the interval it
counts is the user's own `multiPressTimeout`. Measuring the time between calls
ourselves is forbidden, and would hard-code a setting that belongs to the
screen reader.
"""

import addonHandler
import globalPluginHandler
import inputCore
import scriptHandler
import ui
from gui import blockAction
from logHandler import log
from scriptHandler import script

from . import signals, wording
from .core import navigation
from .core.checklist import Checklist
from .core.navigation import Direction, Position, Step

addonHandler.initTranslation()


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
		#: Where the tester is. Meaningful only alongside a checklist, and set
		#: together with it.
		self._position = Position(0, 0)
		#: Where the current series of presses started. Section 3.1: the single
		#: press has already moved by the time the second press arrives, so a
		#: jump measured from the item it landed on would skip a whole section.
		self._anchor = self._position
		log.info("Axygen Checklist loaded")

	@script(
		description=_(
			# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
			"Moves to the next item of the checklist. Twice: to the first item of the next section",
		),
		gesture="kb:NVDA+alt+pageDown",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_nextItem(self, gesture: inputCore.InputGesture) -> None:
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
		self._navigate(Direction.BACKWARD)

	@script(
		# Translators: The description of a command, as it appears in NVDA's Input Gestures dialog.
		description=_("Reads the current item of the checklist again"),
		gesture="kb:NVDA+alt+i",
	)
	@blockAction.when(blockAction.Context.MODAL_DIALOG_OPEN)
	def script_readItem(self, gesture: inputCore.InputGesture) -> None:
		if scriptHandler.getLastScriptRepeatCount() > 0:
			# The second press of this key opens the item dialog (section 3.3),
			# which is not built yet. Reading the item again instead would be
			# behaviour the specification does not have, and it would have to
			# be taken back when the dialog arrives.
			return
		checklist = self._loaded()
		if checklist is None:
			return
		self._speak(checklist, self._position)

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
		checklist = self._loaded()
		if checklist is None:
			return
		jump = scriptHandler.getLastScriptRepeatCount() > 0
		if not jump:
			self._anchor = self._position
		found = navigation.scan(
			checklist,
			self._anchor if jump else self._position,
			direction,
			Step.SECTION if jump else Step.ITEM,
			navigation.visible,
		)
		if found is None:
			self._refuse(direction, jump)
			return
		self._position = found
		self._speak(checklist, found, name_the_section=jump)

	def _refuse(self, direction: Direction, jump: bool) -> None:
		"""Say that there is nothing that way, leaving the position where it is.

		Section 3.1 answers a single press with a tone and a jump with words.
		A tone is what the most frequent of the two can afford; a jump is
		deliberate, and silence would not say whether it failed or simply
		landed somewhere whose name went unheard.
		"""
		if not jump:
			signals.list_boundary()
		elif direction is Direction.FORWARD:
			# Translators: Spoken when there is no section after this one to jump to.
			ui.message(_("End of list"))
		else:
			# Translators: Spoken when there is no section before this one to jump to.
			ui.message(_("Start of list"))

	def _speak(self, checklist: Checklist, position: Position, name_the_section: bool = False) -> None:
		"""Say the item at `position`, the way sections 3.1 and 3.3 both say it."""
		section = navigation.section_at(checklist, position).name if name_the_section else None
		ui.message(wording.spoken_item(navigation.item_at(checklist, position), section))

	def _loaded(self) -> Checklist | None:
		"""The checklist to work on, having said so when there is none.

		Section 4 gives every command the same four words for this, so they are
		said in one place rather than at the head of each script.
		"""
		if self._checklist is None:
			# Translators: Spoken when a command is used before a checklist has been opened.
			ui.message(_("No checklist loaded"))
		return self._checklist
