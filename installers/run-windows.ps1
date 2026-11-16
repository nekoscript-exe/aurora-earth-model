# Windows recipe, not functionally tested on Windows.
param([ValidateSet("auto","cpu","cuda")][string]$Device = "cpu")
$ErrorActionPreference = "Stop"
$AuroraRoot = Split-Path -Parent $PSScriptRoot
Set-Location $AuroraRoot
& "$AuroraRoot/.aurora-venv/Scripts/python.exe" "$AuroraRoot/scripts/doctor.py" --integrity-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$AuroraRoot/.aurora-venv/Scripts/python.exe" "$AuroraRoot/scripts/desktop.py" --device $Device
exit $LASTEXITCODE
