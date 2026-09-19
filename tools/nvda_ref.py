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

Which NVDA the add-on is built for is written down once, as
`addon_lastTestedNVDAVersion` in `buildVars.py` (section 6 of
docs/requirements.md). This module turns that version into the git ref holding
its source, so the workflow names the field instead of repeating the number
next to it -- two numbers in two files drift, and the one that drifts is the
one nobody is looking at.

The ref is a **tag**. NV Access keeps no branch per release: `release-2013.1`
is the only one left, and everything since is tagged. The tags carry two parts
for the first release of a cycle and three for the ones after it, so `2025.3.0`
is `release-2025.3` while `2025.3.1` is `release-2025.3.1`. `git clone
--branch` takes a tag as readily as a branch, and fails loudly on a ref that
does not exist -- the right answer for a version NV Access has not released.

Run it as `uv run python -m tools.nvda_ref`, from the root of the repository:
it prints the ref and nothing else. The `-m` form is the working one, because
reading `buildVars.py` needs the repository root on `sys.path`, and running the
file by path would put this directory there instead.
"""

import re

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


def last_tested_ref() -> str:
	"""The git ref of the NVDA named by `addon_lastTestedNVDAVersion`."""
	version = addon_info["addon_lastTestedNVDAVersion"]
	if version is None:
		raise ValueError("buildVars.py leaves addon_lastTestedNVDAVersion unset")
	return release_ref(version)


if __name__ == "__main__":
	print(last_tested_ref())
