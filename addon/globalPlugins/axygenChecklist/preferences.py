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

#: What auto-advance is when `config.conf` does not say otherwise (section 4).
#: Named rather than spelled twice: the spec string below and the fall back in
#: `_stored` have to be the same value, or a configuration the add-on could not
#: read would answer differently from one that never mentioned the key at all.
AUTO_ADVANCE_DEFAULT = True

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
	AUTO_ADVANCE: f"boolean(default={AUTO_ADVANCE_DEFAULT})",
	# `string` rather than `option(…)`, though the value is one of three and
	# `option` is exactly the check configobj has for that. It buys nothing
	# here and costs the window: see `initial_focus`.
	INITIAL_FOCUS: f'string(default="{FOCUS_COMMENT}")',
}


def auto_advance() -> bool:
	"""Whether a verdict should move the tester on (section 4).

	Asked at the moment a status is recorded rather than held in a variable of
	the add-on's own, because the value is NVDA's: a profile switch changes it
	without anything here being told, and the GUI checkbox of section 5 writes
	it from the other side.

	**A value that will not read comes back as the default**; `_stored` says how
	and why. It matters more here than at the other preference, and section 4
	says so: this is the one read that happens *mid-run*, while a status is being
	recorded and the focus is in the application under test. The exception would
	land between the tester's keystroke and the word of the status they are
	waiting for — the failure section 2 names when it argues for strict type
	checks, and the reason auto-advance may not be read any less carefully than
	the dialog's opening field.
	"""
	return bool(_stored(AUTO_ADVANCE, AUTO_ADVANCE_DEFAULT))


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

	**The answer is always one of the three, and this is the one place that is
	made true.** `config.conf` is a text file a tester may edit by hand, so the
	value read back is whatever is in it — when it reads back at all (`_stored`).

	**Which is why the spec above says `string` and not `option(…)`.** The
	obvious spelling declares the three to configobj — and then does nothing
	with them that helps. `Validator.check` hands back the default only for a
	key that is *missing*; for one that is present and outside the set it raises
	`VdtValueError`. NVDA's `AggregatedSection._cacheLeaf` calls it without
	`missing=True` and catches nothing, and NVDA validated `config.conf` long
	before this module registered its spec, so nothing between the file and here
	ever repairs anything. A hand-edited `initialFocus = note` would therefore
	come out of the read as an **exception** — raised while the settings tab is
	being built, so the whole window would fail to open. In a global plugin that
	is the class of failure section 2 refuses to risk anywhere else, and
	`option` would have bought it for us in exchange for a declaration nobody
	reads.

	**`string` narrows that hole rather than closing it**, which is what
	`_stored` is for and what section 3.3.1 now records. A comma makes configobj
	parse the value as a *list* before any check runs — a hand-edited
	`initialFocus = item, status` arrives as `['item', 'status']` — and `string`
	raises on that exactly as `option` raised on `note`. What `string` buys is
	the common case, not immunity.

	So the set is enforced here, in Python, over whatever `_stored` managed to
	hand back. Both callers may then map the three to three fields and need no
	branch for a value they have never seen.
	"""
	stored = _stored(INITIAL_FOCUS, FOCUS_COMMENT)
	return str(stored) if stored in FOCUS_TARGETS else FOCUS_COMMENT


def set_initial_focus(target: str) -> None:
	"""Open the item dialog on `target` from now on, in `config.conf` (section 3.3.1).

	Assignment and nothing else, as `set_auto_advance` is and for the same
	reasons; saving the file is not ours to do — see the module docstring.
	"""
	_section()[INITIAL_FOCUS] = target


def _stored(key: str, default: object) -> object:
	"""What `config.conf` holds for `key`, or `default` when that will not read.

	One mechanism for both preferences, which is what sections 4 and 3.3.1 ask
	for: `config.conf` is a text file edited by hand, and there must not be two
	answers to what becomes of a value the add-on cannot read.

	**Reading raises, and that is the whole reason this exists.**
	`Validator.check` hands back the spec default only for a key that is
	*missing*; a key that is present and unreadable raises instead. NVDA's
	`AggregatedSection._cacheLeaf` calls it without `missing=True`, and the
	`__getitem__` around it catches only `KeyError` and `TypeError`, so the
	exception travels to us. Nothing upstream repairs it either — NVDA validated
	`config.conf` long before this module registered its spec — and nothing is
	cached on the way out, so the failure repeats on every read rather than
	spending itself once.

	**`except Exception` is deliberate, and the breadth is the cheaper half of
	the trade.** The classes that actually arrive are siblings rather than one
	subclass of the other: `boolean` raises `VdtTypeError` for
	`autoAdvance = maybe`, `option` raised `VdtValueError` for a word outside its
	set, and a list — which a comma in any value produces — raises
	`VdtTypeError` against either spelling. Naming them means importing
	`configobj.validate`, which NVDA ships at runtime but its source tree does
	not carry, so the CI type check cannot resolve it; and importing a bundled
	third-party module for real is the bet the note on `AggregatedSection` above
	refuses, where a move upstream would stop the add-on loading at all. The
	body being one subscript, there is no second failure for the clause to
	swallow.

	`default` is the value the spec declares, not a second opinion about it: a
	configuration the add-on could not read has to answer as one that never
	mentioned the key.
	"""
	try:
		return _section()[key]
	except Exception:
		return default


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
