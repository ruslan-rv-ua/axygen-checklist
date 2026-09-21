# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""What the tester prefers, kept where NVDA keeps what its own users prefer.

There are two of them: auto-advance (section 4) and which field the item dialog
opens on (section 3.3.1). Both are toggled on the *"Settings"* tab of the
add-on's own window (section 5), and that tab is where every later one goes as
well — section 7.3 refuses a category in NVDA's own settings **permanently**,
on three grounds none of which is the number of rows: the transactional frame
of `SettingsPanel`, the race a `Show()`n panel keeps with the `A` key, and a
permanent row in the category list of everyone who installed the add-on.

Section 4 puts auto-advance in
`config.conf["axygenChecklist"]["autoAdvance"]`, spelled `boolean(default=True)`
and registered through `config.conf.spec`. Neither of the two other files the
add-on writes would do. `state.json` (section 2) is an internal cache of the
position, rebuilt by the add-on and outside the version contract of section
7.1, so a preference erased along with it would be a defect; a preferences file
of its own would be a second configuration beside the screen reader's, with its
own moment of reaching the disk. The same deference the timings are held to
(section 6): what belongs to NVDA is taken from NVDA rather than kept here.

**The default is on.** Auto-advance is the main working loop of the product,
and every step of it is spoken, so it is never a surprise.

**The default focus is the comment**, which is what that rule was before it
became a preference. Section 3.3.1 records that this second preference rests on
no named defect — testers simply open that window for different reasons — and
keeps it as small as a preference can be in consequence: one dialog, three
fields, no key of its own.

**The value belongs to the active NVDA profile, not to the add-on.** Writing to
`config.conf[section][key]` lands in the most recently activated profile
(`AggregatedSection._getUpdateSection` returns `self.profiles[-1]`), and NVDA
triggers profiles by the application in focus — which here is the application
under test, because the focus never leaves it (section 1). So auto-advance
toggled while testing one application is that application's setting. Section 4
accepts this rather than working around it: NVDA closed the request to exempt
settings from profiles as not planned, and writing to `config.conf.profiles[0]`
to get "one value for all profiles" would step outside the documented API.

**The spec is registered when this module is imported**, which is while the
global plugin is being imported and long before any command can read the value.
That order matters: `AggregatedSection.__getitem__` caches the fact that a key
does not exist, so a read that happened before the spec was registered would
keep answering `KeyError` afterwards.

**Reaching the disk is NVDA's business too** (section 4): `config.conf` is
saved when NVDA exits if `saveConfigurationOnExit` is on, or by *NVDA+Ctrl+C*.
That is deliberately unlike the checklist, which is written the instant it
changes (section 2) — there the run would be lost, here one press of `A`.
"""

from typing import TYPE_CHECKING, cast

import config

if TYPE_CHECKING:
	# Only the type check ever needs the name, and NVDA carries a note of its
	# own about moving the class to `config.aggregatedSection`. Imported for
	# real, a move would stop the add-on loading at all; imported like this, it
	# stops nothing and the type check says so loudly, which is where a rename
	# belongs.
	from config import AggregatedSection

#: The add-on's own section of `config.conf` (section 4). Named after the
#: add-on, as its folder in the configuration directory is (section 2) and for
#: the same reason: `addon_name` is eternal (section 6).
SECTION = "axygenChecklist"

#: Whether a verdict moves the position on to the next visible item (section 4).
AUTO_ADVANCE = "autoAdvance"

#: Which field of the item dialog holds the focus when it opens (section 3.3.1).
INITIAL_FOCUS = "initialFocus"

#: The three fields the item dialog may open on, in the order they stand in it
#: (section 3.3.1). Identifiers, not words: what a tester hears for each of them
#: is the label of the field itself, and `wording.focus_target_label` says it.
#: *"Note"* is deliberately absent — it is missing from most items, so a choice
#: naming it would mean something other than itself on most of them, and would
#: need a rule for falling back; these three are always there.
FOCUS_ITEM = "item"
FOCUS_STATUS = "status"
FOCUS_COMMENT = "comment"
FOCUS_TARGETS = (FOCUS_ITEM, FOCUS_STATUS, FOCUS_COMMENT)

config.conf.spec[SECTION] = {
	AUTO_ADVANCE: "boolean(default=True)",
	# `option` rather than `string`, so that configobj's own validator refuses
	# anything outside the three and hands back the default instead. The add-on
	# then never has to ask whether what it read is a field it has: the same
	# guard `wx.CB_READONLY` gives the status combo box of section 3.3.1, one
	# layer down and for free.
	INITIAL_FOCUS: "option({}, default={})".format(
		", ".join(f'"{target}"' for target in FOCUS_TARGETS),
		f'"{FOCUS_COMMENT}"',
	),
}


def auto_advance() -> bool:
	"""Whether a verdict should move the tester on (section 4).

	Asked at the moment a status is recorded rather than held in a variable of
	the add-on's own, because the value is NVDA's: a profile switch changes it
	without anything here being told, and the GUI checkbox of section 5 writes
	it from the other side.
	"""
	return bool(_section()[AUTO_ADVANCE])


def set_auto_advance(enabled: bool) -> None:
	"""Turn auto-advance on or off, in `config.conf`, now (section 4).

	Assignment and nothing else, which is what NVDA's own toggles do
	(`script_toggleSpeakCommandKeys` and the rest of `globalCommands.py`):
	write to `config.conf`, then say the new state out loud. Saving the file is
	not ours to do — see the module docstring.
	"""
	_section()[AUTO_ADVANCE] = enabled


def initial_focus() -> str:
	"""Which field the item dialog opens on — one of `FOCUS_TARGETS` (section 3.3.1).

	Asked when the dialog is built rather than held here, for the reason
	`auto_advance` is asked when a status is recorded: the value is NVDA's, and
	a profile switch changes it without anything here being told.

	The answer is always one of the three. `option()` in the spec above makes
	that configobj's job, so the caller may map the three to three fields and
	need no fourth branch for a value it has never heard of.
	"""
	return str(_section()[INITIAL_FOCUS])


def set_initial_focus(target: str) -> None:
	"""Open the item dialog on `target` from now on, in `config.conf` (section 3.3.1).

	Assignment and nothing else, as `set_auto_advance` is and for the same
	reasons; saving the file is not ours to do — see the module docstring.
	"""
	_section()[INITIAL_FOCUS] = target


def _section() -> "AggregatedSection":
	"""The add-on's own section of `config.conf`, named for the type check.

	`config.conf[key]` is declared to hand back a config **value** — the union
	of what a ConfigObj aggregate can hold, down to `KeyError` — because the
	declaration cannot say that a key naming a section answers with one. So
	indexing the result again is an error to pyright and nothing whatever to
	Python. The cast carries the one thing this module knows and the
	declaration does not: `SECTION` stands in `config.conf.spec` above as a
	section, so a section is what comes back.
	"""
	return cast("AggregatedSection", config.conf[SECTION])
