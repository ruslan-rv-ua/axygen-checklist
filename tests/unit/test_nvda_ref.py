# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Guards the rule that turns a version into the NVDA source CI checks against.

`tools/nvda_ref.py` maps `addon_lastTestedNVDAVersion` to the git ref that
holds that release's source, and `checks.yml` clones what it prints. What the
rule is, and why it takes the shape it does, is said once, in that module; what
stands here are the examples, because a ref shape read off NV Access's tags is
the kind of thing that gets tidied into something more regular by someone who
never saw the tags.

The last test looks at the real `buildVars.py`. A version the rule cannot read
would take CI down at the clone, with a message about a ref rather than about
the field that names it; here it fails before the commit, at the field.

Nothing here reaches the network. Whether a ref exists is NV Access's answer to
give, and `git clone --branch` asks it loudly enough.
"""

import unittest

from tools.nvda_ref import last_tested_ref, release_ref


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


class TheVersionInBuildVars(unittest.TestCase):
	def test_is_one_the_rule_can_read(self) -> None:
		# Raising is the failure, and there is nothing to assert beyond it. Asserting on
		# the shape of what comes back would only restate the regex that let it through,
		# and whether the ref exists is NV Access's answer, asked at the clone.
		last_tested_ref()
