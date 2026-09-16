<#
.SYNOPSIS
	Links this working copy into NVDA's add-ons directory for development.

.DESCRIPTION
	Creates a directory junction from NVDA's add-ons directory to the "addon"
	folder of this repository, so that a running NVDA loads the working copy as
	an ordinary add-on: manifest, compatibility checks and gettext translations
	behave exactly as they will in the packaged .nvda-addon.

	Run "scons" at least once before linking. The manifest is generated, and
	NVDA silently skips any directory whose manifest cannot be read.

	NVDA builds its add-on list at startup, so restart NVDA (control+alt+n)
	after the link is created or removed. Once the add-on is loaded, later code
	changes are picked up by Tools > Reload plugins (NVDA+control+f3).

	See docs/development.md for the full development cycle.

.PARAMETER Name
	Add-on name used for the link. Defaults to addon_name from buildVars.py.

.PARAMETER NvdaConfig
	NVDA user configuration directory. Defaults to %APPDATA%\nvda. Point it at
	<portable copy>\userConfig to keep the daily profile untouched.

.PARAMETER Remove
	Remove the link instead of creating it.

.PARAMETER Force
	Repoint an existing link that targets some other directory.

.EXAMPLE
	powershell -ExecutionPolicy Bypass -File tools\dev-link.ps1

.EXAMPLE
	powershell -ExecutionPolicy Bypass -File tools\dev-link.ps1 -Remove
#>
[CmdletBinding()]
param(
	[string] $Name,
	[string] $NvdaConfig = (Join-Path $env:APPDATA 'nvda'),
	[switch] $Remove,
	[switch] $Force
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$addonDir = Join-Path $repoRoot 'addon'

function Get-AddonNameFromBuildVars {
	$buildVars = Join-Path $repoRoot 'buildVars.py'
	if (-not (Test-Path -LiteralPath $buildVars)) {
		throw "buildVars.py not found in $repoRoot. Pass -Name explicitly."
	}
	$match = Select-String -LiteralPath $buildVars -Pattern 'addon_name\s*=\s*["'']([^"'']+)["'']' |
		Select-Object -First 1
	if (-not $match) {
		throw "addon_name not found in $buildVars. Pass -Name explicitly."
	}
	return $match.Matches[0].Groups[1].Value
}

function Get-LinkTarget([string] $path) {
	$item = Get-Item -LiteralPath $path -Force
	if (-not $item.LinkType) {
		return $null
	}
	$target = $item.Target
	if ($target -is [array]) {
		$target = $target[0]
	}
	return $target
}

function Remove-Link([string] $path) {
	# Delete the reparse point only. Remove-Item on a junction follows it into
	# the target in Windows PowerShell 5.1 and deletes the source files there.
	try {
		[System.IO.Directory]::Delete($path)
	} catch {
		& cmd.exe /c rmdir "$path"
		if ($LASTEXITCODE -ne 0) {
			throw "Failed to remove $path"
		}
	}
}

if (-not $Name) {
	$Name = Get-AddonNameFromBuildVars
}
$addonsDir = Join-Path $NvdaConfig 'addons'
$linkPath = Join-Path $addonsDir $Name

if ($Remove) {
	if (-not (Test-Path -LiteralPath $linkPath)) {
		Write-Host "Nothing to remove: $linkPath does not exist."
		exit 0
	}
	$target = Get-LinkTarget $linkPath
	if (-not $target) {
		throw "$linkPath is a real directory, not a development link. Remove that add-on from NVDA's Add-on Store instead."
	}
	Remove-Link $linkPath
	Write-Host "Removed $linkPath (pointed at $target)."
	Write-Host "Restart NVDA (control+alt+n) to unload the add-on."
	exit 0
}

if (-not (Test-Path -LiteralPath $addonDir)) {
	throw "$addonDir not found. The add-on sources belong in the 'addon' folder of the repository."
}
$manifest = Join-Path $addonDir 'manifest.ini'
if (-not (Test-Path -LiteralPath $manifest)) {
	throw "$manifest is missing. Run 'scons' once to generate it, then link again."
}

if (Test-Path -LiteralPath $linkPath) {
	$target = Get-LinkTarget $linkPath
	if (-not $target) {
		throw "$linkPath already exists as a real directory (an installed add-on?). Remove it in NVDA before linking the working copy."
	}
	if ($target.TrimEnd('\') -ieq $addonDir.TrimEnd('\')) {
		Write-Host "Already linked: $linkPath -> $target"
		exit 0
	}
	if (-not $Force) {
		throw "$linkPath points at $target. Re-run with -Force to repoint it at $addonDir."
	}
	Remove-Link $linkPath
}

if (-not (Test-Path -LiteralPath $addonsDir)) {
	New-Item -ItemType Directory -Path $addonsDir -Force | Out-Null
}
New-Item -ItemType Junction -Path $linkPath -Target $addonDir | Out-Null
Write-Host "Linked $linkPath -> $addonDir"
Write-Host "Restart NVDA (control+alt+n) to load the add-on; after that use NVDA+control+f3 for code changes."
