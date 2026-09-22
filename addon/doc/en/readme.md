# Axygen Checklist

Axygen Checklist is an NVDA add-on for testers who work by ear. It reads a test checklist to you item by item, lets you mark each item passed, failed, blocked or skipped, takes your comments and writes everything back to a file, and it does all of this while the system focus stays exactly where you left it: in the application you are testing.

This page is the full guide. It explains what the add-on is for, how a run goes from opening a file to hearing "Checklist complete!", what every key does, what the windows contain, what the messages and sounds mean, and what to do when a key seems to do nothing.

## What it is for, and who it is for

Manual testing with a screen reader has an awkward rhythm. The checklist lives in one window, the product under test in another, and every item costs a trip between them: Alt+Tab to the list, read the item, Alt+Tab back, find the place you were at, do the check, Alt+Tab to the list again to write down the result. Each trip is a chance to lose the place in the product, and the product often announces itself all over again when it gets the focus back.

Axygen Checklist removes the trip. The checklist is loaded into the add-on, and a handful of global NVDA commands read the current item, move to the next one and record the verdict, all without touching the focus. You stay in the product; the list comes to you by speech. When you do want to see the whole thing at once, add a comment or pick a different file, there is a window for that, but you open it deliberately, and when it closes the focus goes back where it was.

The add-on is built for blind and low-vision testers and developers who use NVDA. Everything it says is designed to be heard, not seen: short phrases, a fixed order of words, sounds where a word would be too slow, and silence where the screen reader already tells you what you need to know.

## Before you start

* **NVDA version.** The add-on needs NVDA 2026.1 or newer, which is the 64-bit NVDA with Python 3.13. It is tested up to NVDA 2026.2. On an older NVDA the Add-on Store will not offer it, and a manually installed copy is marked incompatible.
* **Installation.** Install it from the Add-on Store like any other add-on, or open the downloaded `.nvda-addon` file. No configuration is needed before the first use.
* **Language.** The add-on speaks English and Ukrainian, following the interface language of NVDA. There is no separate language setting in the add-on. The name "Axygen Checklist" stays English in both languages; that is how the add-on is listed in the Add-on Store and in NVDA's own dialogs.
* **A checklist file.** The add-on reads checklists from plain JSON files. If nobody has given you one yet, see the section "The checklist file" below for where they come from.

## The idea in one minute

Five key combinations, all under `NVDA+Alt`, do the everyday work:

* `NVDA+Alt+PageDown` and `NVDA+Alt+PageUp` move through the items.
* `NVDA+Alt+Space` marks the current item passed, or puts it back to not checked.
* `NVDA+Alt+I` reads the current item again. Pressed twice, it opens the item dialog.
* `NVDA+Alt+O` arms the **command mode** for three seconds. The key you press next, on its own, does one of the rarer jobs: sets any of the five statuses, opens a file, reads the progress, resets a section, copies a fragment, toggles auto-advance or opens the window.

None of these commands moves the focus when pressed once. A window can only appear on the second press of a series, or from the command mode you armed on purpose. That rule is the heart of the add-on, and every command respects it.

Everything you do is written to the checklist file immediately. There is no save command and nothing to lose if NVDA restarts: the add-on also remembers which file you had open and which item you were on, and puts you back there next time.

## Your first run

1. Open the application you are going to test and leave the focus in it.
2. Press `NVDA+Alt+O`. You hear a short tone: the command mode is armed.
3. Release the keys and press `O` on its own. A standard file dialog titled "Open a checklist" appears, filtered to `.json` files. Pick your checklist and press Enter.
4. The focus returns to your application, and the add-on reads the item you are now on: the section name first, then the text of the item, its status, and the author's note if the item has one. On a fresh file this is the first item of the first section, and the status is "not checked".
5. Do the check the item describes. Then press `NVDA+Alt+Space`. You hear "passed", and, because auto-advance is on by default, the next item is read right away.
6. If the check failed, press `NVDA+Alt+O`, release, then `2`. You hear "failed" and the next item. If you want to say why, press `NVDA+Alt+I` twice: the item dialog opens with the cursor in the comment field, you type your note, and `Ctrl+Enter` saves it and returns you to the application.
7. Carry on. When the last item receives a verdict, you hear a sound and "Checklist complete! All 12 items processed", with ", 2 failed" added when some failed.

