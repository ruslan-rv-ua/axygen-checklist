# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Entry point of the Axygen Checklist add-on.

The checklist behaviour is specified in docs/requirements.md and is not
implemented yet: this module only registers the plugin so that the add-on can be
loaded, linked into a running NVDA and packaged.
"""

import addonHandler
import globalPluginHandler
from logHandler import log

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Global plugin holding the checklist commands."""

	# Translators: The name of the category this add-on's commands appear under
	# in NVDA's Input Gestures dialog.
	scriptCategory = _("Axygen Checklist")

	def __init__(self):
		super().__init__()
		log.info("Axygen Checklist loaded")
