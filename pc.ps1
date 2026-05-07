param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython (Join-Path $repoRoot "pc.py") @RemainingArgs
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $repoRoot "pc.py") @RemainingArgs
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $repoRoot "pc.py") @RemainingArgs
    exit $LASTEXITCODE
}

Write-Host "Python 3 was not found on PATH."
Write-Host "Install Python 3.10+ and then use one of these launch modes:"
Write-Host ""
Write-Host "  Installed mode:"
Write-Host "    pipx install ."
Write-Host "    pc tui"
Write-Host "    pc gui"
Write-Host ""
Write-Host "  Repo-local mode:"
Write-Host "    python .\pc.py tui"
Write-Host "    python .\pc.py gui"
exit 1
