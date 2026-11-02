[CmdletBinding()]
param([ValidateSet('basis','xagent-producers')][string]$Mode,
 [string]$CodeRoot='C:\actions-runner\qrds-local-shadow\code_canonical',
 [string]$RuntimeRepo='C:\actions-runner\qrds-local-shadow\runtime_canonical',
 [string]$Python='C:\Users\jsard\AppData\Local\Programs\Python\Python312\python.exe',
 [switch]$ValidateOnly)
$ErrorActionPreference='Stop'
$mutex=New-Object System.Threading.Mutex($false,('Global\QRDS_FACTORY_SOURCE_'+$Mode))
$held=$false
try {
 try {$held=$mutex.WaitOne(0)} catch [System.Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){Write-Output 'SOURCE_DELIVERY_ALREADY_RUNNING';exit 0}
 $spool=Join-Path $env:LOCALAPPDATA ('QRDS_FACTORY_SOURCE_DELIVERY\'+$Mode)
 $arguments=@('-m','gate_btc_factory.prospective_local_operations','--mode',$Mode,'--runtime-repo',$RuntimeRepo,'--spool',$spool)
 if($ValidateOnly){$arguments+='--validate-only'}
 Push-Location (Join-Path $CodeRoot 'tools')
 try {& $Python @arguments;if($LASTEXITCODE -ne 0){throw 'SOURCE_DELIVERY_FAILED'}} finally {Pop-Location}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
