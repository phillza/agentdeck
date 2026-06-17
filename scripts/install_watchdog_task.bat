@echo off
REM Install a Windows Task Scheduler entry that runs the agentdeck watchdog
REM every minute. The watchdog restarts the server if the port stops responding.
setlocal
cd /d "%~dp0\.."
python scripts\agentdeck_watchdog.py --install-task
endlocal
