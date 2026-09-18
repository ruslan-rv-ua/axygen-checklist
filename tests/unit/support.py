# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Fixture helpers shared by the unit tests.

The `sys.path` entry that makes `core` importable is installed by the package
`__init__`; see the note there.
"""

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


def fixture_names(kind: str) -> list[str]:
	"""Names of every fixture under `tests/fixtures/<kind>`, sorted."""
	names = sorted(path.stem for path in (FIXTURES / kind).glob("*.json"))
	assert names, f"no fixtures under {kind}"
	return names
