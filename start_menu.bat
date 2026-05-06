@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 pc.py ui
    goto :end
)

where python >nul 2>&1
if %errorlevel%==0 (
    python pc.py ui
    goto :end
)

echo Python 3 was not found in PATH.
echo Install Python 3.10+ and then run this file again.
pause

:end
