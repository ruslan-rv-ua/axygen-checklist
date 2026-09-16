# Axygen Checklist

An NVDA add-on for testers who work by ear.

Axygen Checklist walks a test checklist with global commands while the system
focus stays in the application under test. An item can be marked passed, failed
or skipped, commented on, read back by speech and filtered out of the way
without ever leaving the window being tested.

A checklist is a plain JSON file. It carries the items to check and, once the
run is over, the result of each one, so a run can be handed over, kept next to
the build it belongs to, or repeated later.

The add-on is in early development. Commands, spoken feedback and the file
format are still being implemented; nothing here is stable yet.

Copyright (C) 2026 Ruslan Iskov. Distributed under the terms of the GNU General
Public License version 2 or later; see COPYING.txt.
