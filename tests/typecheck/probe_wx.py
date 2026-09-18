# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Keeps the window surface of wx resolvable under the type check CI runs.

The add-on reaches into wx in one place — `commandmode` takes `CallLater`
from it for the three seconds of the command mode — so the package going
missing outright would now be caught there. What no module touches until the
first window lands is the surface this file is about: dialogs, controls,
`ShowModal`, `GetApp()`. Losing the types for those — wxPython dropped from
the `lint` group, the runner moved off Windows, the stubs no longer found —
would go unnoticed until somebody wrote a window against them. Never imported
and never run; pyrightconfig.ci.json lists this directory, and that is the
file's whole life. The shape is the probe issue #20 was measured on, plus the
smallest dialog the windows of the add-on grow from.
"""

import wx


def mainLoopRunning() -> bool:
	app = wx.GetApp()
	return app is not None and app.IsMainLoopRunning()


class Probe(wx.Dialog):
	def __init__(self, parent: wx.Window | None) -> None:
		super().__init__(parent, title="probe")
		self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE)

	def run(self) -> bool:
		return self.ShowModal() == wx.ID_OK
