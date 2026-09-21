# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The window the whole checklist is looked at in (section 5).

Two ways in, and section 5 keeps both: the Tools menu of NVDA, which makes the
window **findable**, and the `G` key of the command mode, which **opens** it.
Whichever was used, the window is the same one.

**It is modal, like the other four** (sections 3.3.1 and 5). It is a
`wx.Dialog` shown through `modal`, so the modality counter NVDA keeps is up
while it stands and every command of the add-on is blocked behind it. That is
the whole of what changed, and everything else in here follows from it: nobody
can rewrite the file underneath the tree, so the tree can act rather than only
report.

**The window is an excursion, not a companion.** It is opened, understood and
closed. The price section 5 names out loud is that NVDA will neither exit nor
restart while it stands — `triggerNVDAExit` refuses while the counter is up —
and what keeps that from being a trap is the excursion: the way out is
`Alt+Tab` to "Axygen Checklist" and Escape, and the first command pressed in
the application under test says so in NVDA's own words.

**While the window stands it says nothing of its own** (section 5). NVDA
announcing the focused node of the tree is the proof that something happened,
and a second word over the top of it is noise. Only failures speak, and the
one that can happen here is a write that did not reach the disk (section 4).

**The one sound the window makes is not a word**: the tree plays the comment
signal (section 5) whenever it puts up a node whose item carries a comment —
the selection landing on one, or a save changing the item under it.
The rule of silence above is about words, which is what would be laid over
NVDA's own proof; a tone does not stand in the speech queue at all and cuts
nothing off. What it buys is the one save that the labels cannot show — a
comment saved on its own leaves the prefix exactly as it was (section 5.2).
Keeping that rule free of exceptions is what `_filling` is for.