The results are already in the file. Hand it over, keep it next to the build it belongs to, or open it again later to continue.

## What you hear about an item

Whenever the add-on lands on an item, whether by navigation, by auto-advance or because you asked with `NVDA+Alt+I`, it says the same thing in the same order:

1. The **text** of the item.
2. Its **status**: "not checked", "passed", "failed", "blocked" or "skipped".
3. The words "has a comment", but only when you have written a comment on this item. The comment itself is not read; it can be a whole paragraph, and you would hear it on every pass. Open the item dialog to read it.
4. After a pause, the author's **note**, if the item has one. Notes are short hints written by the author of the checklist and meant to be heard every time.

For example: "Check the labels of the form fields, failed, has a comment. Check Tab and Shift+Tab."

When you jump to another section, or open a file, the **section name** is read first, so you know where you have landed.

You may hear back-ticks in the text: "Open `http://localhost:8080`". They mark a **fragment**, an exact string the author wants you to reproduce rather than retype from hearing. With NVDA's default punctuation level the back-ticks themselves are silent. See "Fragments" below for how to copy one.

## Moving through the checklist

* `NVDA+Alt+PageDown`, once: the next item. `NVDA+Alt+PageUp`, once: the previous item.
* The same keys pressed **twice quickly**: the first item of the next or the previous section. The section name is read before the item.

At the ends of the list the single press does not move and gives a short beep instead of words; you meet the end of a list every time you read it through, and a beep is faster than a phrase. The double press, which is a deliberate jump, uses words: "End of list" or "Start of list".

A double press is counted with NVDA's own multi-press timeout, the same one that governs `NVDA+T` and similar commands, and you can adjust it in NVDA's keyboard settings. Note that the first press of the pair has already moved you one item by the time the second arrives; the jump is worked out from where you started, so a double press on the last item of a section never skips a section.

The position in the checklist is the add-on's own; it has nothing to do with where the focus is, and moving through the list never changes the focus.

## Marking items

An item has one of five statuses. "Not checked" is where every item starts. "Passed", "failed", "blocked" and "skipped" are **verdicts**. The add-on treats a verdict as "this item has been dealt with", whichever of the four it is.

### The quick way

`NVDA+Alt+Space` is the key you will press most. It toggles between passed and not checked: a not-checked item becomes passed, a passed item goes back to not checked, and an item with any other verdict becomes passed too. One press, one change. There is no double-press meaning on this key, on purpose: the most frequent key of the add-on should never be one accidental double tap away from something destructive, and a nervous second press simply undoes the first.

### The full way

Arm the command mode with `NVDA+Alt+O`, release the keys, and press a digit:

* `1` sets **passed**.
* `2` sets **failed**.
* `3` sets **blocked**.
* `4` sets **skipped**.
* `5` puts the item back to **not checked**.

The new status is spoken, and, with auto-advance on, the next item follows. `5` is the undo slot: it is the one status change after which the add-on stays on the item, so you can re-read it and decide again.

Digits rather than letters because the letters collide: "passed" and "pending" share a P, and the letters of the command mode are already taken by other commands. Digits are also the same in every keyboard layout.

The status can also be set in the item dialog, and in the tree of the checklist window; both are described below.

### Auto-advance

Auto-advance is on when you install the add-on. With it on, giving an item a verdict moves you to the next item and reads it, so a run of straightforward checks is a rhythm of "do the check, press Space, listen". It does not fire when you put an item back to not checked, when you set a status from the item dialog or from the tree, or when the file could not be written; in all three cases you are meant to stay where you are. When there is no next item, you simply stay on the last one, without any beep.

To turn it off or on, arm the command mode and press `A`. You hear "Auto-advance on" or "Auto-advance off". The same option is a checkbox on the Settings tab of the checklist window.

The setting is stored in NVDA's own configuration, which has two consequences worth knowing. First, it belongs to the active configuration profile. If you have NVDA profiles that switch with the application in focus, auto-advance toggled while testing one application is remembered for that application. Second, NVDA writes its configuration to disk on exit if "Save configuration on exit" is enabled, or when you press `NVDA+Ctrl+C`; if you have turned that off and never save by hand, the setting goes back to its default after a restart.

### When the checklist is complete

When a verdict leaves no item in the whole file at "not checked", you hear a sound and the phrase "Checklist complete! All 12 items processed", followed by ", 3 failed" if anything failed. This is about the run being over, not about everything passing: a checklist with failures is still complete once every item has been looked at.

