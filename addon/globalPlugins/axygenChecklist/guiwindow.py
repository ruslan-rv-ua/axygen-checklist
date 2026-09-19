# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The window the whole checklist is looked at in (section 5).

Two ways in, and section 5 keeps both: the Tools menu of NVDA, which makes the
window **findable**, and the `G` key of the command mode, which **opens** it.
Whichever was used, the window is the same one.

**It is the one window of the add-on that is not modal**, and everything else
about it follows from that. The modality counter NVDA keeps is raised by
`displayDialogAsModal` and by nothing else (section 6), so a window shown
without it leaves every command of the add-on working — which is what section 5
rests on, and what `modal` is therefore not the place to show it from. The
tester marks an item with `NVDA+Alt+Space` while this window stands open, and
the file is rewritten underneath it.

**So the tree can go stale, and the answer to that is the way in.** Section 5
weighs the alternatives and takes this one: the tree is rebuilt whenever the
window is opened or raised, which means the key that shows it is also the key
that refreshes it. Rebuilding while the tester stands inside the window is what
is refused — the selection and the panel below would move under their hands —
and editing in the tree is refused outright, for the same reason from the other
end (section 5, and section 7.3 makes it permanent).

**It is a `wx.Frame` holding a `wx.Panel`** (section 6). A frame because NVDA
builds the description of a dialog out of the static labels in it and reads that
description whenever the dialog is announced — and this window is returned to
dozens of times a session, so both of its labels would be spoken on every
return, where a frame announces its title and the control in focus. A panel
because that is what carries the Tab traversal section 5 requires, which
`wx.Dialog` has of its own and `wx.Frame` has not.

**`prePopup()` and `postPopup()` are still called, a window's life apart.** The
first before showing, because `Raise()` does not bring a window forward while
another application owns the foreground, and `G` is pressed from exactly there
(section 1). The second after closing, because the parent of this window is
`gui.mainFrame`, one pixel across and not something Windows can activate in
place of what it just closed.

**One window and one module-level reference to it.** A second `G` finds it and
raises it rather than building another. The reference is cleared when the
window closes and by `close()`, which the plugin calls when NVDA is done with
it: a `wx.CallLater` is not the only thing that outlives a reload of the plugins
(`NVDA+Ctrl+F3`), and a window left standing would belong to a module that no
longer exists.

