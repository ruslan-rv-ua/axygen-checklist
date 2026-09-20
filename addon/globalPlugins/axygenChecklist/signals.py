# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The tones the add-on plays, gathered so that they can be told apart.

Section 3.1 of docs/requirements.md answers the edge of the list with a tone
rather than words, and section 3.2.2 adds the requirement that binds every tone
of the add-on together: the five signals — arming the command mode, the mode
falling away on its own timeout, the edge of the list, the checklist being
finished and a node of the tree whose item carries a comment (section 5) —
**must be audibly different from one another**. That is a property of the set
rather than of any one of them, so the set lives in one module and nothing else
calls `tones.beep` directly. Picking a tone that differs from four others is
only possible with the four in front of you, and here they are, all five of
them.

What they are picked on is pitch **and** length together, because two of them
have to say "the same thing, the other way round": arming the command mode and
the mode falling away are an octave apart, which is the clearest way a tone can
be heard as its own lower echo, and the specification asks for the second to be
the lower one. The rest then stay clear of both pitches and of each other by
length as well — the edge of the list is the lowest and short, the end of the
run is the only long tone of the five, and the comment signal is at once the
highest and the shortest, which is what the most frequent sound of the add-on
has to be.

**A tone and not speech, on purpose.** NVDA cancels speech when a gesture is
executed (`speechEffectWhenExecuted` in `inputCore.executeGesture`), so a
spoken message is cut off by the very next key — and at the edge of a list the
very next key is usually the same one again. `tones.beep` survives that, which
is what section 3.2.2 rests the whole "a signal, not a spoken list" decision on.
"""

import tones


def list_boundary() -> None:
	"""There is nothing that way: a single press of a navigation key at the edge.

	Section 3.1. Low and short, because of the four tones a global command plays
	this is the most frequent — every read-through of a checklist ends against
	it, and then again while the hand makes sure — so it is the one that has to
	cost the least attention. Only the comment signal is heard oftener, and it
	belongs to the window rather than to the keyboard. The deliberate jump
	between sections is answered with words instead (section 3.1): there a tone
	could not say whether the jump failed or merely landed somewhere the tester
	did not catch the name of.
	"""
	tones.beep(220, 80)


def checklist_finished() -> None:
	"""Nothing is still pending: the run is over (section 4).

	The only long tone of the five, and that alone would tell it apart; it also
	sits between the two of the command mode, far enough from each to be
	neither. Once a run, against the boundary's many times a run, and it
	carries news worth stopping for rather than a refusal to step further.
	"""
	tones.beep(880, 200)


def command_mode_armed() -> None:
	"""The command mode has the keys: `NVDA+Alt+O` (section 3.2.2).

	Higher than every tone but the comment signal, and short — a click rather
	than a note, because it is heard on the way into a command and the tester is
	already reaching for the next key. Its own echo below is the same length,
	which is what makes the pair a pair, so pitch is what separates them. It is
	the whole of what arming announces: a list of the fourteen commands would
	outlast the three seconds it was being read for (section 3.2.2), and a tone
	is what survives the keypress that follows, since NVDA cancels speech on
	every gesture and not this.
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


#: The pitch in hz and the length in ms of the comment signal, named instead of
#: written into the call the way the four tones of the keyboard are. This one is
#: the most frequent sound the add-on makes (section 3.1), so it is the one most
#: likely to be tried again by ear on a real machine with a real synthesiser —
#: and a name can be moved from NVDA's Python console,
#: `signals._COMMENT_SIGNAL_HZ = 1760`, between one step of the tree and the
#: next, where a number inside the call would cost a reload for every candidate.
#: `samples/comment-signal-by-ear.json` carries such a line as a fragment.
#:
#: **What a candidate may be is section 3.1's to say, not this pair's.** The
#: relation is normative and the numbers are not, so a candidate stays above
#: 1200 and under 40 — otherwise it is no longer the highest and the shortest
#: of the five, and the tone that was retuned is a different decision rather
#: than the same one heard again.
#:
#: Private, and the console does not argue with that: the underscore says no
#: other module of the add-on may depend on these, which stays true and worth
#: keeping. A console is not a module, and what anything else would have to
#: depend on is the relation, which lives in the specification.
_COMMENT_SIGNAL_HZ = 1500
_COMMENT_SIGNAL_MS = 10


def node_has_comment() -> None:
	"""The node the tree is announcing carries a comment (section 5).

	The shortest and the highest of the five, and it needs to be told apart on
	pitch **and** length more than any of them, because it is heard oftener
	than any of them: it sounds on every announcement of a commented node,
	where the boundary tone — the most frequent of the other four — sounds at
	the two ends of a read-through (section 3.1). That is also why it is a
	click rather than a note. The specification normalises the two relations
	and no numbers, so the pair above can be retuned by ear without touching
	it.

	**It sounds whenever the tree puts such a node up**, whatever brought it
	there: the selection landing on it by arrow, first letter or mouse, or the
	item under the selection having just been saved from the dialog. The rule
	is about the node and not about the key that served it, which is what
	leaves it without an exception — a save is the second case of it rather
	than a way out of the first. That is what makes a save of nothing but a
	comment audible: the label does not change — same status, same prefix —
	so the label has no proof to give, and the tone is the proof (section 5.2).

	Focus returning to a tree that has not moved says nothing: Shift+Tab out of
	the comment panel and back, or Alt+Tab into the window, leave the node
	exactly where it stood. `_follow_selection` is not reached then, and that
	is the behaviour section 5 asks for rather than a gap in it — the signal
	answers "what have I come to", not "where is the focus", and a tone on the
	way back from the panel would sound in the one moment the comment has just
	been read.

	**It is heard ahead of the label it belongs to, and cannot be put after
	it.** The selection event arrives in wx synchronously with the keypress,
	while the node is announced by NVDA out of its own event queue. Sections
	3.1 and 4 accepted that order already for the finished tone, which likewise
	stands before the words it is about (section 6).

	**The words *"has a comment"* do not follow it into the label** (section
	3.3). One fact, two forms, two surfaces: in speech a word, in the label of
	a node a tone that says the same thing earlier and costs the label nothing.
	The price is braille, where the tone does not reach, and section 5 takes it
	knowingly — in speech the words stay, so in braille the fact stays too.
	"""
	tones.beep(_COMMENT_SIGNAL_HZ, _COMMENT_SIGNAL_MS)
