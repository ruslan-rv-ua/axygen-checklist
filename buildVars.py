# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries, SpeechDictionaries

# Since some strings in `addon_info` are translatable,
# we need to include them in the .po files.
# Gettext recognizes only strings given as parameters to the `_` function.
# To avoid initializing translations in this module we simply import a "fake" `_` function
# which returns whatever is given to it as an argument.
from site_scons.site_tools.NVDATool.utils import _

# Add-on information variables
addon_info = AddonInfo(
	# add-on Name/identifier, internal for NVDA
	addon_name="axygenChecklist",
	# Add-on summary/title, usually the user visible name of the add-on
	# Translators: Summary/title for this add-on
	# to be shown on installation and add-on information found in add-on store
	addon_summary=_("Axygen Checklist"),
	# Add-on description
	# Translators: Long description to be shown for this add-on on add-on information from add-on store
	addon_description=_("""Walk a test checklist with global commands while the system focus stays in the application under test.
Items are marked passed, failed or skipped, commented and read back by speech, without ever leaving the window being tested.
Checklists are plain JSON files that record the result of the run."""),
	# version
	# Kept at the "not yet released" sentinel on develop; release branches set the real number.
	addon_version="0.0.0",
	# Brief changelog for this version
	# Translators: what's new content for the add-on version to be shown in the add-on store
	addon_changelog=_("""First development version."""),
	# Author(s)
	addon_author="Ruslan Iskov <ruslan.rv.ua@gmail.com>",
	# URL for the add-on documentation support
	addon_url="https://github.com/ruslan-rv-ua/axygen-checklist",
	# URL for the add-on repository where the source code can be found
	addon_sourceURL="https://github.com/ruslan-rv-ua/axygen-checklist",
	# Documentation file name
	addon_docFileName="readme.html",
	# Minimum NVDA version supported.
	# 2025.1 is the first version that has every API the specification relies on:
	# `gui.message.displayDialogAsModal` landed in 2023.3, `gui.blockAction` earlier
	# still, and `gui.message.MessageDialog` — the confirmation dialog of section 3.2.2
	# and section 5 — in 2025.1, the release that also deprecated `gui.messageBox`.
	addon_minimumNVDAVersion="2025.1.0",
	# Last NVDA version supported/tested.
	addon_lastTestedNVDAVersion="2025.3.0",
	# Add-on update channel (default is None, denoting stable releases,
	# and for development releases, use "dev".)
	addon_updateChannel=None,
	# Add-on license such as GPL 2
	addon_license="GPL v2",
	# URL for the license document the ad-on is licensed under
	addon_licenseURL="https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
)

# Define the python files that are the sources of your add-on.
# Recursive on purpose: the add-on has sub-packages (`core/`, see
# docs/development.md), and without `**` editing one of them would not make
# scons rebuild the `.nvda-addon`, nor reach `scons pot` through `i18nSources`.
pythonSources: list[str] = ["addon/globalPlugins/axygenChecklist/**/*.py"]

# Files that contain strings for translation. Usually your python sources
i18nSources: list[str] = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
# Patterns are matched with pathlib.Path.match, which compares from the right.
# `__pycache__/*`: NVDA compiles the add-on while it runs from the development link
# (see docs/development.md), leaving bytecode of its own Python version in the source tree.
# `*.po`: only the compiled `.mo` is read at runtime.
excludedFiles: list[str] = ["__pycache__/*", "*.po"]

# Base language for the NVDA add-on
# Interface strings are written in English (see docs/requirements.md, section 6);
# Ukrainian ships as a translation catalogue.
baseLanguage: str = "en"

# Markdown extensions for add-on documentation
markdownExtensions: list[str] = []

# Custom braille translation tables
brailleTables: BrailleTables = {}

# Custom speech symbol dictionaries
symbolDictionaries: SymbolDictionaries = {}

# Custom speech dictionaries (distinct from symbol dictionaries above)
speechDictionaries: SpeechDictionaries = {}
