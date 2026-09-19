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

**Two actions live on the tree**, and both are buttons with a key that leads
to them (section 5.1). Enter opens the item dialog on the selected item, by
synthesising a click on "Open item" — Enter does not reach a default button
from a tree (wx ticket #3725), which is the same hole NVDA patches the same
way in its own Elements List. Ctrl+Enter presses "Move to", through the
accelerator table, and that one closes the window.

**The window collects, and it decides nothing.** Where the tester asked to be
moved to comes back out of `show` as a `Position`, and what a save from the
item dialog amounts to goes straight out to `on_save`: whether anything
changed, what reaches the file and what is spoken are settled where every
other change of data is settled, in the plugin and the core.

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

import addonHandler
import wx
from gui import guiHelper
from logHandler import log

from . import itemdialog, modal, wording
from .core.checklist import Checklist, Item
from .core.navigation import Position

addonHandler.initTranslation()

#: How wide the window's controls are drawn, and how tall each kind is, in
#: pixels. The width is the one the item dialog gives its fields, so the windows
#: of the add-on are of a piece on screen; what such a number is for is said
#: there once. The tree is the tall one because the tree is the window.
_CONTROL_WIDTH = 500
_TREE_HEIGHT = 400
_PANEL_HEIGHT = 80

#: The window, while it is open, and None the rest of the time; see `close`.
_window: "_ChecklistWindow | None" = None


def show(
	checklist: Checklist | None,
	position: Position | None,
	on_move: Callable[[Position], None],
	on_save: Callable[[Item, str, str], None],
) -> None:
	"""Open the window on `checklist`, standing on `position` (section 5).

	Both ways in come here — the Tools menu and the `G` key — and there is no
	third case to answer any more: while the window stands, both of them are
	blocked, so a second press cannot arrive and no window has to be found and
	raised rather than built.

	`checklist` is None when none has been opened yet, and the window opens all
	the same. Section 5 puts the choosing of a file **inside** this window, so
	asking for one at the door would put the way in behind having come in
	already — the rule `O` and `A` follow as well (sections 3.2.2 and 4). The
	tree is then empty.

	`position` is where the tester stands, and the node it names opens selected.
	None when there is nowhere to stand — no checklist, or one whose sections are
	all empty (section 2) — and the first node is selected instead.

	`on_move` is called with the position the tester asked to be moved to, and
	only for "Move to": the window has closed by then, so what is said about
	the landing has to outlive that (sections 5.1 and 6). `on_save` is called
	for a save from the item dialog, while the window still stands, and is
	handed the item and the pair the dialog collected (section 5.2).
	"""

	def create(parent: wx.Window) -> "_ChecklistWindow":
		global _window
		_window = _ChecklistWindow(parent, checklist, position, on_save)
		return _window

	def answered(dialog: "_ChecklistWindow", answer: int) -> None:
		global _window
		_window = None
		# Every other way out — the Close button, Escape, the window being shut
		# — is a cancel, and a cancel is nothing happening.
		if answer == wx.ID_OK and dialog.chosen_position is not None:
			on_move(dialog.chosen_position)

	modal.show(create, answered)


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
	item; for a section it is the **first item of the section**, which is the
	meaning a double press of `NVDA+Alt+PageDown` gives a section (section 3.1).
	It is None for a section holding no items — such a section is valid
	(section 2) and has no first item, so there is nowhere to go and the button
	is disabled.

	`item` is what "Open item" would open and what the panel below the tree
	shows. It is None on a section, which carries no item of its own.
	"""

	position: Position | None
	item: Item | None


class _ChecklistWindow(wx.Dialog):
	"""The window itself: the tree, the comment of what is selected, three buttons.

	Built fresh on every way in and filled once, because there is no second
	way in while it stands.
	"""

	def __init__(
		self,
		parent: wx.Window,
		checklist: Checklist | None,
		position: Position | None,
		on_save: Callable[[Item, str, str], None],
	) -> None:
		super().__init__(
			parent,
			# Translators: The title of the add-on's own window, which shows the whole
			# checklist. It is the product name, which is not translated in any locale.
			title=_("Axygen Checklist"),
		)
		self._on_save = on_save
		#: Where "Move to" was asked to go, and None until it is asked; see
		#: `chosen_position`.
		self._chosen: Position | None = None
		# A dialog carries `wx.TAB_TRAVERSAL` itself, so there is no panel here
		# and nothing to hold one: that panel existed only to give a frame the
		# Tab walk it has not got (sections 5 and 6).
		contents = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self._tree: wx.TreeCtrl = contents.addLabeledControl(
			# Translators: The label of the tree of the add-on's window, which holds every
			# section of the checklist and every item in them.
			_("Checklist"),
			wx.TreeCtrl,
			size=(_CONTROL_WIDTH, _TREE_HEIGHT),
			# The root is a place to hang the sections from and is never shown:
			# the top level of the tree is the sections (section 5).
			style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
		)
		self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selection)
		self._tree.Bind(wx.EVT_CHAR, self._on_tree_char)
		self._comment: wx.TextCtrl = contents.addLabeledControl(
			# Translators: The label of the read-only panel under the tree of the add-on's
			# window, which shows the comment left on the selected checklist item.
			_("Comment"),
			wx.TextCtrl,
			style=wx.TE_READONLY | wx.TE_MULTILINE,
			size=(_CONTROL_WIDTH, _PANEL_HEIGHT),
		)
		buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self._open_item: wx.Button = buttons.addButton(
			self,
			# Translators: The label of the button of the add-on's window that opens the
			# selected checklist item in the item dialog. The letter after the ampersand is
			# the mnemonic that activates it.
			label=_("&Open item"),
		)
		self._open_item.Bind(wx.EVT_BUTTON, self._on_open_item)
		self._move_to: wx.Button = buttons.addButton(
			self,
			# Translators: The label of the button of the add-on's window that makes the
			# selected node the current position and closes the window. It deliberately
			# repeats the wording of NVDA's own Elements List. The letter after the ampersand
			# is the mnemonic that activates it.
			label=_("&Move to"),
		)
		self._move_to.Bind(wx.EVT_BUTTON, self._on_move_to)
		buttons.addButton(
			self,
			id=wx.ID_CANCEL,
			# Translators: The label of the button of the add-on's window that closes it.
			# Escape does the same. The letter after the ampersand is the mnemonic that
			# activates it.
			label=_("&Close"),
		)
		# Not `addDialogDismissButtons`: that one is documented for buttons
		# which dismiss the window and are the last thing in it, and "Open item"
		# is neither. The row is placed the same way regardless.
		contents.addItem(buttons)
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(contents.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		main.Fit(self)
		self.SetSizer(main)
		# Escape means Close, said out loud rather than left to wx: without this
		# it goes to the affirmative button when there is no cancel one. A
		# `wx.Dialog` needs no accelerator table for this, where the frame this
		# window used to be did (sections 5 and 6).
		self.SetEscapeId(wx.ID_CANCEL)
		# And Ctrl+Enter means "Move to", from wherever the focus is. The
		# accelerator carries the chord to the same handler the button uses — as
		# a menu command, which is the event an accelerator raises — so there is
		# one way to move and not two. Numpad Enter is bound with it, as in the
		# item dialog and as NVDA checks both codes in its own windows.
		self.Bind(wx.EVT_MENU, self._on_move_to, id=self._move_to.GetId())
		self.SetAcceleratorTable(
			wx.AcceleratorTable(
				[
					wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, self._move_to.GetId()),
					wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_NUMPAD_ENTER, self._move_to.GetId()),
				],
			),
		)
		self._fill(checklist, position)
		# Where the window opens (section 5): on the tree, which is the window.
		self._tree.SetFocus()
		self.CentreOnScreen()

	@property
	def chosen_position(self) -> Position | None:
		"""Where "Move to" was asked to take the tester, and None if it was not asked.

		Read by `show` after the window has closed. None with an answer of
		`wx.ID_OK` cannot happen through the window — the button is disabled
		wherever there is nowhere to go — and is answered by moving nobody.
		"""
		return self._chosen

	def _fill(self, checklist: Checklist | None, position: Position | None) -> None:
		"""Build the tree out of `checklist`, standing on `position`.

		Every section is expanded, because section 5 promises the **whole**
		structure and a collapsed section hides the thing the window was opened
		for. Selecting a node is not optional either: a tree holding no
		selection announces itself by the name of the control alone.
		"""
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
		"""
		node = self._selected()
		self._comment.SetValue(
			"" if node is None or node.item is None or node.item.comment is None else node.item.comment,
		)
		self._open_item.Enable(node is not None and node.item is not None)
		self._move_to.Enable(node is not None and node.position is not None)

	def _selected(self) -> _Node | None:
		"""What the selected node stands for, or None when nothing is selected.

		None means an empty tree or, in principle, a tree holding no selection;
		every node the window builds carries a `_Node`, so a node that does not
		is a programming error rather than a state.
		"""
		node = self._tree.GetSelection()
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
		four, they have to be told apart by ear, and a fifth is not worth a node
		NVDA has already named.

		A chord is left alone. Ctrl+Enter belongs to the accelerator table,
		which takes it before the focused control ever sees it; the guard is
		here so that nothing depends on that being true of every key.
		"""
		if event.GetKeyCode() != wx.WXK_RETURN or event.GetModifiers() != wx.MOD_NONE:
			event.Skip()
			return
		if not self._open_item.IsEnabled():
			wx.Bell()
			return
		_ = self._open_item.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ANY))

	def _on_open_item(self, event: wx.CommandEvent) -> None:
		"""Open the item dialog on the selected item (section 5.2).

		The same dialog the second press of `NVDA+Alt+I` opens, with this window
		as its parent — which is the whole difference, and `modal.show` holds
		what it means.

		The node is read now rather than in the callback, and that is what makes
		the label update land on the right one: the dialog cannot move the
		selection, but reading it once is one fewer thing to be true.
		"""
		node = self._tree.GetSelection()
		selected = self._selected()
		if selected is None or selected.item is None:
			# Unreachable through the window: the button is disabled wherever
			# there is no item under the selection.
			log.error("the item dialog was asked for on a node holding no item")
			return
		item = selected.item
		itemdialog.show(
			item,
			lambda status_value, comment: self._saved(node, item, status_value, comment),
			parent=self,
		)

	def _saved(self, node: wx.TreeItemId, item: Item, status_value: str, comment: str) -> None:
		"""The item dialog was saved: let the plugin write, then show the result.

		**The label is set before NVDA can speak.** This runs the moment the
		modal loop of the item dialog ends, which is before the event loop gets
		to the focus coming back to the tree — so the node NVDA announces is
		already the new one. That is the proof the save happened, and the whole
		reason this window says nothing of its own about it (section 5.2).

		The label is read off the item rather than off what was saved, and that
		is right even when the write failed: section 4 leaves a failed change
		standing in memory, and the tree shows what is in memory.

		The tree is **not** rebuilt. A rebuild would lose the selection and the
		expansion the tester made with their own hands, to change one label.
		"""
		self._on_save(item, status_value, comment)
		self._tree.SetItemText(node, wording.tree_label(item))
		self._follow_selection()

	def _on_move_to(self, event: wx.CommandEvent) -> None:
		"""Move to the selected node and close the window (section 5.1).

		The position itself is not moved here. The window records where it was
		asked to go and ends as `wx.ID_OK`; `show` hands that to the plugin once
		the window has gone, because what is said about the landing has to
		outlive the window closing (section 6).

		Both ways in arrive here: the button as `EVT_BUTTON`, Ctrl+Enter as the
		`EVT_MENU` an accelerator raises. Which one the tester used is not a
		difference worth keeping.
		"""
		node = self._selected()
		if node is None or node.position is None:
			# The button cannot be pressed here — it is disabled wherever there
			# is nowhere to go — but the chord can: an accelerator table hangs
			# off the dialog and fires whatever the button's state is. The
			# answer is the bell a disabled button gets from Enter, for the same
			# reason section 5.1 gives: the add-on has four tones, they have to
			# be told apart by ear, and this is not worth a fifth.
			wx.Bell()
			return
		self._chosen = node.position
		self.EndModal(wx.ID_OK)