What the labels say, which node opens selected and why Escape closes the window
are section 5's; the words for a status are `wording`'s, as everywhere.
"""

import addonHandler
import gui
import scriptHandler
import wx
from gui import guiHelper
from logHandler import log

from . import wording
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

#: The window, while it is open, and None the rest of the time.
_window: "_ChecklistWindow | None" = None


def activate(checklist: Checklist | None, position: Position | None) -> None:
	"""Show the window on `checklist`, standing on `position` (section 5).

	Both ways in come here — the Tools menu and the `G` key — and so does a
	second press on a window that is already open: it is raised and its tree
	rebuilt rather than a second window being made. `activate` rather than the
	`show` the other windows of the add-on offer, and the difference is that one:
	`show` builds a window every time it is called, while this finds the one
	window or makes it. NVDA calls the same operation by the same name for its
	own long-lived windows.

	`checklist` is None when none has been opened yet, and the window opens all
	the same. Section 5 puts the choosing of a file **inside** this window, so
	asking for one at the door would put the way in behind having come in
	already — the rule `O` and `A` follow as well (sections 3.2.2 and 4). The
	tree is then empty.

	`position` is where the tester stands, and the node it names opens selected.
	None when there is nowhere to stand — no checklist, or one whose sections are
	all empty (section 2) — and the first node is selected instead.
	"""
	global _window
	# The series ends with a window, this one included (section 6). For a key of
	# the command mode the call changes nothing, which is what makes it safe to
	# make on every way in rather than only on the ones that could need it.
	scriptHandler.clearLastScript()
	frame = gui.mainFrame
	if frame is None:
		# NVDA has no main frame before its GUI is up or after it has been torn
		# down, and neither a script of the add-on nor its menu item can be
		# reached in either window of time.
		log.error("no main frame to show the window of the add-on from")
		return
	if _window is None:
		_window = _ChecklistWindow(frame)
	_window.fill(checklist, position)
	# Before the window is shown, and only for what it does second: NVDA is not
	# the foreground process — the tester is in the application under test — and
	# `Raise()` below would do nothing without this (section 6).
	frame.prePopup()
	_window.Show()
	if _window.IsIconized():
		# A window the tester minimised is still open, and `Raise()` would leave
		# it down there. Restoring it is what "show me the checklist" means.
		_window.Iconize(False)
	_window.Raise()
	_window.focus_tree()


def close() -> None:
	"""Shut the window if it is open, and leave nothing of it behind.

	What NVDA's being done with the plugin means for this window (section 6). A
	reload of the plugins imports this module afresh, so a window still standing
	would answer to a module nobody holds any more — and its tree would keep
	showing a checklist that the new plugin knows nothing about.

	**The reference goes before the window does**, and the closing is guarded.
	On the way out of NVDA the main frame is torn down first, and a child of it
	is destroyed without ever being closed — after which the name here points at
	a wx object that is not there any more, and any call on it raises. There is
	nothing to do about that and nobody to tell; what matters is that the caller
	is `terminate`, and everything after it in there still has to run.
	"""
	global _window
	window = _window
	_window = None
	if window is None:
		return
	try:
		window.Close()
	except RuntimeError:
		log.debug("the window had gone before the plugin that held it", exc_info=True)


class _ChecklistWindow(wx.Frame):
	"""The window itself: the tree, and the comment of whatever is selected in it.

	Built once and filled as often as it is shown; `fill` is the whole of what
	changes between one opening and the next.
	"""

	def __init__(self, parent: wx.Window) -> None:
		super().__init__(
			parent,
			# Translators: The title of the add-on's own window, which shows the whole
			# checklist. It is the product name, which is not translated in any locale.
			title=_("Axygen Checklist"),
		)
		# Everything lives on a panel rather than on the frame, and that is what
		# makes Tab walk the controls at all: `wx.TAB_TRAVERSAL` comes with a
		# panel and not with a frame (section 6).
		panel = wx.Panel(self)
		# `LabeledControlHelper` rather than the `BoxSizerHelper` the add-on's
		# dialogs use: that one is declared to take a `wx.Dialog`, and this window
		# is deliberately not one. What it adds over this is the spacing, which is
		# two constants of the same module.
		tree = guiHelper.LabeledControlHelper(
			panel,
			# Translators: The label of the tree of the add-on's window, which holds every
			# section of the checklist and every item in them.
			_("Checklist"),
			wx.TreeCtrl,
			size=(_CONTROL_WIDTH, _TREE_HEIGHT),
			# The root is a place to hang the sections from and is never shown:
			# the top level of the tree is the sections (section 5).
			style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
		)
		self._tree: wx.TreeCtrl = tree.control
		self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selection)
		comment = guiHelper.LabeledControlHelper(
			panel,
			# Translators: The label of the read-only panel under the tree of the add-on's
			# window, which shows the comment left on the selected checklist item.
			_("Comment"),
			wx.TextCtrl,
			style=wx.TE_READONLY | wx.TE_MULTILINE,
			size=(_CONTROL_WIDTH, _PANEL_HEIGHT),
		)
		self._comment: wx.TextCtrl = comment.control
		contents = wx.BoxSizer(wx.VERTICAL)
		# The tree takes whatever room the window has; the panel below it keeps
		# the height it was given. The one that grows is the one being read.
		contents.Add(tree.sizer, proportion=1, flag=wx.EXPAND)
		contents.AddSpacer(guiHelper.SPACE_BETWEEN_VERTICAL_DIALOG_ITEMS)
		contents.Add(comment.sizer)
		main = wx.BoxSizer(wx.VERTICAL)
		main.Add(
			contents,
			proportion=1,
			border=guiHelper.BORDER_FOR_DIALOGS,
			flag=wx.ALL | wx.EXPAND,
		)
		panel.SetSizer(main)
		# The panel fills the frame, so that a window the tester has resized gives
		# the room to the tree rather than to a margin around it.
		outer = wx.BoxSizer(wx.VERTICAL)
		outer.Add(panel, proportion=1, flag=wx.EXPAND)
		self.SetSizerAndFit(outer)
		# Escape closes the window (section 5). Through an accelerator table
		# rather than `EVT_CHAR_HOOK`, which section 6 keeps off the windows of
		# the add-on: a table sees only the keys named in it, while a hook sees
		# every key of every control and has to decide what to pass on.
		self.Bind(wx.EVT_MENU, self._on_close_command, id=wx.ID_CLOSE)
		self.SetAcceleratorTable(
			wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, wx.ID_CLOSE)]),
		)
		self.Bind(wx.EVT_CLOSE, self._on_window_closed)
		self.CentreOnScreen()

	def fill(self, checklist: Checklist | None, position: Position | None) -> None:
		"""Build the tree afresh out of `checklist`, standing on `position`.

		Called on every way in (section 5), which is what keeps the tree from
		outliving the file: the global commands rewrite it while this window
		stands open, and the key that shows the window is the one that brings it
		up to date.

		Every section is expanded, because section 5 promises the **whole**
		structure and a collapsed section hides the thing the window was opened
		for. Selecting a node is not optional either: a tree holding no selection
		announces itself by the name of the control alone.
		"""
		self._tree.DeleteAllItems()
		root = self._tree.AddRoot("")
		standing = None
		for section_index, section in enumerate(() if checklist is None else checklist.sections):
			node = self._tree.AppendItem(root, section.name)
			for item_index, item in enumerate(section.items):
				leaf = self._tree.AppendItem(node, wording.tree_label(item))
				# The item itself rather than a pair of indices: what the panel
				# below wants of a node is the comment on it, and nothing here
				# outlives the rebuild that made it.
				self._tree.SetItemData(leaf, item)
				if position == Position(section_index, item_index):
					standing = leaf
		self._tree.ExpandAll()
		self._select(root if standing is None else standing)

	def focus_tree(self) -> None:
		"""Put the focus where the window opens: on the tree (section 5)."""
		self._tree.SetFocus()

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
		# An empty tree raises no selection event, so the panel is told directly.
		# It is the same call the event makes, which is why there is no branch on
		# how the window got here.
		self._show_comment()

	def _on_selection(self, event: wx.TreeEvent) -> None:
		"""The selection moved: show what the item under it was commented with.

		The comment is read off the node rather than kept anywhere, which is what
		makes this the only thing selecting does. Section 5 keeps the tree a view:
		it does not move the position in the checklist, so nothing the tester does
		in here changes what the next global command is about.
		"""
		self._show_comment()
		event.Skip()

	def _show_comment(self) -> None:
		"""Put the comment of the selected item in the panel, or empty it.

		A section and an item nobody has commented on leave it blank alike
		(section 5): a panel saying "no comment" would be telling the tester what
		they can hear for themselves, at the price of a Tab press — the objection
		section 3.3.1 raised to an empty *"Note"* field.
		"""
		item = self._selected_item()
		self._comment.SetValue("" if item is None or item.comment is None else item.comment)

	def _selected_item(self) -> Item | None:
		"""The checklist item the selected node stands for, or None for anything else.

		None covers the three ways there is no item to speak of: nothing is
		selected, the tree is empty, or the node is a section, which carries no
		data of its own.
		"""
		node = self._tree.GetSelection()
		if not node.IsOk():
			return None
		data = self._tree.GetItemData(node)
		return data if isinstance(data, Item) else None

	def _on_close_command(self, event: wx.CommandEvent) -> None:
		"""Escape: close the window (section 5).

		Nothing is at stake in closing it — the window holds no deferred set of
		changes at all, every control in it applies at once — so the key that
		closes windows may close this one without a word.
		"""
		self.Close()

	def _on_window_closed(self, event: wx.CloseEvent) -> None:
		"""The window is going: let go of it and give the foreground back.

		`postPopup()` is the other half of the pair `activate` opened with
		(section 6). The parent of this window is `gui.mainFrame`, which is a
		pixel across and cannot be activated in place of what just closed; the
		pair is how NVDA hands the foreground back to whoever had it.
		"""
		global _window
		_window = None
		frame = gui.mainFrame
		if frame is not None:
			frame.postPopup()
		self.Destroy()
