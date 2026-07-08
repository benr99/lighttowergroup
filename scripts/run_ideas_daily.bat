@echo off
setlocal

REM Light Tower Ideas daily publisher and deployer.
REM First-week safer production target: 3 articles/day from 20 feeds.
REM Increase Count to 10 after several reviewed daily runs.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "scripts\run_ideas_daily_deploy.ps1" -Count 3 -MaxFeeds 20

endlocal
