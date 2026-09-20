# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Names the NVDA source the shell of the add-on is type checked against.

`checks.yml` checks the shell against NVDA's own source, so which source it
checks out decides what the check means. The default branch is `master`, which
is the NVDA after the next one: a method added there passes CI and is missing
in the screen reader the user runs, while a method dropped there fails CI
although the user's NVDA still has it. Neither shows up until someone is
already listening to the add-on fall over.

Which NVDA the add-on runs on is written down once, in `buildVars.py`, and it
takes two fields rather than one: `addon_minimumNVDAVersion` is the oldest
NVDA the manifest lets install the add-on, `addon_lastTestedNVDAVersion` the
newest it is built for (section 6 of docs/requirements.md). This module turns
either of them into the git ref holding that release's source, so a workflow
names the field instead of repeating the number next to it -- two numbers in
two files drift, and the one that drifts is the one nobody is looking at.

Checking the newest alone is half the promise. An API that arrived after the
floor resolves against the ceiling's source, passes CI, and is missing in the
NVDA of a user the manifest let in -- the same failure as checking against
`master`, moved to the other end of the range. So the floor is checked too,
before a release rather than on every commit; docs/development.md, section 4,
has why that moment and what it costs.

The ref is a **tag**. NV Access keeps no branch per release: `release-2013.1`
is the only one left, and everything since is tagged. The tags carry two parts
for the first release of a cycle and three for the ones after it, so `2025.3.0`
is `release-2025.3` while `2025.3.1` is `release-2025.3.1`. `git clone
--branch` takes a tag as readily as a branch, and fails loudly on a ref that
does not exist -- the right answer for a version NV Access has not released.

Run it as `uv run python -m tools.nvda_ref`, from the root of the repository:
it prints the ref of `addon_lastTestedNVDAVersion` and nothing else, while
`uv run python -m tools.nvda_ref minimum` prints the other end's. The bare form
stays the last tested one because that is what every command already written
down pastes. The `-m` form is the working one, because reading `buildVars.py`
needs the repository root on `sys.path`, and running the file by path would put
this directory there instead.
"""

import re
import sys

from buildVars import addon_info

_VERSION = re.compile(r"[0-9]+\.[0-9]+(\.[0-9]+)?")


def release_ref(version: str) -> str:
	"""The git ref of NVDA's source for the release named `version`."""
	if not _VERSION.fullmatch(version):
		raise ValueError(f"not an NVDA version: {version!r}")
	parts = version.split(".")
	if len(parts) == 3 and parts[2] == "0":
		parts = parts[:2]
	return "release-" + ".".join(parts)


# The two functions below differ by one string, and read like something to fold into
# one helper taking the field name. They are not. `addon_info` is an `AddonInfo`,
# which is a TypedDict: the **literal** key is what gives the value a type at all.
# Behind a `field: str` parameter pyright loses it and says so --
# `reportUnknownVariableType` on the version, then `reportUnknownArgumentType` where
# it reaches `release_ref` -- so the fold trades the type checking this module exists
# to feed for two saved lines.
def last_tested_ref() -> str:
	"""The git ref of the NVDA named by `addon_lastTestedNVDAVersion`."""
	version = addon_info["addon_lastTestedNVDAVersion"]
	if version is None:
		raise ValueError("buildVars.py leaves addon_lastTestedNVDAVersion unset")
	return release_ref(version)


def minimum_ref() -> str:
	"""The git ref of the NVDA named by `addon_minimumNVDAVersion`."""
	version = addon_info["addon_minimumNVDAVersion"]
	if version is None:
		raise ValueError("buildVars.py leaves addon_minimumNVDAVersion unset")
	return release_ref(version)


def ref_named_by(arguments: list[str]) -> str:
	"""The ref the command line asks for, given everything after the module name.

	One word rather than a flag, and no argparse behind it: the whole interface is
	which end of the range to name, and a workflow step reads `nvda_ref minimum` at
	a glance. Anything else is refused rather than quietly taken for the default --
	a typo that printed the ceiling's ref would check the ceiling twice and report
	success for a run that never looked at the floor.
	"""
	if not arguments:
		return last_tested_ref()
	if arguments == ["minimum"]:
		return minimum_ref()
	raise SystemExit("usage: python -m tools.nvda_ref [minimum]")


if __name__ == "__main__":
	print(ref_named_by(sys.argv[1:]))