The phrase is spoken however the last verdict was given: by key, from the item dialog or from the tree. When auto-advance also moves you on, the order is the status word, then the completion phrase, then the next item.

## Command mode

`NVDA+Alt+O` arms the command mode for **three seconds**. You hear a short tone. During those three seconds, the letters and digits listed below belong to the add-on. Pressing one of them runs the command, speaks the result and disarms the mode. If you press nothing, the mode expires with a second, lower tone, so you know your next letter will go to the application again.

The mode is written as "`NVDA+Alt+O`, release, then the key": pressing `NVDA+Alt+O` twice without releasing the modifiers just re-arms the mode.

### Keys of the command mode

* `1`, `2`, `3`, `4`, `5`: set the status to passed, failed, blocked, skipped or not checked.
* `O`: open a checklist file.
* `P`: read the name of the current section and the progress in it.
* `R`: reset the current section, after a confirmation.
* `A`: turn auto-advance on or off.
* `G`: open the checklist window.
* `C`: copy a fragment of the current item to the clipboard.

Three more keys are planned and do nothing yet: `F` for the filter to unchecked items, `E` for the report, `N` for switching between recent checklists. See "Not in this version yet" below.

### Things worth knowing about the mode

* **There is no spoken menu.** Reading fourteen keys aloud would take longer than the mode lives. The tone tells you the mode is armed; this page tells you the keys.
* **Space and the arrows are never part of the mode.** While the mode is armed, they still go to your application, as does any key the add-on has not claimed. That key does not cancel the mode either; the mode simply waits for one of its own keys or for the timeout. This is deliberate: an add-on that swallowed Space while you were on a Save button would leave you wondering whether the application failed or the checklist ate the key.
* **Any other add-on command cancels the mode and runs normally.** Arm the mode, change your mind, press `NVDA+Alt+PageDown`, and you move to the next item with no extra word.
* **No checklist is needed to arm the mode.** Without a file, `O`, `A` and `G` work as usual, since they are how you get a file, change a preference or open the window. The other keys say "No checklist loaded".
* **The three seconds are the add-on's own** and do not depend on NVDA's multi-press timeout.
* **Why `O`.** The letter is optimised for the laptop layout with the NVDA key on Caps Lock, where both modifiers fall to the left hand and the letter to the right. With the NVDA key on Insert a different letter may suit you better, and you can change it in NVDA's Input Gestures dialog; see "When a command does nothing" below.

## The item dialog

Press `NVDA+Alt+I` twice quickly and the item dialog opens; from the tree of the checklist window, Enter on an item opens the same dialog. Its title is "Checklist item". This is the one place where you write a comment, and one of the ways to set a status.

The Tab order is:

1. **Item**: the full text of the item, read-only. You can move through it with the arrows, select with Shift+arrows and copy with `Ctrl+C`.
2. **Note**: the author's note, read-only in the same way. This field exists only when the item has a note; otherwise Tab goes straight from Item to Status.
3. **Status**: a drop-down list with the five statuses in the order of the digits: passed, failed, blocked, skipped, not checked. It opens on the current status. You choose; you cannot type a status, so a typo can never put an unknown value into the file.
4. **Comment**: a multi-line field with your comment, if any.
5. **Save** and **Cancel**.

Where the focus lands when the dialog opens is your choice: Item, Status or Comment, set on the Settings tab of the checklist window. By default it is the Comment field, with the cursor at the end of any existing text, so you can start typing at once.

Keys in the dialog:

* `Ctrl+Enter` saves from any field, including from inside the comment, where a plain Enter inserts a new line. `Ctrl+Numpad Enter` does the same.
* **Save** can also be reached by Tab, or by its access key `Alt+S`.
* `Escape` cancels immediately, without asking, even if you changed something; nothing is written. If the status list is open, `Escape` closes the list first and leaves the dialog standing.

On save, the add-on writes the file and says only what actually changed, status first: "failed, comment saved", or just "failed", or "comment saved", or "comment deleted" when you emptied a comment that was there. If nothing changed, it says nothing and writes nothing. Auto-advance does not fire from the dialog: you stay on the item you were editing. The completion phrase is still spoken if this save closed the last unchecked item.

A comment can be added at any status, not only to failures; "passed, but slow" is worth writing down too.

