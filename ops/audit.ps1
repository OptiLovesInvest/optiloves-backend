# ops/audit.ps1 — snapshot + zip + hash
$RPC='https://api.mainnet-beta.solana.com'
$Mint='5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9'
$USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
$Treasury='97q1RGj9fwXtggKGru7RjHRr74z3k89kVFNTks5WCKq2'
$Test='CnyoYEQBgamz3BSRHMdBuQEvt3TnqSwQHZKi6aWXYcyb'
function Rpc($m,$p){(Invoke-WebRequest -Method Post -Uri $RPC -ContentType 'application/json' -Body (@{jsonrpc='2.0';id=1;method=$m;params=$p}|ConvertTo-Json -Compress)).Content|ConvertFrom-Json}
$TreasuryATA=(spl-token address --verbose --token $Mint --owner $Treasury | sls 'Associated token address').ToString().Split(':')[-1].Trim()
$TestATA    =(spl-token address --verbose --token $Mint --owner $Test     | sls 'Associated token address').ToString().Split(':')[-1].Trim()
$TreasuryUSDC=(spl-token address --verbose --token $USDC --owner $Treasury | sls 'Associated token address').ToString().Split(':')[-1].Trim()
$TestUSDC    =(spl-token address --verbose --token $USDC --owner $Test     | sls 'Associated token address').ToString().Split(':')[-1].Trim()
(Rpc 'getAccountInfo' @($Mint,@{encoding='jsonParsed'})).result | ConvertTo-Json -Depth 20 | Out-File .\mint-state.json -Encoding utf8
(Rpc 'getTokenAccountBalance' @($TreasuryATA,@{commitment='finalized'})).result | ConvertTo-Json | Out-File .\opti-treasury.json
(Rpc 'getTokenAccountBalance' @($TestATA,@{commitment='finalized'})).result     | ConvertTo-Json | Out-File .\opti-test.json
(Rpc 'getTokenAccountBalance' @($TreasuryUSDC,@{commitment='finalized'})).result| ConvertTo-Json | Out-File .\usdc-treasury.json
(Rpc 'getTokenAccountBalance' @($TestUSDC,@{commitment='finalized'})).result    | ConvertTo-Json | Out-File .\usdc-test.json
$zip = ".\mainnet-audit-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
Compress-Archive -Force -Path .\mint-state.json,.\opti-*.json,.\usdc-*.json,.\mainnet-proof.txt -DestinationPath $zip
(Get-FileHash $zip -Algorithm SHA256) | Format-List
