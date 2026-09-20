# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Fixture helpers shared by the unit tests, and one reader of source text.

The `sys.path` entry that makes `core` importable is installed by the package
`__init__`; see the note there.
"""

import ast
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"

#: Where the message sits in the arguments of each function the build collects
#: strings from, counting from one. The authority is the keyword list
#: `xgettext` is run with, in `site_scons/site_tools/gettexttool`: its Python
#: defaults give `_` and `ngettext`, the latter naming a singular and a plural
#: that make one entry between them, and the tool adds `--keyword=pgettext:1c,2`
#: -- whose **first** argument is a context rather than a message.
#:
#: `npgettext` is deliberately absent. The keyword list stops at `pgettext`, so
#: a string given to it would never reach the template, and looking for its
#: translation would be looking for the wrong fault. Not that the add-on uses
#: either: section 6 of docs/requirements.md names only `_()` and `ngettext`.
MSGID_POSITIONS = {"_": (1,), "ngettext": (1, 2), "pgettext": (2,)}


def translation_lookups(path: Path) -> Iterator[str]:
	"""The literal message of every translation lookup called in `path`.

	The source is read rather than imported, which is the only way to reach the
	shell of the add-on at all: its modules import NVDA's own, and those do not
	exist outside a running screen reader (docs/development.md). It is also how
	`xgettext` reads them, so what comes back here is what reaches the template.
	"""
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
			continue
		positions = MSGID_POSITIONS.get(node.func.id)
		if positions is None:
			continue
		for argument in [node.args[at - 1] for at in positions if at <= len(node.args)]:
			# A lookup given anything but a literal is extracted by nobody, so
			# the string would be missing from the template rather than from the
			# catalogue -- a different fault, and one worth saying out loud.
			assert isinstance(argument, ast.Constant) and isinstance(argument.value, str), (
				f"{path.relative_to(REPO_ROOT)}: {node.func.id}() on line {node.lineno} "
				"is given something other than a literal string, which nothing can extract"
			)
			yield argument.value


def fixture_path(kind: str, name: str) -> Path:
	"""Path of the fixture `name` under `tests/fixtures/<kind>`."""
	path = FIXTURES / kind / f"{name}.json"
	assert path.is_file(), f"no such fixture: {path}"
	return path


def fixture_text(kind: str, name: str) -> str:
	"""Contents of the fixture `name` under `tests/fixtures/<kind>`."""
	return fixture_path(kind, name).read_text(encoding="utf-8")


def fixture_paths(kind: str) -> list[Path]:
	"""Paths of every fixture under `tests/fixtures/<kind>`, sorted."""
	paths = sorted((FIXTURES / kind).glob("*.json"))
	assert paths, f"no fixtures under {kind}"
	return paths


def fixture_names(kind: str) -> list[str]:
	"""Names of every fixture under `tests/fixtures/<kind>`, sorted."""
	return [path.stem for path in fixture_paths(kind)]


def temporary_directory(test: unittest.TestCase) -> Path:
	"""A directory of `test`'s own, swept away when it ends.

	Writing shows only on disk, so every test about it works through real
	files. Three modules need somewhere to put them; this is the one place
	that decides where and that remembers to clear up.
	"""
	directory = tempfile.mkdtemp()
	test.addCleanup(shutil.rmtree, directory, True)
	return Path(directory)
