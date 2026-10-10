@echo off
cd /d "%~dp0"
py -3 -m cleanmodels
if errorlevel 1 pause
