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
three others is only possible with the three in front of you, and here they
are, all four of them.

What they are picked on is pitch **and** length together, because two of them
have to say "the same thing, the other way round": arming the command mode and
the mode falling away are an octave apart, which is the clearest way a tone can
be heard as its own lower echo, and the specification asks for the second to be
the lower one. The other two then stay clear of both pitches and of each other
by length as well — the edge of the list is the lowest and short, the end of
the run is the only long tone of the four.

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

	The only long tone of the four, and that alone would tell it apart; it also
	sits between the two of the command mode, far enough from each to be
	neither. Once a run, against the boundary's many times a run, and it
	carries news worth stopping for rather than a refusal to step further.
	"""
	tones.beep(880, 200)


def command_mode_armed() -> None:
	"""The command mode has the keys: `NVDA+Alt+O` (section 3.2.2).

	The highest of the four, and as short as anything here gets — a click
	rather than a note, because it is heard on the way into a command and the
	tester is already reaching for the next key. Its own echo below is the same
	length, which is what makes the pair a pair, so pitch is what separates
	them. It is the whole of what arming announces: a list of the
	fourteen commands would outlast the three seconds it was being read for
	(section 3.2.2), and a tone is what survives the keypress that follows,
	since NVDA cancels speech on every gesture and not this.
	"""
	tones.beep(1200, 40)


def command_mode_expired() -> None:
	"""Three seconds are up and the mode has let the keys go (section 3.2.2).

	An octave below the arming tone and the same length, so the pair is heard
	as one thing arriving and the same thing leaving. Without it the mode ends
	in silence and the next letter goes to the application under test; it
	stands where the word *"Cancelled"* used to (section 3.2.3), and it sounds
	only for the timeout — a mode dropped by a command of the add-on says
	nothing at all.
	"""
	tones.beep(600, 40)
