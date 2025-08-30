# === SAFE HEADER (PS5.1-compatible) ===
param(
  [string]$Mint,
  [int]$Decimals,
  [string]$Wallets = ".\wallets.txt",
  [switch]$DryRun
)

# Fallbacks for env / defaults (avoid ?? for PS5.1)
if (-not $Mint) { $Mint = $env:PAYOUT_MINT }
if (-not $Decimals -or $Decimals -eq 0) {
  if ($env:PAYOUT_DECIMALS) { $Decimals = [int]$env:PAYOUT_DECIMALS } else { $Decimals = 6 }
}
if (-not $Mint) { throw "Provide -Mint <USDC_MINT> or set PAYOUT_MINT" }

# Robust script folder + log path
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptRoot = if ($ScriptPath) { Split-Path -Parent $ScriptPath } else { (Get-Location).Path }
$LogPath    = Join-Path $ScriptRoot "run_log.csv"

# Create CSV header once
if (-not (Test-Path $LogPath)) {
  "ts,wallet,tokens,daysHeld,totalDays,usd,ui_amount,raw_amount,tx,ok,message" | Out-File -Encoding utf8 $LogPath
}

# Invariant number formatting
Add-Type -AssemblyName System.Globalization | Out-Null
$culture = [System.Globalization.CultureInfo]::InvariantCulture

# PS5.1-safe defaults moved OUTSIDE param to avoid parser quirks
$CsvPath = ".\holders.csv"
$RateMs  = 900
# === END SAFE HEADER ===
if (-not $Mint) { throw "Provide -Mint <USDC_MINT>" }
if (-not (Test-Path $CsvPath)) { throw "CSV not found: $CsvPath" }

$rows = Import-Csv -Path $CsvPath
if (-not $rows -or $rows.Count -lt 1) { throw "CSV empty." }

$perToken = 1.50
$decimals = 6
$factor = [math]::Pow(10,$decimals)

if (-not (Test-Path $LogPath)) {
  "ts,wallet,tokens,daysHeld,totalDays,usd,ui_amount,raw_amount,tx,ok,message" | Out-File -Encoding utf8 $LogPath
}

foreach ($r in $rows) {
  $w = $r.wallet.Trim()
  $tokens = [decimal]$r.tokens_held
  $daysHeld = [int]$r.days_held
  $totalDays = [int]$r.total_days; if ($totalDays -le 0) { $totalDays = 1 }

  $usd = [math]::Round($perToken * $tokens * ($daysHeld / $totalDays), 2, [MidpointRounding]::AwayFromZero)
  $ui  = [decimal]::Parse("{0:F6}" -f $usd)
  $raw = [long][math]::Round($ui * $factor, 0, [MidpointRounding]::AwayFromZero)

  $ts = (Get-Date).ToString("s")
  if ($usd -le 0) {
    "$ts,$w,$tokens,$daysHeld,$totalDays,$usd,$ui,$raw,,skip,zero payout" | Out-File -Append -Encoding utf8 $LogPath
    Start-Sleep -Milliseconds $RateMs; continue
  }

  if ($DryRun) {
    "$ts,$w,$tokens,$daysHeld,$totalDays,$usd,$ui,$raw,,dryrun,preview only" | Out-File -Append -Encoding utf8 $LogPath
    Start-Sleep -Milliseconds $RateMs; continue
  }

  try {
    $cmd = "spl-token transfer $Mint $ui $w --fund-recipient --allow-unfunded-recipient --no-wait"
    $res = powershell -NoProfile -Command $cmd 2>&1
    $sig = ($res | Select-String -Pattern 'Signature: (.+)$').Matches.Groups[1].Value
    if (-not $sig) { $sig = ($res | Select-String -Pattern '[A-Za-z0-9]{60,}').ToString() }
    "$ts,$w,$tokens,$daysHeld,$totalDays,$usd,$ui,$raw,$sig,ok," | Out-File -Append -Encoding utf8 $LogPath
  } catch {
    $msg = $_.Exception.Message.Replace(',',';')
    "$ts,$w,$tokens,$daysHeld,$totalDays,$usd,$ui,$raw,,fail,$msg" | Out-File -Append -Encoding utf8 $LogPath
  }

  Start-Sleep -Milliseconds $RateMs
}


