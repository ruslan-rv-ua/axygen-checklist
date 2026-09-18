# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Fragments: the exact strings an item asks the tester to reproduce verbatim.

An address, a path, a command, an identifier, a piece of test data — the parts
of an item that have to be reproduced letter for letter rather than retold from
speech. Section 2 of docs/requirements.md marks them in `text` and `note` with
single backticks, and the `C` key of the command mode (section 3.2.2) puts one
in the clipboard.

**The convention lives in the text, not in a field of its own.** An exact string
does not survive being read aloud: a backslash is silent at NVDA's usual
settings and a dot comes out as the word "dot", so `.\\app.exe` reaches the ear
as the bare name of the application — the very thing the item was telling the
tester not to type. Section 2 weighs an array of fragments beside the text and
refuses it: it would either repeat a string the sentence already carries, and
part company with it on the first edit, or force the sentence to be rewritten,
after which converting a handwritten checklist stops being mechanical.

**Nothing here can refuse a file.** An odd delimiter, an empty pair, a delimiter
in the middle of a word — all of it is ordinary text. `text` is the user's data,
and section 2 gives the add-on no right to refuse a checklist over a stray
backtick. So this module has no errors to raise and no opinion to hold: whatever
it is handed, it hands back the fragments it found in it, however few.

**The delimiters are not stripped from the text.** They are part of `text`, and
everything that shows the text shows them — speech, braille, the item dialog,
the tree of the GUI window, the report. Taking them off on the way out would
mean a point of transformation in every one of those places; and a delimiter
that can be seen is itself the hint that there is something here to copy.

What a fragment is settled here; which fields of an item are read for them is a
fact about an item and is settled by `checklist.Item.fragments`.
"""

#: What marks a fragment in `text` and `note`.
#:
#: A backtick because the criterion is mechanical: the delimiter stands inside a
#: spoken sentence, so it must not be heard. Both `symbols.dic` files give it
#: level `most` while the usual `speech.symbolLevel` is `some`, so neither
#: locale speaks it by default. It also never occurs inside the things testers
#: paste — not in a URL, a path, an identifier or a command — and needs no
#: escaping in JSON. Section 2 weighs the alternatives and says why each fails.
#:
#: Section 7.1 counts this character as part of the version contract: authors
#: write files against it, so changing it is a MAJOR — a file that used to yield
#: fragments would quietly stop yielding them.
DELIMITER = "`"


def of(*sources: str | None) -> list[str]:
	"""Every fragment in `sources`, in the order they appear.

	A source that is None is no source at all, so a caller can hand over an
	optional field — an item's `note` — without first asking whether it is
	there. The order of the sources is the caller's: section 2 reads an item's
	`text` before its `note`, and says so where an item is.
	"""
	found: dict[str, None] = {}
	# Line by line, because section 2 forbids a fragment to cross a line break:
	# a delimiter looks for its pair on its own line and nowhere else.
	# `splitlines` rather than a split on "\n" so that every break Python knows
	# counts as one — what reaches the clipboard has to be a single line
	# whichever character ended the one before it.
	for source in sources:
		for line in (source or "").splitlines():
			for fragment in _in_line(line):
				# A dict rather than a list and a set beside it: section 2
				# collapses exact duplicates into one, because the label in the
				# list is the fragment itself and two identical strings are two
				# entries nobody can tell apart. Insertion order is what keeps
				# the first appearance in its place.
				found[fragment] = None
	return list(found)


def _in_line(line: str) -> list[str]:
	"""The fragments of one line, taken in pairs from the left.

	There is no escape, and none is being looked for: section 2 names the limit
	and accepts it, so a fragment that holds a delimiter is simply not something
	the format can say. A doubled delimiter is not Markdown's way out of it
	either — it is two pairs holding nothing.
	"""
	parts = line.split(DELIMITER)
	# Splitting leaves whatever follows the final delimiter in the last part, so
	# a delimiter with nothing to pair with is exactly a last part with no
	# closing one after it. It forms no fragment and stays ordinary text.
	#
	# Trimmed at the edges, and dropped when nothing is left: an empty fragment
	# has nothing to put in the clipboard, and `api.copyToClip` answers an empty
	# string with a silent `False`. The same rule that makes a blank `comment`
	# and an absent one a single state (section 2).
	found = (parts[index].strip() for index in range(1, len(parts) - 1, 2))
	return [fragment for fragment in found if fragment]
