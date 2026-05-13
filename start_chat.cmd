@echo off
cd /d %~dp0
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start_chat.ps1"
pause