## Comments and notes

Two kinds of text can sit under an item, and the add-on treats them very differently.

A **note** is written by the author of the checklist before the run: a hint, a reminder of a setting, the expected result. It is read automatically after the text of the item, every time, and shown in the item dialog in a read-only field. The add-on never changes a note.

A **comment** is your conclusion after the check. You write it in the item dialog, it is stored in the file, and it is not read on every pass; the phrase "has a comment" tells you it is there. Comments are erased when you reset a section or the whole run, because a comment that says "failed because X" about an item nobody has checked yet would mislead the next tester.

## Fragments: copying exact strings

Addresses, paths, commands, identifiers and test data do not survive speech. `.\app.exe` reaches the ear as a bare "app.exe", because the backslash is silent and the dot is read as a word. Checklist authors therefore wrap such strings in single back-ticks: "Open `http://localhost:8080` and check the home page appears". The back-ticks are silent at NVDA's default punctuation level, and they mark what you can copy.

Arm the command mode and press `C`:

* If the current item has **no fragments**, in neither text nor note, you hear "The item has no fragments".
* If it has **exactly one**, it is copied straight away, and NVDA confirms with its own phrase "Copied to clipboard:" followed by the text. No window opens.
* If it has **two or more**, a small dialog titled "Copy a fragment" opens with a list labelled "Fragments". The first fragment is selected. Use the arrows to pick one and press Enter or the Copy button; `Escape` cancels. The dialog closes before the copy is confirmed, so the focus is already back in your application when you hear the confirmation.

Fragments come from the item's text first and then from its note, in order of appearance. Your own comment is not searched; you can copy from it in the item dialog directly.

## Section name and progress

Arm the command mode and press `P` to hear where you are: "Section: Controls, 4 of 5 processed", and when something in the section has failed, ", 1 failed" is added. "Processed" means any status other than not checked. The count always covers the whole section.

## Resetting a section

Arm the command mode and press `R`. A warning dialog appears: "Reset the section? Every status and comment in the section will be erased. This cannot be undone." with Yes and No buttons. `Escape` means No. Yes puts every item of the current section back to not checked, deletes their comments, writes the file, and says "Section reset". Notes written by the author are kept.

Resetting is how you prepare a second run of a section after the product has been fixed. To reset the whole checklist, use the button in the checklist window.

## The checklist window

The window shows the whole checklist as a tree, with the comment of the selected item underneath, and holds the add-on's settings. Open it with `G` in the command mode, or from NVDA's menu: Tools, then Axygen Checklist. Both the window and the menu item are named "Axygen Checklist".

The window is modal. While it is open, the global commands of the add-on do not run, and NVDA itself will not exit or restart until you close it. Think of it as a visit, not a companion: open it, look, close it. It opens centred, can be resized and maximised, and the tree takes all the extra height.

The window has two tabs, **Run** and **Settings**, and a **Close** button below them. `Escape` closes the window. `Ctrl+Tab` switches between the tabs. The focus lands on the tree when the window opens.

### The Run tab

In Tab order:

* **Checklist file**: a read-only field with the path of the open file, followed by a **Browse...** button. Browse opens the same file dialog as `O` in the command mode, starting in the folder of the current file. If the chosen file cannot be loaded, a dialog explains exactly why, naming the section, the item and the field, and the tree keeps showing the old file.
* **Reset all progress**: puts every item of the whole file back to not checked and erases every comment, after a confirmation in the same tone as the section reset. The button is disabled while no file is open.
* **Checklist**: the tree. The first level is the sections, the second the items; all sections are expanded when the window opens. Each item's label starts with its status, "Passed: ", "Failed: ", "Blocked: " or "Skipped: ", so that you can filter by ear from the first syllable. Items that are not checked carry no prefix. The item you are currently on in the run is selected when the window opens.
* **Comment**: a read-only, multi-line panel with the comment of the selected item. It is empty for sections and for items without a comment.

Moving the selection in the tree does **not** move your position in the run. The tree is a view. Only one action moves the position, and it is the one you ask for with `Ctrl+Enter`.

When the selection lands on an item that has a comment, you hear a short, high click just before the label. It is the tree's way of saying "has a comment" without lengthening the label.

### Keys in the tree

