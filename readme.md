# Axygen Checklist

An NVDA add-on for testers who work by ear.

[Українською](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/addon/doc/uk/readme.md)

Axygen Checklist walks a test checklist with global commands while the system
focus stays in the application under test. An item can be marked passed, failed
or skipped, commented on, read back by speech and filtered out of the way
without ever leaving the window being tested.

A checklist is a plain JSON file. It carries the items to check and, once the
run is over, the result of each one, so a run can be handed over, kept next to
the build it belongs to, or repeated later.

## Not in this version yet

This page describes the add-on as a whole, and not all of it is built yet.

* **Walking a checklist at all.** This build only registers the add-on with
  NVDA: no commands, no speech, no file handling. That arrives in 0.1.0.
* **Filtering to unchecked items** (`NVDA+Shift+F`) — due in 0.2.0.

Until 1.0.0 the checklist file format and the set of commands may still change
from one release to the next. From 1.0.0 on, neither changes without a major
version bump.

Copyright (C) 2026 Ruslan Iskov. Distributed under the terms of the GNU General
Public License version 2 or later; see COPYING.txt.
