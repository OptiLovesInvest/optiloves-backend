$ErrorActionPreference = 'Stop'
$ok  = New-Object System.Collections.Generic.List[string]
$bad = New-Object System.Collections.Generic.List[string]
function Pass([string]$m){ Write-Host ("PASS: {0}" -f $m) -ForegroundColor Green; $ok.Add($m) }
function Fail([string]$m){ Write-Host ("FAIL: {0}" -f $m) -ForegroundColor Red;   $bad.Add($m) }

$cfgPath = "C:\Users\ruben\Documents\optiloves-backend\chain.config.json"
$cfgText = Get-Content -Raw $cfgPath
$cfgText = $cfgText -replace '^\uFEFF',''
$cfg = $cfgText | ConvertFrom-Json
$rpc = $cfg.rpc
$mint = $cfg.mint
$treasury = $cfg.treasury
$capUi = [double]($cfg.capUi)

function Rpc($m,$p=@()){
  $b = @{jsonrpc="2.0"; id=1; method=$m; params=$p} | ConvertTo-Json -Compress
  Invoke-RestMethod -Uri $rpc -Method Post -Body $b -ContentType 'application/json'
}

try {
  $ver = Rpc "getVersion"
  if ($ver.result) { Pass ("RPC up: {0}" -f $ver.result.'solana-core') } else { Fail "getVersion failed" }

  $hl = Rpc "getHealth"
  if ($hl.result -eq 'ok') { Pass "Cluster health OK" } else { Fail "Cluster not healthy" }

  $ep = Rpc "getEpochInfo"
  if ($ep.result) { Pass ("Epoch {0} Slot {1}" -f $ep.result.epoch, $ep.result.absoluteSlot) }

  if ($treasury -and $treasury -notmatch '^<PASTE') {
    $bal = Rpc "getBalance" @($treasury)
    $lam = $bal.result.value
    $sol = [math]::Round($lam/1e9, 4)
    if ($lam -ge 1000000) { Pass ("Treasury SOL: {0}" -f $sol) } else { Fail ("Low SOL ({0})" -f $sol) }
  } else { Fail "Treasury not set" }

  if ($mint -and $mint -notmatch '^<PASTE') {
    $mi = Rpc "getAccountInfo" @($mint, @{encoding="jsonParsed"; commitment="confirmed"})
    if (-not $mi.result.value) { throw "Mint not found" }
    $info = $mi.result.value.data.parsed.info
    Pass ("Mint decimals: {0}" -f $info.decimals)

    $sup = Rpc "getTokenSupply" @($mint)
    $uiSupply = [double]$sup.result.value.uiAmount
    Pass ("Supply: {0} (ui: {1})" -f $sup.result.value.amount, $sup.result.value.uiAmountString)

    if ($capUi -gt 0) {
      if ($uiSupply -le $capUi) { Pass ("Supply <= capUi ({0} <= {1})" -f $uiSupply, $capUi) }
      else { Fail ("Supply EXCEEDS capUi ({0} > {1})" -f $uiSupply, $capUi) }
    } else {
      Pass "No capUi set - skipping cap check"
    }

    if ($treasury -and $treasury -notmatch '^<PASTE') {
      $tas = Rpc "getTokenAccountsByOwner" @($treasury, @{mint=$mint}, @{encoding="jsonParsed"})
      $ui = 0.0
      foreach($a in $tas.result.value){ $ui += [double]$a.account.data.parsed.info.tokenAmount.uiAmount }
      Pass ("Treasury tokens: {0}" -f $ui)
    }
  } else {
    Fail "Mint not set"
  }
}
catch {
  Fail ("RPC error: {0}" -f $_.Exception.Message)
}

Write-Host ""
Write-Host "==== SUMMARY ====" -ForegroundColor Cyan
if ($ok.Count)  { Write-Host ("PASS: " + ($ok -join " | ")) -ForegroundColor Green }
if ($bad.Count) { Write-Host ("FAIL: " + ($bad -join " | ")) -ForegroundColor Red }
if ($bad.Count -eq 0) { Write-Host "All chain checks passed." -ForegroundColor Green } else { Write-Host "Review FAIL items." -ForegroundColor Yellow }# ---- Immutable mint checks (auto-added) ----
$mi = Rpc "getAccountInfo" @($mint, @{encoding="jsonParsed";commitment="confirmed"})
if (-not $mi.result.value) { Fail "Mint not found" } else {
  $info = $mi.result.value.data.parsed.info
  if ($null -eq $info.mintAuthority)  { Pass "Mint authority: null" }  else { Fail ("Mint authority set: {0}" -f $info.mintAuthority) }
  if ($null -eq $info.freezeAuthority){ Pass "Freeze authority: null"} else { Fail ("Freeze authority set: {0}" -f $info.freezeAuthority) }
}
if ($cfg.capUi) {
  $sup = Rpc "getTokenSupply" @($mint)
  $uiSupply = [double]$sup.result.value.uiAmount
  if ($uiSupply -eq [double]$cfg.capUi) { Pass ("Supply == capUi ({0})" -f $uiSupply) }
  else { Fail ("Supply != capUi (supply={0}, cap={1})" -f $uiSupply,$cfg.capUi) }
}
