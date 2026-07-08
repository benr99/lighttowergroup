@echo off
setlocal

REM Light Tower Ideas daily publisher.
REM First-week safer production target: 3 articles/day from 20 feeds.
REM Increase --count to 10 after several reviewed daily runs.

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\ideas_daily_agent.py" --publish --count 3 --max-feeds 20
) else (
  python "scripts\ideas_daily_agent.py" --publish --count 3 --max-feeds 20
)

endlocal
