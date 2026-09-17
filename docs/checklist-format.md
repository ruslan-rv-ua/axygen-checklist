# Writing a checklist for Axygen Checklist

[Axygen Checklist](https://github.com/ruslan-rv-ua/axygen-checklist) is an NVDA
add-on for testers who work by ear. It walks a checklist with global hotkeys
while the system focus stays in the application under test, and it records the
outcome of every item back into the same file it read.

A checklist is a plain JSON file. This page is how to write one, and it is
addressed to whoever does — in practice, a coding agent working inside the
project under test.

The normative description of the format is section 2 of
[`requirements.md`](requirements.md), which is in Ukrainian. This page says the
same thing in English, and adds the part a format description does not cover:
the file has two authors, and you are only one of them.

The machine-readable form is
[`checklist-v1.schema.json`](checklist-v1.schema.json) (JSON Schema 2020-12),
published at:

```
https://raw.githubusercontent.com/ruslan-rv-ua/axygen-checklist/main/docs/checklist-v1.schema.json
```

## A checklist in full

Every field the format has, in one file:

```json
{
  "$schema": "https://raw.githubusercontent.com/ruslan-rv-ua/axygen-checklist/main/docs/checklist-v1.schema.json",
  "format_version": 1,
  "checklist_name": "Accessibility of the settings dialog",
  "sections": [
    {
      "section_name": "Controls",
      "items": [
        {"id": 1, "text": "Every button has an accessible name"},
        {"id": 2, "text": "Focus is visible on entry fields", "note": "Try both Tab and Shift+Tab"},
        {"id": 3, "text": "Form fields have labels", "status": "failed", "comment": "The Phone field has no label"}
      ]
    },
    {
      "section_name": "Keyboard navigation",
      "items": [
        {"id": 4, "text": "Tab wraps inside the modal dialog", "status": "passed"}
      ]
    }
  ]
}
```

Items 1 and 2 carry no `status`. That is what an item looks like before anyone
has checked it, and it reads as `"pending"`.

## Fields

| Field | Where | Type | Required | Notes |
|---|---|---|---|---|
| `$schema` | top level | string | no | URL of the schema. The add-on never reads or writes it. |
| `format_version` | top level | integer | no | `1`. Absent means `1`. |
| `checklist_name` | top level | string | **yes** | Name of the checklist. |
| `sections` | top level | array | **yes** | At least one. Flat lists without sections are not supported. |
| `section_name` | section | string | **yes** | Name of the section. |
| `items` | section | array | **yes** | May be empty. |
| `id` | item | integer | **yes** | Unique within the file. See [Identifiers](#identifiers). |
| `text` | item | string | **yes** | What is spoken when the tester reaches the item. |
| `status` | item | string | no | One of the five below. Absent means `"pending"`. |
| `note` | item | string | no | A hint from the author, spoken right after `text`. |
| `comment` | item | string | no | The tester's conclusion. Not yours to write. |

Unknown fields are allowed. The add-on ignores them when reading and keeps them
when it rewrites the file, so extra data you attach to an item survives the run.

`checklist_name`, `section_name`, `text`, `note` and `comment` are content, not
interface. Write them in whatever language the checklist is for; nothing ever
translates them.

## Statuses

| `status` | Meaning |
|---|---|
| `"pending"` | not checked yet |
| `"passed"` | checked, works |
| `"failed"` | checked, does not work |
| `"blocked"` | could not be checked |
| `"skipped"` | deliberately not checked |

These five strings are identifiers, not text. They stay exactly as written in
every interface language, so a checklist saved by a Ukrainian NVDA is readable
by an English one and back. Any other value makes the add-on refuse the whole
file.

## Who owns which fields

The file has two authors, and mixing them up is the one way to do real damage.

| Written by you, the author | Written by the tester, through the add-on |
|---|---|
| `checklist_name`, `section_name` | `status` |
| `id`, `text`, `note` | `comment` |

`note` is a hint that exists **before** the check; `comment` is a conclusion
that exists **after** it. They are never interchangeable, and the add-on offers
no way to edit a `note` — notes are edited here, in the JSON.

Everything in the right-hand column is the result of somebody sitting down and
working through the checklist by ear. The add-on rewrites the entire file the
moment a status changes, so the copy on disk is the live state of a run that
may be happening right now.

### Editing a checklist that has already been used

This is the common request — *"update the checklist, we shipped three new
features"* — and the naive way to serve it destroys an hour of someone's work
while leaving a perfectly valid file behind. Neither the schema nor the add-on
will catch that.

* **Read the file immediately before you write it**, and write back what you
  read. Do not regenerate it from your own idea of what it should contain, and
  do not work from a copy you loaded earlier in the session.
* **Preserve every `status` and `comment` verbatim**, including on items you are
  not otherwise touching. Never invent either one: a `status` you wrote is a
  claim that somebody tested something, and nobody did.
* **Add items, do not renumber them.** See [Identifiers](#identifiers).
* **Removing an item throws away its result.** If an item is obsolete, say so
  and let a human decide; the add-on has no undo.

If what you want is a fresh run of an existing checklist, do not blank the
statuses by hand — the add-on has a *Reset all progress* command for exactly
that, and it is the tester's call to use it.

### Identifiers

`id` is unique within the file, and no behaviour of the add-on reads it: the
add-on tracks position by section and item index. That makes `id` look free.
It is not.

`id` exists so that an item stays the same item across edits of the file. Keep
it stable:

* new items take the next unused number, counting across the whole file;
* existing items keep the number they have;
* gaps left by deleted items stay as gaps.

An agent that renumbers fifty items to insert one makes the diff unreviewable
today, and breaks the run history that a future version of the add-on will hang
off these numbers.

## Writing items that work by ear

The format will take anything you put in `text`. What the tester gets is a
sentence read aloud while their hands are in another application and their eyes
are doing nothing at all. That is a narrow channel, and it changes what a good
item looks like.

**One item is one action and the result you expect.** An item that names only a
subject leaves the tester to invent both the procedure and the standard:

```json
{"id": 1, "text": "Check minimising to the tray"}
```

Check it how, and how would they know it worked? Written for the ear, the same
ground becomes a short run of items that each say what to do and what should
happen:

```json
[
  {"id": 1, "text": "Start the app with --minimize. The window may flash and vanish into the tray", "note": "That flash is expected"},
  {"id": 2, "text": "Press Ctrl+Shift+H - the window comes back"},
  {"id": 3, "text": "The screen reader announces the window and whatever holds focus. Silence here means the bug is alive"}
]
```

**Put preconditions in a first section of their own.** Restarting the screen
reader, closing another copy of the application, turning a setting on - these
are not checks, they are the state the run needs in order to mean anything. A
tester who discovers at item twelve that the first eleven ran against the wrong
state has lost the run, not an item.

**Write sections that stand alone, and order them by what matters.** Runs get
interrupted, and the tester stops where they stop. If the first two sections
carry the substance of what changed, an interrupted run is still worth reading;
if the substance is spread evenly over nine, it is not.

**Say so when correct behaviour looks like a bug.** Anything startling but
intended - a window that flashes before it hides, a pause, a sound - belongs in
`note`. Without it you get a filed defect and a wasted afternoon. `note` is
spoken right after the item, which is exactly when it is needed.

Keep the writing plain. `text` and `note` are spoken, not rendered: emphasis
markers and backticks buy nothing, and depending on the reader's punctuation
settings they may be read out.

## Validation

Put `$schema` at the top of the file. Editors and agents pick it up with no
further setup, and the add-on ignores it.

The schema is deliberately no stricter than the add-on: it permits everything
the add-on will load, including the unknown fields the add-on promises to keep.
So it will not catch a misspelled optional key. Writing

```json
{"id": 7, "text": "Menu opens with F10", "stauts": "passed"}
```

leaves you with an item that is `"pending"` and an extra field nobody reads —
valid against the schema, wrong in the file. Spell the field names from the
table above exactly.

Two things the schema cannot check at all:

* **Uniqueness of `id`.** The identifiers live in `items` inside `sections`, and
  JSON Schema has no way to state uniqueness across that. Check it yourself.
* **Stability of `id`.** That is a property of two versions of a file rather
  than of one, so nothing can check it. It is on you.

### When the add-on refuses a file

Validation happens once, when the file is loaded, and it is all or nothing: any
breach and the checklist does not open. If the tester did not open the file by
hand, all they get is four spoken words, and then they have to come find you.

A file is refused when a required field is missing or has the wrong type, when
`sections` is empty, when two items share an `id`, or when `status` holds
anything outside the five values. An unrecognised `status` is fatal on purpose
rather than being quietly read as `"pending"`: the add-on rewrites the whole
file on the first change, so a quiet fix would erase real results permanently.

`format_version` is the one case with a message of its own. A number higher
than the add-on knows means the file comes from a newer version, and the add-on
says so instead of blaming the file. The schema is pinned to version 1 by name
for the same reason: when `format_version: 2` exists there will be a
`checklist-v2.schema.json` beside this one, and files written for version 1 go
on validating against version 1 forever.

## Paste this into your `AGENTS.md`

If checklists get written in this project regularly, drop this block into the
project's `AGENTS.md` or `CLAUDE.md`. It is the minimum an agent needs in order
not to do damage; everything else is one link away.

````markdown
## Test checklists

Checklists in this project are JSON files for the
[Axygen Checklist](https://github.com/ruslan-rv-ua/axygen-checklist) NVDA add-on.
Format: https://github.com/ruslan-rv-ua/axygen-checklist/blob/develop/docs/checklist-format.md

```json
{
  "$schema": "https://raw.githubusercontent.com/ruslan-rv-ua/axygen-checklist/main/docs/checklist-v1.schema.json",
  "format_version": 1,
  "checklist_name": "What is being tested",
  "sections": [
    {"section_name": "Group", "items": [
      {"id": 1, "text": "One thing to check"},
      {"id": 2, "text": "Another one", "note": "Hint for the tester"}
    ]}
  ]
}
```

* You write `checklist_name`, `section_name`, `id`, `text` and `note`.
* One item is one action plus the result you expect; preconditions go in a
  first section of their own.
* `status` (`pending` / `passed` / `failed` / `blocked` / `skipped`) and
  `comment` belong to the tester and are written by the add-on. When editing an
  existing checklist, re-read the file first and preserve both verbatim. Never
  invent them.
* `id` is unique per file and **never renumbered**: new items take the next
  unused number, existing ones keep theirs.
* Keep `$schema` in the file.
````
