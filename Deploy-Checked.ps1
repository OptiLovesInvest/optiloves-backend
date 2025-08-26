$ErrorActionPreference = 'Stop'

# 1) Chain preflight (mirror to console + capture in $L)
$null = & powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\ruben\Documents\optiloves-backend\Verify-Chain.ps1' |
  Tee-Object -Variable L

if ($L -match '^FAIL:' -or $L -match 'FAIL items') {
  throw 'Chain verifier failed. Aborting deploy.'
}
Write-Host "Preflight OK." -ForegroundColor Green

# 2) Frontend build + deploy (prebuilt preserves .env.local)
Set-Location 'C:\Users\ruben\Documents\Optiloves_Invest_MVP_with_backend\frontend'
npx vercel build
npx vercel deploy --prebuilt --prod -y