* **Enter** on an item opens the item dialog for it, on top of the window. After saving, the item's label and the comment panel update in place; the tree keeps its expansion and selection. On a section, or on an empty tree, Enter rings the system bell.
* **Ctrl+Enter**, "Go to": closes the window, makes the selected item the current item of the run and reads it, section name first. On a section it goes to the section's first item. This is the one key that moves the position.
* **Shift+Enter**, "Next status": cycles the selected item's status one step forward, passed, failed, blocked, skipped, not checked and round again, and writes the file. NVDA re-reads the label with its new prefix; the add-on adds no word of its own. There is no backward step; the longest way round is four presses. Auto-advance never fires from the tree.

Both chords also work with the Enter of the numeric keypad. Outside the tree they do nothing and go to the focused control as usual.

### The Settings tab

* **Automatically move to the next item after marking one**: the auto-advance checkbox, the same option as `A` in the command mode. It applies the moment you toggle it.
* **Field focused when an item is opened**: a drop-down with Item, Status and Comment, choosing where the focus lands when the item dialog opens. Also applied immediately.

The window has no OK or Cancel: there is nothing pending to confirm, everything applies at once.

## The checklist file

### Where checklists come from

A checklist is a JSON file with a name, one or more sections, and items in each section. Each item has a number, a text, optionally a note, and after your run, a status and a comment. Here is a small one:

```json
{
  "format_version": 1,
  "checklist_name": "Accessibility of the login form",
  "sections": [
    {
      "section_name": "Controls",
      "items": [
        {"id": 1, "text": "Every button is reachable with Tab"},
        {"id": 2, "text": "The password field is announced as protected", "note": "Check with `Ctrl+A` in the field too"}
      ]
    }
  ]
}
```

Checklists are usually written by whoever knows the product: a developer, a test lead, or increasingly a coding agent working inside the project's repository. The format is documented for exactly that reader, in English, in [how to write a checklist](https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/checklist-format.md), with a JSON Schema next to it and a block to paste into a project's `AGENTS.md`. One thing that document insists on is worth repeating here: the statuses and comments in a file are the tester's work. An agent asked to "update the checklist for the new features" must add and edit items without regenerating the file and wiping a finished run.

### What the add-on writes, and when

Every change you make, a status, a comment, a reset, is written to the file at once, in full. There is no save command and no unsaved state. The write is atomic: the add-on writes a temporary file next to the checklist and swaps it in, so a crash in the middle leaves the old file intact rather than a truncated one.

The add-on rewrites the whole file each time, in a fixed layout: two-space indentation, one item per line, so that the file stays readable and diffs stay small. Fields it does not know about are kept exactly as they were, which is what lets authors and tools add their own data to a checklist without losing it on the first key press. Text is never translated or altered: the names, texts, notes and comments are yours.

If a write fails, because the file is read-only, locked by an editor or an antivirus, or its drive has gone, you hear "Error writing the file" and nothing else: no status word, no next item, no completion phrase. The change is kept in memory, so the next successful write will carry it to disk; but until then the file is behind. Free the file and repeat the command. Note that repeating with `NVDA+Alt+Space` would toggle the status back; the honest retry is the digit in the command mode, which sets the status you mean.

### Where you left off

The add-on keeps the path of the open checklist and your position in it in a small file of its own, `state.json`, in the `axygenChecklist` folder inside NVDA's configuration directory. It is updated on every move, so a run that ends with an NVDA restart, which in this line of work happens on purpose quite often, resumes from the same item. On start the checklist is loaded silently; NVDA is already talking about itself and the focused window, and one more phrase would only get in the way.

If the remembered file is no longer where it was, you hear "Checklist file not found" and the file dialog opens on its own, starting in the last folder, so you can point the add-on at the file's new place. This is the only time a window of the add-on appears without you asking for it.

If the file has been edited between sessions and your remembered position no longer exists, you start from the first item. Opening the same file again with `O` or Browse returns you to your remembered position; opening a different file starts at its first item.

## Sounds

The add-on uses five short sounds, all different from each other:

* the tone when the command mode is armed;
* a lower tone when the mode expires unused;
* a beep at the start or end of the list on single-step navigation;
* the sound before "Checklist complete!";
* the short click in the tree of the window when the selection lands on an item that has a comment.

Their volume follows NVDA's sound volume. A sound is never interrupted by the key you press next, unlike speech, which is why the command mode signals with a tone rather than words.

## Messages and what to do about them

