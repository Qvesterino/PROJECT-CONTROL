@echo off
setlocal
cd /d "%~dp0"

echo Starting PROJECT CONTROL...
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 gui.py
    if %errorlevel%==0 goto :end
    goto :launch_failed
)

where python >nul 2>&1
if %errorlevel%==0 (
    python gui.py
    if %errorlevel%==0 goto :end
    goto :launch_failed
)

echo Python 3 was not found in PATH.
echo Install Python 3.10+ and try again.
echo.
echo After Python is installed, run this file again:
echo   OPEN_PROJECT_CONTROL.bat
pause
goto :end

:launch_failed
echo.
echo PROJECT CONTROL could not open the desktop window.
echo Try the text menu instead:
echo   start_menu.bat
echo or:
echo   python pc.py tui
pause

:end
