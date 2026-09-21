# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The one piece of layout `guiHelper` does not do, and why it is done here.

`guiHelper.associateElements` picks where a label goes from the **type** of the
control it names: beside it for a `wx.TextCtrl`, a `wx.ComboBox` or a button,
above it for a `wx.ListCtrl`, a `wx.ListBox` or a `wx.TreeCtrl`. The rule is
right for a control a line tall and wrong for a box five lines tall, and the
add-on has three of the second kind — the *"Item"* and *"Note"* fields of the
item dialog (section 3.3.1) and the comment panel of the window (section 5).

Left as it comes, that costs two things. Fields whose labels differ in length
start at different places, so the left edge of the window is ragged; and in the
window itself the tree is labelled from above while the comment panel right
under it is labelled from the side, which are two answers to one question.
Putting the label above every multi-line box settles both, and settles them
the way the tree is already settled rather than by inventing a third way.

**Nothing of what NVDA speaks changes, and that is what makes this free.** The
name of a control comes from the static text immediately before it **in the Tab
order** (section 6), and the Tab order in wx is the order things were created
in — not the order a sizer draws them. So the pair below is created label
first, control second, exactly as `guiHelper.LabeledControlHelper` creates it,
and only the drawing differs. Whoever tidies this back into `associateElements`
will get the label beside the box again; whoever reorders the two lines will
get a tree that announces itself as "tree" and nothing else.

The spacing is not ours either: it is the spacer `associateElements` puts in
its own vertical case, so a hand-built pair and a `guiHelper` one sit the same
distance apart.
"""

from collections.abc import Callable

import wx
from gui import guiHelper


def label_above[ControlT: wx.Control](
	parent: wx.Window,
	text: str,
	control_class: Callable[..., ControlT],
	**kwargs: object,
) -> tuple[wx.Sizer, ControlT]:
	"""A label and the control it names, drawn one above the other.

	Returns the sizer to hand to `BoxSizerHelper.addItem` and the control
	itself. The control is given `wx.EXPAND` and a proportion inside the pair,
	so whether it grows with the window is decided once, by the flags the
	caller adds the sizer with, and not twice.
	"""
	label = wx.StaticText(parent, label=text)
	control = control_class(parent, **kwargs)
	sizer = wx.BoxSizer(wx.VERTICAL)
	sizer.Add(label)
	sizer.AddSpacer(guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_VERTICAL)
	sizer.Add(control, flag=wx.EXPAND, proportion=1)
	return sizer, control
