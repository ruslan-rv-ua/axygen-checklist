# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""Sanity check for the unit test runner.

Tests that import the add-on itself need NVDA's own modules, which exist only
inside a running NVDA; this file only proves that the runner is wired up.
"""

import unittest


class TestRunner(unittest.TestCase):
	def test_runner_collects_tests(self):
		self.assertTrue(True)