**Two actions live on the tree**, and both are buttons with a key that leads
to them (section 5.1). Enter opens the item dialog on the selected item, by
synthesising a click on "Open item" — Enter does not reach a default button
from a tree (wx ticket #3725), which is the same hole NVDA patches the same
way in its own Elements List. Ctrl+Enter presses "Move to", and that one
closes the window.

**Both of those keys belong to the tree and to nothing else in the window**,
and the handlers hang off the tree so that this is structural rather than a
test each of them makes (section 5.1). Ctrl+Enter used to be an accelerator
table on the window, which is why it fired from the path field and the Close
button alike; a table cannot be narrowed, because it hangs off the window by
construction and eats the key before the focused control sees it.

**"Reset all progress" is the window's own action**, and the only one that
reaches every item at once (section 5). It asks first — the same confirmation
the `R` key of the command mode asks about one section, in the same tone and
parented on this window — and a Yes rebuilds the tree **whole** (section 5.3).
Every label changed, so there is nothing in the old tree left worth keeping;
that is the opposite of a save from the item dialog, which changes one label
and must not cost the tester the expansion they made by hand.

**The window holds the run and asks it.** A save from the item dialog, the
next status of the cycle, the file picked with `Browse...` and a confirmed
reset are all commands of the `Run` the plugin handed over, made from here and
answered with events (`core.run`); what reaches the file and what `state.json`
gets are the run's to settle, as for every other change of data. What the
window settles is what it owes those events, and section 5 answers that with
silence: NVDA announcing the node of the tree is the proof, so the window's
narrator speaks only of a write that did not reach the disk and of the end of
the run, and meets everything else with an explicit `case _`. Where the tester
asked to be moved to is the one thing that still comes back out of `show`, as
a `Position`, because "Move to" closes the window and what is said about the
landing has to outlive it.

**The auto-advance checkbox is the one thing in here that writes**, and it is
not an exception to that but a different kind of thing: the option is NVDA's
own configuration (section 4) rather than data of the checklist, so there is
nothing for the plugin or the core to settle about it. Why it is written where
it is shown, and why nothing reads it back, is `_on_auto_advance`'s to say.

**One module-level reference, and it is there for `close()`.** A reload of the
plugins (`NVDA+Ctrl+F3`) is not blocked while a modal dialog is open — NVDA
does not decorate its own reload — so the plugin can be terminated with this
window still standing inside its modal loop. `close()` ends that loop as a
cancel, which is the one answer that means nothing happened.

What the labels say, which node opens selected and why Escape closes the
window are section 5's; the words for a status are `wording`'s, as everywhere.
"""

import dataclasses
from collections.abc import Callable
from pathlib import Path

import addonHandler
import ui
import wx
from gui import guiHelper
from gui.dpiScalingHelper import DpiScalingHelperMixinWithoutInit
from logHandler import log

from . import itemdialog, layout, modal, preferences, signals, wording
from .core import focus
from .core.checklist import Item
from .core.navigation import Position
from .core.progress import Progress
from .core.run import Answer, ChecklistGone, Finished, PlaceNotSaved, Refused, Run, Unreadable, WriteFailed

addonHandler.initTranslation()

#: How tall each kind of control is drawn, before the window is scaled to the
#: screen it is on. The tree is the tall one because the tree is the window.
#: The width is not a number of ours — section 6 has every window of the add-on
#: take `guiHelper.COMPLEX_DIALOG_WIDTH`, which is what NVDA measures its own
#: non-message windows by.
_TREE_HEIGHT = 400
_PANEL_HEIGHT = 80

#: The window, while it is open, and None the rest of the time; see `close`.
_window: "_ChecklistWindow | None" = None


def show(run: Run, on_move: Callable[[Position], None]) -> None:
	"""Open the window on `run` (section 5).

	Both ways in come here — the Tools menu and the `G` key — and there is no
	third case to answer any more: while the window stands, both of them are
	blocked, so a second press cannot arrive and no window has to be found and
	raised rather than built.

	`run` is the one run of the plugin, and the window asks it for everything:
	the checklist the tree is built from, which may be None when none has been
	opened yet — the window opens all the same, on an empty tree, because
	section 5 puts the choosing of a file **inside** it, and asking for one at
	the door would put the way in behind having come in already, the rule `O`
	and `A` follow as well (sections 3.2.2 and 4); the position, whose node
	opens selected, or the first node when there is nowhere to stand (section
	2); and every change made from here — a save, the next status, a file
	picked, a reset — which the run answers with events for `_narrate`.

	`on_move` is called with the position the tester asked to be moved to, and
	only for "Move to": the window has closed by then, so what is said about
	the landing has to outlive that (sections 5.1 and 6). It is the one thing
	that comes back out rather than being asked of the run from here.
	"""

	def build_and_hold(parent: wx.Window) -> "_ChecklistWindow":
		# Named for the second half: the window is also put where `close` can
		# reach it, which is the whole reason this module keeps a name at all.
		global _window
		_window = _ChecklistWindow(parent, run)
		return _window

	def answered(dialog: "_ChecklistWindow", answer: int) -> None:
		global _window
		_window = None
		# Every other way out — the Close button, Escape, the window being shut
		# — is a cancel, and a cancel is nothing happening.
		if answer == wx.ID_OK and dialog.chosen_position is not None:
			on_move(dialog.chosen_position)

	modal.show(build_and_hold, answered)


def close() -> None:
	"""Shut the window if it is open, and leave nothing of it behind.

	What NVDA's being done with the plugin means for this window (section 6).
	The reload of the plugins is not blocked behind a modal dialog — NVDA does
	not decorate `script_reloadPlugins` — so this can be reached with the
	window still inside its modal loop, holding a checklist the plugin about to
	replace this one knows nothing about.

	**Ending the loop as a cancel is the whole of it.** `show` answers a cancel
	by doing nothing, so nothing is written, nothing is spoken and no position
	moves — which is what "NVDA is done with us" should amount to.

	**With the item dialog open on top, the loop ended here is not the topmost
	one**, and that is traced rather than guarded. The reload can arrive while
	a save is being written, and then: this sets the outer dialog's flag, the
	inner loop goes on, and a Save reaches the old plugin's callback. The
	checklist object it writes through is the same document the new plugin will
	read, so the file gets what the tester asked for; the tree is still alive,
	because `modal` destroys the window only once the outer loop has actually
	returned, so the label update lands as usual; and the window then closes as
	a cancel. Machinery to close the inner window first would buy nothing that
	this does not already do.

	**The reference goes before the window does**, and the ending is guarded.
	On the way out of NVDA the main frame is torn down first, and a child of it
	is destroyed without ever being closed — after which the name here points
	at a wx object that is not there any more, and any call on it raises. There
	is nothing to do about that and nobody to tell; what matters is that the
	caller is `terminate`, and everything after it in there still has to run.
	"""
	global _window
	window = _window
	_window = None
	if window is None:
		return
	try:
		window.EndModal(wx.ID_CANCEL)
	except RuntimeError:
		log.debug("the window had gone before the plugin that held it", exc_info=True)


@dataclasses.dataclass(frozen=True)
class _Node:
	"""What a node of the tree stands for: a place to go, and an item to read.

	Both halves are optional and neither implies the other, which is exactly
	what the two buttons ask about (section 5.1).

	`position` is where "Move to" would take the tester. For an item it is that
	item; for a section it is the **first item of the section**, literally the
	first and not the first visible (section 5.1). The scan of section 3.4 is
	deliberately not used: the tree shows the whole structure however the
	filter is set, so the tester is pointing at a section they can see in full,
	and from 0.2.0 that scan would land them somewhere other than the item they
	were looking at. It is None for a section holding no items — such a section
	is valid (section 2) and has no first item, so there is nowhere to go and
	the button is disabled.

	`item` is what "Open item" would open and what the panel below the tree
	shows. It is None on a section, which carries no item of its own.
	"""

	position: Position | None
	item: Item | None


class _ChecklistWindow(DpiScalingHelperMixinWithoutInit, wx.Dialog):
	"""The window itself: two tabs, and "Close" alone in the footer under them.

	Built fresh on every way in and filled once, because there is no second
	way in while it stands.

	**Tab *"Run"* is the working surface** and **tab *"Settings"* is the home of
	the preferences** (section 7.3). The split is not for the two controls on it
	today: a panel in NVDA's own settings is refused for good, so this is where
	every preference the add-on ever grows will arrive.

	**Every button stands beside the thing it acts on** (section 5), and the
	order things are built in here is the Tab order the tester walks: on the run
	page, the file row, then "Reset all progress" because it acts on the file,
	then the tree with the three node buttons in a column against it because
	they act on the selected node, then the comment panel. Reading order and Tab
	order are the same thing, which is what a sighted keyboard user and a
	magnifier user need and what a screen reader user gets for free.

	**The tab strip costs a word at every entry, and the price is accepted.** A
	`wx.Notebook` is a native tab control on wxMSW, and NVDA counts a tab
	control among the ancestors it announces (`isPresentableFocusAncestor`
	excludes four roles and this is not one of them), so the tree is reached
	through "tab control" and the name of the page. There is no hook for
	silencing that in a window of one's own — NVDA does it in app modules for
	*other* applications — and section 7.3 weighs it against the alternative: a
	standing word entering our own window, against a standing row in NVDA's
	category list for everyone who installed the add-on.

	Sized the way section 6 sizes every window of the add-on: NVDA's own width
	for a window that is not a message, scaled to the screen this one is on,
	and a border that can be dragged out — the **tree** taking every pixel of
	the height that is dragged in, because a checklist of sixty items in a box
	of a fixed height is a scrolling window and not the whole structure
	section 5 promises to show.
	"""

	def __init__(self, parent: wx.Window, run: Run) -> None:
		super().__init__(
			parent,
			# Translators: The title of the add-on's own window, which shows the whole
			# checklist. It is the product name, which is not translated in any locale.
			title=_("Axygen Checklist"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX,
		)
		#: The run the window is an excursion into: the checklist the tree is
		#: built from and the place the tester stands, read off it wherever the
		#: tree is filled, and every change made from here is a command of it.
		#: Nothing of either is kept a second time in the window — the run is
		#: where they can change, and the window asks.
		self._run = run
		#: Where "Move to" was asked to go, and None until it is asked; see
		#: `chosen_position`.
		self._chosen: Position | None = None
		#: True while the window builds the tree itself, and that is the whole of
		#: what tells the window's own work apart from a step the tester took
		#: through the tree — the comment signal sounds for the second and not
		#: the first. `_fill` runs three times over the life of a window: at the
		#: door, after a `Browse...` and after a reset, and sections 5 and 5.3
		#: have all three of them silent.
		self._filling = False
		# Two tabs, because this window is the home of the preferences (section
		# 7.3) and a home wants a room for them: a settings panel in NVDA's own
		# dialog is refused for good, so every preference the add-on ever grows
		# arrives here, and without a room of their own they would pile up under
		# the working surface.
		#
		# The page is named *"Run"* and not *"Checklist"* on purpose: the tree
		# inside it is already called *"Checklist"* (section 5 makes that name
		# normative), and the same string twice would open the window with
		# "Checklist... Checklist, tree".
		notebook = wx.Notebook(self)
		run_page = wx.Panel(notebook)
		settings_page = wx.Panel(notebook)
		notebook.AddPage(
			run_page,
			# Translators: The label of the tab of the add-on's window holding the checklist
			# file, the tree and everything the checklist is walked with. It is deliberately
			# not "Checklist", which is the name of the tree inside it.
			_("Run"),
		)
		notebook.AddPage(
			settings_page,
			# Translators: The label of the tab of the add-on's window holding the options of
			# the add-on.
			_("Settings"),
		)
		# Everything of the run page is parented to the page rather than to the
		# dialog, and the order it is created in is still the Tab order the
		# tester walks — within the page, which is where the rule of section 6
		# about a label naming the control after it is measured.
		run_contents = layout.page_contents(run_page)
		run_contents.addItem(self._build_browse_row(run_page), flag=wx.EXPAND)
		self._reset_all = wx.Button(
			run_page,
			# Translators: The label of the button of the add-on's window that puts every item
			# of the checklist back to not checked and erases every comment. The letter after
			# the ampersand is the mnemonic that activates it.
			label=_("&Reset all progress"),
		)
		self._reset_all.Bind(wx.EVT_BUTTON, self._on_reset)
		# A row of its own, right under the `Browse...` pair rather than down
		# in the footer, because this button acts on the **file** and these are
		# the controls that talk about the file (section 5). Under the pair and
		# not inside it: the label "Checklist file" has to keep standing
		# immediately before its own field, which is what both the description
		# NVDA reads and the name of the field itself hang on (section 6).
		run_contents.addItem(self._reset_all)
		tree = guiHelper.LabeledControlHelper(
			run_page,
			# Translators: The label of the tree of the add-on's window, which holds every
			# section of the checklist and every item in them.
			_("Checklist"),
			wx.TreeCtrl,
			size=self.scaleSize((guiHelper.COMPLEX_DIALOG_WIDTH, _TREE_HEIGHT)),
			# The root is a place to hang the sections from and is never shown:
			# the top level of the tree is the sections (section 5).
			style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
		)
		self._tree: wx.TreeCtrl = tree.control
		self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selection)
		self._tree.Bind(wx.EVT_CHAR, self._on_tree_char)
		# Two key handlers on the one control, and cheaper here than one
		# (section 6). The hook runs ahead of the ordinary key events, so the
		# chord is taken first and everything else reaches EVT_CHAR exactly as
		# it always did — numpad Enter included, which EVT_CHAR hands to plain
		# Enter for free because the code it reports is the translated
		# character.
		self._tree.Bind(wx.EVT_CHAR_HOOK, self._on_tree_chord)
		# The three buttons of the node, in a column beside the tree they act on
		# (section 5). Created after the tree, and never between the tree and
		# its label: the name of a tree is the static text immediately before
		# it **in the Tab order**, so a button dropped in there would leave the
		# tree announcing itself as a tree and nothing more (section 6).
		self._open_item = wx.Button(
			run_page,
			# Translators: The label of the button of the add-on's window that opens the
			# selected checklist item in the item dialog. The letter after the ampersand is
			# the mnemonic that activates it.
			label=_("&Open item"),
		)
		self._open_item.Bind(wx.EVT_BUTTON, self._on_open_item)
		self._move_to = wx.Button(
			run_page,
			# Translators: The label of the button of the add-on's window that makes the
			# selected node the current position and closes the window. It deliberately
			# repeats the wording of NVDA's own Elements List. The letter after the ampersand
			# is the mnemonic that activates it.
			label=_("&Move to"),
		)
		self._move_to.Bind(wx.EVT_BUTTON, self._on_move_to)
		self._next_status = wx.Button(
			run_page,
			# Translators: The label of the button of the add-on's window that gives the
			# selected checklist item the next status of the cycle. The letter after the
			# ampersand is the mnemonic that activates it.
			label=_("&Next status"),
		)
		self._next_status.Bind(wx.EVT_BUTTON, self._on_next_status)
		tree_row = wx.BoxSizer(wx.HORIZONTAL)
		tree_row.Add(tree.sizer, flag=wx.EXPAND, proportion=1)
		tree_row.AddSpacer(guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		# Both the same width, which `layout` settles, and held to the top of
		# the row: buttons centred against a tree this tall would float in the
		# middle of it, beside nothing in particular.
		tree_row.Add(
			layout.button_column([self._open_item, self._move_to, self._next_status]),
			flag=wx.ALIGN_TOP,
		)
		# The row is what takes the height the window is dragged out to, and
		# the tree is the only thing in it that grows (section 6).
		run_contents.addItem(tree_row, flag=wx.EXPAND, proportion=1)
		comment_panel, self._comment = layout.label_above(
			run_page,
			# Translators: The label of the read-only panel under the tree of the add-on's
			# window, which shows the comment left on the selected checklist item.
			_("Comment"),
			wx.TextCtrl,
			style=wx.TE_READONLY | wx.TE_MULTILINE,
			size=self.scaleSize((guiHelper.COMPLEX_DIALOG_WIDTH, _PANEL_HEIGHT)),
		)
		# Width only: the panel keeps the height it was given, and the height
		# the window is dragged out to goes to the tree (section 6). The label
		# stands above the panel for the reason it stands above the tree, which
		# is `layout`'s to say — and until now these two neighbours wore theirs
		# two different ways.
		run_contents.addItem(comment_panel, flag=wx.EXPAND)
		layout.inside_page(run_page, run_contents)
		self._build_settings_page(settings_page)
		# The footer belongs to the dialog and not to either page: "Close"
		# dismisses the **window**, so a copy of it riding on a page would go
		# missing from the other one.
		contents = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		contents.addItem(notebook, flag=wx.EXPAND, proportion=1)
		close = wx.Button(
			self,
			id=wx.ID_CANCEL,
			# Translators: The label of the button of the add-on's window that closes it.
			# Escape does the same. The letter after the ampersand is the mnemonic that
			# activates it.
			label=_("&Close"),
		)
		# `addDialogDismissButtons` at last. It is documented for buttons which
		# dismiss the window and are the last thing in it, and asserts as much;
		# while "Open item" shared the row it could not be used, so the row
		# went in through `addItem` with no alignment flag at all and sat
		# pushed **left** — the only such row among the windows a tester sees
		# side by side. Now that "Close" stands alone, the call gives the
		# footer every NVDA window has: pushed right, ruled off from the rest.
		contents.addDialogDismissButtons(close, separated=True)
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(contents.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL | wx.EXPAND, proportion=1)
		main.Fit(self)
		self.SetSizer(main)
		# The size `Fit` just settled is the floor (section 6): a window that
		# can only grow. Without it the tree can be dragged down to no rows at
		# all, and there is no way back — the size is not remembered, so the
		# only repair is to close the window and open it again.
		self.SetMinSize(self.GetSize())
		# Escape means Close, said out loud rather than left to wx: without this
		# it goes to the affirmative button when there is no cancel one. A
		# `wx.Dialog` needs no accelerator table for this, where the frame this
		# window used to be did (sections 5 and 6) — and with Ctrl+Enter now a
		# key of the tree, the window has no accelerator table at all.
		self.SetEscapeId(wx.ID_CANCEL)
		self._fill()
		# Where the window opens (section 5): on the tree, which is the window.
		# The row above it is first in the Tab walk and last to want the focus,
		# and so is the tab strip now in front of both — the tab is switched
		# rarely, and the tree is what the window is opened for.
		self._tree.SetFocus()
		self.CentreOnScreen()

	def _build_settings_page(self, page: wx.Panel) -> None:
		"""The *"Settings"* tab: what the tester prefers, and nothing else (section 5).

		Both preferences the add-on has, and the place every later one goes:
		section 7.3 refuses a category in NVDA's own settings for good, so this
		page is where they live.

		**Both apply the moment they are changed**, because this window has no
		OK and never will (section 5) — a set of changes waiting to be confirmed
		does not exist in it, any more than a deferred write exists in section 2.
		Neither says anything of its own either: NVDA announces the new state of
		a control that was just changed, and that is the proof; a second word
		over the top of it is the noise section 5 keeps out.
		"""
		contents = layout.page_contents(page)
		auto_advance_box = contents.addItem(
			wx.CheckBox(
				page,
				# Translators: The label of the checkbox of the add-on's window that turns on and
				# off moving to the next checklist item once this one has a verdict. The same
				# option is on the A key of the command mode.
				label=_("Automatically move to the next item after marking one"),
			),
		)
		# It opens at whatever the option is (section 4), and it is not kept,
		# for the reason the `Browse...` button is not: nothing in here changes
		# it again. What happens when the tester does is `_on_auto_advance`'s.
		auto_advance_box.SetValue(preferences.auto_advance())
		auto_advance_box.Bind(wx.EVT_CHECKBOX, self._on_auto_advance)
		# `wx.Choice` rather than the read-only combo box the item dialog picks
		# its status with (section 3.3.1): that style was chosen there against a
		# named danger — a typo writing an unknown value into `status`, which
		# section 2 makes fatal — and there is no such danger here. It is also
		# what NVDA's own settings panels offer a choice with. The label stays
		# beside it, since the rule that puts a label above a box measures the
		# height of the box and this one is a line tall (section 6).
		self._initial_focus: wx.Choice = contents.addLabeledControl(
			# Translators: The label of the control of the add-on's settings that chooses which
			# field of the item dialog has the focus when that dialog opens.
			_("Field focused when an item is opened"),
			wx.Choice,
			choices=[wording.focus_target_label(target) for target in focus.TARGETS],
		)
		self._initial_focus.SetSelection(focus.TARGETS.index(preferences.initial_focus()))
		self._initial_focus.Bind(wx.EVT_CHOICE, self._on_initial_focus)
		layout.inside_page(page, contents)

	def _build_browse_row(self, parent: wx.Window) -> wx.Sizer:
		"""The first row of the window: the file that is open, and the way to another.

		Section 5 puts this first in the window, and the order **inside** it is
		load-bearing as well: the label, then the field, then the button. The
		description NVDA reads out when it announces a dialog keeps a label
		whenever the control right after it is a button (section 6), so a
		button between the two would put *"Checklist file"* back into it — and
		the path would be read at every opening, which is the one thing the
		shape of this field exists to prevent.

		**The field is read-only and multiline**, and both halves are a
		requirement rather than a taste (sections 5 and 6). There is nothing to
		type into it: `Browse...` is what opens a file, and what stands in the
		field only says where the browsing starts — so a field that takes
		typing promises an action that does not exist. Read-only used to cost
		two faults at once, which is why the field stayed editable for so long:
		a single-line read-only field is dropped out of the Tab walk by
		wxWidgets and read into the description of the window by NVDA. Being
		multiline takes both away — `AcceptsFocusFromKeyboard()` stays true for
		a multiline field however read-only it is, and only a **single-line**
		read-only field is collected into the description — and it is the same
		pair the item dialog already stands on (section 3.3.1).
		"""
		label = wx.StaticText(
			parent,
			# Translators: The label of the field of the add-on's window that holds the path
			# of the checklist which is open. The button beside it picks another file.
			label=_("Checklist file"),
		)
		# No width is asked for, unlike the tree and the panel below: the row
		# takes the one the tree has already settled, and the field takes what
		# is left of it once the label and the button have theirs. A width of
		# its own would make this row the widest thing in the window and widen
		# the window to suit.
		self._path = wx.TextCtrl(parent, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL)
		# The height is the other half of "drawn as an ordinary field" (section
		# 5): left alone, a multiline box comes out two lines and more. The one
		# line it is held to is asked of the control rather than counted in
		# pixels — the font of the field knows how tall its own line is, at any
		# DPI — and `wx.TE_NO_VSCROLL` keeps the scrollbar wx hands a multiline
		# field out of a box that tall, where it would be a pair of arrows
		# beside nothing.
		self._path.SetMinSize(
			wx.Size(-1, self._path.GetSizeFromTextSize(-1, self._path.GetCharHeight()).height),
		)
		browse = wx.Button(
			parent,
			# Translators: The label of the button of the add-on's window that picks the
			# checklist file to open. It deliberately repeats NVDA's own label for a button
			# that browses for a path, so the Ukrainian catalogue has to repeat it too.
			label=_("Browse..."),
		)
		browse.Bind(wx.EVT_BUTTON, self._on_browse)
		# The button is not kept: it never changes, unlike the two below the
		# tree, which are enabled and disabled as the selection moves.
		row = wx.BoxSizer(wx.HORIZONTAL)
		row.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)
		row.AddSpacer(guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		# The field and the button are a pair NVDA has a spacing for, and the
		# label is put in front of the pair rather than of the field alone
		# because that is the order above.
		row.Add(
			guiHelper.associateElements(self._path, browse),
			proportion=1,
			flag=wx.ALIGN_CENTER_VERTICAL,
		)
		return row

	@property
	def chosen_position(self) -> Position | None:
		"""Where "Move to" was asked to take the tester, and None if it was not asked.

		Read by `show` after the window has closed. None with an answer of
		`wx.ID_OK` cannot happen through the window — the button is disabled
		wherever there is nowhere to go — and is answered by moving nobody.
		"""
		return self._chosen

	def _fill(self) -> None:
		"""Build the tree out of the run's checklist, standing where the run stands.

		Every section is expanded, because section 5 promises the **whole**
		structure and a collapsed section hides the thing the window was opened
		for. Selecting a node is not optional either: a tree holding no
		selection announces itself by the name of the control alone.

		**The path field is filled here too**, which is what section 5 means by
		filling it along with the tree: the three ways this runs are the three
		ways a file becomes the one on show — the window opening, a `Browse...`
		that found a checklist, and a reset, which shows the same file with
		every label of it changed. A file that was refused reaches none of
		them, so nothing in the window claims it (section 5.3).

		**"Reset all progress" is enabled here as well**, for the same reason
		and in the same breath: whether a checklist is open can change only
		where the tree is filled, and that is what says whether the button can
		be pressed at all — with no checklist open there is nothing to erase,
		and an irreversible question about nothing would cost more than a
		button that cannot be pressed (section 5).
		"""
		checklist = self._run.checklist
		position = self._run.position
		# Filling the tree moves the selection twice over — `DeleteAllItems` takes
		# it off the node it was on and `_select` puts it on the new one — and wx
		# raises the selection event for both, inside these calls. The flag covers
		# the whole of the work rather than one line of it, because all of it is
		# the window's own doing and none of it is a step the tester took
		# (section 5). It is dropped through `finally` for the reason `modal.show`
		# pairs its own state that way: a flag left standing by an exception would
		# not break the window, it would silence the signal for the rest of that
		# window's life — and silence is what the signal exists to be told from.
		self._filling = True
		try:
			self._reset_all.Enable(checklist is not None)
			self._path.SetValue(
				"" if checklist is None or checklist.path is None else str(checklist.path),
			)
			self._tree.DeleteAllItems()
			root = self._tree.AddRoot("")
			standing = None
			for section_index, section in enumerate(() if checklist is None else checklist.sections):
				node = self._tree.AppendItem(root, section.name)
				# A section stands for its first item, and for nothing when it holds
				# none; `_Node` says why both are right.
				self._tree.SetItemData(
					node,
					_Node(Position(section_index, 0) if section.items else None, None),
				)
				for item_index, item in enumerate(section.items):
					leaf = self._tree.AppendItem(node, wording.tree_label(item))
					self._tree.SetItemData(leaf, _Node(Position(section_index, item_index), item))
					if position == Position(section_index, item_index):
						standing = leaf
			self._tree.ExpandAll()
			self._select(root if standing is None else standing)
		finally:
			self._filling = False

	def _select(self, standing: wx.TreeItemId) -> None:
		"""Stand on `standing`, or on the first node when that one is the root.

		The root is never shown (section 5), so being asked to select it means
		there was no item to stand on: a checklist whose sections are all empty,
		or none open at all. The first node is then the honest answer — the first
		section, or nothing at all when the tree holds nothing.
		"""
		if standing == self._tree.GetRootItem():
			standing, _cookie = self._tree.GetFirstChild(standing)
		if standing.IsOk():
			self._tree.SelectItem(standing)
			self._tree.EnsureVisible(standing)
		# An empty tree raises no selection event, so the window is told
		# directly. It is the same call the event makes, which is why there is
		# no branch on how the window got here.
		self._follow_selection()

	def _on_selection(self, event: wx.TreeEvent) -> None:
		"""The selection moved: show the comment, and offer what the node allows.

		Section 5 keeps the tree a view of the checklist: selecting does not
		move the position, so nothing the tester does in here changes what the
		next global command is about. What it does change is what the two
		buttons can do with the node under it.
		"""
		self._follow_selection()
		event.Skip()

	def _follow_selection(self) -> None:
		"""Put the selected node's comment in the panel, and enable what it allows.

		A section and an item nobody has commented on leave the panel blank
		alike (section 5): a panel saying "no comment" would be telling the
		tester what they can hear for themselves, at the price of a Tab press —
		the objection section 3.3.1 raised to an empty *"Note"* field.

		The buttons follow the two halves of `_Node`, and they are not the same
		question: "Open item" wants an item and a section has none, while "Move
		to" wants somewhere to go and a section has one — its first item —
		unless it is empty (section 5.1).

		**The comment signal sounds from here** (section 5), which is what puts
		the rule on the node rather than on a step the tester took: `_saved`
		comes through here as well, and that is the one case where the label
		has no proof to give (section 5.2). A save is the second case of one
		rule rather than an exception to it, and `_filling` keeps the window's
		own three rebuilds silent without needing one either.
		"""
		node = self._selected()
		# Read once and used twice, because the panel and the signal are two
		# surfaces of the one fact (section 5) rather than two questions.
		comment = None if node is None or node.item is None else node.item.comment
		self._comment.SetValue("" if comment is None else comment)
		self._open_item.Enable(node is not None and node.item is not None)
		self._move_to.Enable(node is not None and node.position is not None)
		# The same question "Open item" asks, and for the same reason: a section
		# node has no status of its own, and the one bulk change in the add-on
		# is the reset, which asks before it acts (sections 5 and 5.1).
		self._next_status.Enable(node is not None and node.item is not None)
		if comment is not None and not self._filling:
			signals.node_has_comment()

	def _selected(self) -> _Node | None:
		"""What the selected node stands for, or None when nothing is selected."""
		return self._stands_for(self._tree.GetSelection())

	def _stands_for(self, node: wx.TreeItemId) -> _Node | None:
		"""What `node` stands for, or None when it is not a node of this tree.

		None means an empty tree or, in principle, a tree holding no selection;
		every node the window builds carries a `_Node`, so a node that does not
		is a programming error rather than a state.
		"""
		if not node.IsOk():
			return None
		data = self._tree.GetItemData(node)
		if isinstance(data, _Node):
			return data
		log.error("a node of the checklist tree is carrying no data")
		return None

	def _on_tree_char(self, event: wx.KeyEvent) -> None:
		"""Enter on the tree: press "Open item" (section 5.1).

		Enter does not reach the default button of a dialog from inside a tree
		(wx ticket #3725), so the click is synthesised here — the same patch
		NVDA applies in `browseMode.ElementsListDialog.onTreeChar`, down to the
		bell on a button that is disabled. A disabled button is a section or an
		empty tree, and section 5.1 refuses it a tone of its own: the add-on has
		five, they have to be told apart by ear, and a sixth is not worth a node
		NVDA has already named.

		A chord is left alone. Ctrl+Enter is taken by the hook on this same
		tree, which has run and answered before this event exists at all, and
		every other chord is somebody else's to answer.
		"""
		if event.GetKeyCode() != wx.WXK_RETURN or event.GetModifiers() != wx.MOD_NONE:
			event.Skip()
			return
		if not self._open_item.IsEnabled():
			wx.Bell()
			return
		_ = self._open_item.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ANY))

	def _on_tree_chord(self, event: wx.KeyEvent) -> None:
		"""The chords of the tree: Ctrl+Enter and Shift+Enter (section 5.1).

		Ctrl presses "Move to", Shift presses "Next status". Both are keys of
		the tree and of nothing else in the window, and the hook is what makes
		that structural rather than a test: it hangs off the tree, so it is
		simply not called while the focus is anywhere else, and the key travels
		on to whatever control does have the focus untouched. Outside the tree
		there is no command, so there is nothing to report either — the bell
		below is for a command that could not be carried out, which is a
		different thing.

		Both Enter codes are named here, because the hook reports the key
		untranslated and numpad Enter is a code of its own in it. That is the
		same reason plain Enter above stays on EVT_CHAR, where the two merge
		(section 6).
		"""
		if event.GetKeyCode() not in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			event.Skip()
			return
		modifiers = event.GetModifiers()
		if modifiers == wx.MOD_CONTROL:
			pressed = self._move_to
		elif modifiers == wx.MOD_SHIFT:
			pressed = self._next_status
		else:
			event.Skip()
			return
		# The same shape as plain Enter above, and for the same reason: a key of
		# the tree fires where the button it leads to cannot be pressed.
		if not pressed.IsEnabled():
			wx.Bell()
			return
		_ = pressed.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ANY))

	def _on_next_status(self, event: wx.CommandEvent) -> None:
		"""Give the selected item the next status of the cycle (section 5.1).

		Both ways in arrive here as the one event: the button clicked, and the
		click the tree synthesises for Shift+Enter.

		The window decides nothing about the status itself. Which one comes
		next and what reaches the disk belong to the run, as they do for every
		other change of data the window asks for; what is left here is the
		label, which is the window's own (section 5.2), and the silence the
		status is owed.

		The label is also what speaks. It changes under the focus, so NVDA
		takes it for a change of name on the focused node and reads the node
		again — which is why the `Recorded` the run answers with is met by
		nothing here (section 5.1). What is left is what section 4 will not
		let go: a write that did not reach the disk speaks, every time, and
		the end of a run speaks because it is news about the run rather than
		about the window. Neither is late: no window has closed, and the
		focus is on the tree.
		"""
		# The node and what it stands for come from the one lookup, so that the
		# label written below is the label of the item that was just changed.
		node = self._tree.GetSelection()
		selected = self._stands_for(node)
		if selected is None or selected.item is None:
			# Nothing gets this far: the button is disabled on a section node and
			# on an empty tree, and the chord asks it that same question before
			# synthesising the click (section 5.1).
			log.error("the window was asked for the next status of a node holding no item")
			return
		item = selected.item
		self._narrate(self._run.cycle(item))
		# Read off the item rather than off what was written, so that a write
		# that did not reach the disk still shows what is in memory — the rule
		# section 4 accepts by name, and the same one a save from the dialog
		# follows (section 5.2). Nothing else is refreshed: the comment has not
		# changed and the node is the same kind of node. The comment signal is
		# left out on purpose even though NVDA does reread the node here — it
		# marks landing on a node the tester has yet to learn about, and the
		# focus has not moved (section 5.1).
		self._tree.SetItemText(node, wording.tree_label(item))

	def _on_browse(self, event: wx.CommandEvent) -> None:
		"""Ask which checklist to open (section 5).

		The second way to the file dialog, beside the `O` key of the command
		mode (section 3.2.2), and the same window: what differs is the parent
		it hangs off, which `modal.show` holds. The browsing starts where the
		path field points, and the answer arrives long after this has returned,
		in `_picked`.
		"""
		modal.choose_file(self._starting_folder(), self._picked, parent=self)

	def _starting_folder(self) -> Path | None:
		"""Where the browsing starts: the folder of the path in the field (section 5).

		None when the field is empty, which is exactly when no checklist is
		open, and that leaves the choice of folder to Windows. What stands
		there otherwise is the path of the open file: the field is read rather
		than the checklist asked, because the field is the answer section 5
		gives to this question — and, since it is read-only, the two cannot
		disagree.
		"""
		shown = self._path.GetValue()
		return Path(shown).parent if shown else None

	def _picked(self, path: Path) -> None:
		"""A file was picked: show the checklist it holds, or why it holds none.

		Section 5.3, and both halves of it. A file that opened rebuilds the
		tree **whole** — the selection and the expansion are nothing to keep
		here, because the tree is showing another file — and says nothing:
		while the window stands the add-on speaks only of failures (section 5),
		so the landing the run answers with is met by silence and the tree.
		A file that did not open leaves the window exactly as it was and shows
		the concrete reason, which field, which item, which value (section 2).

		Which of the two it is, the run has already decided, and it answers a
		refusal with exactly one event: that is what lets the list be taken
		apart by shape. A file that could not be read at all has no field,
		item or value to name, and the window shows the same short sentence
		the voice would have used; the log is where the file system's reason
		survives. The error hangs off this window rather than off
		`gui.mainFrame` (section 6).
		"""
		answer = self._run.open(path)
		match answer:
			case [Refused(problem)]:
				modal.report(wording.shown_refusal(problem), parent=self)
				return
			case [Unreadable(error)]:
				log.error(f"could not read the checklist at {path}", exc_info=error)
				modal.report(wording.shown_refusal(), parent=self)
				return
			case [ChecklistGone()]:
				log.error(f"the checklist at {path} was gone before it could be opened")
				modal.report(wording.shown_refusal(), parent=self)
				return
			case _:
				self._narrate(answer, after_window=True)
		self._fill()

	def _on_auto_advance(self, event: wx.CommandEvent) -> None:
		"""Auto-advance was turned on or off: write it, now (sections 4 and 5).

		The second way to the option the `A` key of the command mode carries,
		and the same one value: `config.conf["axygenChecklist"]["autoAdvance"]`,
		read when this window was built and written here. There is no third
		place it is kept — not a field of this window holding it until some OK,
		because **this window has no OK**. A set of changes to be confirmed
		somewhere does not exist in it, any more than a deferred write exists in
		section 2, so applying at the moment of the toggle is the shape of the
		window rather than a way around a race.

		The write goes straight out to `preferences` rather than back through a
		callback, which is the one place this window settles anything. The
		option is NVDA's own configuration and not data of the checklist, so
		neither the plugin nor the core has anything to add to a toggle of it —
		no file, no position, no phrase — and a callback out to a one-line
		assignment would be ceremony.

		**Nothing is said**, and nothing needs to be: NVDA announces the new
		state of a checkbox that was just toggled, which is the proof, and a
		second word over the top of it is the noise section 5 keeps out. The two
		phrases of the `A` key stay with the key, which has no such proof to
		lean on — there is no window there at all.

		**Nothing reads this back either.** While the window stands `A` cannot
		be pressed — it is blocked with every other command (section 3.3.1) — so
		there is nothing to keep in step with and no watcher on `config.conf` to
		want. The next window built reads the value afresh, and the value is
		NVDA's own.
		"""
		preferences.set_auto_advance(event.IsChecked())

	def _on_initial_focus(self, event: wx.CommandEvent) -> None:
		"""Another field was picked to open the item dialog on (section 3.3.1).

		The same shape as `_on_auto_advance` and for the same reasons: written
		out to `preferences` the moment it is chosen, because this window has no
		OK to defer it to; nothing said, because NVDA announces the new value of
		the control itself and a second word would be noise.

		The identifier is read back from the position rather than from the label
		shown, which is why `focus.TARGETS` fixes the order the choices are
		built in. Matching on the label would break in every locale but the one
		it was written in.
		"""
		preferences.set_initial_focus(focus.TARGETS[event.GetSelection()])

	def _on_open_item(self, event: wx.CommandEvent) -> None:
		"""Open the item dialog on the selected item (section 5.2).

		The same dialog the second press of `NVDA+Alt+I` opens, with this window
		as its parent — which is the whole difference, and `modal.show` holds
		what it means.

		The node is read once, here, and both what it stands for and the label
		to be updated afterwards come off that one read: the dialog cannot move
		the selection, but asking twice is one more thing that would have to
		stay true.
		"""
		node = self._tree.GetSelection()
		stands_for = self._stands_for(node)
		if stands_for is None or stands_for.item is None:
			# Unreachable through the window: the button is disabled wherever
			# there is no item under the selection.
			log.error("the item dialog was asked for on a node holding no item")
			return
		item = stands_for.item
		itemdialog.show(
			item,
			lambda status_value, comment: self._saved(node, item, status_value, comment),
			parent=self,
		)

	def _saved(self, node: wx.TreeItemId, item: Item, status_value: str, comment: str) -> None:
		"""The item dialog was saved: let the run write, then show the result.

		**The label is set before NVDA can speak.** This runs the moment the
		modal loop of the item dialog ends, which is before the event loop gets
		to the focus coming back to the tree — so the node NVDA announces is
		already the new one. That is the proof the save happened, and the whole
		reason this window says nothing of its own about it (section 5.2): the
		`Saved` the run answers with is met by silence, and only a write that
		did not reach the disk and the end of the run are spoken — late, since
		the dialog has just handed the focus back (section 6).

		The label is read off the item rather than off what was saved, and that
		is right even when the write failed: section 4 leaves a failed change
		standing in memory, and the tree shows what is in memory.

		The tree is **not** rebuilt. A rebuild would lose the selection and the
		expansion the tester made with their own hands, to change one label.
		"""
		self._narrate(self._run.save(item, status_value, comment), after_window=True)
		self._tree.SetItemText(node, wording.tree_label(item))
		self._follow_selection()

	def _on_move_to(self, event: wx.CommandEvent) -> None:
		"""Move to the selected node and close the window (section 5.1).

		The position itself is not moved here. The window records where it was
		asked to go and ends as `wx.ID_OK`; `show` hands that to the plugin once
		the window has gone, because what is said about the landing has to
		outlive the window closing (section 6).

		Both ways in arrive here as the one event: the button clicked, and the
		click the tree synthesises for Ctrl+Enter (section 5.1). Which one the
		tester used is not a difference worth keeping.
		"""
		node = self._selected()
		if node is None or node.position is None:
			# Nothing gets this far. The button is disabled wherever there is
			# nowhere to go, and the chord asks it that same question before
			# synthesising the click — so the bell for the case lives there,
			# beside the one plain Enter rings (section 5.1).
			log.error("the window was asked to move to a node there is no moving to")
			return
		self._chosen = node.position
		self.EndModal(wx.ID_OK)

	def _on_reset(self, event: wx.CommandEvent) -> None:
		"""Ask whether to erase the whole run, and erase it only on a Yes (section 5).

		The same confirmation the `R` key asks about one section, in the same
		tone and by the same mechanism — a warning, because this is an action
		that loses recorded work for good, and Escape means No. What differs is
		the parent: this one hangs off the window rather than off
		`gui.mainFrame`, because the foreground already belongs to us (section
		6), and `modal.confirm` holds the rest.

		The run is asked whether there is a checklist to reset **now**, and not
		again once the answer comes back: nothing can change it in between —
		every command of the add-on is blocked behind this window, and the
		window itself is blocked behind the question — so the run's own answer
		to a reset with nothing open is left for the type check and never met.
		"""
		if self._run.checklist is None:
			# Unreachable through the window: the button is disabled whenever
			# no checklist is open.
			log.error("a reset was asked for with no checklist open")
			return
		modal.confirm(
			_(
				# Translators: The question asked before the whole checklist is reset, that is
				# every item of it put back to not checked and every comment erased.
				"Reset all progress? Every status and comment will be erased. This cannot be undone.",
			),
			on_yes=self._confirmed,
			parent=self,
		)

	def _confirmed(self) -> None:
		"""The tester said Yes: let the run erase itself, then show what is left.

		The tree is rebuilt **whole** (section 5.3), which is the one case
		where a rebuild costs nothing: every label in it changed, so the
		selection and the expansion are not being lost to save a label the way
		they would be after a save from the item dialog (section 5.2). The
		tester is left standing where they stood — a reset moves nobody — and
		the panel and the path field follow the tree, as they do from any other
		filling of it.

		**Nothing is said** unless the write failed: while the window stands
		the add-on speaks only of failures (section 5.3), so the `ChecklistReset`
		the run answers with is met by silence, and the one phrase of a failed
		write goes out late — the confirmation has just closed, and NVDA is
		about to announce the window that took the focus back (section 6). The
		accepted consequence is named in section 5: a reset made while
		standing on an item that was already pending leaves no proof at all,
		and the silence is what says it worked.

		The tree is rebuilt whether or not the write got through. Section 4
		leaves a failed change standing in memory, and the tree shows what is
		in memory — the same rule the label of a saved item follows.
		"""
		self._narrate(self._run.reset(), after_window=True)
		self._fill()

	def _narrate(self, answer: list[Answer], after_window: bool = False) -> None:
		"""Say what the window owes the events of `answer`, which is almost nothing.

		The rule of silence of section 5 as an explicit filter: while the
		window stands, NVDA announcing the node of the tree is the proof that
		something happened, and a second word over it is noise. So a landing,
		a status, a save and a reset are met by `case _` and the tree; what is
		spoken is what section 4 will not let go — a write that did not reach
		the disk, every time, and the end of the run, because it is news about
		the run rather than about the window. Both go to the log first when
		there is a traceback to keep, as does a position that did not reach
		`state.json`, which section 2 keeps out of the voice altogether.

		`after_window` is whether a window opened from this one has just
		closed — the item dialog, the confirmation, the file dialog (section
		6). Then the phrase goes through `modal.message`, or NVDA announcing
		this window getting the focus back would cut it off, and the end of
		the run waits whole through `modal.later`, or its tone would sound a
		window announcement ahead of its words. The next status of the cycle
		closes no window, and its two phrases are heard at once.
		"""
		for event in answer:
			match event:
				case WriteFailed(error):
					log.error("could not write the checklist", exc_info=error)
					(modal.message if after_window else ui.message)(wording.spoken_write_failure())
				case Finished(counted):
					_finish(counted, after_window)
				case PlaceNotSaved(error):
					log.error("could not write the session state", exc_info=error)
				case _:
					pass


def _finish(counted: Progress, after_window: bool) -> None:
	"""Say that the run is over: a tone, and the count (section 4).

	Spoken from the window for the same reason the plugin speaks it — it is
	news about the run, whichever way the last verdict was recorded — and in
	the same shape: the tone sounds straight away and the words queue behind
	it, which is accepted (section 6). After a window the pair waits whole,
	because delaying only the phrase would part the two by a whole window
	announcement.
	"""

	def announce() -> None:
		signals.checklist_finished()
		ui.message(wording.spoken_completion(counted))

	if after_window:
		modal.later(announce)
	else:
		announce()
