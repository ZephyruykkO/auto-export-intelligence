@echo off
cd /d "%~dp0"
start msedge "file:///%~dp0dashboard/index.html" 2>nul
if errorlevel 1 start chrome "file:///%~dp0dashboard/index.html" 2>nul
if errorlevel 1 start "" "dashboard\index.html"
