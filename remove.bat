@echo off

REM === File to remove from git history ===
set FILE=FUTURE_ROADMAP.md

REM === Backup the file ===
copy %FILE% %TEMP%\%FILE%

REM === Remove file from all git history ===
git filter-repo --force --path %FILE% --invert-paths

REM === Restore the file locally (untracked) ===
copy %TEMP%\%FILE% %FILE%