# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Keeps `import wx` resolvable under the type check CI runs.

Nothing in the add-on imports wx until its first window lands, so without
this file nothing would notice the types going missing: wxPython dropped from
the `lint` group, the runner moved off Windows, the stubs no longer found.
Never imported and never run; pyrightconfig.ci.json lists this directory,
and that is the file's whole life. The shape is the probe issue #20 was
measured on, plus the smallest dialog the windows of the add-on grow from.
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
