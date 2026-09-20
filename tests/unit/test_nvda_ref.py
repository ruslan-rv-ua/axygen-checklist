# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Guards the rule that turns a version into the NVDA source CI checks against.

`tools/nvda_ref.py` maps the two versions in `buildVars.py` to the git refs
that hold their source, and the workflows clone what it prints. What the rule
is, and why it takes the shape it does, is said once, in that module; what
stands here are the examples, because a ref shape read off NV Access's tags is
the kind of thing that gets tidied into something more regular by someone who
never saw the tags.

Two of the tests look at the real `buildVars.py`. A version the rule cannot read
would take CI down at the clone, with a message about a ref rather than about
the field that names it; here it fails before the commit, at the field.

The command line is here for one reason: it decides which end of the supported
range a workflow checks, and getting that wrong is silent. A run that meant to
name the floor and named nothing checks the ceiling twice and passes.

Nothing here reaches the network. Whether a ref exists is NV Access's answer to
give, and `git clone --branch` asks it loudly enough.
"""

import unittest

from tools.nvda_ref import last_tested_ref, minimum_ref, ref_named_by, release_ref


class ReleaseRef(unittest.TestCase):
	def test_the_first_release_of_a_cycle_loses_its_trailing_zero(self) -> None:
		self.assertEqual(release_ref("2025.3.0"), "release-2025.3")

	def test_a_release_after_it_keeps_all_three_parts(self) -> None:
		self.assertEqual(release_ref("2025.3.1"), "release-2025.3.1")

	def test_a_version_already_in_two_parts_is_left_alone(self) -> None:
		self.assertEqual(release_ref("2025.3"), "release-2025.3")

	def test_a_zero_in_the_middle_is_not_a_trailing_one(self) -> None:
		self.assertEqual(release_ref("2026.0.1"), "release-2026.0.1")

	def test_anything_that_is_not_a_version_is_refused(self) -> None:
		for version in ("", "2025", "2025.3.0.1", "2025.3.0beta1", "2025.x.0", "release-2025.3"):
			with self.subTest(version=version):
				with self.assertRaises(ValueError):
					release_ref(version)


class TheVersionsInBuildVars(unittest.TestCase):
	def test_the_last_tested_one_is_one_the_rule_can_read(self) -> None:
		# Raising is the failure, and there is nothing to assert beyond it. Asserting on
		# the shape of what comes back would only restate the regex that let it through,
		# and whether the ref exists is NV Access's answer, asked at the clone.
		last_tested_ref()

	def test_the_minimum_one_is_one_the_rule_can_read(self) -> None:
		# The floor is checked for the same reason as the ceiling, and by the same rule:
		# the release workflow clones this ref too (docs/development.md, section 4).
		minimum_ref()


class TheCommandLine(unittest.TestCase):
	def test_names_the_last_tested_end_when_asked_for_nothing(self) -> None:
		self.assertEqual(ref_named_by([]), last_tested_ref())

	def test_names_the_floor_when_asked_for_it(self) -> None:
		self.assertEqual(ref_named_by(["minimum"]), minimum_ref())

	def test_refuses_anything_else_instead_of_falling_back(self) -> None:
		# Falling back to the default here is the failure worth guarding: the run would
		# check the ceiling a second time and report success, having never looked at the
		# floor it was called for.
		for arguments in (["Minimum"], ["--minimum"], ["maximum"], ["minimum", "extra"], [""]):
			with self.subTest(arguments=arguments):
				with self.assertRaises(SystemExit):
					ref_named_by(arguments)
