@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Verify-Chain-Gate.ps1"
if errorlevel 1 (
  echo [pre-push] Chain verifier failed. Aborting push.
  exit /b 1
)
exit /b 0