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

#: The functions `xgettext` collects strings from, as `pyproject.toml` declares
#: them builtins for the lint. The number of leading arguments each one takes
#: from the catalogue is what differs: `_` names one message, `ngettext` names a
#: singular and a plural that make one entry between them.
LOOKUPS = {"_": 1, "ngettext": 2, "pgettext": 1, "npgettext": 2}


def translation_lookups(path: Path) -> Iterator[str]:
	"""The literal argument of every translation lookup called in `path`.

	The source is read rather than imported, which is the only way to reach the
	shell of the add-on at all: its modules import NVDA's own, and those do not
	exist outside a running screen reader (docs/development.md). It is also how
	`xgettext` reads them, so what comes back here is what reaches the template.
	"""
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
			continue
		taken = LOOKUPS.get(node.func.id)
		if taken is None:
			continue
		for argument in node.args[:taken]:
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
