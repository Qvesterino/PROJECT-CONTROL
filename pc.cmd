@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" pc.py %*
    exit /b %errorlevel%
)

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 pc.py %*
    exit /b %errorlevel%
)

where python >nul 2>&1
if %errorlevel%==0 (
    python pc.py %*
    exit /b %errorlevel%
)

echo Python 3 was not found on PATH.
echo Install Python 3.10+ and then use one of these launch modes:
echo.
echo   Installed mode:
echo     pipx install .
echo     pc tui
echo     pc gui
echo.
echo   Repo-local mode:
echo     .\pc.cmd tui
echo     .\pc.cmd gui
echo     python .\pc.py tui
echo     python .\pc.py gui
exit /b 1
