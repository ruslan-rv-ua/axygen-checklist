# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Guards the checklist schema against drifting away from the specification.

`docs/checklist-v1.schema.json` is a derived artefact: section 2 of
`docs/requirements.md` is normative, and the schema only restates it in a form
machines can read. Two texts describing one format drift apart, so the tie is
here rather than in anyone's discipline.

The tie has three strands:

* every fenced ``json`` block in the specification and in the authoring guide
  that holds a whole checklist is validated against the schema, which makes the
  documented examples machine-checked;
* the fixtures under ``tests/fixtures/invalid`` mirror the validation contract
  of section 2 clause by clause, so a clause that disappears from the
  specification leaves a fixture behind in the diff;
* uniqueness of ``id`` is checked by hand, because JSON Schema cannot state it:
  the identifiers live in ``items`` inside ``sections``, and ``uniqueItems``
  works on a single array.

The tests assert only that an invalid fixture is rejected, never which keyword
rejected it. A validator's wording belongs to no contract, and asserting on it
would break at the next release of `jsonschema` without catching anything.
"""

import json
import re
import unittest
from pathlib import Path
from typing import Any, Iterator

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "checklist-v1.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
DOCUMENTS = (
	REPO_ROOT / "docs" / "requirements.md",
	REPO_ROOT / "docs" / "checklist-format.md",
)

SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

_FENCE = re.compile(r"^(\s*)(`{3,})(.*)$")


def iter_fenced_blocks(text: str, info: str) -> Iterator[str]:
	"""Yield the body of every fenced code block whose info string is `info`.

	Blocks nested inside other fences are found too: the authoring guide wraps a
	``json`` example in a four-backtick ``markdown`` fence, and that example is
	meant to be checked like any other.
	"""
	lines = text.split("\n")
	index = 0
	while index < len(lines):
		opening = _FENCE.match(lines[index])
		if opening is None:
			index += 1
			continue
		indent, ticks, block_info = opening.group(1), opening.group(2), opening.group(3).strip()
		index += 1
		body: list[str] = []
		while index < len(lines):
			closing = _FENCE.match(lines[index])
			if closing is not None and closing.group(2).startswith(ticks) and not closing.group(3).strip():
				break
			line = lines[index]
			body.append(line[len(indent) :] if line.startswith(indent) else line)
			index += 1
		index += 1
		block = "\n".join(body)
		if block_info == info:
			yield block
		else:
			yield from iter_fenced_blocks(block, info)


def is_whole_checklist(document: object) -> bool:
	"""Whether a parsed block is a whole file rather than a fragment.

	Counterexamples in the documentation are written as fragments precisely so
	that this returns false for them; see section 2 of `requirements.md`.
	"""
	return isinstance(document, dict) and "checklist_name" in document


def duplicate_ids(document: Any) -> list[object]:
	"""Item identifiers that occur more than once in the file."""
	seen: set[object] = set()
	duplicates: list[object] = []
	sections = document.get("sections") if isinstance(document, dict) else None
	for section in sections if isinstance(sections, list) else []:
		items = section.get("items") if isinstance(section, dict) else None
		for item in items if isinstance(items, list) else []:
			if not isinstance(item, dict):
				continue
			identifier = item.get("id")
			if not isinstance(identifier, int):
				continue
			if identifier in seen:
				duplicates.append(identifier)
			seen.add(identifier)
	return duplicates


def contract_errors(document: Any) -> list[str]:
	"""Everything the validation contract of section 2 has against a document."""
	errors = [error.message for error in VALIDATOR.iter_errors(document)]
	errors += [f"duplicate id: {identifier}" for identifier in duplicate_ids(document)]
	return errors


def load_fixtures(kind: str) -> list[Path]:
	paths = sorted((FIXTURES / kind).glob("*.json"))
	assert paths, f"no fixtures under {kind}"
	return paths


class TestSchema(unittest.TestCase):
	def test_schema_is_a_valid_2020_12_schema(self):
		jsonschema.Draft202012Validator.check_schema(SCHEMA)

	def test_schema_declares_the_expected_dialect(self):
		self.assertEqual(SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema")

	def test_schema_id_matches_its_path(self):
		# `$schema` in a checklist pins this URL, so the file may not be renamed
		# or moved without the identifier following it.
		self.assertTrue(SCHEMA["$id"].endswith(f"/docs/{SCHEMA_PATH.name}"), SCHEMA["$id"])


class TestFixtures(unittest.TestCase):
	def test_valid_fixtures_are_accepted(self):
		for path in load_fixtures("valid"):
			with self.subTest(fixture=path.name):
				document = json.loads(path.read_text(encoding="utf-8"))
				self.assertEqual(contract_errors(document), [])

	def test_invalid_fixtures_are_rejected(self):
		for path in load_fixtures("invalid"):
			with self.subTest(fixture=path.name):
				document = json.loads(path.read_text(encoding="utf-8"))
				self.assertNotEqual(contract_errors(document), [])


class TestDocumentedExamples(unittest.TestCase):
	def test_every_documented_checklist_validates(self):
		checked = 0
		for path in DOCUMENTS:
			text = path.read_text(encoding="utf-8")
			for number, block in enumerate(iter_fenced_blocks(text, "json"), start=1):
				document = json.loads(block)
				if not is_whole_checklist(document):
					continue
				checked += 1
				with self.subTest(document=path.name, block=number):
					self.assertEqual(contract_errors(document), [])
		# A scanner that silently stops finding blocks would turn this whole
		# test into a no-op, so the count is asserted rather than trusted.
		self.assertGreaterEqual(checked, 3, "expected the documented examples to be found")

	def test_documented_fragments_are_not_mistaken_for_files(self):
		# The counterexample in the authoring guide is a fragment on purpose:
		# a whole invalid file in the documentation would fail the test above.
		guide = (REPO_ROOT / "docs" / "checklist-format.md").read_text(encoding="utf-8")
		fragments = [
			block
			for block in iter_fenced_blocks(guide, "json")
			if not is_whole_checklist(json.loads(block))
		]
		self.assertTrue(fragments, "expected at least one fragment in the authoring guide")
