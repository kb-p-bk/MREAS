# install_cli.ps1
# Installs CLI wrappers ('mreas' and 'mre') into ~/.local/bin (which is on PATH)

$ErrorActionPreference = "Stop"
$RepoRoot = (Get-Item $PSScriptRoot).FullName
$LocalBin = Join-Path $HOME ".local\bin"

if (-not (Test-Path $LocalBin)) {
    New-Item -ItemType Directory -Path $LocalBin -Force | Out-Null
}

# 1. mreas.cmd & mre.cmd (for cmd.exe and powershell)
$cmdContent = @"
@echo off
uv --project "$RepoRoot" run mreas %*
"@

$mreCmdContent = @"
@echo off
uv --project "$RepoRoot" run mre %*
"@

Set-Content -Path (Join-Path $LocalBin "mreas.cmd") -Value $cmdContent -Encoding ASCII
Set-Content -Path (Join-Path $LocalBin "mre.cmd") -Value $mreCmdContent -Encoding ASCII

# 2. mreas & mre (bash / sh / git bash wrappers)
$shRepoRoot = $RepoRoot -replace '\\', '/'
$shContent = @"
#!/usr/bin/env sh
uv --project "$shRepoRoot" run mreas "`$@"
"@

$mreShContent = @"
#!/usr/bin/env sh
uv --project "$shRepoRoot" run mre "`$@"
"@

Set-Content -Path (Join-Path $LocalBin "mreas") -Value $shContent -Encoding UTF8
Set-Content -Path (Join-Path $LocalBin "mre") -Value $mreShContent -Encoding UTF8

Write-Host "[SUCCESS] Installed 'mreas' and 'mre' CLI wrappers to $LocalBin"
Write-Host "You can now run 'mreas' or 'mre' from any terminal or directory!"
