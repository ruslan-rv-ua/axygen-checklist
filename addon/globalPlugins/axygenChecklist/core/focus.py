# A part of the Axygen Checklist add-on for NVDA
# Copyright (C) 2026 Ruslan Iskov
# This file is covered by the GNU General Public License version 2 or later.
# See the file COPYING.txt for more details.

"""The field the item dialog opens on, on the side of it that is an identifier.

Section 3.3.1 of docs/requirements.md lets the tester choose which field the
item dialog opens on — the item, the status or the comment — and keeps the
choice in `config.conf`. That preference crosses the boundary between the core
and the shell the way the statuses do (`core.status`), and the cut runs in the
same place: between the identifier and the word.

The identifiers are here. They are what stands in `config.conf`, the same
whatever the interface language; the shell reads the value back and holds it
to one of the three (`preferences.initial_focus`). The words a tester hears
for them are the labels of the fields themselves, interface strings wrapped in
`_()`, and live in the shell (`wording.focus_target_label`).

They are in the core rather than beside the preference for one reason: the
words have no business with `config.conf`. `wording` reaches NVDA through
`gettext` and through nothing else, and three identifiers imported from
`preferences` were the one thing that used to bring `config` in with them.

*"Note"* is deliberately absent — it is missing from most items, so a choice
naming it would mean something other than itself on most of them, and would
need a rule for falling back; these three are always there.
"""

ITEM = "item"
STATUS = "status"
COMMENT = "comment"

#: The three fields the item dialog may open on, in the order they stand in it
#: (section 3.3.1). The choice on the settings tab is built in this order and
#: reads the identifier back from the position picked rather than from the
#: label shown, which would hold in one locale and break in every other.
TARGETS: tuple[str, ...] = (ITEM, STATUS, COMMENT)
