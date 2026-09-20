# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The three seconds in which the keys belong to the add-on.

Section 3.2.2 of docs/requirements.md. `NVDA+Alt+O` **arms** a temporary layer
holding every rare command of the product, and the reason such a layer is
allowed at all is what shapes this module: a maximal layer — one entry, then
arrows, space, digits and letters — was weighed and rejected against the focus
invariant of section 1, because while it was armed the space bar would belong
to the checklist rather than to the application under test. The mode accepted
instead never takes a key the tester reaches for by reflex, and it holds what
it does take only while all three of these are true: it was armed deliberately,
it was armed just now, and no command of the add-on has run since.

**The lifetime is a timer of the add-on's own** (section 6). A series of
presses is `scriptHandler.getLastScriptRepeatCount()` and nothing else, but
this is not a series: three seconds is longer than `multiPressTimeout`, so NVDA
would have called the second press the first of a new series. `wx.CallLater`
is named by the specification for exactly that reason, and the interval below
is not the hard-coded 500 ms the same section forbids — it is measured against
nothing, and only has to outlast a series.

**The bindings come off one at a time.** `clearGestureBindings()` is forbidden
here (section 3.2.2): it empties `_gestureMap` whole, and that map already
holds the five global combinations, which `ScriptableObject.__init__` bound
from `_scriptDecoratorGestures`. One arming of the mode would leave the add-on
with no hotkeys at all until NVDA restarted — and the trap is a quiet one,
since arming works and everything after it does not.

**Two of the five tones of the add-on are raised here**, and only raised: what
each one sounds like and why is `signals`' business, told once there. This
module holds the other half — at which moment each is played, and that the
lower one belongs to the timeout alone.
"""

from collections.abc import Mapping

import wx
from baseObject import ScriptableObject

from . import signals

#: How long the mode holds the keys, in milliseconds (section 3.2.2). Three
#: seconds is long enough that a command is never announced and then taken
#: away mid-thought, and short enough that a mode armed by accident is gone
#: before the tester has typed anything into the application under test.
LIFETIME = 3000


class CommandMode:
	"""The one modal state of the add-on (section 3.2.3), and it never arms itself.

	`owner` is the object the keys are bound on — the global plugin, whose
	scripts they name — and `keys` maps a gesture identifier to the name of the
	script it runs, without the `script_` prefix. Both are handed over rather
	than looked up here, so that the table of the mode stays beside the scripts
	it names.

	A key the mode has not bound is not the mode's business: it reaches the
	application under test, and the mode lives on to its timeout or to the next
	command of the add-on. Section 3.2.2 accepts that limit deliberately —
	intercepting arbitrary keys while the focus is in someone else's window is
	not something this add-on may do.
	"""

	def __init__(self, owner: ScriptableObject, keys: Mapping[str, str]) -> None:
		super().__init__()
		self._owner = owner
		self._keys = dict(keys)
		#: The timer counting this arming down, and the whole of the state:
		#: None is a mode that is not armed, and the keys are bound exactly
		#: while it is not None.
		self._timer: wx.CallLater | None = None

	def arm(self) -> None:
		"""Take the keys for three seconds, and say so with a tone.

		Dropping what is already armed first is what makes a second
		`NVDA+Alt+O` a fresh arming rather than a second layer (section 3.2.2):
		the timer starts again, and the keys bound are the same keys.

		**A tone and no list of the commands**, which section 3.2.2 decides and
		`signals.command_mode_armed` carries the reasons for.
		"""
		self.disarm()
		# A name in `keys` that is not a script of the owner raises here, and
		# that is where it belongs: the table is a module constant naming
		# scripts of the same class, so a miss is a typo, and it surfaces on the
		# first arming ever attempted rather than becoming a state to survive.
		# Which is why nothing below tries to unbind half a mode.
		for identifier, script_name in self._keys.items():
			self._owner.bindGesture(identifier, script_name)
		self._timer = wx.CallLater(LIFETIME, self._expire)
		signals.command_mode_armed()

	def disarm(self) -> None:
		"""Give the keys back, silently, and stop the clock.

		Silence is the requirement (section 3.2.3): a command of the add-on
		takes the mode away and then runs as usual, and anything said about the
		mode here would land in front of the command's own answer, reporting an
		action the tester never took. The lower tone belongs to the timeout
		alone, and `_expire` is where it is played.

		Doing nothing when nothing is armed is what lets every script call this
		without asking first.
		"""
		if self._timer is None:
			return
		self._timer.Stop()
		self._timer = None
		# One at a time, never `clearGestureBindings()`; see the module
		# docstring for what that would take with it.
		for identifier in self._keys:
			self._owner.removeGestureBinding(identifier)

	def _expire(self) -> None:
		"""Three seconds are up: let the keys go, and say so.

		The one moment the lower tone sounds (section 3.2.2), and the only
		difference between this and any other way the mode ends. What the tone
		is for is with the tone, in `signals.command_mode_expired`.
		"""
		self.disarm()
		signals.command_mode_expired()
