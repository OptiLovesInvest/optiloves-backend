# ops/smoke.ps1 — quick mainnet sanity
$RPC='https://api.mainnet-beta.solana.com'
$Mint='5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9'
$USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
$Treasury='97q1RGj9fwXtggKGru7RjHRr74z3k89kVFNTks5WCKq2'
$Test=(solana address).Trim()
function Rpc($m,$p){(Invoke-WebRequest -Method Post -Uri $RPC -ContentType 'application/json' -Body (@{jsonrpc='2.0';id=1;method=$m;params=$p}|ConvertTo-Json -Compress)).Content|ConvertFrom-Json}
$TreasuryATA=(spl-token address --verbose --token $Mint --owner $Treasury | sls 'Associated token address').ToString().Split(':')[-1].Trim()
$TestATA    =(spl-token address --verbose --token $Mint --owner $Test     | sls 'Associated token address').ToString().Split(':')[-1].Trim()
"OPTI (treasury/test): " + (Rpc 'getTokenAccountBalance' @($TreasuryATA,@{commitment='finalized'})).result.value.uiAmountString + " / " + (Rpc 'getTokenAccountBalance' @($TestATA,@{commitment='finalized'})).result.value.uiAmountString
$TreasuryUSDC=(spl-token address --verbose --token $USDC --owner $Treasury | sls 'Associated token address').ToString().Split(':')[-1].Trim()
$TestUSDC    =(spl-token address --verbose --token $USDC --owner $Test     | sls 'Associated token address').ToString().Split(':')[-1].Trim()
"USDC (treasury/test): " + (Rpc 'getTokenAccountBalance' @($TreasuryUSDC,@{commitment='finalized'})).result.value.uiAmountString + " / " + (Rpc 'getTokenAccountBalance' @($TestUSDC,@{commitment='finalized'})).result.value.uiAmountString
spl-token display $Mint | findstr /i "Authority Supply Decimals"
