@echo off
setlocal
cd /d "%~dp0"
"C:\Users\Ben\AppData\Local\Programs\Python\Python313\python.exe" agent_runtime.py >> agent_run.log 2>&1
exit /b %ERRORLEVEL%
