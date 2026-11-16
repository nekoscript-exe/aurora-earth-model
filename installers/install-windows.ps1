# Recipe only: Windows has not been tested by this distribution workflow.
param([string]$Prefix = "", [string]$Wheelhouse = "")
$ErrorActionPreference = "Stop"
$AuroraRoot = Split-Path -Parent $PSScriptRoot
$AuroraArgs = @("-3.14", "$AuroraRoot/scripts/install.py", "--profile", "cpu")
if ($Prefix) { $AuroraArgs += @("--prefix", $Prefix) }
if ($Wheelhouse) { $AuroraArgs += @("--wheelhouse", $Wheelhouse) }
Write-Warning "Windows installer recipe: not functionally validated on Windows."
& py @AuroraArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
