# Axygen Checklist

An NVDA add-on for testers who work by ear.

[Українською](readme.uk.md)

Axygen Checklist reads a test checklist to you item by item and lets you record the result of each check with a few global NVDA commands, while the system focus stays in the application you are testing. No more Alt+Tab between the list and the product: the list comes to you by speech, and the verdict goes into the file with one key press.

An item can be marked passed, failed, blocked or skipped, given a comment and read back on request. Every change is written to the checklist file immediately, and the add-on remembers where you were across NVDA restarts. When you want the whole picture, a window shows the checklist as a tree with the comment of the selected item and the add-on's settings.

The full user guide, the same one NVDA opens from the add-on's Help button, is in [addon/doc/en/readme.md](addon/doc/en/readme.md). It walks through a first run, explains every key and window, and lists the messages and sounds and what they mean.

## Who it is for

Blind and low-vision testers and developers who use NVDA and run manual checklists against desktop or web applications. Everything the add-on says is designed to be heard: short phrases in a fixed order, sounds where a word would be too slow, silence where the screen reader already says enough.

## Getting started

1. Install the add-on from the Add-on Store or from the `.nvda-addon` file. It needs NVDA 2026.1 or newer and is tested up to 2026.2.
2. Put the focus in the application you are going to test.
3. Press `NVDA+Alt+O`, release, then press `O`. Choose a checklist file in the dialog that opens. The first item is read to you, section name first.
4. Do the check, then press `NVDA+Alt+Space` to mark the item passed. The next item follows.
5. For any other verdict press `NVDA+Alt+O`, release, then a digit: `2` failed, `3` blocked, `4` skipped, `5` back to not checked. `NVDA+Alt+I` twice opens the item dialog where you type a comment.

That is the whole loop. `NVDA+Alt+PageDown` and `NVDA+Alt+PageUp` move through the items, twice quickly through the sections, and `NVDA+Alt+I` reads the current item again. The rarer commands, progress, section reset, copying an exact string from the item, auto-advance and the window, live behind `NVDA+Alt+O` as single letters; the guide lists them all. Every command is also listed, with a description, in NVDA's Input Gestures dialog under the category **Axygen Checklist**, where you can rebind any of them.

## Checklist files

A checklist is a plain JSON file with sections and items. It carries the items to check and, once the run is over, the status and comment of each one, so a run can be handed over, kept next to the build it belongs to, or repeated later.

Checklists are usually written by a coding agent working inside the project under test, so the format is documented for one: [how to write a checklist](docs/checklist-format.md), with a [JSON Schema](docs/checklist-v1.schema.json) next to it and a block to paste into your project's `AGENTS.md`. Worth reading before letting an agent edit a checklist somebody has already run: the statuses and comments in the file are a tester's work, not the agent's to regenerate.

## Status of the project

The core is complete: opening a file, moving, marking, the item dialog with comments, fragments, resets, auto-advance, the window, and resuming after a restart. Still to come are the filter to unchecked items (0.2.0), a Markdown report of the run (1.0.0) and voice switching between recent checklists (1.1.0). Until 1.0.0 the file format and the set of commands may change between releases; from 1.0.0 on, neither changes without a major version bump.

## For developers

The behaviour is specified in [docs/requirements.md](docs/requirements.md) (in Ukrainian), which is the single source of truth for the format, the keys and the wording. Building, linking the working copy into a live NVDA and the release checklist are in [docs/development.md](docs/development.md). Issues and tasks live in the [GitHub tracker](https://github.com/ruslan-rv-ua/axygen-checklist/issues).

Copyright (C) 2026 Ruslan Iskov. Distributed under the terms of the GNU General Public License version 2 or later; see [COPYING.txt](COPYING.txt).
