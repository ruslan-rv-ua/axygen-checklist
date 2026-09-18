# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""How a file of this add-on reaches the disk.

Section 2 of docs/requirements.md asks for the same thing of both files the
add-on writes — the checklist and `state.json` — and for the same reason, so
the rule lives in one place rather than twice:

**A write arrives whole or not at all.** The text goes into a file beside the
target and replaces it in a single operation. Writing straight into the target
would empty it *before* filling it again, and both of these files are rewritten
hundreds of times a session by an add-on that is able to bring the screen
reader down; a crash inside that window would leave a stump. For the checklist
the stump costs the texts and the notes an author wrote by hand, not merely the
run — the same loss that an unknown status being fatal and unknown fields
surviving a rewrite are there to prevent.

Nothing else about the two files is shared. What goes *in* them is the business
of `checklist` and of `session`, which is why this module takes text and has no
opinion about it.
"""

import contextlib
import os
from pathlib import Path


def write(path: Path, text: str) -> None:
	"""Put `text` in the file at `path`, whole or not at all (section 2).

	Raises `OSError` if it did not get there; the previous contents are then
	still on disk, and nothing is left lying beside them.

	The parent folder has to exist already: making one is a decision about
	where a file belongs, which the caller has and this module does not.
	"""
	# A sibling of the target rather than a file in the temporary directory,
	# because the swap is a single operation only within one volume.
	temporary = path.with_name(path.name + ".tmp")
	try:
		# UTF-8 and `\n`, whatever the platform default is. The add-on only
		# ever runs on Windows, but a checklist is a data file that usually
		# lives in version control beside the product under test, so what it
		# writes is the same on every machine that reads the repository.
		temporary.write_text(text, encoding="utf-8", newline="\n")
		os.replace(temporary, path)
	except OSError:
		with contextlib.suppress(OSError):
			temporary.unlink()
		raise
