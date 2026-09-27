@echo off
setlocal

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "LOCAL_BIN=%USERPROFILE%\.local\bin"

if not exist "%LOCAL_BIN%" mkdir "%LOCAL_BIN%"

echo @echo off > "%LOCAL_BIN%\mreas.cmd"
echo uv --project "%REPO_ROOT%" run mreas %%* >> "%LOCAL_BIN%\mreas.cmd"

echo @echo off > "%LOCAL_BIN%\mre.cmd"
echo uv --project "%REPO_ROOT%" run mre %%* >> "%LOCAL_BIN%\mre.cmd"

echo [SUCCESS] Installed 'mreas' and 'mre' CLI wrappers to %LOCAL_BIN%
echo You can now run 'mreas' or 'mre' from any terminal or directory!
