@echo off
setlocal
set "RUNTIME_RUNNER=C:\Users\Ben\Downloads\Lighttowergroupsite\.agent-runtime\scripts\run_agent_runtime.bat"
if not exist "%RUNTIME_RUNNER%" (
  echo [ERROR] Isolated agent runtime is missing. Run setup_agent_runtime.ps1 first.
  exit /b 1
)
call "%RUNTIME_RUNNER%"
exit /b %ERRORLEVEL%
