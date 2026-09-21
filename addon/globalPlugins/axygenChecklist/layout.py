# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The pieces of layout `guiHelper` does not do, and why they are done here.

Every one of them is a case where the helper does most of the work and stops one
step short, and each is built out of its own constants, so that a hand-made pair
and a `guiHelper` one sit exactly the same distance apart.

Two of the four are about notebook pages, which `guiHelper` has never had to
draw: its own dialogs have no tabs. `page_contents` carries the one cast the
window needs and the reason for it; `inside_page` puts a built page inside the
border every window of the add-on stands in.

`guiHelper.associateElements` picks where a label goes from the **type** of the
control it names: beside it for a `wx.TextCtrl`, a `wx.ComboBox` or a button,
above it for a `wx.ListCtrl`, a `wx.ListBox` or a `wx.TreeCtrl`. The rule is
right for a control a line tall and wrong for a box five lines tall, and the
add-on has three of the second kind — the *"Item"* and *"Note"* fields of the
item dialog (section 3.3.1) and the comment panel of the window (section 5).

The path field of the window is multiline as well and is **not** one of them:
it is held to a single line (section 5), and the rule measures the height of
the box rather than the style it was made with. Whoever brings it here will
move a label that has nothing to gain by moving.

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

`guiHelper.ButtonHelper` is the other one, and it stops at the spacing: it adds
each button to its sizer with no flags at all, so a vertical group comes out
ragged down the right edge, every button only as wide as its own label. Its own
docstring says a button may go straight into a sizer instead, and that is what
`button_column` does -- with the helper's spacing constant, and with `wx.EXPAND`,
which in a vertical sizer makes every item as wide as the widest of them.
"""

from collections.abc import Callable, Sequence
from typing import cast

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


def page_contents(page: wx.Panel) -> guiHelper.BoxSizerHelper:
	"""A `BoxSizerHelper` that builds the contents of a notebook page.

	The cast is the whole of it, and it is here rather than at each page so
	that the reason is written once. `BoxSizerHelper.__init__` declares its
	parent as `wx.Dialog`, and only **one** of its methods needs that much:
	`addDialogDismissButtons` calls `CreateButtonSizer` on the parent, which
	belongs to a dialog. Everything a page asks of it — `addItem`,
	`addLabeledControl` — reaches the parent through a weak reference and
	wants no more than a `wx.Window`.

	A page never adds dismiss buttons, and cannot: "Close" belongs to the
	dialog, under both tabs (section 5). So the declaration is narrower than
	the contract this use needs, and the cast says which of the two is being
	relied on. Whoever gives a page a dismiss button will get `AttributeError`
	from wx rather than a type error from here — which is the cost of the cast,
	and it is named so that it is not discovered as a surprise.
	"""
	return guiHelper.BoxSizerHelper(cast("wx.Dialog", page), orientation=wx.VERTICAL)


def inside_page(page: wx.Panel, contents: guiHelper.BoxSizerHelper) -> None:
	"""Give `page` what `contents` built, inside the border every window stands in.

	The third thing `guiHelper` stops one step short of. It has the border
	(`BORDER_FOR_DIALOGS`) and it has the sizer helper, but nothing that puts a
	notebook page in the one wearing the other — its own dialogs have no pages.

	**The border goes on each page rather than once around the notebook**, and
	that is the whole reason this is not simply the line the dialog already uses
	around its own contents: a page is what a control is actually drawn in, so a
	single border outside the tab strip would leave every control flush against
	the edge of its own page.
	"""
	sizer = wx.BoxSizer(wx.VERTICAL)
	sizer.Add(contents.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL | wx.EXPAND, proportion=1)
	page.SetSizer(sizer)


def button_column(buttons: Sequence[wx.Button]) -> wx.Sizer:
	"""A column of buttons, every one of them drawn as wide as the widest.

	Which of them is the widest is not ours to know: the labels are
	translated, and the longer of two swaps with the shorter from one locale
	to the next. `wx.EXPAND` asks the question at layout time instead of
	answering it here.
	"""
	sizer = wx.BoxSizer(wx.VERTICAL)
	for index, button in enumerate(buttons):
		if index:
			sizer.AddSpacer(guiHelper.SPACE_BETWEEN_BUTTONS_VERTICAL)
		sizer.Add(button, flag=wx.EXPAND)
	return sizer