* **"No checklist loaded"**: a command needs a file and none is open. Arm the command mode and press `O`.
* **"The checklist has no items"**: the file loaded fine but has no items to check. Add items to it.
* **"Error reading the file"**: the file could not be loaded, whether because it is not valid JSON, a required field is missing or has the wrong type, an item's id is not unique, or a status has a value the add-on does not know. Spoken on its own when the file was loaded without you, at NVDA start. When you have just chosen the file yourself, a dialog gives the exact reason instead, with the section and item numbered from one and the item's id when it has one.
* **"This file was created by a newer version of the add-on"**: the file's format version is newer than this add-on knows. Update the add-on; nothing is wrong with the file.
* **"Error writing the file"**: see "What the add-on writes, and when" above.
* **"Checklist file not found"**: the remembered file has moved or been deleted; the file dialog opens so you can choose one.
* **"End of list"** and **"Start of list"**: there is no section further in that direction.
* **"Section reset"**: the current section has been put back to not checked and written.
* **"Copied to clipboard:"** and **"Unable to copy"**: NVDA's own confirmation and refusal after `C`.

## All commands at a glance

Global, working everywhere:

* `NVDA+Alt+PageDown`: next item; twice, first item of the next section.
* `NVDA+Alt+PageUp`: previous item; twice, first item of the previous section.
* `NVDA+Alt+Space`: toggle passed and not checked.
* `NVDA+Alt+I`: read the current item; twice, open the item dialog.
* `NVDA+Alt+O`: arm the command mode for three seconds.

In the command mode, after `NVDA+Alt+O` and releasing:

* `1` passed, `2` failed, `3` blocked, `4` skipped, `5` not checked.
* `O` open a file. `P` section and progress. `R` reset the section. `A` auto-advance on or off. `G` the window. `C` copy a fragment.

In the item dialog: `Ctrl+Enter` saves, `Escape` cancels, Tab moves between the fields.

In the tree of the window: Enter opens the item, `Ctrl+Enter` goes to it and closes the window, `Shift+Enter` gives it the next status. `Escape` closes the window. `Ctrl+Tab` switches the tabs.

## When a command does nothing

Axygen Checklist claims the `NVDA+Alt` prefix. Another add-on may bind the same combination, and nothing tells you so: whichever global plugin NVDA happens to reach first wins, and that order is not guaranteed to survive a restart. The key simply does the wrong thing, or nothing.

The fix is NVDA's own dialog: **Preferences, Input Gestures, category Axygen Checklist**. Deleting a binding there hands the key back to whoever else wants it; adding one gives a command a combination of your choosing. Every command appears in that category with a line on what it does, including the ones that normally live inside the command mode and ship with no key at all, so you can give a direct key to, say, "Opens a checklist file" if you use it often. Only the five status digits are absent: they exist only inside the mode.

The same dialog is the answer if `NVDA+Alt+O` feels wrong under your hands. It was chosen for an NVDA key on Caps Lock; with the NVDA key on Insert a different letter is easier, and you can pick it.

The keys inside the add-on's windows, Tab, Escape, `Ctrl+Enter`, `Shift+Enter`, are ordinary window keys and are not listed in Input Gestures. If `Ctrl+Enter` does nothing in the tree, another global plugin has claimed it, and Input Gestures is again where to look.

## Not in this version yet

This page describes the add-on as a whole, and not all of it is built yet. Walking a checklist works from end to end: opening a file, moving, marking with the key and with the digits, the item dialog with comments, copying fragments, progress, section and full reset, auto-advance, the window with its tree and settings, and resuming after a restart. What is missing sits around that core:

* **Filtering to unchecked items** (`F` in the command mode): due in 0.2.0.
* **A Markdown report of the run** (`E`): due in 1.0.0.
* **Switching between recent checklists by voice** (`N`): due in 1.1.0.

Until 1.0.0 the checklist file format and the set of commands may still change from one release to the next. From 1.0.0 on, neither changes without a major version bump, and an older add-on will refuse to open a file written in a newer format rather than damage it.

## Feedback and source

The source code, the issue tracker and the specification live at [github.com/ruslan-rv-ua/axygen-checklist](https://github.com/ruslan-rv-ua/axygen-checklist).

Copyright (C) 2026 Ruslan Iskov. Distributed under the terms of the GNU General Public License version 2 or later; see COPYING.txt.
