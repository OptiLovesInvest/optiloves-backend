param(
  [string]$WalletList = ".\wallets.txt",
  [string]$OutCsv     = ".\holders.csv",
  [int]$TotalDays     = 0
)
function Get-QuarterDays {
  $now = Get-Date
  $q = [math]::Floor(($now.Month-1)/3)+1
  $end = Get-Date -Year $now.Year -Month (3*$q) -Day 1
  $end = $end.AddMonths(1).AddDays(-1)
  $start = $end.AddMonths(-2).AddDays(1-$end.Day)
  (($end-$start).Days + 1)
}
if ($TotalDays -le 0) { $TotalDays = Get-QuarterDays }

if (-not (Test-Path $WalletList)) { throw "Missing $WalletList" }
$wallets = Get-Content $WalletList | ? { $_ -and -not $_.StartsWith('#') } | % { $_.Trim() } | ? { $_ }
$tokMap = @{}
if (Test-Path ".\tokens.csv") {
  # tokens.csv: wallet,tokens_held
  Import-Csv ".\tokens.csv" | % { $tokMap[$_.wallet.Trim()] = [decimal]$_.tokens_held }
}

"wallet,tokens_held,days_held,total_days" | Set-Content -Encoding UTF8 $OutCsv
foreach($w in $wallets){
  $t = 0
  if ($tokMap.ContainsKey($w)) { $t = $tokMap[$w] }
  Add-Content -Encoding UTF8 $OutCsv ("{0},{1},{2},{3}" -f $w,$t,$TotalDays,$TotalDays)
}