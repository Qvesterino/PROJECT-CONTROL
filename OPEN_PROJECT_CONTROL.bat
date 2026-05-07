@echo off
setlocal
cd /d "%~dp0"

echo Starting PROJECT CONTROL...
echo.
call "%~dp0pc.cmd" gui
if %errorlevel%==0 goto :end

:launch_failed
echo.
echo PROJECT CONTROL could not open the desktop window.
echo Try the text menu instead:
echo   start_menu.bat
echo or:
echo   .\pc.cmd tui
echo or:
echo   python .\pc.py tui
pause

:end
