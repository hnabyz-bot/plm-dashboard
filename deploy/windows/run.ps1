param([Parameter(Mandatory=$true)][string]$ConfigPath)
$ErrorActionPreference='Stop'
$config=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$repoRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$web=Join-Path $repoRoot 'design_handoff_plm_dashboard'
$server=Join-Path $PSScriptRoot 'dashboard_server.py'
if(!(Test-Path -LiteralPath $config.python_executable -PathType Leaf)){throw 'Configure an existing Python executable'}
if(!$config.source -or !$config.bind_addresses -or !$config.port){throw 'Source, explicit bind addresses and port are required'}
$taskServerArgs=@($server,'--web-root',$web,'--source',[string]$config.source,'--port',[string]$config.port)
foreach($address in $config.bind_addresses){$taskServerArgs+=@('--bind',[string]$address)}
if($config.log_file){$taskServerArgs+=@('--log',[string]$config.log_file)}
& $config.python_executable @taskServerArgs
exit $LASTEXITCODE