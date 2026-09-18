# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The tones the add-on plays, gathered so that they can be told apart.

Section 3.1 of docs/requirements.md answers the edge of the list with a tone
rather than words, and section 3.2.2 adds the requirement that binds every tone
of the add-on together: the four signals — arming the command mode, the mode
falling away on its own timeout, the edge of the list and the checklist being
finished — **must be audibly different from one another**. That is a property
of the set rather than of any one of them, so the set lives in one module and
nothing else calls `tones.beep` directly. Picking a tone that differs from
three others is only possible with the three in front of you, and this is where
they will be.

Two of the four arrive with the command mode that raises them (section 3.2.2);
the two here are the edge of the list and the end of the run.

**A tone and not speech, on purpose.** NVDA cancels speech when a gesture is
executed (`speechEffectWhenExecuted` in `inputCore.executeGesture`), so a
spoken message is cut off by the very next key — and at the edge of a list the
very next key is usually the same one again. `tones.beep` survives that, which
is what section 3.2.2 rests the whole "a signal, not a spoken list" decision on.
"""

import tones


def list_boundary() -> None:
	"""There is nothing that way: a single press of a navigation key at the edge.

	Section 3.1. Low and short, because this is the most frequent of the four
	signals — every read-through of a checklist ends against it, and then again
	while the hand makes sure — so it is the one that has to cost the least
	attention. The deliberate jump between sections is answered with words
	instead (section 3.1): there a tone could not say whether the jump failed
	or merely landed somewhere the tester did not catch the name of.
	"""
	tones.beep(220, 80)


def checklist_finished() -> None:
	"""Nothing is still pending: the run is over (section 4).

	High and long, which is what tells it apart from the edge of the list —
	the only other signal built so far, and the low short one. The two that
	arrive with the command mode are short as well (section 3.2.2), so this
	stays the only long tone of the four and the only one above the middle.

	Once a run, against the boundary's many times a run, and it carries news
	worth stopping for rather than a refusal to step further.
	"""
	tones.beep(880, 200)
