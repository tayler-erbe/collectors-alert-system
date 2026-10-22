@echo off
rem Keeps the alert loop running: restarts it 30 s after any exit. Started at logon by the scheduled task.
cd /d %~dp0
:loop
python -X utf8 -u -m alert.main >> data\alert.log 2>&1
timeout /t 30 /nobreak >nul
goto loop
