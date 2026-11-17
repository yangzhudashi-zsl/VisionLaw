param(
    [string]$CondaExe = 'C:\anaconda3\Scripts\conda.exe',
    [string]$EnvPrefix = '',
    [string]$PipIndex = 'https://pypi.org/simple'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
if (-not $EnvPrefix) { $EnvPrefix = Join-Path $ProjectRoot '.envs\visionlaw' }
$PythonExe = Join-Path $EnvPrefix 'python.exe'
if (-not (Test-Path -LiteralPath $PythonExe)) {
    & $CondaExe create --prefix $EnvPrefix python=3.10 pip -y --override-channels -c https://repo.anaconda.com/pkgs/main
    if ($LASTEXITCODE -ne 0) { throw 'Conda environment creation failed.' }
}
& $PythonExe -m pip install --index-url $PipIndex -r (Join-Path $PSScriptRoot 'requirements-tools.txt')
if ($LASTEXITCODE -ne 0) { throw 'Configuration-tool dependency installation failed.' }
& $PythonExe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency metadata check failed.' }
Write-Host "Local configuration environment ready: $PythonExe"
Write-Host 'Upstream runtime requires Linux. No training, simulation, rendering or API call was performed.'
