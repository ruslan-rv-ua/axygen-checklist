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

Checklists are usually written by a coding agent working inside the project
under test, so the format is documented for one:
[how to write a checklist](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/checklist-format.md),
with a [JSON Schema](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/checklist-v1.schema.json)
next to it and a block to paste into your project's `AGENTS.md`. Worth reading
before letting an agent edit a checklist somebody has already run: the statuses
and comments in the file are a tester's work, not the agent's to regenerate.

## Not in this version yet

This page describes the add-on as a whole, and not all of it is built yet.

* **Walking a checklist at all.** This build only registers the add-on with
  NVDA: no commands, no speech, no file handling. That arrives in 0.1.0.
* **Filtering to unchecked items** — due in 0.2.0.

Until 1.0.0 the checklist file format and the set of commands may still change
from one release to the next. From 1.0.0 on, neither changes without a major
version bump.

## When a command does nothing

Axygen Checklist claims the `NVDA+Alt` prefix. Another add-on may bind the same
combination, and nothing tells you so: whichever global plugin NVDA happens to
reach first wins, and that order is not guaranteed to survive a restart. The
key simply does the wrong thing.

The fix is NVDA's own dialog: **Preferences → Input Gestures → category Axygen
Checklist**. Deleting a binding there hands the key back to whoever else wants
it; adding one gives a command a combination of your choosing. Every command
appears in that category, including the ones that normally live inside the
command mode and ship with no key at all.

The same dialog is the answer if the entry key feels wrong under your hands.
It was chosen for an `NVDA` key on `CapsLock`, where both modifiers fall to the
left hand and the letter to the right; with `NVDA` on `Insert` a different
letter is easier.

Copyright (C) 2026 Ruslan Iskov. Distributed under the terms of the GNU General
Public License version 2 or later; see COPYING.txt.
