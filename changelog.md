## 0.1.0

The first release: the core of walking a checklist, everything in the specification except the filter to unchecked items.

* Open a checklist from a JSON file and walk it with global hotkeys while the system focus stays on the application under test.
* Move between items and sections, hear the current item, its note and the progress of the section.
* Mark the current item passed, failed, blocked or skipped from the command mode, with the key or with a digit; the item dialog, opened with `NVDA+Alt+I` pressed twice, takes a comment on the verdict.
* Copy a fragment of the current item to the clipboard.
* Reset a section from the command mode, or the whole run from the window, after a confirmation.
* Auto-advance to the next unchecked item after a verdict, switchable in the settings.
* Resume the last checklist and position after NVDA restarts.
* The add-on window: the checklist as a tree, the item dialog, the settings tab.
* English and Ukrainian interface and help.

Requires NVDA 2026.1 or later. Until 1.0.0 the checklist file format and the set of commands may still change between releases.
