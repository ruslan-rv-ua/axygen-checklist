# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Fixture helpers shared by the unit tests.

The `sys.path` entry that makes `core` importable is installed by the package
`__init__`; see the note there.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


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
