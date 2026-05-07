@echo off
setlocal
cd /d "%~dp0"

call "%~dp0pc.cmd" gui
if %errorlevel% neq 0 pause
