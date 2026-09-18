# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""How far a run has got through a stretch of a checklist.

Three behaviours of docs/requirements.md ask the same question of the data and
the specification says outright that they are one measure: the progress of a
section spoken by the `P` key (section 3.3), the end of the checklist announced
after a status is assigned (section 4), and the visibility predicate of the
filter (section 3.4). Three behaviours, one dimension, no divergence in the
code — so the counting is written once, here, and the measure itself is
`status.is_verdict`.

**What is counted is what has been looked at**, not what worked. Section 3.3
refuses the word "done" for it: with five states it would mean nothing in
particular, and a checklist holding one failure is finished work rather than
work still to do. That is why section 4 ends the run on "nothing is still
pending" and not on "everything passed".

The count is taken over items rather than over a checklist or a section,
because the two callers hand over different stretches of the same file — one
section, or all of them — and what they have in common is the items.
"""

import dataclasses
from collections.abc import Iterable

from . import status
from .checklist import Item


@dataclasses.dataclass(frozen=True)
class Progress:
	"""How many items there are, how many carry a verdict, how many failed.

	`failed` is counted apart from `processed` rather than instead of it: both
	the progress of a section (section 3.3) and the end of the checklist
	(section 4) name the failures only when there are any — no noise when all
	is well, and loud when it is not.
	"""

	total: int
	processed: int
	failed: int

	@property
	def finished(self) -> bool:
		"""Whether nothing here is still waiting to be checked.

		The condition section 4 announces the end of a checklist on. Nothing to
		count satisfies it vacuously, and no command reaches that: a checklist
		whose sections are all empty is valid (section 2), but every command
		answers it with "the checklist has no items" before it could assign a
		status to anything.
		"""
		return self.processed == self.total


def of(items: Iterable[Item]) -> Progress:
	"""Count `items` the one way the add-on counts them."""
	counted = list(items)
	return Progress(
		total=len(counted),
		processed=sum(1 for item in counted if status.is_verdict(item.status)),
		failed=sum(1 for item in counted if item.status == status.FAILED),
	)
