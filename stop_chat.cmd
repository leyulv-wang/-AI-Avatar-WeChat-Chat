@echo off
setlocal

for %%P in (8000 5173) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r ":%%P .*LISTENING"') do (
    echo Killing process on port %%P PID=%%a
    taskkill /PID %%a /T /F >nul 2>&1
  )
)

echo Ports 8000/5173 have been stopped.
pause
