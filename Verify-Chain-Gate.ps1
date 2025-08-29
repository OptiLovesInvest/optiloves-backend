$ErrorActionPreference='Stop'
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ruben\Documents\optiloves-backend\Verify-Chain.ps1" 2>&1 | Tee-Object -Variable L
# Fail if verifier prints any FAIL or if PowerShell returned non-zero
if ($LASTEXITCODE -ne 0 -or ($L -match '^FAIL:' -or $L -match 'FAIL items')) { exit 1 } else { exit 0 }