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

**The convention lives in the text**, rather than in a field of its own listing
the fragments beside it. Section 2 weighs that field and rejects it, and says
why; what follows from it here is that finding a fragment is a matter of
reading a string, so that is all this module does.

**Nothing here can refuse a file.** An odd delimiter, an empty pair, a delimiter
in the middle of a word — all of it is ordinary text. `text` is the user's data,
and section 2 gives the add-on no right to refuse a checklist over a stray
backtick. So this module has no errors to raise and no opinion to hold: whatever
it is handed, it hands back the fragments it found in it, however few.

**What comes out carries no delimiters, and the text keeps its own.** They are
part of `text`, and everything that shows the text shows them (section 2); the
stripping happens here because a fragment is on its way to the clipboard, which
is the one place the delimiters would be wrong.

What a fragment is settled here; which fields of an item are read for them is a
fact about an item and is settled by `checklist.Item.fragments`.
"""

#: What marks a fragment in `text` and `note`. Section 2 chooses the character
#: and weighs the alternatives it rejects.
#:
#: It is named here rather than spelled inline because section 7.1 counts it as
#: part of the version contract: authors write files against this character, so
#: changing it is a MAJOR — a file that used to yield fragments would quietly
#: stop yielding them.
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
	#
	# `splitlines` breaks on more than the "\n" and CRLF section 2 has in mind —
	# on every separator Python counts as a line break. That is deliberately the
	# generous direction: the rule is there so that what reaches the clipboard
	# is one line, and a fragment straddling some rarer separator would break
	# that just as thoroughly. Erring the other way would let one through.
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
